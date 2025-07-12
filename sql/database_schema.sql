-- ELK Auto Resolver Database Schema
-- PostgreSQL 데이터베이스 스키마

-- 데이터베이스 생성 (관리자 권한으로 실행)
-- CREATE DATABASE elk_resolver;

-- 에러 로그 테이블
CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    severity VARCHAR(20) DEFAULT 'ERROR',
    stack_trace TEXT,
    elasticsearch_id VARCHAR(100),
    raw_log_data JSONB,
    hash_signature VARCHAR(64) UNIQUE NOT NULL,  -- 중복 에러 방지
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 해결책 테이블 (학습 데이터)
CREATE TABLE IF NOT EXISTS solutions (
    id SERIAL PRIMARY KEY,
    error_hash VARCHAR(64) NOT NULL REFERENCES error_logs(hash_signature),
    solution_type VARCHAR(50) NOT NULL,  -- 'kubernetes', 'config_fix', 'restart' 등
    solution_description TEXT NOT NULL,
    solution_commands JSONB,  -- 실행할 명령어들
    success_rate DECIMAL(5,2) DEFAULT 0.00,
    execution_count INTEGER DEFAULT 0,
    last_success_at TIMESTAMP,
    ai_analysis TEXT,  -- AI가 분석한 내용
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 실행 이력 테이블
CREATE TABLE IF NOT EXISTS execution_history (
    id SERIAL PRIMARY KEY,
    error_log_id INTEGER REFERENCES error_logs(id),
    solution_id INTEGER REFERENCES solutions(id),
    execution_status VARCHAR(20) NOT NULL,  -- 'success', 'failed', 'timeout'
    execution_output TEXT,
    execution_time INTERVAL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_by VARCHAR(50) DEFAULT 'auto-resolver'
);

-- 에러 패턴 테이블 (자주 발생하는 에러 패턴)
CREATE TABLE IF NOT EXISTS error_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(100) NOT NULL,
    pattern_regex TEXT NOT NULL,
    error_category VARCHAR(50) NOT NULL,
    priority INTEGER DEFAULT 5,  -- 1=highest, 10=lowest
    auto_resolve BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 시스템 상태 테이블
CREATE TABLE IF NOT EXISTS system_status (
    id SERIAL PRIMARY KEY,
    component_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'healthy', 'warning', 'error'
    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_count INTEGER DEFAULT 0,
    last_error_at TIMESTAMP,
    metadata JSONB
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_error_logs_hash ON error_logs(hash_signature);
CREATE INDEX IF NOT EXISTS idx_error_logs_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_solutions_error_hash ON solutions(error_hash);
CREATE INDEX IF NOT EXISTS idx_execution_history_error_log_id ON execution_history(error_log_id);
CREATE INDEX IF NOT EXISTS idx_execution_history_executed_at ON execution_history(executed_at);

-- 함수: 해결책 성공률 업데이트
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

-- 트리거: 실행 이력 추가 시 성공률 자동 업데이트
CREATE TRIGGER trigger_update_solution_success_rate
    AFTER INSERT ON execution_history
    FOR EACH ROW
    EXECUTE FUNCTION update_solution_success_rate();

-- 샘플 에러 패턴 데이터
INSERT INTO error_patterns (pattern_name, pattern_regex, error_category, priority, auto_resolve) VALUES
('Pod CrashLoopBackOff', 'CrashLoopBackOff.*pod.*', 'kubernetes', 1, true),
('Out of Memory', 'OutOfMemory|OOMKilled.*', 'resource', 2, true),
('Connection Refused', 'Connection refused.*port.*', 'network', 3, true),
('Disk Full', 'No space left on device|disk.*full', 'storage', 1, true),
('Service Unavailable', 'Service Unavailable|503.*', 'service', 4, false);

-- 샘플 시스템 상태 데이터
INSERT INTO system_status (component_name, status, error_count) VALUES
('elasticsearch', 'healthy', 0),
('logstash', 'healthy', 0),
('kibana', 'healthy', 0),
('filebeat', 'healthy', 0);

-- 권한 설정 (필요시 실행)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO elk_resolver_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO elk_resolver_user;