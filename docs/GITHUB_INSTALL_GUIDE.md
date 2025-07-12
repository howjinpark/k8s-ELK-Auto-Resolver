# GitHub에서 ELK Auto Resolver 설치하기

## 간단한 설치 방법

### 1단계: GitHub에서 프로젝트 클론

```bash
# GitHub에서 직접 클론
git clone https://github.com/howjinpark/k8s-ELK-Auto-Resolver.git
cd k8s-ELK-Auto-Resolver

# 또는 ZIP 다운로드
wget https://github.com/howjinpark/k8s-ELK-Auto-Resolver/archive/main.zip
unzip main.zip
cd k8s-ELK-Auto-Resolver-main
```

### 2단계: 자동 설치 실행

```bash
# 설치 스크립트 실행 권한 부여
chmod +x install.sh

# 자동 설치 실행 (모든 의존성 자동 설치)
./install.sh
```

### 3단계: API 키 설정

```bash
# 환경 변수 파일 수정
nano config/.env

# 다음 값들을 실제 값으로 수정:
# PERPLEXITY_API_KEY=your_perplexity_api_key
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
# ELASTICSEARCH_PASSWORD=your_elasticsearch_password
```

### 4단계: 실행

```bash
# 가상환경 활성화
source venv/bin/activate

# ELK Auto Resolver 시작
python3 scripts/start_resolver.py
```

## 필요한 API 키 발급 방법

### Perplexity AI API 키
1. [Perplexity AI](https://www.perplexity.ai/) 방문
2. 회원가입 및 로그인
3. API 섹션에서 새 API 키 생성
4. 키를 복사하여 `.env` 파일에 추가

### Slack 웹훅 URL
1. Slack 워크스페이스에서 "앱 추가" 클릭
2. "Incoming Webhooks" 검색 및 추가
3. 알림을 받을 채널 선택
4. 생성된 웹훅 URL을 복사하여 `.env` 파일에 추가

## 시스템 요구사항

- **OS**: Ubuntu 20.04+ (또는 호환 Linux)
- **Python**: 3.8+
- **메모리**: 최소 4GB RAM
- **디스크**: 최소 20GB 여유 공간
- **네트워크**: 인터넷 연결 필요
- **권한**: sudo 권한 필요 (설치용)

## 설치 스크립트가 자동으로 처리하는 것들

1. **시스템 패키지 설치**
   - Python 3, pip, PostgreSQL
   - Git, curl, build-essential
   - kubectl (Kubernetes CLI)

2. **Python 환경 설정**
   - 가상환경 생성
   - 필수 Python 패키지 설치

3. **데이터베이스 설정**
   - PostgreSQL 사용자 및 데이터베이스 생성
   - 스키마 자동 생성
   - 권한 설정

4. **시스템 서비스 등록**
   - systemd 서비스 파일 생성
   - 자동 시작 설정

## 프로덕션 배포 (서비스로 실행)

```bash
# 시스템 서비스 활성화
sudo systemctl enable elk-auto-resolver
sudo systemctl start elk-auto-resolver

# 서비스 상태 확인
sudo systemctl status elk-auto-resolver

# 실시간 로그 확인
journalctl -u elk-auto-resolver -f
```

## 개발 환경 실행

```bash
# 포그라운드에서 실행 (개발/테스트용)
source venv/bin/activate
python3 scripts/start_resolver.py

# 백그라운드에서 실행
nohup python3 scripts/start_resolver.py > elk_resolver.log 2>&1 &
```

## 문제 해결

### 설치 실패 시
```bash
# 로그 확인
cat install.log

# 수동으로 의존성 설치
sudo apt update
sudo apt install python3 python3-pip postgresql -y
```

### 권한 문제 시
```bash
# PostgreSQL 연결 확인
sudo -u postgres psql -c "SELECT version();"

# 파일 권한 설정
chmod 600 config/.env
```

### Kubernetes 연결 문제 시
```bash
# kubectl 설정 확인
kubectl cluster-info
kubectl get nodes

# ELK Stack 네임스페이스 확인
kubectl get namespaces
kubectl get pods -n elk-stack
```

## 업데이트 방법

```bash
# 최신 버전으로 업데이트
git pull origin main

# 의존성 업데이트
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 서비스 재시작
sudo systemctl restart elk-auto-resolver
```

## 제거 방법

```bash
# 서비스 중지 및 비활성화
sudo systemctl stop elk-auto-resolver
sudo systemctl disable elk-auto-resolver

# 서비스 파일 제거
sudo rm /etc/systemd/system/elk-auto-resolver.service
sudo systemctl daemon-reload

# 데이터베이스 제거 (선택사항)
sudo -u postgres psql -c "DROP DATABASE elk_resolver;"
sudo -u postgres psql -c "DROP USER elk_user;"

# 프로젝트 디렉토리 제거
rm -rf /path/to/k8s-ELK-Auto-Resolver
```

이 방법으로 GitHub에서 직접 다운받아서 몇 분 안에 설치할 수 있습니다!