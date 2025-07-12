#!/bin/bash

# ELK Auto Resolver 자동 설치 스크립트
# Ubuntu 20.04+ 환경용

set -e  # 오류 발생 시 스크립트 중단

echo "=== ELK Auto Resolver 설치 시작 ==="
echo ""
echo "⚠️  설치 전 필수 확인사항:"
echo "1. ELK Stack이 Kubernetes에 설치되어 있어야 합니다"
echo "2. Perplexity AI API 키가 준비되어 있어야 합니다" 
echo "3. Slack 웹훅 URL이 준비되어 있어야 합니다"
echo ""
echo "선수조건 가이드: docs/PREREQUISITES.md"
echo ""
read -p "선수조건을 모두 준비했습니까? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "설치를 중단합니다. 선수조건을 먼저 준비해주세요."
    exit 1
fi
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. 시스템 요구사항 확인
log_info "시스템 요구사항 확인 중..."

# Ubuntu 버전 확인
if ! lsb_release -a 2>/dev/null | grep -q "Ubuntu"; then
    log_warning "Ubuntu가 아닌 시스템에서 실행 중입니다. 일부 명령어가 다를 수 있습니다."
fi

# 메모리 확인
total_mem=$(free -m | awk 'NR==2{print $2}')
if [ "$total_mem" -lt 4000 ]; then
    log_warning "메모리가 4GB 미만입니다 (${total_mem}MB). 성능에 영향을 줄 수 있습니다."
fi

# 디스크 공간 확인
available_space=$(df -h . | awk 'NR==2{print $4}' | sed 's/G//')
if [ "${available_space%.*}" -lt 20 ]; then
    log_warning "디스크 여유 공간이 20GB 미만입니다. 충분한 공간을 확보하세요."
fi

log_success "시스템 요구사항 확인 완료"

# 2. 필수 패키지 설치
log_info "시스템 패키지 업데이트 및 필수 패키지 설치 중..."

sudo apt update -y
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    curl \
    wget \
    build-essential \
    libpq-dev \
    postgresql \
    postgresql-contrib

log_success "필수 패키지 설치 완료"

# 3. Python 버전 확인
log_info "Python 버전 확인 중..."
python_version=$(python3 --version | cut -d' ' -f2)
log_info "Python 버전: $python_version"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    log_success "Python 버전 확인 완료 (3.8+)"
else
    log_error "Python 3.8 이상이 필요합니다. 현재 버전: $python_version"
    exit 1
fi

# 4. PostgreSQL 설정
log_info "PostgreSQL 설정 중..."

# PostgreSQL 서비스 시작
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 데이터베이스 사용자 및 데이터베이스 생성
DB_PASSWORD="elk_resolver_$(date +%s)"
log_info "데이터베이스 비밀번호: $DB_PASSWORD"

sudo -u postgres psql -c "DROP USER IF EXISTS elk_user;" 2>/dev/null || true
sudo -u postgres psql -c "DROP DATABASE IF EXISTS elk_resolver;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER elk_user WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE elk_resolver OWNER elk_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE elk_resolver TO elk_user;"

log_success "PostgreSQL 설정 완료"

# 5. 프로젝트 디렉토리 설정
log_info "프로젝트 디렉토리 설정 중..."

PROJECT_DIR="/opt/elk-auto-resolver"
if [ -d "$PROJECT_DIR" ]; then
    log_warning "기존 설치 디렉토리가 발견되었습니다. 백업 중..."
    sudo mv "$PROJECT_DIR" "${PROJECT_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
fi

sudo mkdir -p "$PROJECT_DIR"
sudo chown -R $USER:$USER "$PROJECT_DIR"

# 현재 디렉토리에서 프로젝트 파일 복사
if [ -f "config/config.yaml" ]; then
    log_info "현재 디렉토리에서 프로젝트 파일 복사 중..."
    cp -r . "$PROJECT_DIR/"
else
    log_error "프로젝트 파일을 찾을 수 없습니다. 올바른 디렉토리에서 실행하세요."
    exit 1
fi

cd "$PROJECT_DIR"
log_success "프로젝트 디렉토리 설정 완료: $PROJECT_DIR"

# 6. Python 가상환경 설정
log_info "Python 가상환경 설정 중..."

