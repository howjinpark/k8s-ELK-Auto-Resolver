# PostgreSQL 데이터베이스 운영 가이드

## 🔐 데이터베이스 접속 방법

### 기본 접속
```bash
# PostgreSQL 사용자로 접속
sudo -u postgres psql elk_resolver

# 또는 직접 접속 (비밀번호 입력)
psql -h localhost -U postgres -d elk_resolver
```

### 연결 테스트
```bash
# 서비스 상태 확인
sudo systemctl status postgresql

# 연결 테스트
sudo -u postgres psql elk_resolver -c "SELECT version();"

# 데이터베이스 목록
sudo -u postgres psql -l
```

## 📋 테이블 구조 및 조회

### 전체 테이블 목록
```sql
-- psql 접속 후 실행
\dt

-- 또는 SQL로 조회
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```

### 테이블별 상세 구조
```sql
-- 각 테이블의 컬럼 정보
\d error_logs
\d solutions  
\d execution_history
\d error_patterns
\d system_status

-- 또는 SQL로 조회
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'error_logs';
```

## 🔍 에러 로그 조회 (error_logs)

### 기본 조회 명령어
```sql
-- 최근 10개 에러 로그
SELECT 
    id, 
    error_type, 
    LEFT(error_message, 50) as message_preview,
    source_system,
    severity,
    created_at 
FROM error_logs 
ORDER BY created_at DESC 
LIMIT 10;

-- 특정 에러 타입 조회
SELECT * FROM error_logs 
WHERE error_type = 'configuration' 
ORDER BY created_at DESC;

-- 특정 시스템의 에러
SELECT * FROM error_logs 
WHERE source_system LIKE '%worker-1%' 
ORDER BY created_at DESC;

-- 특정 시간 범위의 에러
SELECT * FROM error_logs 
WHERE created_at >= NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

### 에러 통계 조회
```sql
-- 에러 타입별 통계
SELECT 
    error_type, 
    COUNT(*) as total_count,
    COUNT(DISTINCT source_system) as affected_systems,
    MIN(created_at) as first_occurrence,
    MAX(created_at) as last_occurrence
FROM error_logs 
GROUP BY error_type 
ORDER BY total_count DESC;

-- 시간대별 에러 발생 패턴
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as error_count
FROM error_logs 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;

-- 심각도별 통계
SELECT 
    severity,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM error_logs), 2) as percentage
FROM error_logs 
GROUP BY severity
ORDER BY count DESC;
```

### 에러 상세 정보 조회
```sql
-- 특정 에러의 전체 정보 (JSON 포함)
SELECT 
    id,
    error_type,
    error_message,
    source_system,
    severity,
    stack_trace,
    raw_log_data,
    created_at
FROM error_logs 
WHERE id = 1;

-- 원시 로그 데이터의 특정 필드 추출
SELECT 
    id,
    error_message,
    raw_log_data->>'program' as program,
    raw_log_data->'host'->>'name' as host_name
FROM error_logs 
WHERE raw_log_data->>'program' = 'kernel'
LIMIT 5;
```

## 🛠️ 해결책 조회 (solutions)

### 기본 해결책 조회
```sql
-- 모든 해결책 목록
SELECT 
    id,
    solution_type,
    LEFT(solution_description, 100) as description,
    success_rate,
    execution_count,
    last_success_at,
    created_at
FROM solutions
ORDER BY success_rate DESC, execution_count DESC;

-- 성공률이 높은 해결책
SELECT 
    s.id,
    s.solution_type,
    s.solution_description,
    s.success_rate,
    s.execution_count,
    el.error_type
FROM solutions s
JOIN error_logs el ON s.error_hash = el.hash_signature
WHERE s.success_rate > 50
ORDER BY s.success_rate DESC;

-- 특정 에러 타입의 해결책
SELECT 
    s.*,
    el.error_type,
    el.error_message
