#!/usr/bin/env python3
"""
ELK Auto Resolver 종료 테스트
"""

import sys
import time
import signal
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from src.start_https_resolver import HTTPSELKResolver

def test_shutdown():
    """종료 테스트"""
    print("=== ELK Auto Resolver 종료 테스트 ===")
    
    resolver = HTTPSELKResolver()
    
    print("5초 후 자동으로 종료 신호를 보냅니다...")
    print("또는 Ctrl+C를 눌러서 즉시 종료하세요.")
    
    def auto_shutdown():
        time.sleep(5)
        print("\n자동 종료 신호 전송...")
        resolver._signal_handler(signal.SIGINT, None)
    
    import threading
    shutdown_thread = threading.Thread(target=auto_shutdown, daemon=True)
    shutdown_thread.start()
    
    try:
        # 테스트용 간단한 실행
        print("ELK Auto Resolver 시작...")
        result = resolver.run()
        print(f"종료 코드: {result}")
        
    except KeyboardInterrupt:
        print("\nCtrl+C 감지 - 정상 종료")
    except Exception as e:
        print(f"오류 발생: {e}")
    
    print("테스트 완료")

if __name__ == "__main__":
    test_shutdown()