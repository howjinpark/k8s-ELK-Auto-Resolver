# ELK Auto Resolver 설치 가이드

ELK Auto Resolver를 처음부터 설치하고 설정하는 방법을 상세히 안내합니다.

## 📋 목차

1. [시스템 요구사항](#1-시스템-요구사항)
2. [사전 준비사항](#2-사전-준비사항)
3. [의존성 설치](#3-의존성-설치)
4. [데이터베이스 설정](#4-데이터베이스-설정)
5. [환경 변수 설정](#5-환경-변수-설정)
6. [ELK Stack 설정](#6-elk-stack-설정)
7. [Slack 연동 설정](#7-slack-연동-설정)
8. [AI 서비스 설정](#8-ai-서비스-설정)
9. [시스템 검증](#9-시스템-검증)
10. [자동 시작 설정](#10-자동-시작-설정)

---

## 1. 시스템 요구사항

### 최소 시스템 사양
- **OS**: Ubuntu 20.04 LTS 이상 (또는 호환 Linux 배포판)
- **CPU**: 2 코어 이상
- **메모리**: 4GB RAM 이상 (권장: 8GB)
- **디스크**: 10GB 이상 여유 공간
- **네트워크**: 인터넷 연결 (API 호출용)

### 소프트웨어 요구사항
- **Python**: 3.8 이상
- **PostgreSQL**: 12 이상
- **Kubernetes**: kubectl 설정 완료
- **Git**: 버전 관리용

### 확인 명령어
```bash
# 시스템 정보 확인
uname -a
lsb_release -a

# Python 버전 확인
python3 --version

# PostgreSQL 버전 확인
postgres --version

# kubectl 설정 확인
kubectl version --client
```

---

## 2. 사전 준비사항

### 2.1 시스템 업데이트
```bash
# 시스템 패키지 업데이트
sudo apt update
sudo apt upgrade -y

# 필수 도구 설치
sudo apt install -y curl wget git htop vim
```

### 2.2 방화벽 설정
```bash
# UFW 방화벽 설정
sudo ufw allow ssh
sudo ufw allow 5432/tcp    # PostgreSQL
sudo ufw allow 9200/tcp    # Elasticsearch (로컬)
sudo ufw --force enable
```

### 2.3 사용자 권한 설정
```bash
# 현재 사용자를 docker 그룹에 추가 (필요시)
sudo usermod -aG docker $USER

# 로그아웃 후 다시 로그인하여 권한 적용
```

---

## 3. 의존성 설치

### 3.1 Python 패키지 설치
```bash
# pip 업그레이드
python3 -m pip install --upgrade pip

# 필수 Python 패키지 설치
pip3 install elasticsearch==8.11.1
pip3 install requests==2.31.0
pip3 install psycopg2-binary==2.9.9
pip3 install PyYAML==6.0.1
pip3 install kubernetes==28.1.0
pip3 install urllib3==1.26.18
```

### 3.2 requirements.txt 생성
```bash
# requirements.txt 파일 생성
cat > requirements.txt << 'EOF'
elasticsearch==8.11.1
requests==2.31.0
psycopg2-binary==2.9.9
PyYAML==6.0.1
kubernetes==28.1.0
urllib3==1.26.18
EOF

# 패키지 설치
pip3 install -r requirements.txt
```

### 3.3 설치 확인
```bash
# 설치된 패키지 확인
pip3 list | grep -E "(elasticsearch|requests|psycopg2|yaml|kubernetes)"
```

---

## 4. 데이터베이스 설정

### 4.1 PostgreSQL 설치
```bash
# PostgreSQL 설치
sudo apt install -y postgresql postgresql-contrib

# PostgreSQL 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 상태 확인
sudo systemctl status postgresql
```

### 4.2 데이터베이스 생성
```bash
# PostgreSQL 사용자로 전환
sudo -u postgres psql

# 데이터베이스 및 사용자 생성 (PostgreSQL 프롬프트에서)
CREATE DATABASE elk_resolver;
CREATE USER elk_resolver_user WITH PASSWORD 'elk_resolver_2024';
GRANT ALL PRIVILEGES ON DATABASE elk_resolver TO elk_resolver_user;
\q
```

### 4.3 데이터베이스 스키마 생성
```bash
# 스키마 파일 생성
cat > database_schema.sql << 'EOF'
-- ELK Auto Resolver 데이터베이스 스키마

-- 에러 로그 테이블
CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    error_type VARCHAR(50) NOT NULL,
    error_message TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(100),
    hash_signature VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 해결책 테이블
CREATE TABLE IF NOT EXISTS solutions (
    id SERIAL PRIMARY KEY,
    error_hash VARCHAR(64) NOT NULL,
    solution_type VARCHAR(50) NOT NULL,
    solution_description TEXT,
    solution_commands TEXT,
    ai_analysis TEXT,
    success_rate DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (error_hash) REFERENCES error_logs(hash_signature)
);

-- 실행 이력 테이블
CREATE TABLE IF NOT EXISTS execution_history (
    id SERIAL PRIMARY KEY,
    solution_id INTEGER NOT NULL,
    execution_status VARCHAR(20) NOT NULL,
    execution_output TEXT,
    execution_time DECIMAL(10,2),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (solution_id) REFERENCES solutions(id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_error_logs_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_solutions_type ON solutions(solution_type);
CREATE INDEX IF NOT EXISTS idx_solutions_success_rate ON solutions(success_rate);
CREATE INDEX IF NOT EXISTS idx_execution_history_status ON execution_history(execution_status);
EOF

# 스키마 적용
sudo -u postgres psql elk_resolver < database_schema.sql
```

### 4.4 데이터베이스 연결 테스트
```bash
# 연결 테스트
sudo -u postgres psql elk_resolver -c "SELECT COUNT(*) FROM error_logs;"

# 테이블 목록 확인
sudo -u postgres psql elk_resolver -c "\dt"
```

---

## 5. 환경 변수 설정

### 5.1 .env 파일 생성
```bash
# .env 파일 생성
cat > .env << 'EOF'
# ELK Auto Resolver Environment Variables
# 보안 관련 설정들을 여기에 저장

# Perplexity AI API 설정
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# Slack 웹훅 설정
SLACK_WEBHOOK_URL=your_slack_webhook_url_here

# 데이터베이스 설정
DATABASE_PASSWORD=elk_resolver_2024

# Elasticsearch 설정
ELASTICSEARCH_PASSWORD=elastic123
EOF
```

### 5.2 파일 권한 설정
```bash
# .env 파일 권한 설정 (소유자만 읽기/쓰기)
chmod 600 .env

# 권한 확인
ls -la .env
# 예상 출력: -rw------- 1 user user 256 Jul 11 16:30 .env
```

### 5.3 환경 변수 로더 다운로드
```bash
# load_env.py 파일이 있는지 확인
ls -la load_env.py

# 환경 변수 로드 테스트
python3 load_env.py
```

---

## 6. ELK Stack 설정

### 6.1 ELK Stack 상태 확인
```bash
# ELK Stack 파드 상태 확인
kubectl get pods -n elk-stack

# 서비스 상태 확인
kubectl get svc -n elk-stack
```

### 6.2 HTTPS 연결 테스트
```bash
# 포트 포워딩 설정
kubectl port-forward -n elk-stack svc/elasticsearch 9200:9200 &

# 연결 테스트
curl -k -u elastic:elastic123 https://localhost:9200

# 클러스터 상태 확인
curl -k -u elastic:elastic123 https://localhost:9200/_cluster/health?pretty
```

### 6.3 인덱스 확인
```bash
# 로그 인덱스 확인
curl -k -u elastic:elastic123 https://localhost:9200/_cat/indices?v | grep logstash

# 로그 개수 확인
curl -k -u elastic:elastic123 https://localhost:9200/logstash-*/_count?pretty
```

---

## 7. Slack 연동 설정

### 7.1 Slack 앱 생성
1. [Slack API 웹사이트](https://api.slack.com/apps) 접속
2. **"Create New App"** → **"From scratch"** 선택
3. 앱 이름: `ELK Auto Resolver`
4. 워크스페이스 선택

### 7.2 Incoming Webhooks 설정
1. **"Incoming Webhooks"** → **"Activate Incoming Webhooks"** ON
2. **"Add New Webhook to Workspace"** 클릭
3. 채널 선택: `#error-detection` (또는 원하는 채널)
4. 생성된 웹훅 URL 복사

### 7.3 환경 변수 업데이트
```bash
# .env 파일에 Slack 웹훅 URL 추가
sed -i 's/your_slack_webhook_url_here/https:\/\/hooks.slack.com\/services\/YOUR\/WEBHOOK\/URL/' .env

# 설정 확인
grep SLACK_WEBHOOK_URL .env
```

### 7.4 Slack 알림 테스트
```bash
# 알림 테스트
python3 slack_notifier.py test

# 성공 시 출력 예시:
# 테스트 메시지 전송 중...
# 전송 결과: 성공
```

---

## 8. AI 서비스 설정

### 8.1 Perplexity API 키 발급
1. [Perplexity AI 웹사이트](https://docs.perplexity.ai/docs/getting-started) 접속
2. 계정 생성 및 로그인
3. API 키 생성
4. 사용량 한도 확인

### 8.2 API 키 설정
```bash
# .env 파일에 API 키 추가
sed -i 's/your_perplexity_api_key_here/pplx-your-actual-api-key/' .env

# 설정 확인
grep PERPLEXITY_API_KEY .env
```

### 8.3 AI 연결 테스트
```bash
# API 키 유효성 테스트
python3 -c "
import requests
import os
from load_env import load_env_file

env_vars = load_env_file()
api_key = env_vars.get('PERPLEXITY_API_KEY')

headers = {'Authorization': f'Bearer {api_key}'}
response = requests.get('https://api.perplexity.ai', headers=headers)
print(f'API 연결 상태: {response.status_code}')
"
```

---

## 9. 시스템 검증

### 9.1 전체 시스템 테스트
```bash
# ELK Auto Resolver 실행 테스트
python3 start_https_resolver.py &
RESOLVER_PID=$!

# 30초 대기
sleep 30

# 프로세스 상태 확인
ps aux | grep python3 | grep start_https_resolver

# 프로세스 종료
kill $RESOLVER_PID
```

### 9.2 각 구성 요소 검증
```bash
# 1. 환경 변수 로드 테스트
python3 load_env.py

# 2. 데이터베이스 연결 테스트
python3 -c "
from database import DatabaseManager
db = DatabaseManager()
success = db.connect()
print(f'데이터베이스 연결: {\"성공\" if success else \"실패\"}')
if success:
    db.disconnect()
"

# 3. Elasticsearch 연결 테스트
python3 -c "
from error_monitor import ErrorMonitor
monitor = ErrorMonitor()
success = monitor.connect_elasticsearch()
print(f'Elasticsearch 연결: {\"성공\" if success else \"실패\"}')
"

# 4. Slack 알림 테스트
python3 slack_notifier.py test
```

### 9.3 로그 확인
```bash
# 로그 파일 확인
ls -la elk_auto_resolver.log

# 최근 로그 확인
tail -n 20 elk_auto_resolver.log
```

---

## 10. 자동 시작 설정

### 10.1 systemd 서비스 생성
```bash
# 서비스 파일 생성
sudo tee /etc/systemd/system/elk-auto-resolver.service > /dev/null <<EOF
[Unit]
Description=ELK Auto Resolver Service
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PWD
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 start_https_resolver.py
ExecStop=/bin/kill -TERM \$MAINPID
Restart=on-failure
RestartSec=30
StandardOutput=append:/var/log/elk-auto-resolver.log
StandardError=append:/var/log/elk-auto-resolver.log

[Install]
WantedBy=multi-user.target
EOF
```

### 10.2 서비스 등록 및 시작
```bash
# 서비스 등록
sudo systemctl daemon-reload
sudo systemctl enable elk-auto-resolver

# 서비스 시작
sudo systemctl start elk-auto-resolver

# 서비스 상태 확인
sudo systemctl status elk-auto-resolver
```

### 10.3 서비스 관리 명령어
```bash
# 서비스 시작
sudo systemctl start elk-auto-resolver

# 서비스 중지
sudo systemctl stop elk-auto-resolver

# 서비스 재시작
sudo systemctl restart elk-auto-resolver

# 서비스 상태 확인
sudo systemctl status elk-auto-resolver

# 서비스 로그 확인
sudo journalctl -u elk-auto-resolver -f
```

---

## 🔧 설치 검증 체크리스트

### 시스템 요구사항 확인
- [ ] Ubuntu 20.04 LTS 이상
- [ ] Python 3.8 이상
- [ ] PostgreSQL 12 이상
- [ ] kubectl 설정 완료
- [ ] 4GB 이상 RAM
- [ ] 10GB 이상 디스크 여유 공간

### 의존성 설치 확인
- [ ] Python 패키지 설치 완료
- [ ] PostgreSQL 서비스 실행 중
- [ ] 데이터베이스 스키마 생성 완료
- [ ] 필요한 시스템 패키지 설치 완료

### 환경 변수 설정 확인
- [ ] .env 파일 생성 및 권한 설정 (600)
- [ ] Perplexity API 키 설정
- [ ] Slack 웹훅 URL 설정
- [ ] 데이터베이스 패스워드 설정
- [ ] 환경 변수 로드 테스트 성공

### 외부 서비스 연동 확인
- [ ] ELK Stack 연결 성공
- [ ] Elasticsearch HTTPS 연결 성공
- [ ] 데이터베이스 연결 성공
- [ ] Slack 알림 테스트 성공
- [ ] Perplexity AI 연결 성공

### 시스템 검증 확인
- [ ] 전체 시스템 테스트 통과
- [ ] 각 구성 요소 개별 테스트 통과
- [ ] 로그 파일 정상 생성
- [ ] 에러 없이 30초 이상 실행

### 자동 시작 설정 확인
- [ ] systemd 서비스 생성
- [ ] 서비스 등록 및 활성화
- [ ] 부팅 시 자동 시작 설정
- [ ] 서비스 상태 정상

---

## 🚨 설치 문제 해결

### 일반적인 문제들

#### 1. Python 패키지 설치 실패
```bash
# pip 업그레이드
python3 -m pip install --upgrade pip

# 시스템 패키지 설치
sudo apt install -y python3-dev libpq-dev

# 개별 패키지 설치 시도
pip3 install psycopg2-binary --no-cache-dir
```

#### 2. PostgreSQL 연결 실패
```bash
# PostgreSQL 서비스 상태 확인
sudo systemctl status postgresql

# 연결 설정 확인
sudo -u postgres psql -c "SELECT version();"

# 방화벽 확인
sudo ufw status | grep 5432
```

#### 3. 권한 문제
```bash
# 파일 권한 설정
chmod 600 .env
chmod +x start_https_resolver.py

# 사용자 그룹 확인
groups $USER
```

#### 4. 네트워크 연결 문제
```bash
# 인터넷 연결 확인
ping -c 4 google.com
ping -c 4 api.perplexity.ai

# 포트 확인
netstat -tlnp | grep -E "(9200|5432)"
```

---

## 📝 설치 완료 후 할 일

### 1. 보안 설정 확인
```bash
# .env 파일 권한 재확인
ls -la .env

# 방화벽 상태 확인
sudo ufw status

# 시스템 업데이트 확인
sudo apt list --upgradable
```

### 2. 모니터링 설정
```bash
# 로그 로테이션 설정
sudo vim /etc/logrotate.d/elk-auto-resolver

# 내용:
# /var/log/elk-auto-resolver.log {
#     daily
#     rotate 30
#     compress
#     delaycompress
#     missingok
#     notifempty
#     create 0644 $USER $USER
# }
```

### 3. 백업 설정
```bash
# 데이터베이스 백업 스크립트
cat > backup_db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
sudo -u postgres pg_dump elk_resolver > "backup_elk_resolver_$DATE.sql"
find . -name "backup_elk_resolver_*.sql" -mtime +7 -delete
EOF

chmod +x backup_db.sh

# 크론잡 설정 (매일 백업)
(crontab -l 2>/dev/null; echo "0 2 * * * $PWD/backup_db.sh") | crontab -
```

### 4. 문서 확인
```bash
# 추가 문서 확인
ls -la docs/
cat docs/TROUBLESHOOTING.md
cat docs/SECURITY.md
```

---

## 🎉 설치 완료

축하합니다! ELK Auto Resolver 설치가 완료되었습니다.

### 다음 단계
1. **시스템 모니터링**: 로그 파일을 정기적으로 확인하세요
2. **성능 최적화**: 시스템 사용량에 따라 임계값 조정
3. **보안 업데이트**: 정기적으로 패키지 업데이트 실행
4. **백업 관리**: 데이터베이스 백업 정상 작동 확인

### 유용한 명령어
```bash
# 서비스 상태 확인
sudo systemctl status elk-auto-resolver

# 실시간 로그 확인
sudo tail -f /var/log/elk-auto-resolver.log

# 수동 실행 (테스트용)
python3 start_https_resolver.py
```

문제가 발생하면 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 문서를 참조하거나 GitHub Issues에 문의해 주세요.

---

**설치 가이드 작성: ELK Auto Resolver Team**  
**최종 업데이트: 2025-07-11**