FROM solutions s
JOIN error_logs el ON s.error_hash = el.hash_signature
WHERE el.error_type = 'configuration';
```

### 해결책 명령어 조회
```sql
-- 해결책의 명령어 상세보기 (JSON 파싱)
SELECT 
    id,
    solution_type,
    solution_commands,
    jsonb_array_length(solution_commands) as command_count
FROM solutions
WHERE id = 1;

-- 특정 명령어 타입 검색
SELECT 
    id,
    solution_type,
    cmd.value->>'command' as command,
    cmd.value->>'description' as description
FROM solutions s,
     jsonb_array_elements(s.solution_commands) cmd
WHERE cmd.value->>'type' = 'kubectl';
```

## 📊 실행 이력 조회 (execution_history)

### 실행 결과 조회
```sql
-- 최근 실행 이력
SELECT 
    eh.id,
    el.error_type,
    s.solution_type,
    eh.execution_status,
    eh.execution_time,
    eh.executed_at
FROM execution_history eh
JOIN error_logs el ON eh.error_log_id = el.id
JOIN solutions s ON eh.solution_id = s.id
ORDER BY eh.executed_at DESC
LIMIT 20;

-- 성공/실패 통계
SELECT 
    execution_status,
    COUNT(*) as count,
    ROUND(AVG(EXTRACT(EPOCH FROM execution_time)), 2) as avg_time_seconds
FROM execution_history
GROUP BY execution_status;

-- 해결책별 성공률
SELECT 
    s.solution_type,
    COUNT(*) as total_executions,
    COUNT(*) FILTER (WHERE eh.execution_status = 'success') as successful,
    ROUND(
        COUNT(*) FILTER (WHERE eh.execution_status = 'success') * 100.0 / COUNT(*), 
        2
    ) as success_rate
FROM execution_history eh
JOIN solutions s ON eh.solution_id = s.id
GROUP BY s.solution_type
HAVING COUNT(*) >= 3
ORDER BY success_rate DESC;
```

### 성능 분석
```sql
-- 실행 시간 분석
SELECT 
    s.solution_type,
    COUNT(*) as executions,
    MIN(EXTRACT(EPOCH FROM eh.execution_time)) as min_time,
    AVG(EXTRACT(EPOCH FROM eh.execution_time)) as avg_time,
    MAX(EXTRACT(EPOCH FROM eh.execution_time)) as max_time
FROM execution_history eh
JOIN solutions s ON eh.solution_id = s.id
WHERE eh.execution_time IS NOT NULL
GROUP BY s.solution_type
ORDER BY avg_time;

-- 시간대별 실행 패턴
SELECT 
    EXTRACT(HOUR FROM executed_at) as hour,
    COUNT(*) as executions,
    COUNT(*) FILTER (WHERE execution_status = 'success') as successful
FROM execution_history
WHERE executed_at >= NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour;
```

## 🎯 에러 패턴 관리 (error_patterns)

### 패턴 조회 및 관리
```sql
-- 모든 에러 패턴
SELECT * FROM error_patterns ORDER BY priority;

-- 자동 해결 가능한 패턴
SELECT * FROM error_patterns WHERE auto_resolve = true;

-- 새 패턴 추가
INSERT INTO error_patterns (
    pattern_name, 
    pattern_regex, 
    error_category, 
    priority, 
    auto_resolve
) VALUES (
    'Docker Container Error',
    'docker.*container.*error',
    'container',
    3,
    true
);

-- 패턴 수정
UPDATE error_patterns 
SET priority = 2, auto_resolve = false 
WHERE pattern_name = 'Service Unavailable';

-- 패턴 삭제
DELETE FROM error_patterns WHERE id = 6;
```

## 🖥️ 시스템 상태 모니터링 (system_status)

### 상태 조회
```sql
-- 전체 시스템 상태
SELECT 
    component_name,
    status,
    error_count,
    last_check,
    EXTRACT(EPOCH FROM (NOW() - last_check)) as seconds_since_check
FROM system_status
ORDER BY 
    CASE status 
        WHEN 'error' THEN 1 
        WHEN 'warning' THEN 2 
        ELSE 3 
    END,
    error_count DESC;

