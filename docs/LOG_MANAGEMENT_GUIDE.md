# ELK Auto Resolver 로그 관리 가이드

## 개요

ELK Auto Resolver에 자동 로그 정리 및 관리 기능이 추가되었습니다. 이 기능은 시스템 성능을 유지하고 저장 공간을 효율적으로 관리하기 위해 오래된 로그 데이터를 자동으로 정리합니다.

## 주요 기능

### 1. 시간 기반 필터링
- **최대 검색 시간 제한**: 너무 오래된 로그는 검색하지 않음 (기본값: 24시간)
- **효율적인 검색**: 최근 데이터에만 집중하여 검색 성능 향상
- **메모리 절약**: 불필요한 데이터 로딩 방지

### 2. 자동 로그 정리
- **Elasticsearch 인덱스 정리**: 오래된 logstash-* 인덱스 자동 삭제
- **데이터베이스 정리**: 에러 로그, 해결책, 실행 이력 정리
- **정기적 실행**: 설정된 간격마다 자동 실행

### 3. 독립적인 정리 스케줄러
- **백그라운드 실행**: 메인 시스템과 독립적으로 동작
- **안전한 정리**: 참조 무결성을 유지하면서 데이터 정리
- **시스템 모니터링**: 메모리 및 디스크 사용률 모니터링

## 설정 방법

### config.yaml 설정

```yaml
# 로그 관리 및 정리 설정
log_management:
  # 자동 정리 간격 (시간)
  cleanup_interval_hours: 24
  
  # 로그 보존 기간 (일)
  retention_days: 7
  
  # 최대 검색 시간 (시간) - 너무 오래된 로그는 검색하지 않음
  max_search_hours: 24
  
  # Elasticsearch 인덱스 정리 설정
  elasticsearch_cleanup:
    enabled: true
    # 삭제할 인덱스 패턴 (logstash-YYYY.MM.DD 형식)
    index_pattern: "logstash-*"
    # 보존할 최근 인덱스 개수
    keep_recent_indices: 7
  
  # 데이터베이스 정리 설정  
  database_cleanup:
    enabled: true
    # 에러 로그 보존 기간 (일)
    error_logs_retention_days: 7
    # 해결책 보존 기간 (일) - 참조되지 않는 것만 삭제
    solutions_retention_days: 30
    # 실행 이력 보존 기간 (일)
    execution_history_retention_days: 14
```

### 설정 항목 설명

| 설정 항목 | 기본값 | 설명 |
|-----------|--------|------|
| `cleanup_interval_hours` | 24 | 자동 정리 실행 간격 (시간) |
| `retention_days` | 7 | 기본 로그 보존 기간 (일) |
| `max_search_hours` | 24 | 에러 검색 시 최대 시간 범위 (시간) |
| `error_logs_retention_days` | 7 | 에러 로그 보존 기간 (일) |
| `solutions_retention_days` | 30 | 해결책 보존 기간 (일) |
| `execution_history_retention_days` | 14 | 실행 이력 보존 기간 (일) |

## 사용 방법

### 1. 메인 시스템에 통합된 정리 기능

ELK Auto Resolver를 정상적으로 실행하면 자동으로 로그 정리 기능이 활성화됩니다:

```bash
cd /root/elk-auto-resolver
python3 scripts/start_resolver.py
```

**로그 예시:**
```
2025-07-12 02:11:47 - src.error_monitor - INFO - 에러 검색 시간 범위: 2025-07-12T01:11:47 ~ 2025-07-12T02:11:47
2025-07-12 02:11:47 - src.error_monitor - INFO - 5개의 에러 로그 발견 (최근 60분간)
2025-07-12 14:11:47 - src.error_monitor - INFO - 로그 정리 완료: 3개 인덱스 삭제, 7일 이전 데이터 정리
```

### 2. 독립적인 정리 스케줄러 실행

메인 시스템과 별도로 정리 전용 스케줄러를 실행할 수 있습니다:

```bash
cd /root/elk-auto-resolver
python3 scripts/start_log_cleanup.py
```

**백그라운드 실행:**
```bash
nohup python3 scripts/start_log_cleanup.py > /tmp/cleanup.log 2>&1 &
```

### 3. 수동 정리 실행

Python 스크립트를 통한 즉시 정리:

```python
from src.log_cleanup_scheduler import LogCleanupScheduler

# 스케줄러 생성
scheduler = LogCleanupScheduler()

# 강제 정리 실행
success = scheduler.force_cleanup()
print(f"정리 완료: {success}")

# 상태 확인
status = scheduler.get_cleanup_status()
print(f"상태: {status}")
```

## 정리 과정 상세

### Elasticsearch 정리

