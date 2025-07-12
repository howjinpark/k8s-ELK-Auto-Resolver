#!/usr/bin/env python3
"""
ELK Stack 에러 모니터링 모듈
Elasticsearch에서 실시간으로 에러 로그를 감지하고 분석
"""

import time
import re
import yaml
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from elasticsearch import Elasticsearch
from .database import DatabaseManager
from .slack_notifier import SlackNotifier

class ErrorMonitor:
    """ELK Stack 에러 모니터링 클래스"""
    
    def __init__(self, config_path: str = None):
        """
        에러 모니터 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.es = None
        self.db = DatabaseManager(config_path)
        self.slack = SlackNotifier(config_path)
        self.logger = logging.getLogger(__name__)
        self.error_patterns = []
        self.last_check_time = datetime.now()
        self.running = True  # 종료 제어용 플래그
        
    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드 (환경 변수 포함)"""
        try:
            from .load_env import load_config_with_env
            return load_config_with_env(config_path)
        except Exception as e:
            raise Exception(f"설정 파일을 읽을 수 없습니다: {e}")
    
    def connect_elasticsearch(self) -> bool:
        """Elasticsearch 연결 (HTTPS/TLS 지원)"""
        try:
            es_config = self.config['elasticsearch']
            
            # HTTPS/TLS 설정 확인
            use_ssl = es_config.get('use_ssl', False)
            scheme = 'https' if use_ssl else 'http'
            
            # Elasticsearch 클라이언트 설정
            es_params = {
                'hosts': [f"{scheme}://{es_config['host']}:{es_config['port']}"],
                'request_timeout': 30,
                'max_retries': 3,
                'retry_on_timeout': True
            }
            
            # HTTPS 설정 추가
            if use_ssl:
                es_params.update({
                    'verify_certs': es_config.get('verify_certs', False),
                    'ssl_show_warn': es_config.get('ssl_show_warn', False),
                    'ca_certs': es_config.get('ca_certs'),
                    'ssl_assert_hostname': False,
                    'ssl_assert_fingerprint': None
                })
                
                # 사용자 인증 설정
                username = es_config.get('username')
                password = es_config.get('password')
                if username and password:
                    es_params['basic_auth'] = (username, password)
                    self.logger.info("Elasticsearch 사용자 인증 설정됨")
            
            self.es = Elasticsearch(**es_params)
            
            # 연결 테스트
            if self.es.ping():
                self.logger.info(f"Elasticsearch 연결 성공 ({scheme}://{es_config['host']}:{es_config['port']})")
                return True
            else:
                self.logger.error("Elasticsearch 연결 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"Elasticsearch 연결 오류: {e}")
            # Kubernetes 서비스를 통한 연결 시도
            return self._try_k8s_connection()
    
    def _try_k8s_connection(self) -> bool:
        """Kubernetes 서비스를 통한 Elasticsearch 연결 시도"""
        try:
            es_config = self.config['elasticsearch']
            k8s_host = es_config.get('k8s_service_host')
            k8s_port = es_config.get('k8s_service_port')
            
            if not k8s_host or not k8s_port:
                return False
                
            self.logger.info("Kubernetes 서비스를 통한 연결 시도...")
            
            # HTTPS 설정
            use_ssl = es_config.get('use_ssl', False)
            scheme = 'https' if use_ssl else 'http'
            
            es_params = {
                'hosts': [f"{scheme}://{k8s_host}:{k8s_port}"],
                'request_timeout': 30,
                'max_retries': 3,
                'retry_on_timeout': True
            }
            
            if use_ssl:
                es_params.update({
                    'verify_certs': False,  # Kubernetes 내부 통신
                    'ssl_show_warn': False,
                    'ssl_assert_hostname': False
                })
                
                username = es_config.get('username')
                password = es_config.get('password')
                if username and password:
                    es_params['basic_auth'] = (username, password)
            
            self.es = Elasticsearch(**es_params)
            
            if self.es.ping():
                self.logger.info(f"Kubernetes 서비스 연결 성공 ({scheme}://{k8s_host}:{k8s_port})")
                return True
            else:
                self.logger.error("Kubernetes 서비스 연결 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"Kubernetes 서비스 연결 오류: {e}")
            return False
    
    def load_error_patterns(self) -> bool:
        """데이터베이스에서 에러 패턴 로드"""
        try:
            if not self.db.connect():
                return False
                
            self.error_patterns = self.db.get_error_patterns()
            self.logger.info(f"{len(self.error_patterns)}개의 에러 패턴 로드됨")
            return True
            
        except Exception as e:
            self.logger.error(f"에러 패턴 로드 실패: {e}")
            return False
    
    def search_errors(self, time_range: int = 60) -> List[Dict]:
        """
        Elasticsearch에서 에러 로그 검색 (시간 필터링 적용)
        
        Args:
            time_range: 검색 시간 범위 (초)
            
        Returns:
            에러 로그 리스트
        """
        try:
            # 최대 검색 시간 제한 (설정에서 가져오거나 기본값 사용)
            max_search_time = self.config.get('log_management', {}).get('max_search_hours', 24) * 3600
            time_range = min(time_range, max_search_time)
            
            # 검색 시간 범위 설정
            end_time = datetime.now()
            start_time = end_time - timedelta(seconds=time_range)
            
            self.logger.info(f"에러 검색 시간 범위: {start_time.isoformat()} ~ {end_time.isoformat()}")
            
            # Elasticsearch 쿼리 구성 - 실제 ELK 데이터 구조에 맞게 수정
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "range": {
                                    "@timestamp": {
                                        "gte": start_time.isoformat(),
                                        "lte": end_time.isoformat()
                                    }
                                }
                            }
                        ],
                        "should": [
                            # 로그 레벨 기반 필터링
                            {"match": {"log.level": "ERROR"}},
                            {"match": {"log.level": "FATAL"}},
                            {"match": {"log.level": "CRITICAL"}},
                            {"match": {"level": "ERROR"}},
                            {"match": {"level": "FATAL"}},
                            {"match": {"level": "CRITICAL"}},
                            
                            # 메시지 내용 기반 필터링 (배열 필드 고려)
                            {"match": {"message": "error"}},
                            {"match": {"message": "exception"}},
                            {"match": {"message": "failed"}},
                            {"match": {"message": "crash"}},
                            {"match": {"message": "panic"}},
                            {"match": {"message": "fatal"}},
                            {"match": {"message": "killed"}},
                            {"match": {"message": "segmentation fault"}},
                            {"match": {"message": "out of memory"}},
                            {"match": {"message": "connection refused"}},
                            {"match": {"message": "timeout"}},
                            {"match": {"message": "permission denied"}},
                            
                            # 이벤트 원본 메시지 기반 필터링
                            {"match": {"event.original": "error"}},
                            {"match": {"event.original": "exception"}},
                            {"match": {"event.original": "failed"}},
                            
                            # 특정 프로그램의 심각한 로그
                            {"bool": {
                                "must": [
                                    {"match": {"program": "kernel"}},
                                    {"wildcard": {"message": "*error*"}}
                                ]
                            }},
                            {"bool": {
                                "must": [
                                    {"match": {"program": "systemd"}},
                                    {"wildcard": {"message": "*failed*"}}
                                ]
                            }}
                        ],
                        "minimum_should_match": 1
                    }
                },
                "sort": [
                    {"@timestamp": {"order": "desc"}}
                ],
                "size": 100
            }
            
            # 검색 실행
            index_pattern = self.config['elasticsearch']['index_pattern']
            response = self.es.search(index=index_pattern, body=query)
            
            errors = []
            for hit in response['hits']['hits']:
                error_data = self._parse_log_entry(hit)
                if error_data:
                    errors.append(error_data)
            
            self.logger.info(f"{len(errors)}개의 에러 로그 발견 (최근 {time_range//60}분간)")
            return errors
            
        except Exception as e:
            self.logger.error(f"에러 검색 실패: {e}")
            return []
    
    def _parse_log_entry(self, hit: Dict) -> Optional[Dict]:
        """
        Elasticsearch 로그 엔트리 파싱
        
        Args:
            hit: Elasticsearch 검색 결과
            
        Returns:
            파싱된 에러 데이터
        """
        try:
            source = hit['_source']
            
            # 메시지 필드 처리 (배열이거나 문자열일 수 있음)
            message = source.get('message', '')
            if isinstance(message, list):
                # 배열인 경우 첫 번째 요소 사용 (가장 완전한 메시지)
                message = message[0] if message else ''
            elif not isinstance(message, str):
                message = str(message)
            
            # 원본 이벤트 메시지도 확인
            original_message = source.get('event', {}).get('original', '')
            
            # 더 완전한 메시지 선택
            final_message = message if len(message) > len(original_message) else original_message
            
            # 호스트 정보 추출
            host_info = source.get('host', {})
            host_name = 'unknown'
            if isinstance(host_info, dict):
                host_name = host_info.get('name', host_info.get('hostname', 'unknown'))
            elif isinstance(host_info, str):
                host_name = host_info
            
            # 기본 정보 추출
            error_data = {
                'elasticsearch_id': hit['_id'],
                'timestamp': source.get('@timestamp'),
                'error_message': final_message,
                'source_system': host_name,
                'severity': source.get('log', {}).get('level', source.get('level', 'INFO')),
                'raw_log_data': source
            }
            
            # 에러 타입 분류
            error_data['error_type'] = self._classify_error(error_data['error_message'])
            
            # 스택 트레이스 추출
            if 'exception' in source:
                error_data['stack_trace'] = str(source['exception'])
            elif 'stack_trace' in source:
                error_data['stack_trace'] = source['stack_trace']
            elif 'error' in source and 'stack_trace' in source['error']:
                error_data['stack_trace'] = source['error']['stack_trace']
            
            # 프로그램/서비스 정보 추가
            if 'program' in source:
                error_data['source_system'] = f"{host_name}-{source['program']}"
            
            return error_data
            
        except Exception as e:
            self.logger.error(f"로그 엔트리 파싱 실패: {e}")
            self.logger.debug(f"문제가 된 데이터: {hit}")
            return None
    
    def _classify_error(self, error_message: str) -> str:
        """
        에러 메시지를 분류하여 에러 타입 결정
        
        Args:
            error_message: 에러 메시지
            
        Returns:
            에러 타입
        """
        # 빈 메시지 처리
        if not error_message or not isinstance(error_message, str):
            return 'unknown'
            
        error_message_lower = error_message.lower()
        
        # 패턴 매칭으로 에러 타입 분류
        for pattern in self.error_patterns:
            try:
                if re.search(pattern['pattern_regex'], error_message, re.IGNORECASE):
                    return pattern['error_category']
            except Exception as e:
                self.logger.warning(f"패턴 매칭 오류: {e}")
                continue
        
        # 기본 분류 규칙 - 더 구체적인 키워드들 추가
        keyword_classifications = {
            'memory': ['memory', 'oom', 'out of memory', 'oomkilled', 'killed', 'segmentation fault', 'segfault'],
            'network': ['connection', 'network', 'timeout', 'refused', 'unreachable', 'dns', 'resolve', 'connect'],
            'storage': ['disk', 'storage', 'space', 'filesystem', 'no space left', 'quota', 'volume'],
            'kubernetes': ['kubernetes', 'pod', 'container', 'deployment', 'service', 'namespace', 'kubectl'],
            'database': ['database', 'sql', 'query', 'mysql', 'postgres', 'elasticsearch', 'connection pool'],
            'system': ['kernel', 'system', 'driver', 'hardware', 'cpu', 'thermal'],
            'security': ['permission', 'access', 'denied', 'unauthorized', 'forbidden', 'authentication'],
            'configuration': ['config', 'configuration', 'invalid', 'missing', 'not found', 'syntax error']
        }
        
        # 키워드 기반 분류
        for category, keywords in keyword_classifications.items():
            if any(keyword in error_message_lower for keyword in keywords):
                return category
        
        # 로그 레벨이 INFO나 DEBUG면 일반 로그로 분류
        if any(level in error_message_lower for level in ['info', 'debug', 'trace']):
            return 'info'
        
        # 기본값
        return 'application'
    
    def check_error_threshold(self, error_type: str, count: int) -> bool:
        """
        에러 임계값 체크
        
        Args:
            error_type: 에러 타입
            count: 에러 개수
            
        Returns:
            임계값 초과 여부
        """
        threshold = self.config['monitoring']['error_threshold']
        if count >= threshold:
            self.logger.warning(f"에러 임계값 초과: {error_type} - {count}개")
            return True
        return False
    
    def process_errors(self, errors: List[Dict]) -> List[Dict]:
        """
        에러 리스트 처리 및 필터링
        
        Args:
            errors: 에러 리스트
            
        Returns:
            처리해야 할 에러 리스트
        """
        processed_errors = []
        error_counts = {}
        
        # 에러 카운팅
        for error in errors:
            error_type = error['error_type']
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # 임계값 체크 및 처리 대상 선별
        notified_types = set()  # 이미 알림을 보낸 에러 타입 추적
        
        for error in errors:
            error_type = error['error_type']
            
            # 임계값 체크
            if self.check_error_threshold(error_type, error_counts[error_type]):
                # 동일 타입에 대해 한 번만 알림 전송
                if error_type not in notified_types:
                    error_samples = [e['error_message'] for e in errors if e['error_type'] == error_type]
                    self.slack.send_error_detected(
                        error_type=error_type,
                        error_count=error_counts[error_type],
                        error_samples=error_samples
                    )
                    notified_types.add(error_type)
                
                # 데이터베이스에 저장
                error_id = self.db.insert_error_log(error)
                if error_id:
                    error['error_id'] = error_id
                    processed_errors.append(error)
        
        return processed_errors
    
    def monitor_loop(self):
        """메인 모니터링 루프 (자동 로그 정리 포함)"""
        self.logger.info("에러 모니터링 시작")
        
        # 초기 연결
        if not self.connect_elasticsearch():
            self.logger.error("Elasticsearch 연결 실패. 모니터링 중단")
            return
        
        if not self.load_error_patterns():
            self.logger.error("에러 패턴 로드 실패. 모니터링 중단")
            return
        
        check_interval = self.config['monitoring']['check_interval']
        cleanup_interval = self.config.get('log_management', {}).get('cleanup_interval_hours', 24) * 3600
        last_cleanup = datetime.now()
        
        try:
            while self.running:
                self.logger.info("에러 검색 중...")
                
                # 주기적인 로그 정리 (설정된 간격마다)
                if (datetime.now() - last_cleanup).total_seconds() >= cleanup_interval:
                    self.cleanup_old_logs()
                    last_cleanup = datetime.now()
                
                # 에러 검색 (제한된 시간 범위)
                errors = self.search_errors(check_interval)
                
                if errors:
                    # 에러 처리
                    processed_errors = self.process_errors(errors)
                    
                    if processed_errors:
                        self.logger.info(f"{len(processed_errors)}개의 에러가 처리 대기 중")
                        # 여기서 AI Analyzer로 전달
                        yield processed_errors
                
                # 종료 체크
                if not self.running:
                    self.logger.info("모니터링 중단 요청 - 루프 종료")
                    break
                
                # 시스템 상태 업데이트
                self._update_system_status()
                
                # 대기 (최소 간격 보장) - 종료 신호 체크
                sleep_time = max(check_interval, 30)  # 최소 30초 대기
                
                # 1초씩 나눌어서 대기하며 종료 신호 체크
                for i in range(sleep_time):
                    if not self.running:
                        self.logger.info("종료 신호 감지 - 모니터링 중단")
                        return
                    time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt - 모니터링 중단됨")
            self.running = False
        except Exception as e:
            self.logger.error(f"모니터링 오류: {e}")
            self.running = False
        finally:
            self.logger.info("모니터링 루프 종료 - 리소스 정리")
            try:
                if self.db:
                    self.db.disconnect()
            except Exception as e:
                self.logger.error(f"데이터베이스 연결 해제 실패: {e}")
    
    def cleanup_old_logs(self):
        """오래된 로그 자동 정리"""
        try:
            log_config = self.config.get('log_management', {})
            retention_days = log_config.get('retention_days', 7)
            
            # 삭제할 날짜 계산
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # 오래된 인덱스 패턴 생성 (logstash-YYYY.MM.DD 형식)
            old_indices = []
            for days_back in range(retention_days + 1, retention_days + 30):  # 추가로 30일 더 확인
                old_date = datetime.now() - timedelta(days=days_back)
                index_name = f"logstash-{old_date.strftime('%Y.%m.%d')}"
                old_indices.append(index_name)
            
            # 인덱스 삭제
            deleted_count = 0
            for index in old_indices:
                try:
                    if self.es.indices.exists(index=index):
                        self.es.indices.delete(index=index)
                        deleted_count += 1
                        self.logger.info(f"오래된 인덱스 삭제: {index}")
                except Exception as e:
                    self.logger.warning(f"인덱스 삭제 실패 {index}: {e}")
            
            # 와일드카드 패턴으로 일괄 삭제 시도
            try:
                old_pattern = f"logstash-{cutoff_date.strftime('%Y.%m')}*"
                response = self.es.indices.delete(index=old_pattern, ignore=[404])
                self.logger.info(f"패턴 기반 로그 정리 완료: {old_pattern}")
            except Exception as e:
                self.logger.warning(f"패턴 기반 삭제 실패: {e}")
            
            # 데이터베이스의 오래된 에러 로그도 정리
            self.db.cleanup_old_error_logs(retention_days)
            
            self.logger.info(f"로그 정리 완료: {deleted_count}개 인덱스 삭제, {retention_days}일 이전 데이터 정리")
            
        except Exception as e:
            self.logger.error(f"로그 정리 실패: {e}")
    
    def _update_system_status(self):
        """시스템 상태 업데이트"""
        try:
            # Elasticsearch 상태 체크
            if self.es.ping():
                self.db.update_system_status('elasticsearch', 'healthy', 0)
            else:
                self.db.update_system_status('elasticsearch', 'error', 1)
                
        except Exception as e:
            self.logger.error(f"시스템 상태 업데이트 실패: {e}")


# 사용 예제
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 에러 모니터 시작
    monitor = ErrorMonitor()
    
    # 모니터링 루프 실행
    for errors in monitor.monitor_loop():
        print(f"처리할 에러: {len(errors)}개")
        for error in errors:
            print(f"- {error['error_type']}: {error['error_message'][:100]}...")