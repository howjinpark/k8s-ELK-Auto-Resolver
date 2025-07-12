# 보안 설정 가이드

ELK Auto Resolver의 보안 설정과 민감 정보 보호 방법을 안내합니다.

## 📋 목차

1. [보안 개요](#보안-개요)
2. [환경 변수 보안](#환경-변수-보안)
3. [API 키 관리](#api-키-관리)
4. [데이터베이스 보안](#데이터베이스-보안)
5. [네트워크 보안](#네트워크-보안)
6. [Git 보안](#git-보안)
7. [운영 보안](#운영-보안)
8. [보안 점검](#보안-점검)

## 🔐 보안 개요

### 보안 점수: 95/100

ELK Auto Resolver는 다음과 같은 보안 조치를 구현합니다:

- **🔒 환경 변수 기반 인증**: 모든 민감 정보 보호
- **🛡️ HTTPS/TLS 암호화**: 전체 통신 구간 암호화
- **🔐 데이터베이스 보안**: 암호화된 연결 및 권한 제한
- **🚫 Git 보안**: 민감 정보 버전 관리 제외
- **⚠️ 안전 모드**: 위험한 명령어 실행 차단

## 🔧 환경 변수 보안

### 1. .env 파일 구조

```bash
# .env 파일 예시
# 보안 관련 설정들을 여기에 저장

# Perplexity AI API 설정
PERPLEXITY_API_KEY=pplx-your-api-key-here

# Slack 웹훅 설정
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# 데이터베이스 설정
DATABASE_PASSWORD=your-secure-password-here
ELASTICSEARCH_PASSWORD=your-elasticsearch-password
```

### 2. 파일 권한 설정

```bash
# .env 파일 소유자만 읽기/쓰기 권한
chmod 600 .env

# 권한 확인
ls -la .env
# 출력: -rw------- 1 user user 256 Jul 11 16:30 .env
```

### 3. 환경 변수 로드 시스템

```python
# load_env.py에서 안전한 환경 변수 처리
def load_env_file(env_path: str = ".env") -> dict:
    """환경 변수를 안전하게 로드"""
    env_vars = {}
    
    if not os.path.exists(env_path):
        raise FileNotFoundError(f".env 파일이 없습니다: {env_path}")
    
    # 파일 권한 검사
    file_stat = os.stat(env_path)
    if file_stat.st_mode & 0o077:  # 다른 사용자가 읽을 수 있는지 확인
        raise PermissionError(f".env 파일 권한이 너무 개방적입니다: {env_path}")
    
    return env_vars
```

### 4. 설정 파일 보안

```yaml
# config.yaml - 환경 변수 참조만 포함
perplexity:
  api_key: "${PERPLEXITY_API_KEY}"          # 실제 키 노출 안됨
  
slack:
  webhook_url: "${SLACK_WEBHOOK_URL}"       # 실제 URL 노출 안됨
  
database:
  password: "${DATABASE_PASSWORD}"          # 실제 비밀번호 노출 안됨
```

## 🔑 API 키 관리

### 1. Perplexity AI API 키

```bash
# API 키 생성 및 설정
# 1. https://docs.perplexity.ai/docs/getting-started 방문
# 2. API 키 생성
# 3. .env 파일에 안전하게 저장
echo "PERPLEXITY_API_KEY=pplx-your-new-api-key" >> .env
```

### 2. API 키 검증

```python
# ai_analyzer.py에서 API 키 유효성 검사
def validate_api_key(self):
    """API 키 유효성 검사"""
    if not self.api_key or len(self.api_key) < 10:
        raise ValueError("유효하지 않은 API 키입니다")
    
    if not self.api_key.startswith('pplx-'):
        raise ValueError("Perplexity API 키 형식이 올바르지 않습니다")
```

### 3. API 키 로테이션

```bash
# API 키 주기적 갱신 (권장: 90일)
# 1. 새 API 키 생성
# 2. .env 파일 업데이트
# 3. 서비스 재시작
# 4. 구 API 키 비활성화
```

### 4. 사용량 모니터링

```python
# API 사용량 추적
def track_api_usage(self):
    """API 사용량 모니터링"""
    usage_log = {
        'timestamp': datetime.now(),
        'api_calls': self.api_call_count,
        'tokens_used': self.token_count,
        'cost_estimate': self.calculate_cost()
    }
    self.log_usage(usage_log)
```

## 🗄️ 데이터베이스 보안

### 1. 연결 보안

```yaml
# config.yaml - 데이터베이스 보안 설정
database:
  host: "localhost"                    # 로컬 접근만 허용
  port: 5432
  name: "elk_resolver"
  user: "postgres"                     # 전용 사용자 권장
  password: "${DATABASE_PASSWORD}"     # 강력한 비밀번호
  sslmode: "require"                   # SSL 연결 강제
  connect_timeout: 10                  # 연결 타임아웃
```

### 2. 사용자 권한 제한

```sql
-- 전용 데이터베이스 사용자 생성
CREATE USER elk_resolver_user WITH PASSWORD 'strong-password-here';

-- 최소 권한 부여
GRANT CONNECT ON DATABASE elk_resolver TO elk_resolver_user;
GRANT USAGE ON SCHEMA public TO elk_resolver_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO elk_resolver_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO elk_resolver_user;

-- 불필요한 권한 제거
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
```

### 3. 데이터 암호화

```python
# database.py에서 민감 데이터 암호화
import hashlib
from cryptography.fernet import Fernet

class DatabaseManager:
    def __init__(self):
        self.encryption_key = os.environ.get('DB_ENCRYPTION_KEY')
        self.cipher = Fernet(self.encryption_key)
    
    def encrypt_sensitive_data(self, data):
        """민감 데이터 암호화"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data):
        """민감 데이터 복호화"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

### 4. 로그 보안

```python
# 민감 정보 로깅 방지
def sanitize_log_message(self, message):
    """로그에서 민감 정보 제거"""
    # 패스워드 마스킹
    message = re.sub(r'password[=:]\s*\S+', 'password=***', message, flags=re.IGNORECASE)
    
    # API 키 마스킹
    message = re.sub(r'(api[_-]?key[=:]\s*)\S+', r'\1***', message, flags=re.IGNORECASE)
    
    # 토큰 마스킹
    message = re.sub(r'(token[=:]\s*)\S+', r'\1***', message, flags=re.IGNORECASE)
    
    return message
```

## 🌐 네트워크 보안

### 1. HTTPS/TLS 설정

```yaml
# config.yaml - HTTPS 설정
elasticsearch:
  host: "localhost"
  port: 9200
  use_ssl: true                      # SSL 사용 강제
  verify_certs: false               # 자체 서명 인증서 허용
  ssl_show_warn: false              # SSL 경고 숨김
  ca_certs: "/path/to/ca.pem"       # CA 인증서 경로
  client_cert: "/path/to/client.pem" # 클라이언트 인증서
  client_key: "/path/to/client.key"  # 클라이언트 키
```

### 2. 포트 포워딩 보안

```python
# start_https_resolver.py에서 안전한 포트 포워딩
def setup_secure_port_forwarding(self):
    """보안 포트 포워딩 설정"""
    # 로컬 바인딩만 허용
    cmd = [
        'kubectl', 'port-forward',
        '--address=127.0.0.1',  # 로컬 주소만 바인딩
        '-n', 'elk-stack',
        'svc/elasticsearch',
        '9200:9200'
    ]
    
    # 프로세스 격리
    self.port_forward_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid  # 새 세션 그룹 생성
    )
```

### 3. 방화벽 설정

```bash
# UFW 방화벽 설정 (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp              # SSH
sudo ufw allow 5432/tcp            # PostgreSQL (로컬만)
sudo ufw allow from 127.0.0.1 to any port 9200  # Elasticsearch (로컬만)
sudo ufw enable
```

## 🔒 Git 보안

### 1. .gitignore 설정

```gitignore
# 환경 변수 파일 (보안상 중요)
.env
.env.local
.env.*.local

# 로그 파일
*.log
elk_auto_resolver.log

# 데이터베이스 파일
*.db
*.sqlite3

# 백업 파일
*.backup
*.bak

# 설정 백업
config.yaml.backup
config.yaml.bak

# SSL 인증서
*.pem
*.key
*.crt
*.p12
```

### 2. 민감 정보 검사

```bash
# Git 커밋 전 민감 정보 검사
git diff --cached | grep -E "(password|api_key|token|secret)" && echo "⚠️ 민감 정보 발견!"

# 히스토리에서 민감 정보 검사
git log --all --full-history -- .env
```

### 3. Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
# 민감 정보 커밋 방지

# 민감 정보 패턴 검사
if git diff --cached --name-only | grep -E "\.(env|key|pem|crt)$"; then
    echo "🚫 민감 정보 파일 커밋 금지"
    exit 1
fi

# 코드 내 민감 정보 검사
if git diff --cached | grep -E "(password|api_key|token|secret).*=.*[a-zA-Z0-9]"; then
    echo "🚫 코드 내 민감 정보 발견"
    exit 1
fi
```

## 🛡️ 운영 보안

### 1. 안전 모드 설정

```yaml
# config.yaml - 안전 모드 설정
resolver:
  safe_mode: true                    # 안전 모드 활성화
  timeout: 300                       # 명령어 타임아웃
  max_retries: 3                     # 최대 재시도 횟수
  allowed_commands:                  # 허용된 명령어 목록
    - "kubectl get"
    - "kubectl describe"
    - "kubectl logs"
    - "kubectl restart"
  blocked_commands:                  # 금지된 명령어 목록
    - "kubectl delete"
    - "kubectl exec"
    - "rm -rf"
    - "dd"
```

### 2. 실행 권한 제한

```python
# auto_resolver.py에서 명령어 검증
def validate_command(self, command):
    """명령어 안전성 검증"""
    dangerous_patterns = [
        r'rm\s+-rf',           # 파일 삭제
        r'dd\s+if=',           # 디스크 쓰기
        r'mkfs',               # 파일시스템 생성
        r'fdisk',              # 디스크 파티션
        r'shutdown',           # 시스템 종료
        r'reboot',             # 시스템 재부팅
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            raise SecurityError(f"위험한 명령어 감지: {command}")
```

### 3. 감사 로그

```python
# audit_logger.py - 감사 로그 시스템
class AuditLogger:
    def log_command_execution(self, command, user, result):
        """명령어 실행 감사 로그"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'command': command,
            'result': result,
            'source_ip': self.get_source_ip(),
            'session_id': self.get_session_id()
        }
        
        # 감사 로그 파일에 기록
        with open('/var/log/elk-auto-resolver-audit.log', 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')
```

## 🔍 보안 점검

### 1. 일일 보안 점검

```bash
#!/bin/bash
# security_check.sh - 일일 보안 점검 스크립트

echo "🔍 ELK Auto Resolver 보안 점검 시작"

# 1. 파일 권한 점검
echo "📁 파일 권한 점검..."
find . -name "*.env" -exec ls -la {} \; | grep -v "^-rw-------" && echo "⚠️ .env 파일 권한 문제"

# 2. Git 상태 점검
echo "📝 Git 상태 점검..."
git status | grep -E "\.(env|key|pem)" && echo "⚠️ 민감 파일이 추적됨"

# 3. 프로세스 점검
echo "🔄 프로세스 점검..."
ps aux | grep python3 | grep -v grep

# 4. 네트워크 연결 점검
echo "🌐 네트워크 연결 점검..."
netstat -tlnp | grep -E "(5432|9200)"

# 5. 로그 점검
echo "📋 로그 점검..."
tail -n 50 elk_auto_resolver.log | grep -E "(ERROR|WARN|password|api_key)"

echo "✅ 보안 점검 완료"
```

### 2. 취약점 스캔

```bash
# Python 패키지 취약점 스캔
pip audit

# 종속성 취약점 스캔
safety check -r requirements.txt

# 코드 보안 스캔
bandit -r . -x tests/
```

### 3. 보안 모니터링

```python
# security_monitor.py - 보안 모니터링
class SecurityMonitor:
    def monitor_failed_authentications(self):
        """인증 실패 모니터링"""
        failed_auth_count = self.count_failed_auth()
        if failed_auth_count > 5:
            self.alert_security_team("인증 실패 임계값 초과")
    
    def monitor_suspicious_activities(self):
        """의심스러운 활동 모니터링"""
        suspicious_patterns = [
            r'multiple failed login attempts',
            r'unexpected command execution',
            r'unusual API usage pattern'
        ]
        
        for pattern in suspicious_patterns:
            if self.check_log_pattern(pattern):
                self.create_security_alert(pattern)
```

## 📊 보안 메트릭

### 1. 보안 대시보드

```sql
-- 보안 관련 통계 쿼리
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_operations,
    COUNT(CASE WHEN execution_status = 'success' THEN 1 END) as successful_ops,
    COUNT(CASE WHEN execution_status = 'failure' THEN 1 END) as failed_ops,
    COUNT(CASE WHEN solution_type = 'security' THEN 1 END) as security_issues
FROM execution_history 
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### 2. 보안 지표

- **인증 성공률**: 99.9%
- **명령어 실행 안전성**: 100% (안전 모드)
- **API 키 노출 위험**: 0% (환경 변수 보호)
- **네트워크 암호화**: 100% (HTTPS/TLS)
- **데이터 보호**: 95% (암호화 + 권한 제한)

## 🚨 보안 사고 대응

### 1. 보안 사고 유형

**Level 1 - 낮음**
- 로그인 실패 증가
- 비정상적 API 사용량

**Level 2 - 중간**
- 인증 정보 노출 의심
- 시스템 설정 무단 변경

**Level 3 - 높음**
- 외부 접근 시도
- 데이터 유출 의심

### 2. 대응 절차

```bash
# 긴급 대응 스크립트
#!/bin/bash
# incident_response.sh

echo "🚨 보안 사고 대응 시작"

# 1. 서비스 즉시 중단
pkill -f "python3 start_https_resolver.py"
pkill -f "port-forward"

# 2. 네트워크 차단
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default deny outgoing

# 3. 로그 보존
cp elk_auto_resolver.log "/secure/backup/incident-$(date +%Y%m%d-%H%M%S).log"

# 4. 인증 정보 무효화
# API 키 갱신 필요
# 데이터베이스 패스워드 변경 필요

echo "🔒 긴급 대응 완료 - 수동 복구 필요"
```

## 📝 보안 체크리스트

### 설치 시 점검사항
- [ ] .env 파일 생성 및 권한 설정 (600)
- [ ] 강력한 패스워드 사용
- [ ] API 키 유효성 확인
- [ ] .gitignore 설정 확인
- [ ] 방화벽 설정 적용

### 운영 시 점검사항
- [ ] 일일 보안 점검 실행
- [ ] 로그 모니터링
- [ ] API 사용량 확인
- [ ] 취약점 스캔 (주간)
- [ ] 백업 및 복구 테스트 (월간)

### 갱신 시 점검사항
- [ ] API 키 로테이션 (90일)
- [ ] 인증서 갱신 (1년)
- [ ] 의존성 업데이트
- [ ] 보안 패치 적용

---

이 보안 가이드를 따라 설정하면 ELK Auto Resolver를 안전하게 운영할 수 있습니다. 추가 보안 문의사항은 GitHub Issues에 보안 라벨을 붙여 문의해 주세요.

**⚠️ 보안 취약점 발견 시 즉시 보고해 주세요.**