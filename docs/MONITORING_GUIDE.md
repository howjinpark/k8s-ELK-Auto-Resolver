# ELK Auto Resolver 모니터링 가이드

## 📊 실시간 모니터링 대시보드

### 데이터베이스 기반 대시보드 쿼리
```sql
-- 실시간 시스템 상태 대시보드
WITH recent_stats AS (
    SELECT 
        COUNT(*) as total_errors,
        COUNT(DISTINCT error_type) as error_types,
        COUNT(DISTINCT source_system) as affected_systems
    FROM error_logs 
    WHERE created_at >= NOW() - INTERVAL '1 hour'
),
resolution_stats AS (
    SELECT 
        COUNT(*) as total_resolutions,
        COUNT(*) FILTER (WHERE execution_status = 'success') as successful_resolutions,
        ROUND(
            COUNT(*) FILTER (WHERE execution_status = 'success') * 100.0 / NULLIF(COUNT(*), 0), 
            2
        ) as success_rate
    FROM execution_history 
    WHERE executed_at >= NOW() - INTERVAL '1 hour'
)
SELECT 
    rs.total_errors,
    rs.error_types,
    rs.affected_systems,
    res.total_resolutions,
    res.successful_resolutions,
    res.success_rate || '%' as hourly_success_rate
FROM recent_stats rs, resolution_stats res;
```

### 시스템 헬스 체크
```bash
#!/bin/bash
# health_check.sh - 시스템 전체 상태 점검

echo "=== ELK Auto Resolver 헬스 체크 ==="
echo "시간: $(date)"
echo

# 1. PostgreSQL 상태
echo "📊 PostgreSQL 상태:"
sudo systemctl is-active postgresql
sudo -u postgres psql elk_resolver -c "SELECT COUNT(*) as total_errors FROM error_logs;" 2>/dev/null || echo "❌ DB 연결 실패"
echo

# 2. Elasticsearch 상태  
echo "🔍 Elasticsearch 상태:"
curl -s http://localhost:9200/_cluster/health | jq '.status' 2>/dev/null || echo "❌ ES 연결 실패"
echo

# 3. 메인 프로세스 상태
echo "⚙️  메인 프로세스:"
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "✅ 실행 중 (PID: $(pgrep -f 'python3.*main.py'))"
else
    echo "❌ 중지됨"
fi
echo

# 4. 최근 1시간 활동
echo "📈 최근 1시간 활동:"
sudo -u postgres psql elk_resolver -c "
SELECT 
    COUNT(*) as errors_detected,
    COUNT(DISTINCT error_type) as error_types
FROM error_logs 
WHERE created_at >= NOW() - INTERVAL '1 hour';
" 2>/dev/null
echo

# 5. 포트 상태
echo "🌐 포트 상태:"
netstat -tulpn | grep :9200 && echo "✅ ES 포트포워딩 활성" || echo "❌ ES 포트포워딩 비활성"
netstat -tulpn | grep :5432 && echo "✅ PostgreSQL 포트 활성" || echo "❌ PostgreSQL 포트 비활성"
```

## 📈 성능 메트릭

### 시스템 성능 모니터링
```sql
-- 성능 메트릭 대시보드
SELECT 
    'Error Detection Rate' as metric,
    COUNT(*) || ' errors/hour' as value
FROM error_logs 
WHERE created_at >= NOW() - INTERVAL '1 hour'

UNION ALL

SELECT 
    'Average Resolution Time',
    ROUND(AVG(EXTRACT(EPOCH FROM execution_time)), 2) || ' seconds'
FROM execution_history 
WHERE executed_at >= NOW() - INTERVAL '24 hours'
    AND execution_time IS NOT NULL

UNION ALL

SELECT 
    'AI Analysis Success Rate',
    COUNT(*) FILTER (WHERE success_rate > 0) * 100 / NULLIF(COUNT(*), 0) || '%'
FROM solutions 
WHERE created_at >= NOW() - INTERVAL '24 hours'

UNION ALL

SELECT 
    'Database Size',
    pg_size_pretty(pg_database_size('elk_resolver'))

UNION ALL

SELECT 
    'Active Error Types',
    COUNT(DISTINCT error_type) || ' types'
FROM error_logs 
WHERE created_at >= NOW() - INTERVAL '24 hours';
```

