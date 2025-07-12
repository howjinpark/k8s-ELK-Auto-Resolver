#!/usr/bin/env python3
"""
HTTPS 환경용 ELK Auto Resolver 시작 스크립트
"""

import os
import sys
import time
import logging
import subprocess
import signal
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(project_root / 'elk_auto_resolver.log'))
    ]
)

logger = logging.getLogger(__name__)

class HTTPSELKResolver:
    """HTTPS 환경용 ELK Auto Resolver 관리자"""
    
    def __init__(self):
        self.port_forward_process = None
        self.running = True
        self.monitor = None
        
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        logger.info(f"종료 신호 수신: {signum} - 정리 작업 시작")
        self.running = False
        
        # 모니터 중지
        if self.monitor:
            self.monitor.running = False
            logger.info("ErrorMonitor 중지 신호 전송")
        
        self.cleanup()
        logger.info("ELK Auto Resolver 종료")
        sys.exit(0)
    
    def setup_port_forwarding(self):
        """Elasticsearch 포트 포워딩 설정"""
        try:
            logger.info("Elasticsearch 포트 포워딩 설정 중...")
            
            # 기존 포트 포워딩 프로세스 종료
            self._kill_existing_port_forwards()
            
            # 새로운 포트 포워딩 시작
            cmd = [
                'kubectl', 'port-forward', 
                '-n', 'elk-stack', 
                'svc/elasticsearch', 
                '9200:9200'
            ]
            
            self.port_forward_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            # 포트 포워딩이 준비될 때까지 대기
            logger.info("포트 포워딩 준비 대기 중...")
            time.sleep(5)
            
            # 연결 테스트
            if self._test_connection():
                logger.info("✅ 포트 포워딩 설정 완료")
                return True
            else:
                logger.error("❌ 포트 포워딩 연결 테스트 실패")
                return False
                
        except Exception as e:
            logger.error(f"포트 포워딩 설정 실패: {e}")
            return False
    
    def _kill_existing_port_forwards(self):
        """기존 포트 포워딩 프로세스 종료"""
        try:
            # Linux/macOS
            if os.name != 'nt':
                subprocess.run(
                    ['pkill', '-f', 'kubectl.*port-forward.*elasticsearch'],
                    capture_output=True
                )
            # Windows
            else:
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'kubectl.exe'],
                    capture_output=True
                )
            time.sleep(2)
        except Exception as e:
            logger.warning(f"기존 포트 포워딩 종료 중 오류: {e}")
    
    def _test_connection(self):
        """HTTPS 연결 테스트"""
        try:
            from elasticsearch import Elasticsearch
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            es = Elasticsearch(
                ['https://localhost:9200'],
                verify_certs=False,
                ssl_show_warn=False,
                ssl_assert_hostname=False,
                basic_auth=('elastic', self.config['elasticsearch']['password']),
                request_timeout=10
            )
            
            return es.ping()
        except Exception as e:
            logger.error(f"연결 테스트 실패: {e}")
            return False
    
    def start_monitoring(self):
        """에러 모니터링 시작"""
        try:
            from src.error_monitor import ErrorMonitor
            from src.ai_analyzer import AIAnalyzer
            from src.auto_resolver import AutoResolver
            from src.slack_notifier import SlackNotifier
            
            logger.info("ELK Auto Resolver 모듈 초기화 중...")
            
            # 모듈 초기화
            self.monitor = ErrorMonitor()
            analyzer = AIAnalyzer()
            resolver = AutoResolver()
            slack = SlackNotifier()
            
            # Elasticsearch 연결
            if not self.monitor.connect_elasticsearch():
                logger.error("ErrorMonitor Elasticsearch 연결 실패")
                return False
            
            # 에러 패턴 로드
            if not self.monitor.load_error_patterns():
                logger.error("에러 패턴 로드 실패")
                return False
            
            logger.info("✅ ELK Auto Resolver 시작됨")
            
            # 메인 모니터링 루프
            for errors in self.monitor.monitor_loop():
                if not self.running or not self.monitor.running:
                    logger.info("종료 신호 감지 - 모니터링 루프 중단")
                    break
                    
                if errors:
                    logger.info(f"🔍 {len(errors)}개의 에러 감지됨")
                    
                    # AI 분석
                    for error in errors:
                        try:
                            logger.info(f"🔍 에러 분석 시작: {error['error_type']}")
                            analysis_result = analyzer.analyze_error(error)
                            
                            if analysis_result and analysis_result.get('solution_type'):
                                # 해결책 출처 구분
                                if analysis_result.get('is_reused', False):
                                    logger.info(f"📚 DB 재사용 해결책 발견: {analysis_result['solution_type']}")
                                else:
                                    logger.info(f"🤖 AI 분석 해결책 발견: {analysis_result['solution_type']}")
                                
                                # 자동 해결 실행
                                execution_result = resolver.resolve_error(analysis_result)
                                
                                if execution_result['success']:
                                    if analysis_result.get('is_reused', False):
                                        logger.info("✅ 에러 자동 해결 성공 (DB 재사용)")
                                    else:
                                        logger.info("✅ 에러 자동 해결 성공 (AI 분석)")
                                    
                                    # Slack 해결 성공 알림 전송
                                    slack.send_resolution_success(
                                        error_type=error['error_type'],
                                        solution_type=analysis_result['solution_type'],
                                        solution_summary=analysis_result.get('description', '해결 완료'),
                                        is_reused=analysis_result.get('is_reused', False)
                                    )
                                else:
                                    logger.warning(f"⚠️ 에러 해결 실패: {execution_result['errors']}")
                                    
                                    # Slack 해결 실패 알림 전송
                                    slack.send_resolution_failed(
                                        error_type=error['error_type'],
                                        solution_type=analysis_result['solution_type'],
                                        failure_reason=execution_result.get('failure_reason', '알 수 없는 오류'),
                                        error_details=execution_result.get('errors', [])
                                    )
                            else:
                                logger.info("해결책을 찾을 수 없음 - AI 분석 결과가 없거나 solution_type이 누락됨")
                                
                        except Exception as e:
                            logger.error(f"에러 처리 중 오류: {e}")
                            continue
            
            return True
            
        except Exception as e:
            logger.error(f"모니터링 시작 실패: {e}")
            return False
    
    def cleanup(self):
        """정리 작업"""
        logger.info("정리 작업 시작...")
        
        # 모니터 중지
        if self.monitor:
            self.monitor.running = False
            logger.info("모니터 종료 요청")
        
        # 포트 포워딩 프로세스 종료
        if self.port_forward_process:
            try:
                logger.info(f"포트 포워딩 프로세스 종료 시도 (PID: {self.port_forward_process.pid})")
                
                if os.name != 'nt':
                    # Linux/macOS: 프로세스 그룹 전체 종료
                    try:
                        os.killpg(os.getpgid(self.port_forward_process.pid), signal.SIGTERM)
                        self.port_forward_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        logger.warning("정상 종료 시간 초과 - 강제 종료")
                        os.killpg(os.getpgid(self.port_forward_process.pid), signal.SIGKILL)
                        self.port_forward_process.wait(timeout=2)
                else:
                    # Windows
                    self.port_forward_process.terminate()
                    try:
                        self.port_forward_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.port_forward_process.kill()
                        self.port_forward_process.wait(timeout=2)
                        
                logger.info("포트 포워딩 프로세스 종료됨")
                
            except Exception as e:
                logger.error(f"포트 포워딩 종료 실패: {e}")
                # 최종 수단으로 pkill 사용
                try:
                    subprocess.run(['pkill', '-f', 'kubectl.*port-forward.*elasticsearch'], 
                                 capture_output=True, timeout=5)
                    logger.info("백업 종료 명령어 실행 완료")
                except Exception as backup_e:
                    logger.error(f"백업 종료 명령어 실패: {backup_e}")
        
        # 짧은 대기 후 충분한 시간 제공
        time.sleep(1)
        logger.info("정리 작업 완료")
    
    def run(self):
        """메인 실행 함수"""
        logger.info("🚀 HTTPS ELK Auto Resolver 시작")
        
        try:
            # 포트 포워딩 설정
            if not self.setup_port_forwarding():
                logger.error("포트 포워딩 설정 실패")
                return 1
            
            # 모니터링 시작
            if not self.start_monitoring():
                logger.error("모니터링 시작 실패")
                return 1
            
            logger.info("ELK Auto Resolver 정상 종료")
            return 0
            
        except KeyboardInterrupt:
            logger.info("사용자에 의한 중단 (Ctrl+C)")
            self.running = False
            return 0
        except Exception as e:
            logger.error(f"실행 중 오류: {e}")
            self.running = False
            return 1
        finally:
            self.cleanup()

def main():
    """메인 함수"""
    print("=== HTTPS ELK Auto Resolver ===")
    print("HTTPS 환경에서 ELK Auto Resolver를 실행합니다.")
    print("Ctrl+C로 중단할 수 있습니다.\n")
    
    # 필요한 모듈 확인
    required_modules = ['elasticsearch', 'kubernetes', 'yaml', 'psycopg2']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ 필요한 모듈이 없습니다: {', '.join(missing_modules)}")
        print("pip install -r requirements.txt 를 실행하세요.")
        return 1
    
    # Kubernetes 설정 확인
    try:
        subprocess.run(['kubectl', 'version', '--client'], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ kubectl이 설치되지 않았거나 접근할 수 없습니다.")
        return 1
    
    # ELK 네임스페이스 확인
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'namespace', 'elk-stack'],
            capture_output=True, check=True
        )
    except subprocess.CalledProcessError:
        print("❌ elk-stack 네임스페이스가 존재하지 않습니다.")
        return 1
    
    # 해결기 실행
    resolver = HTTPSELKResolver()
    return resolver.run()

if __name__ == "__main__":
    sys.exit(main())