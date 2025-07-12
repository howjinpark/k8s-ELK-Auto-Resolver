#!/usr/bin/env python3
"""
ELK Auto Resolver 메인 애플리케이션
에러 탐지 → AI 분석 → 자동 해결 전체 워크플로우 실행
"""

import sys
import time
import logging
import signal
from datetime import datetime
from typing import Dict, List
import threading

from error_monitor import ErrorMonitor
from ai_analyzer import AIAnalyzer
from auto_resolver import AutoResolver
from database import DatabaseManager

class ELKAutoResolver:
    """ELK Auto Resolver 메인 클래스"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        메인 애플리케이션 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config_path = config_path
        self.running = False
        
        # 로깅 설정
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 모듈 초기화
        try:
            self.error_monitor = ErrorMonitor(config_path)
            self.ai_analyzer = AIAnalyzer(config_path)
            self.auto_resolver = AutoResolver(config_path)
            self.db = DatabaseManager(config_path)
            
            self.logger.info("ELK Auto Resolver 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"초기화 실패: {e}")
            sys.exit(1)
        
        # 통계 정보
        self.stats = {
            'detected_errors': 0,
            'analyzed_errors': 0,
            'resolved_errors': 0,
            'failed_resolutions': 0,
            'start_time': datetime.now()
        }
        
        # 신호 핸들러 설정
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/elk-auto-resolver.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러 (종료 처리)"""
        self.logger.info(f"종료 신호 수신: {signum}")
        self.stop()
    
    def start(self):
        """메인 서비스 시작"""
        self.logger.info("=== ELK Auto Resolver 시작 ===")
        self.running = True
        
        # 시작 전 연결 테스트
        if not self._initial_health_check():
            self.logger.error("초기 연결 테스트 실패")
            return False
        
        # 통계 출력 스레드 시작
        stats_thread = threading.Thread(target=self._stats_reporter, daemon=True)
        stats_thread.start()
        
        try:
            # 메인 모니터링 루프
            for detected_errors in self.error_monitor.monitor_loop():
                if not self.running:
                    break
                
                if detected_errors:
                    self.stats['detected_errors'] += len(detected_errors)
                    self.logger.info(f"새로운 에러 {len(detected_errors)}개 탐지")
                    
                    # 에러 분석 실행
                    self._process_errors(detected_errors)
                
        except KeyboardInterrupt:
            self.logger.info("사용자 인터럽트")
        except Exception as e:
            self.logger.error(f"메인 루프 오류: {e}")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """서비스 중지"""
        self.logger.info("ELK Auto Resolver 중지 중...")
        self.running = False
        
        # 최종 통계 출력
        self._print_final_stats()
    
    def _initial_health_check(self) -> bool:
        """초기 연결 상태 확인"""
        self.logger.info("초기 연결 상태 확인 중...")
        
        try:
            # Elasticsearch 연결 확인
            if not self.error_monitor.connect_elasticsearch():
                self.logger.error("Elasticsearch 연결 실패")
                return False
            
            # 데이터베이스 연결 확인
            if not self.db.connect():
                self.logger.error("PostgreSQL 연결 실패")
                return False
            
            self.db.disconnect()
            
            # 에러 패턴 로드
            if not self.error_monitor.load_error_patterns():
                self.logger.error("에러 패턴 로드 실패")
                return False
            
            self.logger.info("모든 연결 확인 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"연결 확인 중 오류: {e}")
            return False
    
    def _process_errors(self, detected_errors: List[Dict]):
        """
        탐지된 에러들을 처리
        
        Args:
            detected_errors: 탐지된 에러 리스트
        """
        try:
            self.logger.info(f"에러 분석 시작: {len(detected_errors)}개")
            
            # AI 분석 실행
            analysis_results = self.ai_analyzer.analyze_multiple_errors(detected_errors)
            self.stats['analyzed_errors'] += len(analysis_results)
            
            if not analysis_results:
                self.logger.warning("분석된 에러가 없음")
                return
            
            self.logger.info(f"AI 분석 완료: {len(analysis_results)}개")
            
            # 자동 해결 실행
            self._execute_resolutions(analysis_results)
            
        except Exception as e:
            self.logger.error(f"에러 처리 중 오류: {e}")
    
    def _execute_resolutions(self, analysis_results: List[Dict]):
        """
        분석 결과를 바탕으로 자동 해결 실행
        
        Args:
            analysis_results: AI 분석 결과 리스트
        """
        try:
            self.logger.info(f"자동 해결 시작: {len(analysis_results)}개")
            
            # 자동 해결 실행
            resolution_results = self.auto_resolver.resolve_multiple_errors(analysis_results)
            
            # 결과 통계 업데이트
            for result in resolution_results:
                if result['success']:
                    self.stats['resolved_errors'] += 1
                else:
                    self.stats['failed_resolutions'] += 1
            
            # 결과 요약 출력
            successful = sum(1 for r in resolution_results if r['success'])
            failed = len(resolution_results) - successful
            
            self.logger.info(f"자동 해결 완료: 성공 {successful}개, 실패 {failed}개")
            
            # 상세 결과 로깅
            for i, result in enumerate(resolution_results, 1):
                analysis = result.get('analysis_result', {})
                status = "✅ 성공" if result['success'] else "❌ 실패"
                
                self.logger.info(
                    f"  {i}. {analysis.get('solution_type', 'unknown')} - "
                    f"{status} ({result['execution_time']}초)"
                )
                
                if not result['success'] and result['errors']:
                    for error in result['errors']:
                        self.logger.warning(f"    오류: {error}")
            
        except Exception as e:
            self.logger.error(f"자동 해결 실행 중 오류: {e}")
    
    def _stats_reporter(self):
        """주기적으로 통계 정보 출력"""
        while self.running:
            try:
                time.sleep(300)  # 5분마다 출력
                
                if self.running:
                    uptime = datetime.now() - self.stats['start_time']
                    
                    self.logger.info("=== 통계 정보 ===")
                    self.logger.info(f"가동 시간: {uptime}")
                    self.logger.info(f"탐지된 에러: {self.stats['detected_errors']}개")
                    self.logger.info(f"분석된 에러: {self.stats['analyzed_errors']}개")
                    self.logger.info(f"해결된 에러: {self.stats['resolved_errors']}개")
                    self.logger.info(f"해결 실패: {self.stats['failed_resolutions']}개")
                    
                    if self.stats['analyzed_errors'] > 0:
                        success_rate = (self.stats['resolved_errors'] / self.stats['analyzed_errors']) * 100
                        self.logger.info(f"해결 성공률: {success_rate:.1f}%")
                    
                    self.logger.info("================")
                
            except Exception as e:
                self.logger.error(f"통계 출력 오류: {e}")
    
    def _print_final_stats(self):
        """최종 통계 출력"""
        uptime = datetime.now() - self.stats['start_time']
        
        print("\n" + "="*50)
        print("ELK Auto Resolver 최종 통계")
        print("="*50)
        print(f"가동 시간: {uptime}")
        print(f"탐지된 에러: {self.stats['detected_errors']}개")
        print(f"분석된 에러: {self.stats['analyzed_errors']}개")
        print(f"해결된 에러: {self.stats['resolved_errors']}개")
        print(f"해결 실패: {self.stats['failed_resolutions']}개")
        
        if self.stats['analyzed_errors'] > 0:
            success_rate = (self.stats['resolved_errors'] / self.stats['analyzed_errors']) * 100
            print(f"해결 성공률: {success_rate:.1f}%")
        
        print("="*50)
    
    def run_once(self) -> Dict:
        """
        한 번만 실행 (테스트용)
        
        Returns:
            실행 결과
        """
        self.logger.info("일회성 실행 모드")
        
        if not self._initial_health_check():
            return {'success': False, 'error': '초기 연결 테스트 실패'}
        
        try:
            # 에러 검색
            errors = self.error_monitor.search_errors(300)  # 최근 5분
            
            if not errors:
                return {'success': True, 'message': '탐지된 에러 없음'}
            
            # 에러 처리
            processed_errors = self.error_monitor.process_errors(errors)
            
            if not processed_errors:
                return {'success': True, 'message': '처리할 에러 없음'}
            
            # AI 분석
            analysis_results = self.ai_analyzer.analyze_multiple_errors(processed_errors)
            
            if not analysis_results:
                return {'success': True, 'message': '분석할 수 있는 에러 없음'}
            
            # 자동 해결
            resolution_results = self.auto_resolver.resolve_multiple_errors(analysis_results)
            
            # 결과 반환
            successful = sum(1 for r in resolution_results if r['success'])
            
            return {
                'success': True,
                'detected': len(errors),
                'processed': len(processed_errors),
                'analyzed': len(analysis_results),
                'resolved': successful,
                'failed': len(resolution_results) - successful
            }
            
        except Exception as e:
            self.logger.error(f"일회성 실행 오류: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """메인 함수"""
    print("ELK Auto Resolver v1.0")
    print("에러 탐지 → AI 분석 → 자동 해결")
    print("-" * 40)
    
    # 실행 모드 확인
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # 일회성 실행
        resolver = ELKAutoResolver()
        result = resolver.run_once()
        print(f"실행 결과: {result}")
    else:
        # 지속적 실행
        resolver = ELKAutoResolver()
        resolver.start()


if __name__ == "__main__":
    main()