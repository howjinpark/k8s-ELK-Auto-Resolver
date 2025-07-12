# ELK Auto Resolver - 데이터베이스 설계 문서

## 📊 개요

ELK Auto Resolver는 PostgreSQL 데이터베이스를 사용하여 에러 로그, 해결책, 실행 이력을 관리하고 학습 데이터를 축적합니다.

## 🏗️ 전체 ERD (Entity Relationship Diagram)

```
┌─────────────────────────────────────┐
│              error_logs             │
├─────────────────────────────────────┤
│ 🔑 id (SERIAL)                     │
│    timestamp                        │
│    error_type                       │
│    error_message                    │
│    source_system                    │
│    severity                         │
│    stack_trace                      │
│    elasticsearch_id                 │
│    raw_log_data (JSONB)            │
│ 🗝️  hash_signature (UNIQUE)         │
│    created_at                       │
└─────────────────────────────────────┘
              │
              │ 1:N
              ▼
┌─────────────────────────────────────┐
│             solutions               │
├─────────────────────────────────────┤
│ 🔑 id (SERIAL)                     │
│ 🔗 error_hash → error_logs.hash_... │
│    solution_type                    │
│    solution_description             │
│    solution_commands (JSONB)        │
│    success_rate                     │
│    execution_count                  │
│    last_success_at                  │
│    ai_analysis                      │
│    created_at                       │
│    updated_at                       │
└─────────────────────────────────────┘
              │
              │ 1:N
              ▼
┌─────────────────────────────────────┐
│          execution_history          │
├─────────────────────────────────────┤
│ 🔑 id (SERIAL)                     │
│ 🔗 error_log_id → error_logs.id    │
│ 🔗 solution_id → solutions.id      │
│    execution_status                 │
│    execution_output                 │
│    execution_time                   │
│    executed_at                      │
│    executed_by                      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│           error_patterns            │
├─────────────────────────────────────┤
│ 🔑 id (SERIAL)                     │
│    pattern_name                     │
│    pattern_regex                    │
│    error_category                   │
│    priority                         │
│    auto_resolve                     │
│    created_at                       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│           system_status             │
├─────────────────────────────────────┤
│ 🔑 id (SERIAL)                     │
│    component_name                   │
│    status                          │
│    last_check                      │
│    error_count                     │
│    last_error_at                   │
│    metadata (JSONB)                │
└─────────────────────────────────────┘
```

## 📋 테이블 상세 설계

### 1. error_logs (에러 로그 테이블)

**목적**: ELK Stack에서 탐지된 모든 에러 로그를 저장

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| `id` | SERIAL | PRIMARY KEY | 에러 로그 고유 ID |
| `timestamp` | TIMESTAMP | DEFAULT NOW() | 에러 발생 시간 |
| `error_type` | VARCHAR(100) | NOT NULL | 에러 분류 (kubernetes, memory, network 등) |
| `error_message` | TEXT | NOT NULL | 에러 메시지 내용 |
| `source_system` | VARCHAR(50) | NOT NULL | 에러 발생 시스템 |
| `severity` | VARCHAR(20) | DEFAULT 'ERROR' | 심각도 (ERROR, FATAL, CRITICAL) |
| `stack_trace` | TEXT | NULLABLE | 스택 트레이스 정보 |
| `elasticsearch_id` | VARCHAR(100) | NULLABLE | Elasticsearch 문서 ID |
| `raw_log_data` | JSONB | NULLABLE | 원시 로그 데이터 (JSON) |
| `hash_signature` | VARCHAR(64) | UNIQUE, NOT NULL | 중복 방지용 해시값 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 레코드 생성 시간 |

**인덱스**:
```sql
CREATE INDEX idx_error_logs_timestamp ON error_logs(timestamp);
CREATE INDEX idx_error_logs_hash ON error_logs(hash_signature);
CREATE INDEX idx_error_logs_type ON error_logs(error_type);
```

**비즈니스 규칙**:
- `hash_signature`는 `error_type + error_message`의 SHA256 해시
- 동일한 에러의 중복 저장 방지
- JSONB 타입으로 유연한 로그 데이터 저장

---

### 2. solutions (해결책 테이블)

**목적**: AI가 생성한 해결책과 성공률 정보를 저장

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| `id` | SERIAL | PRIMARY KEY | 해결책 고유 ID |
| `error_hash` | VARCHAR(64) | FK → error_logs.hash_signature | 연관된 에러 해시 |
| `solution_type` | VARCHAR(50) | NOT NULL | 해결책 유형 (kubernetes, config_fix, restart 등) |
| `solution_description` | TEXT | NOT NULL | 해결책 설명 |
| `solution_commands` | JSONB | NOT NULL | 실행할 명령어들 (JSON 배열) |
| `success_rate` | DECIMAL(5,2) | DEFAULT 0.00 | 성공률 (0.00~100.00) |
| `execution_count` | INTEGER | DEFAULT 0 | 총 실행 횟수 |
| `last_success_at` | TIMESTAMP | NULLABLE | 마지막 성공 시간 |
| `ai_analysis` | TEXT | NULLABLE | AI 분석 내용 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 해결책 생성 시간 |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | 마지막 수정 시간 |