-- 문제가 있는 컴포넌트
SELECT * FROM system_status 
WHERE status != 'healthy' 
ORDER BY error_count DESC;

-- 상태 업데이트
UPDATE system_status 
SET status = 'healthy', error_count = 0, last_check = NOW() 
WHERE component_name = 'elasticsearch';
```

## 🧹 데이터베이스 유지보수

### 데이터 정리
```sql
-- 오래된 에러 로그 삭제 (30일 이전)
DELETE FROM error_logs 
WHERE created_at < NOW() - INTERVAL '30 days';

-- 오래된 실행 이력 삭제 (90일 이전)
DELETE FROM execution_history 
WHERE executed_at < NOW() - INTERVAL '90 days';

-- 통계 정보 업데이트
ANALYZE error_logs;
ANALYZE solutions;
ANALYZE execution_history;
```

### 백업 및 복원
```bash
# 데이터베이스 백업
sudo -u postgres pg_dump elk_resolver > backup_$(date +%Y%m%d).sql

# 특정 테이블만 백업
sudo -u postgres pg_dump elk_resolver -t error_logs > error_logs_backup.sql

# 복원
sudo -u postgres psql elk_resolver < backup_20250710.sql
```

### 인덱스 관리
```sql
-- 인덱스 사용량 확인
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- 인덱스 재구성
REINDEX TABLE error_logs;
REINDEX TABLE solutions;
```

## 📈 고급 분석 쿼리

### 에러 트렌드 분석
```sql
-- 일별 에러 발생 트렌드
SELECT 
    DATE(created_at) as date,
    error_type,
    COUNT(*) as count
FROM error_logs 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at), error_type
ORDER BY date DESC, count DESC;

-- 시스템별 에러 발생 패턴
SELECT 
    source_system,
    error_type,
    COUNT(*) as error_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY source_system), 
        2
    ) as percentage
FROM error_logs
GROUP BY source_system, error_type
HAVING COUNT(*) > 5
ORDER BY source_system, error_count DESC;
```

### 성능 메트릭
```sql
-- 해결책 효율성 분석
SELECT 
    s.solution_type,
    COUNT(DISTINCT el.error_type) as error_types_handled,
    AVG(s.success_rate) as avg_success_rate,
    SUM(s.execution_count) as total_executions,
    COUNT(*) as solution_variants
FROM solutions s
JOIN error_logs el ON s.error_hash = el.hash_signature
GROUP BY s.solution_type
ORDER BY avg_success_rate DESC;

-- AI 분석 품질 메트릭
SELECT 
    DATE(s.created_at) as date,
    COUNT(*) as solutions_created,
    AVG(s.success_rate) as avg_success_rate,
    COUNT(*) FILTER (WHERE s.success_rate > 70) as high_quality_solutions
FROM solutions s
WHERE s.created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(s.created_at)
ORDER BY date DESC;
```

## 🔧 유용한 관리 명령어

### 데이터베이스 정보
```sql
-- 데이터베이스 크기
SELECT pg_size_pretty(pg_database_size('elk_resolver'));

-- 테이블별 크기
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;

-- 연결 상태
SELECT * FROM pg_stat_activity WHERE datname = 'elk_resolver';
```

### 빠른 접속 스크립트
```bash
# ~/.bashrc에 추가
alias elkdb="sudo -u postgres psql elk_resolver"
alias elk-errors="sudo -u postgres psql elk_resolver -c \"SELECT id, error_type, LEFT(error_message, 60), created_at FROM error_logs ORDER BY created_at DESC LIMIT 10;\""
alias elk-stats="sudo -u postgres psql elk_resolver -c \"SELECT error_type, COUNT(*) FROM error_logs GROUP BY error_type ORDER BY COUNT(*) DESC;\""

# 사용법
elkdb          # 데이터베이스 접속
elk-errors     # 최근 에러 10개 조회
elk-stats      # 에러 타입별 통계
```

이 가이드를 통해 PostgreSQL 데이터베이스를 효과적으로 관리하고 모니터링할 수 있습니다.