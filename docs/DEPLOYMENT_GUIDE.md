# ELK Auto Resolver 배포 가이드

## 개요

이 가이드는 새로운 환경에서 ELK Auto Resolver를 설정하고 실행하는 방법을 설명합니다.

## 사전 요구사항

### 1. 시스템 요구사항

- **운영체제**: Ubuntu 20.04+ 또는 CentOS 7+ (Linux 권장)
- **메모리**: 최소 4GB RAM (권장 8GB+)
- **CPU**: 최소 2 Core (권장 4 Core+)
- **디스크**: 최소 20GB 여유 공간
- **네트워크**: 인터넷 접속 필요 (API 호출용)

### 2. 필수 소프트웨어

```bash
# Python 3.8+ 설치 확인
python3 --version

# pip 설치
sudo apt update
sudo apt install python3-pip python3-venv -y

# Git 설치
sudo apt install git -y

# PostgreSQL 설치
sudo apt install postgresql postgresql-contrib -y

# Kubernetes 도구 설치 (kubectl)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

## 1단계: 프로젝트 다운로드

### GitHub에서 복제
```bash
# 프로젝트 클론
git clone https://github.com/your-username/elk-auto-resolver.git
cd elk-auto-resolver

# 또는 압축 파일로 전송받은 경우
tar -xzf elk-auto-resolver.tar.gz
cd elk-auto-resolver
```

### 파일 구조 확인
```bash
tree -L 2
# 예상 구조:
# ├── config/
# │   ├── config.yaml
# │   └── .env.example
# ├── src/
# │   ├── *.py (Python 모듈들)
# ├── scripts/
# │   ├── start_resolver.py
# │   └── start_log_cleanup.py
# ├── docs/
# └── sql/
```

## 2단계: Python 환경 설정

### 가상환경 생성 및 활성화
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 필수 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt
```

### requirements.txt 내용
```txt
elasticsearch==8.5.0
kubernetes==24.2.0
psycopg2-binary==2.9.5
PyYAML==6.0
requests==2.28.2
python-dotenv==0.19.2
psutil==5.9.4
```

## 3단계: 데이터베이스 설정

### PostgreSQL 설정
```bash
# PostgreSQL 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 데이터베이스 사용자 생성
sudo -u postgres psql -c "CREATE USER elk_user WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE elk_resolver OWNER elk_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE elk_resolver TO elk_user;"

# 스키마 생성
sudo -u postgres psql -d elk_resolver -f sql/create_schema.sql
```

### 데이터베이스 스키마 생성 스크립트
```bash
# sql/create_schema.sql 실행하여 테이블 생성
cat sql/create_schema.sql
```

## 4단계: 환경 변수 설정

### .env 파일 생성
```bash
# 환경 변수 파일 복사 및 수정
cp config/.env.example config/.env
nano config/.env
```

### .env 파일 내용 설정
```bash
# ELK Auto Resolver Environment Variables

# Perplexity AI API 설정 (필수)
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# Slack 웹훅 설정 (필수)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# 데이터베이스 설정
DATABASE_PASSWORD=your_secure_password

# Elasticsearch 설정
ELASTICSEARCH_PASSWORD=your_elasticsearch_password
```

### API 키 발급 방법

