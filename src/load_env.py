#!/usr/bin/env python3
"""
환경 변수 로드 모듈
.env 파일에서 환경 변수를 읽어 config.yaml의 ${VAR} 형식을 치환
"""

import os
import re
import yaml
from pathlib import Path

def load_env_file(env_path: str = ".env") -> dict:
    """
    .env 파일에서 환경 변수 로드
    
    Args:
        env_path: .env 파일 경로
        
    Returns:
        환경 변수 딕셔너리
    """
    env_vars = {}
    
    if not os.path.exists(env_path):
        return env_vars
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars

def substitute_env_vars(config: dict, env_vars: dict) -> dict:
    """
    설정에서 ${VAR} 형식을 환경 변수로 치환
    
    Args:
        config: 설정 딕셔너리
        env_vars: 환경 변수 딕셔너리
        
    Returns:
        치환된 설정 딕셔너리
    """
    def substitute_value(value):
        if isinstance(value, str):
            # ${VAR} 형식 찾기
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            
            for match in matches:
                env_value = env_vars.get(match, os.getenv(match, ''))
                if env_value:
                    value = value.replace(f'${{{match}}}', env_value)
                else:
                    print(f"경고: 환경 변수 '{match}'가 설정되지 않았습니다.")
        
        elif isinstance(value, dict):
            return {k: substitute_value(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [substitute_value(item) for item in value]
        
        return value
    
    return substitute_value(config)

def load_config_with_env(config_path: str = None, env_path: str = None) -> dict:
    """
    환경 변수가 적용된 설정 파일 로드
    
    Args:
        config_path: 설정 파일 경로
        env_path: 환경 변수 파일 경로
        
    Returns:
        환경 변수가 적용된 설정 딕셔너리
    """
    import os
    from pathlib import Path
    
    # 프로젝트 루트 디렉토리 찾기
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    
    # 기본 경로 설정
    if config_path is None:
        config_path = str(project_root / 'config' / 'config.yaml')
    if env_path is None:
        env_path = str(project_root / 'config' / '.env')
    
    # .env 파일 로드
    env_vars = load_env_file(env_path)
    
    # config.yaml 파일 로드
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 환경 변수 치환
    config = substitute_env_vars(config, env_vars)
    
    return config

if __name__ == "__main__":
    # 테스트
    config = load_config_with_env()
    print("로드된 설정:")
    print(yaml.dump(config, default_flow_style=False, allow_unicode=True))