**인덱스**:
```sql
CREATE INDEX idx_solutions_error_hash ON solutions(error_hash);
```

**비즈니스 규칙**:
- 하나의 에러에 대해 여러 해결책이 존재할 수 있음
- `success_rate`는 실행 이력을 바탕으로 자동 계산
- `solution_commands`는 JSON 형태로 명령어 배열 저장

**solution_commands JSON 구조**:
```json
[
  {
    "type": "kubectl",
    "command": "kubectl rollout restart deployment/elasticsearch -n elk-stack",
    "description": "Elasticsearch 재시작",
    "safe": true,
    "critical": true
  }
]
```

---

### 3. execution_history (실행 이력 테이블)

**목적**: 해결책 실행 결과와 성능 데이터를 기록

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| `id` | SERIAL | PRIMARY KEY | 실행 이력 고유 ID |
| `error_log_id` | INTEGER | FK → error_logs.id | 연관된 에러 로그 ID |
| `solution_id` | INTEGER | FK → solutions.id | 사용된 해결책 ID |
| `execution_status` | VARCHAR(20) | NOT NULL | 실행 결과 (success, failed, timeout) |
| `execution_output` | TEXT | NULLABLE | 실행 출력 결과 |
| `execution_time` | INTERVAL | NULLABLE | 실행 소요 시간 |
| `executed_at` | TIMESTAMP | DEFAULT NOW() | 실행 시간 |
| `executed_by` | VARCHAR(50) | DEFAULT 'auto-resolver' | 실행 주체 |

**인덱스**:
```sql
CREATE INDEX idx_execution_history_error_log_id ON execution_history(error_log_id);
CREATE INDEX idx_execution_history_executed_at ON execution_history(executed_at);
```

**비즈니스 규칙**:
- 모든 해결책 실행 시도를 기록 (성공/실패 무관)
- 실행 시간으로 성능 분석 가능
- 트리거를 통해 자동으로 solutions 테이블의 성공률 업데이트

---

### 4. error_patterns (에러 패턴 테이블)

**목적**: 에러 분류와 자동 해결 여부를 결정하는 패턴 정의

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| `id` | SERIAL | PRIMARY KEY | 패턴 고유 ID |
| `pattern_name` | VARCHAR(100) | NOT NULL | 패턴 이름 |
| `pattern_regex` | TEXT | NOT NULL | 정규표현식 패턴 |
| `error_category` | VARCHAR(50) | NOT NULL | 에러 카테고리 |
| `priority` | INTEGER | DEFAULT 5 | 우선순위 (1=최고, 10=최저) |
| `auto_resolve` | BOOLEAN | DEFAULT false | 자동 해결 허용 여부 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 패턴 생성 시간 |

**비즈니스 규칙**:
- `priority`가 낮을수록 높은 우선순위
- `auto_resolve`가 false인 경우 수동 승인 필요
- 정규표현식으로 유연한 패턴 매칭

**샘플 데이터**:
```sql
INSERT INTO error_patterns VALUES
(1, 'Pod CrashLoopBackOff', 'CrashLoopBackOff.*pod.*', 'kubernetes', 1, true),
(2, 'Out of Memory', 'OutOfMemory|OOMKilled.*', 'resource', 2, true),
(3, 'Connection Refused', 'Connection refused.*port.*', 'network', 3, true);
```

---

### 5. system_status (시스템 상태 테이블)

**목적**: ELK Stack 각 컴포넌트의 상태를 추적

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| `id` | SERIAL | PRIMARY KEY | 상태 레코드 고유 ID |
| `component_name` | VARCHAR(50) | NOT NULL | 컴포넌트 이름 |
| `status` | VARCHAR(20) | NOT NULL | 상태 (healthy, warning, error) |
| `last_check` | TIMESTAMP | DEFAULT NOW() | 마지막 체크 시간 |
| `error_count` | INTEGER | DEFAULT 0 | 에러 발생 횟수 |
| `last_error_at` | TIMESTAMP | NULLABLE | 마지막 에러 시간 |
| `metadata` | JSONB | NULLABLE | 추가 메타데이터 |

**비즈니스 규칙**:
- 각 ELK 컴포넌트당 하나의 레코드
- 주기적으로 상태 업데이트
- 헬스 체크 기반 모니터링

---

## 🔧 트리거 및 함수

### 1. 성공률 자동 업데이트 트리거

