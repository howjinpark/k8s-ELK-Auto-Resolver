#!/usr/bin/env python3
"""
ELK Auto Resolver 로그 정리 스케줄러
- 정기적으로 오래된 로그와 데이터 정리
- 독립적으로 실행되는 백그라운드 서비스
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any
from .error_monitor import ErrorMonitor
from .database import DatabaseManager

class LogCleanupScheduler:
    """로그 정리 스케줄러 클래스"""
    
    def __init__(self, config_path: str = None):
        """
        스케줄러 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.cleanup_thread = None
        
        # 설정값 추출
        self.log_config = self.config.get('log_management', {})
        self.cleanup_interval = self.log_config.get('cleanup_interval_hours', 24) * 3600  # 초로 변환
        self.retention_days = self.log_config.get('retention_days', 7)
        
        # 컴포넌트 초기화
        self.error_monitor = None
        self.db_manager = None
        
        self.logger.info(f"로그 정리 스케줄러 초기화 완료 - 정리 간격: {self.cleanup_interval//3600}시간, 보존 기간: {self.retention_days}일")
    
    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드"""
        try:
            from .load_env import load_config_with_env
            return load_config_with_env(config_path)
        except Exception as e:
            raise Exception(f"설정 파일을 읽을 수 없습니다: {e}")
    
    def start(self):
        """스케줄러 시작"""
        if self.running:
            self.logger.warning("스케줄러가 이미 실행 중입니다")
            return
        
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.cleanup_thread.start()
        self.logger.info("로그 정리 스케줄러 시작됨")
    
    def stop(self):
        """스케줄러 중지"""
        self.running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=10)
        self.logger.info("로그 정리 스케줄러 중지됨")
    
    def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        last_cleanup = datetime.now() - timedelta(seconds=self.cleanup_interval)  # 즉시 첫 실행
        
        while self.running:
            try:
                current_time = datetime.now()
                time_since_cleanup = (current_time - last_cleanup).total_seconds()
                
                # 정리 시간이 되었는지 확인
                if time_since_cleanup >= self.cleanup_interval:
                    self.logger.info("정기 로그 정리 시작")
                    
                    success = self.perform_cleanup()
                    
                    if success:
                        last_cleanup = current_time
                        self.logger.info("정기 로그 정리 완료")
                    else:
                        self.logger.error("정기 로그 정리 실패")
                
                # 1분마다 체크
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"스케줄러 루프 오류: {e}")
                time.sleep(60)
    
    def perform_cleanup(self) -> bool:
        """로그 정리 수행"""
        try:
            cleanup_success = True
            
            # Elasticsearch 정리
            if self.log_config.get('elasticsearch_cleanup', {}).get('enabled', True):
                es_success = self._cleanup_elasticsearch()
                cleanup_success = cleanup_success and es_success
            
            # 데이터베이스 정리
            if self.log_config.get('database_cleanup', {}).get('enabled', True):
                db_success = self._cleanup_database()
                cleanup_success = cleanup_success and db_success
            
            # 시스템 리소스 정리
            self._cleanup_system_resources()
            
            return cleanup_success
            
        except Exception as e:
            self.logger.error(f"로그 정리 중 오류 발생: {e}")
            return False
    
    def _cleanup_elasticsearch(self) -> bool:
        """Elasticsearch 인덱스 정리"""
        try:
            # ErrorMonitor 인스턴스가 없으면 생성
            if not self.error_monitor:
                self.error_monitor = ErrorMonitor()
                if not self.error_monitor.connect_elasticsearch():
                    self.logger.error("Elasticsearch 연결 실패")
                    return False
            
            # 정리 실행
            self.error_monitor.cleanup_old_logs()
            return True
            
        except Exception as e:
            self.logger.error(f"Elasticsearch 정리 실패: {e}")
            return False
    
    def _cleanup_database(self) -> bool:
        """데이터베이스 정리"""
        try:
            # DatabaseManager 인스턴스가 없으면 생성
            if not self.db_manager:
                self.db_manager = DatabaseManager()
                if not self.db_manager.connect():
                    self.logger.error("데이터베이스 연결 실패")
                    return False
            
            # 각 테이블별 보존 기간 설정
            db_config = self.log_config.get('database_cleanup', {})
            
            # 에러 로그 정리
            error_retention = db_config.get('error_logs_retention_days', self.retention_days)
            self.db_manager.cleanup_old_error_logs(error_retention)
            
            return True
            
        except Exception as e:
            self.logger.error(f"데이터베이스 정리 실패: {e}")
            return False
    
    def _cleanup_system_resources(self):
        """시스템 리소스 정리"""
        try:
            # 메모리 사용량 로그
            import psutil
            memory_info = psutil.virtual_memory()
            self.logger.info(f"시스템 메모리 사용률: {memory_info.percent}%")
            
            # 디스크 사용량 로그
            disk_info = psutil.disk_usage('/')
            disk_percent = (disk_info.used / disk_info.total) * 100
            self.logger.info(f"디스크 사용률: {disk_percent:.1f}%")
            
            # 높은 사용률 경고
            if memory_info.percent > 85:
                self.logger.warning(f"높은 메모리 사용률 감지: {memory_info.percent}%")
            
            if disk_percent > 85:
                self.logger.warning(f"높은 디스크 사용률 감지: {disk_percent:.1f}%")
                
        except Exception as e:
            self.logger.warning(f"시스템 리소스 정보 수집 실패: {e}")
    
    def force_cleanup(self) -> bool:
        """강제 정리 실행"""
        self.logger.info("강제 로그 정리 시작")
        return self.perform_cleanup()
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """정리 상태 정보 반환"""
        return {
            'running': self.running,
            'cleanup_interval_hours': self.cleanup_interval // 3600,
            'retention_days': self.retention_days,
            'elasticsearch_cleanup_enabled': self.log_config.get('elasticsearch_cleanup', {}).get('enabled', True),
            'database_cleanup_enabled': self.log_config.get('database_cleanup', {}).get('enabled', True),
            'thread_alive': self.cleanup_thread.is_alive() if self.cleanup_thread else False
        }


# 독립 실행 스크립트
def main():
    """스케줄러 독립 실행"""
    import signal
    import sys
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/tmp/elk-auto-resolver-cleanup.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("ELK Auto Resolver 로그 정리 스케줄러 시작")
    
    # 스케줄러 생성 및 시작
    scheduler = LogCleanupScheduler()
    
    def signal_handler(signum, frame):
        logger.info("종료 신호 수신, 스케줄러 중지 중...")
        scheduler.stop()
        sys.exit(0)
    
    # 신호 처리기 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        scheduler.start()
        
        # 상태 정보 출력
        status = scheduler.get_cleanup_status()
        logger.info(f"스케줄러 상태: {status}")
        
        # 메인 스레드 대기
        while scheduler.running:
            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("사용자에 의한 중단")
    except Exception as e:
        logger.error(f"스케줄러 실행 오류: {e}")
    finally:
        scheduler.stop()
        logger.info("ELK Auto Resolver 로그 정리 스케줄러 종료")


if __name__ == "__main__":
    main()