1. **인덱스 패턴 확인**: `logstash-YYYY.MM.DD` 형식의 인덱스 검색
2. **보존 기간 계산**: `retention_days` 설정을 기준으로 삭제 대상 결정
3. **안전한 삭제**: 존재 여부 확인 후 개별 인덱스 삭제
4. **와일드카드 정리**: 패턴 기반 일괄 삭제 시도

### 데이터베이스 정리

1. **의존성 순서**: 실행 이력 → 해결책 → 에러 로그 순으로 삭제
2. **참조 무결성**: 다른 테이블에서 참조되는 데이터는 보존
3. **트랜잭션**: 모든 정리 작업을 트랜잭션으로 처리
4. **롤백**: 오류 발생 시 자동 롤백

## 모니터링 및 로그

### 정리 로그 확인

```bash
# 메인 시스템 로그
tail -f /tmp/elk-auto-resolver.log | grep -i "정리\|cleanup"

# 독립 스케줄러 로그
tail -f /tmp/elk-auto-resolver-cleanup.log
```

### 정리 통계 확인

```bash
# Elasticsearch 인덱스 확인
curl -k -u elastic:elastic123 "https://localhost:9200/_cat/indices/logstash-*?v"

# 데이터베이스 테이블 크기 확인
psql -h localhost -U postgres -d elk_resolver -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_stat_get_tuples_returned(c.oid) as rows
FROM pg_tables pt
JOIN pg_class c ON c.relname = pt.tablename
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

## 성능 최적화

### 1. 정리 간격 조정

- **빈번한 정리** (1-6시간): 실시간 시스템, 높은 로그 볼륨
- **일반적인 정리** (12-24시간): 표준 운영 환경
- **느린 정리** (48-72시간): 개발 환경, 낮은 로그 볼륨

### 2. 보존 기간 최적화

```yaml
# 고성능 환경
log_management:
  retention_days: 3
  max_search_hours: 12
  
# 표준 환경  
log_management:
  retention_days: 7
  max_search_hours: 24
  
# 분석용 환경
log_management:
  retention_days: 30
  max_search_hours: 168  # 7일
```

### 3. 선택적 정리

특정 컴포넌트만 정리하려면:

```yaml
log_management:
  elasticsearch_cleanup:
    enabled: false  # Elasticsearch 정리 비활성화
  database_cleanup:
    enabled: true   # 데이터베이스만 정리
```

## 문제 해결

### 일반적인 문제

1. **권한 오류**
   ```bash
   # Elasticsearch 인증 확인
   curl -k -u elastic:elastic123 "https://localhost:9200/_cluster/health"
   
   # 데이터베이스 연결 확인
   psql -h localhost -U postgres -d elk_resolver -c "SELECT 1;"
   ```

2. **디스크 공간 부족**
   ```bash
   # 즉시 정리 실행
   python3 -c "
   from src.log_cleanup_scheduler import LogCleanupScheduler
   scheduler = LogCleanupScheduler()
   scheduler.force_cleanup()
   "
   ```

3. **정리 실패**
   ```bash
   # 로그 확인
   grep -i "error\|fail" /tmp/elk-auto-resolver-cleanup.log
   
   # 수동으로 오래된 인덱스 삭제
   curl -k -u elastic:elastic123 -X DELETE "https://localhost:9200/logstash-2025.07.01"
   ```

### 고급 문제 해결

1. **메모리 사용량 확인**
   ```python
   import psutil
   print(f"메모리 사용률: {psutil.virtual_memory().percent}%")
   print(f"디스크 사용률: {psutil.disk_usage('/').percent}%")
   ```

2. **Elasticsearch 클러스터 상태**
   ```bash
   curl -k -u elastic:elastic123 "https://localhost:9200/_cluster/health?pretty"
   ```

3. **데이터베이스 연결 풀 상태**
   ```sql
   SELECT * FROM pg_stat_activity WHERE datname = 'elk_resolver';
   ```

## 모범 사례

1. **정기적인 모니터링**: 주간 단위로 정리 통계 확인
2. **백업 전략**: 중요한 데이터는 정리 전 백업
3. **테스트 환경**: 프로덕션 적용 전 테스트 환경에서 검증
4. **점진적 적용**: 보존 기간을 점진적으로 줄여가며 최적화
5. **알림 설정**: 정리 실패 시 Slack 알림 활용

## 업데이트 적용

기존 ELK Auto Resolver에 로그 관리 기능을 적용하려면:

1. **설정 파일 업데이트**: `config.yaml`에 `log_management` 섹션 추가
2. **코드 업데이트**: 최신 버전의 모듈 파일들 적용
3. **권한 확인**: Elasticsearch 및 데이터베이스 삭제 권한 확인
4. **테스트 실행**: 안전한 환경에서 정리 기능 테스트