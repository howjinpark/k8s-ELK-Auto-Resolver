#!/bin/bash

# ELK Auto Resolver 배포용 패키지 생성 스크립트
# 다른 컴퓨터로 전송할 수 있는 완전한 패키지를 만듭니다.

set -e

echo "=== ELK Auto Resolver 배포 패키지 생성 ==="

# 현재 디렉토리가 프로젝트 루트인지 확인
if [ ! -f "config/config.yaml" ]; then
    echo "❌ 프로젝트 루트 디렉토리에서 실행하세요."
    exit 1
fi

# 임시 작업 디렉토리 생성
TEMP_DIR="/tmp/elk-auto-resolver-deploy"
PACKAGE_NAME="elk-auto-resolver-$(date +%Y%m%d_%H%M%S)"
PACKAGE_DIR="$TEMP_DIR/$PACKAGE_NAME"

echo "📦 패키지 디렉토리 생성: $PACKAGE_DIR"
rm -rf "$TEMP_DIR"
mkdir -p "$PACKAGE_DIR"

# 필요한 파일들 복사
echo "📄 프로젝트 파일 복사 중..."

# 소스 코드
cp -r src/ "$PACKAGE_DIR/"
cp -r config/ "$PACKAGE_DIR/"
cp -r scripts/ "$PACKAGE_DIR/"
cp -r docs/ "$PACKAGE_DIR/"
cp -r sql/ "$PACKAGE_DIR/"

# ELK Stack 배포 파일들 (있는 경우)
if [ -d "elk/" ]; then
    cp -r elk/ "$PACKAGE_DIR/"
fi

# 테스트 환경 (있는 경우)
if [ -d "testelk/" ]; then
    cp -r testelk/ "$PACKAGE_DIR/"
fi

# 루트 파일들
cp README.md "$PACKAGE_DIR/" 2>/dev/null || echo "README.md 없음"
cp requirements.txt "$PACKAGE_DIR/"
cp install.sh "$PACKAGE_DIR/"
cp *.yaml "$PACKAGE_DIR/" 2>/dev/null || true

# .env 파일은 .env.example만 복사 (보안상 실제 .env는 제외)
if [ -f "config/.env" ]; then
    echo "⚠️  보안을 위해 .env 파일은 제외됩니다. .env.example을 참고하여 새로 생성하세요."
fi

# 제외할 파일들 정리
echo "🧹 불필요한 파일 정리 중..."
find "$PACKAGE_DIR" -name "*.pyc" -delete
find "$PACKAGE_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$PACKAGE_DIR" -name "*.log" -delete 2>/dev/null || true
find "$PACKAGE_DIR" -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true

# 배포용 설치 스크립트 생성
echo "🔧 배포용 README 생성 중..."
cat > "$PACKAGE_DIR/DEPLOY_README.md" << 'EOF'
# ELK Auto Resolver 배포 패키지

이 패키지는 새로운 환경에 ELK Auto Resolver를 설치하기 위한 모든 파일을 포함합니다.

## 빠른 설치

1. **패키지 압축 해제**
   ```bash
   tar -xzf elk-auto-resolver-YYYYMMDD_HHMMSS.tar.gz
   cd elk-auto-resolver-YYYYMMDD_HHMMSS
   ```

2. **자동 설치 실행**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **환경 변수 설정**
   ```bash
   nano config/.env
   # 다음 값들을 실제 값으로 수정:
   # - PERPLEXITY_API_KEY
   # - SLACK_WEBHOOK_URL  
   # - ELASTICSEARCH_PASSWORD
   ```

4. **ELK Auto Resolver 실행**
   ```bash
   source venv/bin/activate
   python3 scripts/start_resolver.py
   ```

## 상세 설치 가이드

자세한 설치 방법은 `docs/DEPLOYMENT_GUIDE.md`를 참고하세요.

## 필수 요구사항

- Ubuntu 20.04+ (또는 호환 Linux 배포판)
- Python 3.8+
- 최소 4GB RAM, 20GB 디스크 공간
- Kubernetes 클러스터 접근 권한
- 인터넷 연결 (API 호출용)

## 지원

문제가 발생하면 다음 문서들을 참고하세요:
- `docs/DEPLOYMENT_GUIDE.md` - 상세 설치 가이드
- `docs/ELK-STACK-TROUBLESHOOTING-GUIDE.md` - 문제 해결
- `docs/LOG_MANAGEMENT_GUIDE.md` - 로그 관리

## 보안 주의사항

- `.env` 파일에 실제 API 키와 비밀번호를 설정하세요
- 파일 권한을 적절히 설정하세요 (`chmod 600 config/.env`)
- 방화벽 설정을 확인하세요
EOF

# 배포용 빠른 시작 스크립트 생성
cat > "$PACKAGE_DIR/quick_start.sh" << 'EOF'
#!/bin/bash

echo "=== ELK Auto Resolver 빠른 시작 ==="
echo ""
echo "1. 자동 설치 실행:"
echo "   ./install.sh"
echo ""
echo "2. 환경 변수 설정:"
echo "   nano config/.env"
echo ""
echo "3. ELK Auto Resolver 실행:"
echo "   source venv/bin/activate"
echo "   python3 scripts/start_resolver.py"
echo ""
echo "자세한 가이드는 DEPLOY_README.md를 참고하세요."
EOF

chmod +x "$PACKAGE_DIR/quick_start.sh"

# 패키지 정보 파일 생성
cat > "$PACKAGE_DIR/PACKAGE_INFO.txt" << EOF
ELK Auto Resolver 배포 패키지

생성 일시: $(date)
생성 호스트: $(hostname)
패키지 버전: $(date +%Y.%m.%d)

포함된 구성 요소:
- ELK Auto Resolver 소스 코드
- 설치 스크립트 (install.sh)
- 설정 파일 템플릿
- 상세 문서
- ELK Stack 배포 파일 (선택사항)

설치 요구사항:
- Ubuntu 20.04+ 또는 호환 Linux
- Python 3.8+
- PostgreSQL
- kubectl (Kubernetes 접근용)
- 4GB+ RAM, 20GB+ 디스크

주요 API 의존성:
- Perplexity AI (에러 분석용)
- Slack Webhooks (알림용)
- Elasticsearch (로그 검색용)
- PostgreSQL (데이터 저장용)
EOF

# 압축 파일 생성
echo "📦 압축 파일 생성 중..."
cd "$TEMP_DIR"
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME/"

# 현재 디렉토리로 이동
FINAL_PATH="$(pwd)/${PACKAGE_NAME}.tar.gz"
mv "${PACKAGE_NAME}.tar.gz" "$FINAL_PATH"

# 정리
rm -rf "$TEMP_DIR"

# 완료 메시지
echo ""
echo "✅ 배포 패키지 생성 완료!"
echo ""
echo "📍 파일 위치: $FINAL_PATH"
echo "📏 파일 크기: $(du -h "$FINAL_PATH" | cut -f1)"
echo ""
echo "배포 방법:"
echo "1. 다른 서버에 파일 전송:"
echo "   scp $FINAL_PATH user@target-server:/tmp/"
echo ""
echo "2. 대상 서버에서 설치:"
echo "   cd /tmp"
echo "   tar -xzf ${PACKAGE_NAME}.tar.gz"
echo "   cd ${PACKAGE_NAME}"
echo "   ./install.sh"
echo ""
echo "3. 환경 변수 설정 후 실행"
echo "   nano config/.env"
echo "   source venv/bin/activate"  
echo "   python3 scripts/start_resolver.py"
echo ""
EOF