### 리소스 사용량 모니터링
```bash
#!/bin/bash
# resource_monitor.sh

echo "=== 리소스 사용량 모니터링 ==="
echo "시간: $(date)"
echo

# CPU 사용량
echo "💻 CPU 사용량:"
ps aux | grep "python3.*main.py" | grep -v grep | awk '{print $3"% CPU, "$4"% MEM, PID "$2}'
echo

# 메모리 사용량
echo "🧠 메모리 사용량:"
free -h
echo

# 디스크 사용량
echo "💾 디스크 사용량:"
df -h / /var/log
echo

# PostgreSQL 연결수
echo "🔗 PostgreSQL 연결:"
sudo -u postgres psql elk_resolver -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE datname='elk_resolver';" 2>/dev/null
echo

# 로그 파일 크기
echo "📄 로그 파일 크기:"
ls -lh /var/log/elk-auto-resolver* 2>/dev/null || echo "로그 파일 없음"
```

## 🚨 알림 및 경고

### 자동 알림 스크립트
```bash
#!/bin/bash
# alert_check.sh - 문제 상황 자동 감지 및 알림

# 설정
MAX_ERROR_RATE=50          # 시간당 최대 에러 개수
MIN_SUCCESS_RATE=70        # 최소 성공률 (%)
MAX_DB_SIZE_GB=10          # 최대 DB 크기 (GB)

echo "=== 알림 체크 $(date) ==="

# 1. 에러 발생률 체크
error_count=$(sudo -u postgres psql elk_resolver -t -c "
SELECT COUNT(*) FROM error_logs 
WHERE created_at >= NOW() - INTERVAL '1 hour';
" 2>/dev/null | tr -d ' ')

if [ "$error_count" -gt "$MAX_ERROR_RATE" ]; then
    echo "🚨 경고: 시간당 에러 발생률 초과 ($error_count > $MAX_ERROR_RATE)"
fi

# 2. 해결 성공률 체크
success_rate=$(sudo -u postgres psql elk_resolver -t -c "
SELECT ROUND(
    COUNT(*) FILTER (WHERE execution_status = 'success') * 100.0 / NULLIF(COUNT(*), 0)
) FROM execution_history 
WHERE executed_at >= NOW() - INTERVAL '6 hours';
" 2>/dev/null | tr -d ' ')

if [ "$success_rate" -lt "$MIN_SUCCESS_RATE" ]; then
    echo "🚨 경고: 해결 성공률 저하 ($success_rate% < $MIN_SUCCESS_RATE%)"
fi

# 3. 데이터베이스 크기 체크
db_size_mb=$(sudo -u postgres psql elk_resolver -t -c "
SELECT pg_database_size('elk_resolver') / 1024 / 1024;
" 2>/dev/null | tr -d ' ' | cut -d'.' -f1)

if [ "$db_size_mb" -gt "$((MAX_DB_SIZE_GB * 1024))" ]; then
    echo "🚨 경고: 데이터베이스 크기 초과 (${db_size_mb}MB > ${MAX_DB_SIZE_GB}GB)"
fi

# 4. 프로세스 상태 체크
if ! pgrep -f "python3.*main.py" > /dev/null; then
    echo "🚨 심각: 메인 프로세스 중지됨"
fi

# 5. Elasticsearch 연결 체크
if ! curl -s http://localhost:9200/_cluster/health > /dev/null; then
    echo "🚨 경고: Elasticsearch 연결 실패"
fi

echo "알림 체크 완료"
```

