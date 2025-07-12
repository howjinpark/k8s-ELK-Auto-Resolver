#!/bin/bash

# ELK Auto Resolver 실행 스크립트
# 가상환경 활성화를 자동으로 처리합니다

set -e

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== ELK Auto Resolver 시작 ==="

# 가상환경 존재 확인
if [ ! -d "venv" ]; then
    echo "❌ 가상환경을 찾을 수 없습니다."
    echo "먼저 ./scripts/install.sh를 실행하세요."
    exit 1
fi

# 환경 변수 파일 확인
if [ ! -f "config/.env" ]; then
    echo "❌ 환경 변수 파일을 찾을 수 없습니다."
    echo "config/.env 파일을 생성하고 API 키를 설정하세요."
    exit 1
fi

# API 키 설정 확인
if grep -q "your_.*_api_key\|YOUR.*WEBHOOK" config/.env; then
    echo "⚠️  환경 변수가 기본값으로 설정되어 있습니다."
    echo "config/.env 파일에서 실제 API 키를 설정하세요:"
    echo "- PERPLEXITY_API_KEY"
    echo "- SLACK_WEBHOOK_URL"
    echo "- ELASTICSEARCH_PASSWORD"
    echo ""
    read -p "설정을 완료했습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "설정을 완료한 후 다시 실행하세요."
        exit 1
    fi
fi

echo "🔧 가상환경 활성화 중..."
source venv/bin/activate

echo "🚀 ELK Auto Resolver 시작..."
python3 scripts/start_resolver.py