python3 -m venv venv
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip

# 필수 패키지 설치
pip install -r requirements.txt

log_success "Python 가상환경 및 패키지 설치 완료"

# 7. 환경 변수 파일 생성
log_info "환경 변수 파일 설정 중..."

if [ ! -f "config/.env" ]; then
    cp config/.env.example config/.env
    
    # 데이터베이스 비밀번호 자동 설정
    sed -i "s/your_secure_database_password/$DB_PASSWORD/" config/.env
    
    log_warning "config/.env 파일을 수정하여 API 키들을 설정하세요:"
    log_warning "- PERPLEXITY_API_KEY: Perplexity AI API 키"
    log_warning "- SLACK_WEBHOOK_URL: Slack 웹훅 URL"
    log_warning "- ELASTICSEARCH_PASSWORD: Elasticsearch 비밀번호"
else
    log_info "기존 .env 파일이 발견되었습니다."
fi

# 파일 권한 설정
chmod 600 config/.env
chmod 700 config/

log_success "환경 변수 파일 설정 완료"

# 8. 데이터베이스 스키마 생성
log_info "데이터베이스 스키마 생성 중..."

if [ -f "sql/create_schema.sql" ]; then
    PGPASSWORD="$DB_PASSWORD" psql -h localhost -U elk_user -d elk_resolver -f sql/create_schema.sql
    log_success "데이터베이스 스키마 생성 완료"
else
    log_warning "sql/create_schema.sql 파일을 찾을 수 없습니다. 수동으로 스키마를 생성하세요."
fi

# 9. kubectl 설치 (선택사항)
log_info "kubectl 설치 확인 중..."

if ! command -v kubectl &> /dev/null; then
    log_info "kubectl 설치 중..."
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    sudo mv kubectl /usr/local/bin/
    log_success "kubectl 설치 완료"
else
    log_info "kubectl이 이미 설치되어 있습니다."
fi

# 10. 시스템 서비스 생성 (선택사항)
log_info "시스템 서비스 생성 중..."

cat << EOF | sudo tee /etc/systemd/system/elk-auto-resolver.service > /dev/null
[Unit]
Description=ELK Auto Resolver
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python scripts/start_resolver.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

log_success "시스템 서비스 생성 완료"

# 11. 설치 완료 및 다음 단계 안내
echo ""
echo "=== ELK Auto Resolver 설치 완료 ==="
echo ""
log_success "설치가 성공적으로 완료되었습니다!"
echo ""
echo "다음 단계:"
echo ""
echo "1. 환경 변수 설정 (중요!):"
echo "   nano $PROJECT_DIR/config/.env"
echo ""
echo "   다음 항목들을 실제 값으로 수정하세요:"
echo "   - PERPLEXITY_API_KEY=your_actual_perplexity_api_key"
echo "   - SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/ACTUAL/WEBHOOK"
echo "   - ELASTICSEARCH_PASSWORD=your_elasticsearch_password"
echo ""
echo "2. Kubernetes 클러스터 연결 설정:"
echo "   kubectl cluster-info"
echo ""
echo "3. ELK Stack 배포 (필요시):"
echo "   kubectl apply -f $PROJECT_DIR/elk/"
echo ""
echo "4. 연결 테스트:"
echo "   cd $PROJECT_DIR"
echo "   source venv/bin/activate"
echo "   python3 -c \"from src.load_env import load_config_with_env; print('✅ 설정 로드 성공')\" "
echo ""
echo "5. ELK Auto Resolver 실행:"
echo "   python3 scripts/start_resolver.py"
echo ""
echo "또는 서비스로 실행:"
echo "   sudo systemctl enable elk-auto-resolver"
echo "   sudo systemctl start elk-auto-resolver"
echo "   sudo systemctl status elk-auto-resolver"
echo ""
echo "로그 확인:"
echo "   tail -f $PROJECT_DIR/elk_resolver.log"
echo "   journalctl -u elk-auto-resolver -f"
echo ""
echo "자세한 설정 방법은 docs/DEPLOYMENT_GUIDE.md를 참고하세요."
echo ""
log_info "데이터베이스 비밀번호: $DB_PASSWORD"
log_warning "이 비밀번호를 안전한 곳에 저장하세요!"
echo ""