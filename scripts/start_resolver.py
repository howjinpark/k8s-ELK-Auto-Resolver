#!/usr/bin/env python3
"""
ELK Auto Resolver 시작 스크립트 (프로젝트 루트에서 실행)
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트로 이동
project_root = Path(__file__).parent.parent
os.chdir(project_root)

# Python path 설정
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# 메인 스크립트 실행
if __name__ == "__main__":
    from src.start_https_resolver import HTTPSELKResolver
    
    resolver = HTTPSELKResolver()
    resolver.run()