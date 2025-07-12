# Slack 알림 연동 가이드

ELK Auto Resolver에서 Slack 알림을 설정하고 관리하는 방법을 안내합니다.

## 📋 목차

1. [Slack 앱 생성](#slack-앱-생성)
2. [웹훅 설정](#웹훅-설정)
3. [환경 변수 구성](#환경-변수-구성)
4. [알림 설정](#알림-설정)
5. [알림 유형](#알림-유형)
6. [문제 해결](#문제-해결)
7. [고급 설정](#고급-설정)

## 🚀 Slack 앱 생성

### 1. Slack 앱 만들기

1. [Slack API 웹사이트](https://api.slack.com/apps)에 접속
2. **"Create New App"** 클릭
3. **"From scratch"** 선택
4. 앱 정보 입력:
   - **App Name**: `ELK Auto Resolver`
   - **Development Slack Workspace**: 사용할 워크스페이스 선택
5. **"Create App"** 클릭

### 2. 앱 기본 정보 설정

```yaml
# 앱 설정 예시
App Name: ELK Auto Resolver
Short Description: AI-powered error resolution system
App Icon: 🤖 (또는 커스텀 아이콘)
Background Color: #FF6B6B
```

## 🔗 웹훅 설정

### 1. Incoming Webhooks 활성화

1. 좌측 메뉴에서 **"Incoming Webhooks"** 선택
2. **"Activate Incoming Webhooks"** 토글을 **ON**으로 설정
3. **"Add New Webhook to Workspace"** 클릭

### 2. 채널 선택 및 권한 부여

1. **채널 선택**: `#error-detection` (또는 원하는 채널)
2. **"Allow"** 클릭하여 권한 부여
3. **Webhook URL 복사**: `https://hooks.slack.com/services/T.../B.../...`

### 3. 웹훅 URL 확인

```bash
# 웹훅 URL 형식 확인
https://hooks.slack.com/services/YOUR_TEAM_ID/YOUR_BOT_ID/YOUR_TOKEN
                                 ↑ Team ID   ↑ Bot ID    ↑ Token
```

## 🔧 환경 변수 구성

### 1. .env 파일 설정

```bash
# .env 파일에 Slack 웹훅 URL 추가
echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL" >> .env
```

### 2. 환경 변수 확인

```bash
# 환경 변수 로드 테스트
python3 load_env.py

# 출력 예시에서 Slack 설정 확인
slack:
  webhook_url: https://hooks.slack.com/services/YOUR_TEAM_ID/YOUR_BOT_ID/YOUR_TOKEN
  channel: error-detection
  enabled: true
```

## ⚙️ 알림 설정

### 1. config.yaml 설정

```yaml
# Slack 알림 설정
slack:
  webhook_url: "${SLACK_WEBHOOK_URL}"
  channel: "error-detection"          # 알림 채널
  enabled: true                       # 알림 활성화/비활성화
```

### 2. 알림 테스트

```bash
# Slack 알림 테스트
python3 slack_notifier.py test

# 성공 시 출력
테스트 메시지 전송 중...
전송 결과: 성공
```

### 3. 실시간 알림 제어

```yaml
# 알림 끄기
slack:
  enabled: false

# 알림 켜기
slack:
  enabled: true
```

## 📱 알림 유형

### 🚨 에러 탐지 알림

**발생 조건**: 에러 임계값 초과 (기본: 25개)

```
🚨 에러 탐지 알림

에러 타입: configuration
발생 횟수: 44회
탐지 시간: 2025-07-11 16:33:19
자동 해결 시도: 진행 중...

에러 샘플:
1. Jul 11 16:08:58 worker-1 multipathd[764]: sda: failed to get sysfs uid...
2. Jul 11 16:08:58 worker-1 multipathd[764]: sdb: failed to get udev uid...
3. Jul 11 16:09:03 worker-1 multipathd[764]: sda: failed to get sysfs uid...
```

### ✅ 해결 성공 알림

**발생 조건**: 에러 자동 해결 완료

```
✅ 에러 해결 완료

에러 타입: configuration
해결 방법: 📚 DB 재사용 (또는 🤖 AI 분석)
해결 시간: 2025-07-11 16:35:22
해결책 타입: config_fix

해결 방법 요약:
multipath.conf 파일 수정으로 가상 디스크 블랙리스트 추가
multipathd 서비스 재시작하여 설정 적용
```

### ❌ 해결 실패 알림

**발생 조건**: 에러 해결 시도 실패

```
❌ 에러 해결 실패

에러 타입: configuration
시도한 해결책: config_fix
실패 시간: 2025-07-11 16:20:13
후속 조치: 수동 확인 필요

실패 이유:
중요 명령어 실패: 명령어 실행 시간 초과 (300초)

상세 정보:
1. kubectl 명령어 실행 실패 - 타임아웃 발생
2. multipath 설정 파일 수정 실패
3. 네트워크 연결 문제로 인한 지연
```

## 🔧 문제 해결

### 1. 웹훅 URL 오류

**문제**: `404 Not Found` 또는 `channel_not_found`

**해결**:
```bash
# 웹훅 URL 확인
echo $SLACK_WEBHOOK_URL

# 채널 설정 확인
# config.yaml에서 채널명 올바른지 확인
```

### 2. 권한 부족 오류

**문제**: `missing_scope` 또는 `not_authed`

**해결**:
1. Slack 앱 설정 > **OAuth & Permissions**
2. **Bot Token Scopes**에서 다음 권한 추가:
   - `chat:write`
   - `chat:write.public`
   - `incoming-webhook`

### 3. 메시지 전송 실패

**문제**: `invalid_payload` 또는 `channel_not_found`

**해결**:
```bash
# 직접 테스트
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"테스트 메시지"}' \
  $SLACK_WEBHOOK_URL
```

### 4. 알림이 오지 않음

**체크리스트**:
- [ ] `.env` 파일에 올바른 웹훅 URL 설정
- [ ] `config.yaml`에서 `enabled: true` 설정
- [ ] 채널명 정확성 (`error-detection`)
- [ ] 에러 임계값 초과 여부 (25개 이상)
- [ ] 네트워크 연결 상태

## 🎨 고급 설정

### 1. 메시지 커스터마이징

```python
# slack_notifier.py에서 메시지 형식 수정
def send_error_detected(self, error_type, error_count, error_samples):
    message = {
        "username": "ELK Auto Resolver",
        "icon_emoji": ":warning:",  # 아이콘 변경
        "attachments": [
            {
                "color": "danger",      # 색상 변경
                "title": f"🚨 에러 탐지 알림",
                # ... 기타 설정
            }
        ]
    }
```

### 2. 다중 채널 알림

```yaml
# config.yaml 확장 설정
slack:
  webhook_url: "${SLACK_WEBHOOK_URL}"
  channels:
    error: "error-detection"
    success: "success-reports"
    failure: "failure-alerts"
  enabled: true
```

### 3. 알림 필터링

```python
# 특정 에러 타입만 알림
def should_notify(self, error_type):
    notify_types = ['configuration', 'security', 'critical']
    return error_type in notify_types
```

### 4. 알림 빈도 제한

```python
# 동일 에러 타입 알림 간격 제한 (예: 1시간)
def check_notification_cooldown(self, error_type):
    last_notification = self.get_last_notification_time(error_type)
    return time.time() - last_notification > 3600  # 1시간
```

### 5. 멘션 기능

```python
# 특정 조건에서 팀 멘션
def add_mention_if_critical(self, error_type, message):
    if error_type == 'security':
        message['text'] = f"<!channel> {message['text']}"
    elif error_type == 'critical':
        message['text'] = f"<@U12345678> {message['text']}"  # 특정 사용자
    return message
```

## 📊 모니터링 및 통계

### 1. 알림 전송 로그

```bash
# 알림 전송 성공/실패 확인
grep "slack_notifier" elk_auto_resolver.log

# 출력 예시
2025-07-11 16:33:19,854 - slack_notifier - INFO - Slack 알림 전송 성공
2025-07-11 16:35:22,123 - slack_notifier - INFO - Slack 알림 전송 성공
```

### 2. 알림 통계 확인

```sql
-- 알림 전송 통계 (데이터베이스 쿼리)
SELECT 
    DATE(created_at) as date,
    COUNT(*) as notification_count,
    COUNT(CASE WHEN error_type = 'configuration' THEN 1 END) as config_errors,
    COUNT(CASE WHEN error_type = 'network' THEN 1 END) as network_errors
FROM error_logs 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

## 🔐 보안 고려사항

### 1. 웹훅 URL 보호

```bash
# .env 파일 권한 설정
chmod 600 .env

# Git에서 제외 확인
git status | grep -v ".env"
```

### 2. 민감 정보 필터링

```python
# 로그에서 민감 정보 제거
def sanitize_error_message(self, message):
    # 패스워드, 토큰 등 제거
    sanitized = re.sub(r'password=\w+', 'password=***', message)
    sanitized = re.sub(r'token=\w+', 'token=***', sanitized)
    return sanitized
```

### 3. 웹훅 URL 로테이션

```bash
# 주기적으로 웹훅 URL 갱신
# 1. Slack에서 새 웹훅 생성
# 2. .env 파일 업데이트
# 3. 기존 웹훅 비활성화
```

---

## 💡 팁과 권장사항

### 1. 채널 구성 전략

```
#error-detection     # 에러 탐지 알림
#error-resolved      # 해결 완료 알림
#error-failed        # 해결 실패 알림 (관리자만)
#elk-status          # 시스템 상태 업데이트
```

### 2. 알림 타이밍 최적화

- **즉시 알림**: 보안 관련 에러
- **배치 알림**: 일반적인 설정 에러
- **요약 알림**: 일일/주간 통계

### 3. 팀 워크플로우 통합

```yaml
# 에러 심각도별 알림 전략
severity:
  critical: 즉시 알림 + 전화 연동
  high: 즉시 알림 + 담당자 멘션
  medium: 5분 간격 알림
  low: 시간당 요약 알림
```

이 가이드를 따라 설정하면 ELK Auto Resolver의 모든 활동을 Slack을 통해 실시간으로 모니터링할 수 있습니다.

---

**추가 도움이 필요한 경우 GitHub Issues에 문의해 주세요.**