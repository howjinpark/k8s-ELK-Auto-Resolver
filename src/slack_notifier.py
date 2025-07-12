#!/usr/bin/env python3
"""
Slack 알림 모듈
ELK Auto Resolver의 에러 탐지, 해결 성공/실패 알림을 Slack으로 전송
"""

import json
import requests
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

class SlackNotifier:
    """Slack 알림 전송 클래스"""
    
    def __init__(self, config_path: str = None):
        """
        Slack 알림 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger(__name__)
        self.webhook_url = self.config['slack']['webhook_url']
        self.channel = self.config['slack']['channel']
        self.enabled = self.config['slack'].get('enabled', True)
        
    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드 (환경 변수 포함)"""
        try:
            from .load_env import load_config_with_env
            return load_config_with_env(config_path)
        except Exception as e:
            raise Exception(f"설정 파일을 읽을 수 없습니다: {e}")
    
    def _send_slack_message(self, message: Dict) -> bool:
        """
        Slack 메시지 전송
        
        Args:
            message: 전송할 메시지 데이터
            
        Returns:
            전송 성공 여부
        """
        try:
            if not self.enabled:
                self.logger.info("Slack 알림이 비활성화되어 있습니다")
                return True
            
            if not self.webhook_url:
                self.logger.warning("Slack webhook URL이 설정되지 않았습니다")
                return False
            
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("Slack 알림 전송 성공")
                return True
            else:
                self.logger.error(f"Slack 알림 전송 실패: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Slack 알림 전송 중 오류: {e}")
            return False
    
    def send_error_detected(self, error_type: str, error_count: int, error_samples: List[str]) -> bool:
        """
        에러 탐지 알림 전송
        
        Args:
            error_type: 에러 타입
            error_count: 에러 개수
            error_samples: 에러 샘플 메시지들
            
        Returns:
            전송 성공 여부
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 에러 샘플 정리 (최대 3개)
            sample_text = ""
            for i, sample in enumerate(error_samples[:3]):
                sample_text += f"{i+1}. {sample[:100]}...\n"
            
            message = {
                "channel": self.channel,
                "username": "ELK Auto Resolver",
                "icon_emoji": ":warning:",
                "attachments": [
                    {
                        "color": "danger",
                        "title": f"🚨 에러 탐지 알림",
                        "fields": [
                            {
                                "title": "에러 타입",
                                "value": error_type,
                                "short": True
                            },
                            {
                                "title": "발생 횟수",
                                "value": f"{error_count}회",
                                "short": True
                            },
                            {
                                "title": "탐지 시간",
                                "value": timestamp,
                                "short": True
                            },
                            {
                                "title": "자동 해결 시도",
                                "value": "진행 중...",
                                "short": True
                            }
                        ],
                        "text": f"*에러 샘플:*\n```{sample_text}```"
                    }
                ]
            }
            
            return self._send_slack_message(message)
            
        except Exception as e:
            self.logger.error(f"에러 탐지 알림 생성 실패: {e}")
            return False
    
    def send_resolution_success(self, error_type: str, solution_type: str, 
                              solution_summary: str, is_reused: bool = False) -> bool:
        """
        에러 해결 성공 알림 전송
        
        Args:
            error_type: 에러 타입
            solution_type: 해결책 타입
            solution_summary: 해결 방법 요약
            is_reused: DB 재사용 여부
            
        Returns:
            전송 성공 여부
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 해결 방법 구분
            resolution_method = "📚 DB 재사용" if is_reused else "🤖 AI 분석"
            
            message = {
                "channel": self.channel,
                "username": "ELK Auto Resolver",
                "icon_emoji": ":white_check_mark:",
                "attachments": [
                    {
                        "color": "good",
                        "title": f"✅ 에러 해결 완료",
                        "fields": [
                            {
                                "title": "에러 타입",
                                "value": error_type,
                                "short": True
                            },
                            {
                                "title": "해결 방법",
                                "value": resolution_method,
                                "short": True
                            },
                            {
                                "title": "해결 시간",
                                "value": timestamp,
                                "short": True
                            },
                            {
                                "title": "해결책 타입",
                                "value": solution_type,
                                "short": True
                            }
                        ],
                        "text": f"*해결 방법 요약:*\n```{solution_summary}```"
                    }
                ]
            }
            
            return self._send_slack_message(message)
            
        except Exception as e:
            self.logger.error(f"해결 성공 알림 생성 실패: {e}")
            return False
    
    def send_resolution_failed(self, error_type: str, solution_type: str, 
                             failure_reason: str, error_details: List[str]) -> bool:
        """
        에러 해결 실패 알림 전송
        
        Args:
            error_type: 에러 타입
            solution_type: 시도한 해결책 타입
            failure_reason: 실패 이유
            error_details: 실패 상세 정보
            
        Returns:
            전송 성공 여부
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 에러 상세 정보 정리
            error_text = ""
            for i, detail in enumerate(error_details[:3]):
                error_text += f"{i+1}. {detail[:150]}...\n"
            
            message = {
                "channel": self.channel,
                "username": "ELK Auto Resolver",
                "icon_emoji": ":x:",
                "attachments": [
                    {
                        "color": "warning",
                        "title": f"❌ 에러 해결 실패",
                        "fields": [
                            {
                                "title": "에러 타입",
                                "value": error_type,
                                "short": True
                            },
                            {
                                "title": "시도한 해결책",
                                "value": solution_type,
                                "short": True
                            },
                            {
                                "title": "실패 시간",
                                "value": timestamp,
                                "short": True
                            },
                            {
                                "title": "후속 조치",
                                "value": "수동 확인 필요",
                                "short": True
                            }
                        ],
                        "text": f"*실패 이유:*\n```{failure_reason}```\n\n*상세 정보:*\n```{error_text}```"
                    }
                ]
            }
            
            return self._send_slack_message(message)
            
        except Exception as e:
            self.logger.error(f"해결 실패 알림 생성 실패: {e}")
            return False
    
    def send_test_message(self) -> bool:
        """
        테스트 메시지 전송
        
        Returns:
            전송 성공 여부
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            message = {
                "channel": self.channel,
                "username": "ELK Auto Resolver",
                "icon_emoji": ":robot_face:",
                "text": f"🚀 ELK Auto Resolver 테스트 메시지\n시간: {timestamp}"
            }
            
            return self._send_slack_message(message)
            
        except Exception as e:
            self.logger.error(f"테스트 메시지 전송 실패: {e}")
            return False

def main():
    """테스트 실행"""
    import sys
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        notifier = SlackNotifier()
        
        if len(sys.argv) > 1 and sys.argv[1] == "test":
            # 테스트 메시지 전송
            print("테스트 메시지 전송 중...")
            result = notifier.send_test_message()
            print(f"전송 결과: {'성공' if result else '실패'}")
        else:
            print("사용법: python slack_notifier.py test")
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    main()