```sql
CREATE OR REPLACE FUNCTION update_solution_success_rate()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE solutions 
    SET 
        success_rate = (
            SELECT 
                CASE 
                    WHEN COUNT(*) = 0 THEN 0 
                    ELSE (COUNT(*) FILTER (WHERE execution_status = 'success') * 100.0 / COUNT(*))
                END
            FROM execution_history 
            WHERE solution_id = NEW.solution_id
        ),
        execution_count = (
            SELECT COUNT(*) 
            FROM execution_history 
            WHERE solution_id = NEW.solution_id
        ),
        last_success_at = CASE 
            WHEN NEW.execution_status = 'success' THEN NEW.executed_at 
            ELSE last_success_at 
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.solution_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_solution_success_rate
    AFTER INSERT ON execution_history
    FOR EACH ROW
    EXECUTE FUNCTION update_solution_success_rate();
```

**동작 방식**:
- `execution_history`에 새 레코드 삽입 시 자동 실행
- 해당 해결책의 성공률과 실행 횟수 자동 계산
- 성공한 경우 `last_success_at` 업데이트

---

## 📈 데이터 플로우

### 1. 에러 탐지 → 저장
```
Elasticsearch → Error Monitor → error_logs 테이블
```

### 2. AI 분석 → 해결책 생성
```
error_logs → AI Analyzer → solutions 테이블
```

### 3. 해결책 실행 → 이력 기록
```
solutions → Auto Resolver → execution_history 테이블
```

### 4. 성공률 자동 업데이트
```
execution_history → Trigger → solutions.success_rate 업데이트
```

---

## 🔍 주요 쿼리 예제

### 1. 에러 타입별 통계
```sql
SELECT 
    error_type,
    COUNT(*) as total_errors,
    COUNT(DISTINCT DATE(created_at)) as days_occurred
FROM error_logs 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY error_type
ORDER BY total_errors DESC;
```

### 2. 해결책 성공률 랭킹
```sql
SELECT 
    solution_type,
    AVG(success_rate) as avg_success_rate,
    SUM(execution_count) as total_executions
FROM solutions 
WHERE execution_count > 0
GROUP BY solution_type
ORDER BY avg_success_rate DESC;
```

### 3. 최근 실행 이력
```sql
SELECT 
    el.error_type,
    s.solution_type,
    eh.execution_status,
    eh.execution_time,
    eh.executed_at
FROM execution_history eh
JOIN error_logs el ON eh.error_log_id = el.id
JOIN solutions s ON eh.solution_id = s.id
WHERE eh.executed_at >= NOW() - INTERVAL '24 hours'
ORDER BY eh.executed_at DESC;
```

### 4. 시스템 상태 대시보드
```sql
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
```

---

## 🛡️ 보안 고려사항

### 1. 접근 권한
```sql
-- 읽기 전용 사용자 생성
CREATE USER elk_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE elk_resolver TO elk_readonly;
GRANT USAGE ON SCHEMA public TO elk_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO elk_readonly;

-- 애플리케이션 사용자 권한 제한
REVOKE ALL ON SCHEMA public FROM elk_resolver_user;
GRANT CONNECT ON DATABASE elk_resolver TO elk_resolver_user;
GRANT INSERT, SELECT, UPDATE ON ALL TABLES IN SCHEMA public TO elk_resolver_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO elk_resolver_user;
```

### 2. 데이터 보호
- 민감한 정보는 `raw_log_data`에서 마스킹 처리
- API 키나 비밀번호는 별도 암호화 저장
- 로그 데이터 보존 기간 설정 (예: 90일)

### 3. 백업 전략
```sql
-- 주요 테이블 백업
pg_dump elk_resolver -t error_logs -t solutions > backup_$(date +%Y%m%d).sql
```

---

## 📊 성능 최적화

### 1. 파티셔닝 (대용량 데이터용)
```sql
-- 월별 파티셔닝 예제
CREATE TABLE error_logs_y2024m01 PARTITION OF error_logs
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### 2. 인덱스 최적화
- 자주 사용되는 WHERE 조건에 인덱스 생성
- 복합 인덱스로 쿼리 성능 향상
- JSONB 컬럼에 GIN 인덱스 적용

### 3. 정기 유지보수
```sql
-- 통계 정보 업데이트
ANALYZE error_logs;
ANALYZE solutions;
ANALYZE execution_history;

-- 오래된 데이터 정리 (90일 이전)
DELETE FROM error_logs WHERE created_at < NOW() - INTERVAL '90 days';
```

---

## 📝 마이그레이션 가이드

### 새 컬럼 추가 예제
```sql
-- solutions 테이블에 AI 모델 정보 컬럼 추가
ALTER TABLE solutions ADD COLUMN ai_model VARCHAR(50);
ALTER TABLE solutions ADD COLUMN ai_confidence DECIMAL(3,2);

-- 기본값 설정
UPDATE solutions SET ai_model = 'llama-3.1-sonar-large-128k-online' WHERE ai_model IS NULL;
```

### 인덱스 추가
```sql
CREATE INDEX CONCURRENTLY idx_solutions_ai_model ON solutions(ai_model);
CREATE INDEX CONCURRENTLY idx_error_logs_severity ON error_logs(severity);
```

이 설계 문서는 ELK Auto Resolver의 데이터베이스 구조를 완전히 설명하며, 확장성과 성능을 고려한 설계가 되어있습니다.