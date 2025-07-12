#!/bin/bash

# ELK Auto Resolver 백그라운드 실행 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== ELK Auto Resolver 백그라운드 실행 ==="

# 기본 검증 (run.sh와 동일)
if [ ! -d "venv" ]; then
    echo "❌ 가상환경을 찾을 수 없습니다. 먼저 ./scripts/install.sh를 실행하세요."
    exit 1
fi

if [ ! -f "config/.env" ]; then
    echo "❌ config/.env 파일을 찾을 수 없습니다."
    exit 1
fi

# 이미 실행 중인지 확인
if pgrep -f "python3.*start_resolver.py" > /dev/null; then
    echo "⚠️  ELK Auto Resolver가 이미 실행 중입니다."
    echo "실행 중인 프로세스:"
    pgrep -f "python3.*start_resolver.py" | xargs ps -p
    echo ""
    read -p "기존 프로세스를 종료하고 새로 시작하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "기존 프로세스 종료 중..."
        pkill -f "python3.*start_resolver.py" || true
        sleep 2
    else
        echo "실행을 취소합니다."
        exit 1
    fi
fi

echo "🔧 가상환경 활성화 및 백그라운드 실행..."

# 백그라운드 실행
nohup bash -c "
source venv/bin/activate
python3 scripts/start_resolver.py
" > elk_resolver.log 2>&1 &

PID=$!
echo "✅ ELK Auto Resolver가 백그라운드에서 시작되었습니다."
echo "📍 프로세스 ID: $PID"
echo "📄 로그 파일: $SCRIPT_DIR/elk_resolver.log"
echo ""
echo "실시간 로그 확인:"
echo "  tail -f elk_resolver.log"
echo ""
echo "프로세스 상태 확인:"
echo "  ps aux | grep start_resolver"
echo ""
echo "프로세스 종료:"
echo "  kill $PID"
echo "  또는: pkill -f start_resolver"