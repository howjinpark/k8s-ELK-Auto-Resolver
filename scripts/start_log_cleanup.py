#!/usr/bin/env python3
"""
ELK Auto Resolver 로그 정리 스케줄러 실행 스크립트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from src.log_cleanup_scheduler import main

if __name__ == "__main__":
    main()