### 크론탭 설정
```bash
# crontab -e 실행 후 추가
# 매 10분마다 헬스 체크
*/10 * * * * /root/elk-auto-resolver/health_check.sh >> /var/log/elk-health.log 2>&1

# 매 시간마다 알림 체크
0 * * * * /root/elk-auto-resolver/alert_check.sh >> /var/log/elk-alerts.log 2>&1

# 매일 새벽 2시 백업
0 2 * * * sudo -u postgres pg_dump elk_resolver > /backup/elk_resolver_$(date +\%Y\%m\%d).sql
```

## 📊 실시간 로그 모니터링

### 실시간 로그 확인
```bash
# 메인 로그 실시간 모니터링
tail -f /var/log/elk-auto-resolver.log | grep -E "(ERROR|SUCCESS|WARNING)"

# 특정 패턴 필터링
tail -f /var/log/elk-auto-resolver.log | grep -E "(AI 분석|해결책|에러 탐지)"

# 색상 강조 (colordiff 필요)
tail -f /var/log/elk-auto-resolver.log | grep --color=always -E "(ERROR|SUCCESS|분석 완료)"
```

### 로그 분석 스크립트
```bash
#!/bin/bash
# log_analysis.sh

LOG_FILE="/var/log/elk-auto-resolver.log"

echo "=== 로그 분석 (최근 24시간) ==="
echo

# 1. 에러 통계
echo "📊 에러 레벨별 통계:"
grep "$(date -d '1 day ago' '+%Y-%m-%d')" "$LOG_FILE" | \
awk '{print $4}' | sort | uniq -c | sort -nr

echo

# 2. AI 분석 통계
echo "🤖 AI 분석 통계:"
echo "- 분석 시도: $(grep -c "에러 분석 중" "$LOG_FILE")"
echo "- 분석 완료: $(grep -c "AI 분석 완료" "$LOG_FILE")"  
echo "- 분석 실패: $(grep -c "에러 분석 실패" "$LOG_FILE")"

echo

# 3. 해결 통계
echo "🔧 해결 통계:"
echo "- 해결 시도: $(grep -c "에러 해결 시작" "$LOG_FILE")"
echo "- 해결 성공: $(grep -c "에러 해결 완료.*success" "$LOG_FILE")"
echo "- 해결 실패: $(grep -c "에러 해결 완료.*failed" "$LOG_FILE")"

echo

# 4. 최근 에러 패턴
echo "🎯 최근 에러 패턴 (상위 5개):"
grep "에러 로그 삽입 완료" "$LOG_FILE" | tail -100 | \
awk -F'에러 타입: ' '{print $2}' | awk '{print $1}' | \
sort | uniq -c | sort -nr | head -5
```

## 🔧 성능 최적화 모니터링

### 데이터베이스 성능 체크
```sql
-- 느린 쿼리 및 성능 이슈 체크
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
WHERE query LIKE '%error_logs%' 
ORDER BY total_time DESC 
LIMIT 10;

-- 테이블 스캔 통계
SELECT 
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables 
WHERE schemaname = 'public';

-- 인덱스 사용률
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
```

### API 성능 모니터링
```bash
#!/bin/bash
# api_performance.sh

echo "=== API 성능 모니터링 ==="

# 퍼플렉시티 API 응답시간 테스트
start_time=$(date +%s.%N)

response=$(curl -s -w "%{http_code}" \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"sonar","messages":[{"role":"user","content":"test"}]}' \
  https://api.perplexity.ai/chat/completions)

end_time=$(date +%s.%N)
response_time=$(echo "$end_time - $start_time" | bc)

http_code="${response: -3}"
echo "퍼플렉시티 API:"
echo "- HTTP 코드: $http_code"
echo "- 응답시간: ${response_time}초"

# Elasticsearch 응답시간 테스트
start_time=$(date +%s.%N)
es_response=$(curl -s -w "%{http_code}" http://localhost:9200/_cluster/health)
end_time=$(date +%s.%N)
es_response_time=$(echo "$end_time - $start_time" | bc)

es_code="${es_response: -3}"
echo "Elasticsearch:"
echo "- HTTP 코드: $es_code" 
echo "- 응답시간: ${es_response_time}초"
```