#### Perplexity AI API 키
1. [Perplexity AI](https://www.perplexity.ai/) 회원가입
2. API 섹션에서 새 API 키 생성
3. `.env` 파일에 추가

#### Slack 웹훅 URL
1. Slack 워크스페이스에서 앱 설정
2. "Incoming Webhooks" 활성화
3. 채널 선택 후 웹훅 URL 복사
4. `.env` 파일에 추가

## 5단계: Kubernetes 클러스터 연결

### kubectl 설정 확인
```bash
# 클러스터 연결 테스트
kubectl cluster-info
kubectl get nodes

# ELK Stack 네임스페이스 확인
kubectl get namespace elk-stack
kubectl get pods -n elk-stack
```

### kubeconfig 파일 설정
```bash
# kubeconfig 파일 경로 설정 (필요시)
export KUBECONFIG=/path/to/your/kubeconfig
echo 'export KUBECONFIG=/path/to/your/kubeconfig' >> ~/.bashrc
```

## 6단계: ELK Stack 배포 (선택사항)

### 기존 ELK Stack이 없는 경우
```bash
# ELK Stack 배포 (간단한 버전)
kubectl apply -f elk/elasticsearch-simple.yaml
kubectl apply -f elk/logstash-simple.yaml
kubectl apply -f elk/kibana-simple-new.yaml
kubectl apply -f elk/filebeat-simple.yaml

# 또는 HTTPS 버전
kubectl apply -f elk/elasticsearch-https-final.yaml
kubectl apply -f elk/logstash-https-final.yaml
kubectl apply -f elk/kibana-https-final.yaml
kubectl apply -f elk/filebeat-https-final.yaml
```

### ELK Stack 상태 확인
```bash
# 모든 Pod가 Running 상태인지 확인
kubectl get pods -n elk-stack

# 서비스 확인
kubectl get svc -n elk-stack
```

## 7단계: 설정 파일 수정

### config.yaml 환경에 맞게 수정
```bash
nano config/config.yaml
```

### 주요 설정 항목
```yaml
elasticsearch:
  host: "localhost"  # 또는 실제 Elasticsearch 호스트
  port: 9200
  use_ssl: true      # HTTPS 사용 여부
  username: "elastic"
  password: "${ELASTICSEARCH_PASSWORD}"

database:
  host: "localhost"  # 또는 실제 데이터베이스 호스트
  port: 5432
  name: "elk_resolver"
  user: "elk_user"
  password: "${DATABASE_PASSWORD}"

kubernetes:
  namespace: "elk-stack"
  config_path: "~/.kube/config"  # 실제 kubeconfig 경로

monitoring:
  check_interval: 60      # 확인 간격 (초)
  error_threshold: 25     # 알림 임계값

log_management:
  cleanup_interval_hours: 24
  retention_days: 7
```

## 8단계: 연결 테스트

### 개별 구성 요소 테스트
```bash
# PostgreSQL 연결 테스트
python3 -c "
import psycopg2
from src.load_env import load_config_with_env
config = load_config_with_env()
db_config = config['database']
conn = psycopg2.connect(
    host=db_config['host'],
    port=db_config['port'],
    database=db_config['name'],
    user=db_config['user'],
    password=db_config['password']
)
print('✅ PostgreSQL 연결 성공')
conn.close()
"

# Elasticsearch 연결 테스트
python3 -c "
from elasticsearch import Elasticsearch
import urllib3
urllib3.disable_warnings()
es = Elasticsearch(
    ['https://localhost:9200'],
    verify_certs=False,
    ssl_show_warn=False,
    basic_auth=('elastic', 'your_password'),
    request_timeout=10
)
if es.ping():
    print('✅ Elasticsearch 연결 성공')
else:
    print('❌ Elasticsearch 연결 실패')
"

# Kubernetes 연결 테스트
kubectl get pods -n elk-stack
```

### Slack 알림 테스트
```bash
# Slack 웹훅 테스트
python3 -c "
from src.slack_notifier import SlackNotifier
slack = SlackNotifier()
slack.send_test_message('ELK Auto Resolver 테스트 메시지')
print('✅ Slack 알림 테스트 완료')
"
```

## 9단계: 실행

### 수동 실행
```bash
# 가상환경 활성화
source venv/bin/activate

# ELK Auto Resolver 시작
python3 scripts/start_resolver.py
```

### 백그라운드 실행
```bash
# 백그라운드에서 실행
nohup python3 scripts/start_resolver.py > elk_resolver.log 2>&1 &

# 로그 확인
tail -f elk_resolver.log
```

### 서비스로 등록 (선택사항)
```bash
# systemd 서비스 파일 생성
sudo nano /etc/systemd/system/elk-auto-resolver.service
```

```ini
[Unit]
Description=ELK Auto Resolver
After=network.target postgresql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/elk-auto-resolver
Environment=PATH=/path/to/elk-auto-resolver/venv/bin
ExecStart=/path/to/elk-auto-resolver/venv/bin/python scripts/start_resolver.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable elk-auto-resolver
sudo systemctl start elk-auto-resolver

# 상태 확인
sudo systemctl status elk-auto-resolver
```

## 10단계: 검증 및 모니터링

### 정상 작동 확인
```bash
# 로그 확인
tail -f elk_resolver.log | grep -E "(✅|❌|INFO|ERROR)"

# 데이터베이스 확인
psql -h localhost -U elk_user -d elk_resolver -c "SELECT COUNT(*) FROM error_logs;"

# Slack 채널에서 알림 확인
```

### 성능 모니터링
```bash
# 시스템 리소스 확인
htop
df -h
free -h

# 프로세스 모니터링
ps aux | grep python3
```

## 문제 해결

### 일반적인 문제들

#### 1. 데이터베이스 연결 실패
```bash
# PostgreSQL 서비스 상태 확인
sudo systemctl status postgresql

# 방화벽 확인
sudo ufw status
sudo ufw allow 5432

# 연결 설정 확인
sudo nano /etc/postgresql/*/main/pg_hba.conf
sudo nano /etc/postgresql/*/main/postgresql.conf
```

#### 2. Elasticsearch 연결 실패
```bash
# 포트 포워딩 확인
kubectl port-forward -n elk-stack service/elasticsearch 9200:9200

# SSL 인증서 문제 시
# config.yaml에서 verify_certs: false 설정
```

#### 3. Kubernetes 권한 문제
```bash
# RBAC 권한 확인
kubectl auth can-i get pods --namespace=elk-stack
kubectl auth can-i create jobs --namespace=elk-stack

# ServiceAccount 생성 (필요시)
kubectl create serviceaccount elk-resolver
kubectl create clusterrolebinding elk-resolver --clusterrole=cluster-admin --serviceaccount=default:elk-resolver
```

#### 4. API 키 문제
```bash
# .env 파일 권한 확인
chmod 600 config/.env

# 환경 변수 로드 확인
python3 -c "from src.load_env import load_config_with_env; print(load_config_with_env())"
```

## 보안 고려사항

### 1. 파일 권한 설정
```bash
# 민감한 파일 권한 설정
chmod 600 config/.env
chmod 700 config/
chown -R your_user:your_group /path/to/elk-auto-resolver
```

### 2. 방화벽 설정
```bash
# 필요한 포트만 열기
sudo ufw allow 5432  # PostgreSQL
sudo ufw allow 9200  # Elasticsearch (필요시)
sudo ufw enable
```

### 3. 정기 업데이트
```bash
# 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python 패키지 업데이트
pip install --upgrade -r requirements.txt
```

## 백업 및 복구

### 데이터베이스 백업
```bash
# 백업 생성
pg_dump -h localhost -U elk_user elk_resolver > elk_resolver_backup.sql

# 복구
psql -h localhost -U elk_user elk_resolver < elk_resolver_backup.sql
```

### 설정 파일 백업
```bash
# 설정 파일들 백업
tar -czf elk_resolver_config_backup.tar.gz config/ sql/
```

## 성능 최적화

### 1. 리소스 할당 조정
```yaml
# config.yaml에서 조정
monitoring:
  check_interval: 120  # 간격 늘리기
  error_threshold: 50  # 임계값 높이기

log_management:
  retention_days: 3    # 보존 기간 단축
```

### 2. 데이터베이스 최적화
```sql
-- 인덱스 확인 및 생성
CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_error_logs_type ON error_logs(error_type);

-- 통계 업데이트
ANALYZE;
```

### 3. 로그 레벨 조정
```python
# 로그 레벨을 WARNING으로 변경 (성능 향상)
logging.basicConfig(level=logging.WARNING)
```

이 가이드를 따라하면 새로운 환경에서도 ELK Auto Resolver를 성공적으로 배포하고 실행할 수 있습니다.