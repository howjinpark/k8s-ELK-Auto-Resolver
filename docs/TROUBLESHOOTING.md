# ELK Auto Resolver 문제 해결 가이드

ELK Auto Resolver 운영 시 발생할 수 있는 문제들과 해결책을 정리한 가이드입니다.

## 📋 목차

1. [환경 변수 관련 문제](#1-환경-변수-관련-문제)
2. [Elasticsearch 연결 문제](#2-elasticsearch-연결-문제)
3. [Slack 알림 문제](#3-slack-알림-문제)
4. [AI 분석 문제](#4-ai-분석-문제)
5. [데이터베이스 문제](#5-데이터베이스-문제)
6. [자동 해결 문제](#6-자동-해결-문제)
7. [포트 포워딩 문제](#7-포트-포워딩-문제)
8. [권한 및 보안 문제](#8-권한-및-보안-문제)
9. [성능 및 타임아웃 문제](#9-성능-및-타임아웃-문제)
10. [로그 및 모니터링 문제](#10-로그-및-모니터링-문제)

---

## 1. 환경 변수 관련 문제

### 🚨 문제: .env 파일 로드 실패

**증상**
```
설정 파일을 읽을 수 없습니다: Environment variable not found
FileNotFoundError: .env 파일이 없습니다
```

**원인**
- `.env` 파일이 존재하지 않음
- 환경 변수가 올바르게 설정되지 않음
- 파일 권한 문제

**해결책**
```bash
# 1. .env 파일 생성
touch .env

# 2. 필수 환경 변수 설정
cat > .env << 'EOF'
PERPLEXITY_API_KEY=your_api_key_here
SLACK_WEBHOOK_URL=your_webhook_url_here
DATABASE_PASSWORD=your_db_password
ELASTICSEARCH_PASSWORD=your_es_password
EOF

# 3. 파일 권한 설정
chmod 600 .env

# 4. 환경 변수 로드 테스트
python3 load_env.py
```

### 🚨 문제: API 키 형식 오류

**증상**
```
ValueError: 유효하지 않은 API 키입니다
ValueError: Perplexity API 키 형식이 올바르지 않습니다
```

**해결책**
```bash
# Perplexity API 키 형식 확인
echo "PERPLEXITY_API_KEY=pplx-your-actual-api-key-here" > .env

# API 키 형식 검증
python3 -c "
import os
from load_env import load_env_file
env_vars = load_env_file()
api_key = env_vars.get('PERPLEXITY_API_KEY')
print(f'API 키: {api_key[:10]}...')
print(f'형식 확인: {api_key.startswith(\"pplx-\")}')"
```

---

## 2. Elasticsearch 연결 문제

### 🚨 문제: HTTPS 연결 실패

**증상**
```
elastic_transport.transport - INFO - HEAD https://localhost:9200/ [status:401 duration:0.201s]
error_monitor - ERROR - Elasticsearch 연결 실패
ConnectionRefusedError: [Errno 111] Connection refused
```

**원인**
- 포트 포워딩이 설정되지 않음
- 인증 정보 불일치
- SSL 인증서 문제

**해결책**
```bash
# 1. 포트 포워딩 상태 확인
kubectl get pods -n elk-stack
kubectl port-forward -n elk-stack svc/elasticsearch 9200:9200

# 2. 인증 정보 확인
curl -k -u elastic:elastic123 https://localhost:9200

# 3. ELK Auto Resolver 재시작
python3 start_https_resolver.py
```

### 🚨 문제: API 호환성 문제

**증상**
```
DeprecationWarning: The 'http_auth' parameter is deprecated
DeprecationWarning: The 'timeout' parameter is deprecated
```

**해결책**
```python
# 이미 수정된 코드에서 사용하는 형식
es = Elasticsearch(
    ['https://localhost:9200'],
    basic_auth=('elastic', 'elastic123'),      # http_auth 대신
    request_timeout=10,                        # timeout 대신
    verify_certs=False,
    ssl_show_warn=False
)
```

---

## 3. Slack 알림 문제

### 🚨 문제: Slack 알림 전송 실패

**증상**
```
slack_notifier - ERROR - Slack 알림 전송 실패: 404
channel_not_found
invalid_payload
```

**원인**
- 잘못된 웹훅 URL
- 채널 권한 문제
- 메시지 형식 오류

**해결책**
```bash
# 1. 웹훅 URL 직접 테스트
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"테스트 메시지"}' \
  $SLACK_WEBHOOK_URL

# 2. 채널 설정 확인
# error-detection 채널에 봇 권한 확인

# 3. 알림 테스트
python3 slack_notifier.py test

# 4. 채널명 수정 (필요시)
# config.yaml에서 channel: "" (빈 문자열로 기본 채널 사용)
```

### 🚨 문제: 알림 중복 발송

**증상**
```
slack_notifier - INFO - Slack 알림 전송 성공
slack_notifier - INFO - Slack 알림 전송 성공
slack_notifier - INFO - Slack 알림 전송 성공
```

**해결책**
```python
# 이미 수정된 코드에서 중복 방지 로직 적용
notified_types = set()  # 이미 알림을 보낸 에러 타입 추적

if error_type not in notified_types:
    self.slack.send_error_detected(...)
    notified_types.add(error_type)
```

---

## 4. AI 분석 문제

### 🚨 문제: AI 분석 실패

**증상**
```
ai_analyzer - ERROR - JSON 파싱 실패: Extra data: line 23 column 1
ai_analyzer - ERROR - 에러 분석 실패: HTTP 401 Unauthorized
```

**원인**
- Perplexity API 키 만료 또는 잘못됨
- API 사용량 한도 초과
- 네트워크 연결 문제

**해결책**
```bash
# 1. API 키 유효성 확인
curl -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  https://api.perplexity.ai/chat/completions

# 2. API 사용량 확인
# Perplexity 대시보드에서 사용량 확인

# 3. 네트워크 연결 확인
ping api.perplexity.ai

# 4. 로그 상세 확인
tail -f elk_auto_resolver.log | grep ai_analyzer
```

### 🚨 문제: 해결책 생성 실패

**증상**
```
해결책을 찾을 수 없음 - AI 분석 결과가 없거나 solution_type이 누락됨
```

**해결책**
```bash
# 1. 에러 샘플 확인
python3 -c "
from error_monitor import ErrorMonitor
monitor = ErrorMonitor()
monitor.connect_elasticsearch()
errors = monitor.search_errors()
print(f'에러 개수: {len(errors)}')
for i, error in enumerate(errors[:3]):
    print(f'{i+1}. {error[\"error_message\"][:100]}...')
"

# 2. AI 분석 직접 테스트
python3 -c "
from ai_analyzer import AIAnalyzer
analyzer = AIAnalyzer()
test_error = {
    'error_type': 'configuration',
    'error_message': 'multipathd failed to get sysfs uid',
    'timestamp': '2025-07-11T16:00:00Z'
}
result = analyzer.analyze_error(test_error)
print(f'분석 결과: {result}')
"
```

---

## 5. 데이터베이스 문제

### 🚨 문제: 데이터베이스 연결 실패

**증상**
```
database - ERROR - 데이터베이스 연결 실패
psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed
```

**원인**
- PostgreSQL 서비스가 실행되지 않음
- 잘못된 데이터베이스 설정
- 권한 문제

**해결책**
```bash
# 1. PostgreSQL 서비스 상태 확인
sudo systemctl status postgresql

# 2. 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 3. 데이터베이스 연결 테스트
sudo -u postgres psql elk_resolver -c "SELECT 1;"

# 4. 사용자 권한 확인
sudo -u postgres psql -c "SELECT usename FROM pg_user;"
```

### 🚨 문제: 외래키 제약 오류

**증상**
```
psycopg2.errors.ForeignKeyViolation: insert or update on table "solutions" 
violates foreign key constraint "solutions_error_hash_fkey"
```

**해결책**
```python
# 이미 수정된 코드에서 올바른 순서로 실행
# 1. 에러 로그 먼저 저장
error_id = self.db.insert_error_log(error)
if error_id:
    error['error_id'] = error_id
    # 2. AI 분석 나중에 실행
    analysis_result = analyzer.analyze_error(error)
```

---

## 6. 자동 해결 문제

### 🚨 문제: 명령어 실행 시간 초과

**증상**
```
auto_resolver - ERROR - 중요 명령어 실패, 실행 중단
명령어 실행 시간 초과 (300초)
```

**원인**
- 명령어 실행 시간이 5분(300초) 초과
- 네트워크 지연 또는 시스템 부하
- 잘못된 명령어

**해결책**
```bash
# 1. 타임아웃 설정 확인
grep -n "timeout" config.yaml

# 2. 수동 명령어 테스트
kubectl get pods -n elk-stack
kubectl logs -n elk-stack <pod-name>

# 3. 해결책 검토
python3 -c "
from database import DatabaseManager
db = DatabaseManager()
db.connect()
cursor = db.conn.cursor()
cursor.execute('SELECT solution_type, solution_commands FROM solutions ORDER BY created_at DESC LIMIT 5')
for row in cursor.fetchall():
    print(f'해결책: {row[0]}')
    print(f'명령어: {row[1][:200]}...')
"
```

### 🚨 문제: 해결책 실행 실패

**증상**
```
auto_resolver - WARNING - 명령어 실행 실패 (exit code: 1)
kubectl 명령어 실행 실패 - 권한 부족
```

**해결책**
```bash
# 1. kubectl 권한 확인
kubectl auth can-i get pods --namespace=elk-stack
kubectl auth can-i patch deployment --namespace=elk-stack

# 2. 서비스 어카운트 확인
kubectl get serviceaccount -n elk-stack
kubectl describe clusterrole system:admin

# 3. 안전 모드 설정 확인
grep -n "safe_mode" config.yaml
```

---

## 7. 포트 포워딩 문제

### 🚨 문제: 포트 포워딩 실패

**증상**
```
Unable to listen on port 9200: address already in use
포트 포워딩 프로세스 종료됨
```

**원인**
- 포트 9200이 이미 사용 중
- 기존 포트 포워딩 프로세스 존재
- 네트워크 권한 문제

**해결책**
```bash
# 1. 포트 사용 상태 확인
lsof -i :9200
netstat -tlnp | grep :9200

# 2. 기존 프로세스 종료
pkill -f "port-forward"
pkill -f "kubectl.*9200"

# 3. 수동 포트 포워딩 테스트
kubectl port-forward -n elk-stack svc/elasticsearch 9200:9200

# 4. 연결 테스트
curl -k -u elastic:elastic123 https://localhost:9200
```

### 🚨 문제: 자동 포트 포워딩 관리 실패

**증상**
```
port_forward_process.wait(timeout=5)
subprocess.TimeoutExpired: Command 'kubectl port-forward' timed out
```

**해결책**
```bash
# 1. 프로세스 상태 확인
ps aux | grep port-forward

# 2. 수동 정리
sudo pkill -f "kubectl.*port-forward"
sudo pkill -f "port-forward.*9200"

# 3. 재시작
python3 start_https_resolver.py
```

---

## 8. 권한 및 보안 문제

### 🚨 문제: 파일 권한 오류

**증상**
```
PermissionError: .env 파일 권한이 너무 개방적입니다
FileNotFoundError: Permission denied
```

**해결책**
```bash
# 1. .env 파일 권한 수정
chmod 600 .env
ls -la .env

# 2. 로그 파일 권한 수정
chmod 644 elk_auto_resolver.log
chown $USER:$USER elk_auto_resolver.log

# 3. 실행 권한 확인
chmod +x start_https_resolver.py
```

### 🚨 문제: Kubernetes 권한 부족

**증상**
```
Error from server (Forbidden): pods is forbidden
Error from server (Forbidden): deployments.apps is forbidden
```

**해결책**
```bash
# 1. 현재 권한 확인
kubectl auth can-i --list --namespace=elk-stack

# 2. 필요한 권한 확인
kubectl auth can-i get pods --namespace=elk-stack
kubectl auth can-i patch deployment --namespace=elk-stack

# 3. 관리자에게 권한 요청
# 필요 권한: pods, deployments, services에 대한 get, patch, update 권한
```

---

## 9. 성능 및 타임아웃 문제

### 🚨 문제: 시스템 응답 지연

**증상**
```
AI 분석 시간: 30초 이상
에러 처리 대기시간 과도함
```

**해결책**
```bash
# 1. 시스템 리소스 확인
top -p $(pgrep -f "python3 start_https_resolver")
free -h
df -h

# 2. 네트워크 지연 확인
ping api.perplexity.ai
curl -w "Total time: %{time_total}s\n" https://api.perplexity.ai

# 3. 임계값 조정
# config.yaml에서 error_threshold 증가 (25 → 50)
```

### 🚨 문제: 메모리 사용량 과다

**증상**
```
시스템 메모리 부족
Python 프로세스 메모리 누수
```

**해결책**
```bash
# 1. 메모리 사용량 확인
ps aux --sort=-%mem | head -10
htop

# 2. 프로세스 재시작
pkill -f "python3 start_https_resolver"
python3 start_https_resolver.py

# 3. 시스템 정리
sudo apt clean
sudo apt autoremove
```

---

## 10. 로그 및 모니터링 문제

### 🚨 문제: 로그 파일 크기 과대

**증상**
```
elk_auto_resolver.log 파일 크기가 수 GB
디스크 공간 부족
```

**해결책**
```bash
# 1. 로그 파일 크기 확인
ls -lh elk_auto_resolver.log

# 2. 로그 로테이션 설정
sudo logrotate -f /etc/logrotate.conf

# 3. 수동 로그 정리
tail -n 1000 elk_auto_resolver.log > elk_auto_resolver_recent.log
mv elk_auto_resolver_recent.log elk_auto_resolver.log
```

### 🚨 문제: 모니터링 데이터 부족

**증상**
```
에러 통계 정보 부족
성능 메트릭 누락
```

**해결책**
```bash
# 1. 데이터베이스 통계 확인
python3 -c "
from database import DatabaseManager
db = DatabaseManager()
db.connect()
cursor = db.conn.cursor()

# 에러 통계
cursor.execute('SELECT error_type, COUNT(*) FROM error_logs GROUP BY error_type')
print('에러 타입별 통계:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}개')

# 해결책 성공률
cursor.execute('SELECT AVG(success_rate) FROM solutions WHERE success_rate > 0')
avg_success = cursor.fetchone()[0]
print(f'평균 성공률: {avg_success:.1f}%')
"

# 2. 실시간 모니터링
tail -f elk_auto_resolver.log | grep -E "(ERROR|SUCCESS|FAIL)"
```

---

## 🛠️ 일반적인 진단 명령어

### 시스템 상태 확인
```bash
# 1. 프로세스 상태
ps aux | grep -E "(python3|port-forward)" | grep -v grep

# 2. 네트워크 연결
netstat -tlnp | grep -E "(9200|5432|5044)"

# 3. 서비스 상태
kubectl get pods -n elk-stack
sudo systemctl status postgresql

# 4. 로그 확인
tail -f elk_auto_resolver.log
```

### 연결 테스트
```bash
# 1. Elasticsearch 연결
curl -k -u elastic:elastic123 https://localhost:9200

# 2. 데이터베이스 연결
python3 -c "from database import DatabaseManager; db = DatabaseManager(); print('성공' if db.connect() else '실패')"

# 3. Slack 알림 테스트
python3 slack_notifier.py test

# 4. 환경 변수 확인
python3 load_env.py
```

---

## 🚨 긴급 복구 절차

### 전체 시스템 재시작
```bash
# 1. 모든 프로세스 종료
pkill -f "python3 start_https_resolver"
pkill -f "port-forward"

# 2. 시스템 정리
sudo systemctl restart postgresql
kubectl delete pods -n elk-stack --grace-period=0 --force

# 3. 서비스 재시작
kubectl get pods -n elk-stack
python3 start_https_resolver.py
```

### 데이터베이스 복구
```bash
# 1. 데이터베이스 백업
sudo -u postgres pg_dump elk_resolver > backup.sql

# 2. 스키마 재생성 (필요시)
sudo -u postgres psql elk_resolver < database_schema.sql

# 3. 연결 테스트
python3 -c "from database import DatabaseManager; db = DatabaseManager(); db.connect(); print('복구 완료')"
```

---

## 📞 추가 지원

### 로그 수집 방법
```bash
# 문제 발생 시 다음 정보 수집
echo "=== 시스템 정보 ===" > debug_info.txt
uname -a >> debug_info.txt
python3 --version >> debug_info.txt

echo "=== 프로세스 상태 ===" >> debug_info.txt
ps aux | grep -E "(python3|port-forward)" >> debug_info.txt

echo "=== 네트워크 상태 ===" >> debug_info.txt
netstat -tlnp | grep -E "(9200|5432)" >> debug_info.txt

echo "=== 최근 로그 ===" >> debug_info.txt
tail -n 50 elk_auto_resolver.log >> debug_info.txt

echo "=== 환경 변수 ===" >> debug_info.txt
python3 load_env.py >> debug_info.txt 2>&1
```

### GitHub Issues 리포팅
문제 발생 시 다음 정보와 함께 GitHub Issues에 리포트해 주세요:
- 문제 증상 및 에러 메시지
- 시스템 환경 정보
- 수행한 해결 시도
- 관련 로그 파일

---

이 문제 해결 가이드는 실제 운영 경험을 바탕으로 작성되었습니다. 추가적인 문제가 발견되면 지속적으로 업데이트될 예정입니다.