## 📋 일일/주간/월간 리포트

### 일일 리포트
```sql
-- 일일 활동 리포트
WITH daily_stats AS (
    SELECT 
        DATE(created_at) as date,
        COUNT(*) as total_errors,
        COUNT(DISTINCT error_type) as error_types,
        COUNT(DISTINCT source_system) as affected_systems
    FROM error_logs 
    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY DATE(created_at)
),
resolution_stats AS (
    SELECT 
        DATE(executed_at) as date,
        COUNT(*) as total_resolutions,
        COUNT(*) FILTER (WHERE execution_status = 'success') as successful,
        ROUND(AVG(EXTRACT(EPOCH FROM execution_time)), 2) as avg_time
    FROM execution_history 
    WHERE executed_at >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY DATE(executed_at)
)
SELECT 
    COALESCE(ds.date, rs.date) as date,
    COALESCE(ds.total_errors, 0) as errors,
    COALESCE(ds.error_types, 0) as error_types,
    COALESCE(ds.affected_systems, 0) as systems,
    COALESCE(rs.total_resolutions, 0) as resolutions,
    COALESCE(rs.successful, 0) as successful,
    COALESCE(rs.avg_time, 0) as avg_resolution_time
FROM daily_stats ds 
FULL OUTER JOIN resolution_stats rs ON ds.date = rs.date
ORDER BY date DESC;
```

### 자동 리포트 생성
```bash
#!/bin/bash
# generate_report.sh

REPORT_DATE=$(date '+%Y-%m-%d')
REPORT_FILE="/var/log/elk-report-$REPORT_DATE.txt"

{
    echo "=== ELK Auto Resolver 일일 리포트 ==="
    echo "날짜: $REPORT_DATE"
    echo "생성시간: $(date)"
    echo
    
    echo "📊 오늘의 통계:"
    sudo -u postgres psql elk_resolver -c "
    SELECT 
        COUNT(*) as 총_에러수,
        COUNT(DISTINCT error_type) as 에러_타입수,
        COUNT(DISTINCT source_system) as 영향받은_시스템수
    FROM error_logs 
    WHERE DATE(created_at) = CURRENT_DATE;
    "
    
    echo
    echo "🎯 에러 타입별 분포:"
    sudo -u postgres psql elk_resolver -c "
    SELECT 
        error_type as 에러타입,
        COUNT(*) as 발생횟수,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM error_logs WHERE DATE(created_at) = CURRENT_DATE), 2) as 비율
    FROM error_logs 
    WHERE DATE(created_at) = CURRENT_DATE
    GROUP BY error_type 
    ORDER BY COUNT(*) DESC;
    "
    
    echo
    echo "🔧 해결 성과:"
    sudo -u postgres psql elk_resolver -c "
    SELECT 
        COUNT(*) as 총_해결시도,
        COUNT(*) FILTER (WHERE execution_status = 'success') as 성공,
        COUNT(*) FILTER (WHERE execution_status = 'failed') as 실패,
        ROUND(COUNT(*) FILTER (WHERE execution_status = 'success') * 100.0 / COUNT(*), 2) as 성공률
    FROM execution_history 
    WHERE DATE(executed_at) = CURRENT_DATE;
    "
    
    echo
    echo "📈 시간별 활동:"
    sudo -u postgres psql elk_resolver -c "
    SELECT 
        EXTRACT(HOUR FROM created_at) as 시간,
        COUNT(*) as 에러수
    FROM error_logs 
    WHERE DATE(created_at) = CURRENT_DATE
    GROUP BY EXTRACT(HOUR FROM created_at)
    ORDER BY 시간;
    "
    
} > "$REPORT_FILE"

echo "리포트 생성 완료: $REPORT_FILE"
```

이 모니터링 가이드를 통해 ELK Auto Resolver 시스템의 상태를 실시간으로 추적하고 성능을 최적화할 수 있습니다.