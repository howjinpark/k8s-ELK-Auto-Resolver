#!/usr/bin/env python3
"""
Auto Resolver 모듈 - AI 분석 결과를 바탕으로 자동 에러 해결 실행
"""

import yaml
import subprocess
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from kubernetes import client, config
from .database import DatabaseManager

class AutoResolver:
    """자동 에러 해결 실행 클래스"""
    
    def __init__(self, config_path: str = None):
        """
        자동 해결기 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.db = DatabaseManager(config_path)
        self.logger = logging.getLogger(__name__)
        
        # Kubernetes 클라이언트 초기화
        try:
            config.load_kube_config(self.config['kubernetes']['config_path'])
            self.k8s_v1 = client.CoreV1Api()
            self.k8s_apps = client.AppsV1Api()
            self.logger.info("Kubernetes 클라이언트 초기화 완료")
        except Exception as e:
            self.logger.warning(f"Kubernetes 설정 로드 실패: {e}")
            self.k8s_v1 = None
            self.k8s_apps = None
        
        self.namespace = self.config['kubernetes']['namespace']
        self.max_retries = self.config['resolver']['max_retries']
        self.timeout = self.config['resolver']['timeout']
        self.safe_mode = self.config['resolver']['safe_mode']
        
    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드 (환경 변수 포함)"""
        try:
            from .load_env import load_config_with_env
            return load_config_with_env(config_path)
        except Exception as e:
            raise Exception(f"설정 파일을 읽을 수 없습니다: {e}")
    
    def resolve_error(self, analysis_result: Dict) -> Dict:
        """
        분석 결과를 바탕으로 에러 해결 실행
        
        Args:
            analysis_result: AI 분석 결과
            
        Returns:
            실행 결과
        """
        execution_result = {
            'success': False,
            'executed_commands': [],
            'errors': [],
            'execution_time': 0,
            'status': 'failed'
        }
        
        start_time = datetime.now()
        
        try:
            self.logger.info(f"에러 해결 시작: {analysis_result['solution_type']}")
            
            # 실행 전 사전 검사
            if not self._pre_execution_check(analysis_result):
                execution_result['errors'].append("사전 검사 실패")
                return execution_result
            
            # 명령어 순차 실행
            all_success = True
            for i, command_info in enumerate(analysis_result['commands']):
                self.logger.info(f"명령어 실행 중 ({i+1}/{len(analysis_result['commands'])}): {command_info.get('description', '')}")
                
                cmd_result = self._execute_command(command_info)
                execution_result['executed_commands'].append(cmd_result)
                
                if not cmd_result['success']:
                    all_success = False
                    execution_result['errors'].append(f"명령어 실행 실패: {cmd_result['error']}")
                    
                    # 실패 시 중단할지 계속할지 결정
                    if command_info.get('critical', True):
                        self.logger.error("중요 명령어 실패, 실행 중단")
                        execution_result['failure_reason'] = f"중요 명령어 실패: {cmd_result.get('error', '알 수 없는 오류')}"
                        break
                
                # 명령어 간 대기 시간
                if i < len(analysis_result['commands']) - 1:
                    time.sleep(2)
            
            execution_result['success'] = all_success
            execution_result['status'] = 'success' if all_success else 'partial_success'
            
            # 실패 이유 설정
            if not all_success and 'failure_reason' not in execution_result:
                if execution_result['errors']:
                    execution_result['failure_reason'] = execution_result['errors'][0]
                else:
                    execution_result['failure_reason'] = '알 수 없는 실행 오류'
            
            # 실행 후 검증
            if all_success:
                verification_result = self._post_execution_verification(analysis_result)
                if not verification_result:
                    execution_result['status'] = 'needs_verification'
                    execution_result['errors'].append("실행 후 검증 필요")
            
        except Exception as e:
            self.logger.error(f"에러 해결 실행 중 오류: {e}")
            execution_result['errors'].append(str(e))
            execution_result['status'] = 'error'
        
        finally:
            end_time = datetime.now()
            execution_result['execution_time'] = int((end_time - start_time).total_seconds())
            
            # 실행 결과 데이터베이스 기록
            self._record_execution_result(analysis_result, execution_result)
        
        self.logger.info(f"에러 해결 완료: {execution_result['status']}")
        return execution_result
    
    def _pre_execution_check(self, analysis_result: Dict) -> bool:
        """
        실행 전 사전 검사
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            검사 통과 여부
        """
        try:
            # Kubernetes 연결 확인
            if self.k8s_v1 and analysis_result['solution_type'] == 'kubernetes':
                try:
                    self.k8s_v1.list_namespace()
                    self.logger.info("Kubernetes 연결 확인됨")
                except Exception as e:
                    self.logger.error(f"Kubernetes 연결 실패: {e}")
                    return False
            
            # 네임스페이스 존재 확인
            if self.k8s_v1:
                try:
                    self.k8s_v1.read_namespace(self.namespace)
                    self.logger.info(f"네임스페이스 '{self.namespace}' 확인됨")
                except Exception as e:
                    self.logger.error(f"네임스페이스 '{self.namespace}' 없음: {e}")
                    return False
            
            # 안전 모드에서 위험한 작업 차단
            if self.safe_mode:
                for cmd in analysis_result['commands']:
                    if not cmd.get('safe', False):
                        self.logger.error(f"안전 모드에서 위험한 명령어 차단: {cmd.get('command', '')}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"사전 검사 오류: {e}")
            return False
    
    def _execute_command(self, command_info: Dict) -> Dict:
        """
        개별 명령어 실행
        
        Args:
            command_info: 명령어 정보
            
        Returns:
            실행 결과
        """
        result = {
            'command': command_info.get('command', ''),
            'type': command_info.get('type', ''),
            'description': command_info.get('description', ''),
            'success': False,
            'output': '',
            'error': '',
            'execution_time': 0
        }
        
        start_time = time.time()
        
        try:
            command_type = command_info.get('type', 'bash')
            command = command_info.get('command', '')
            
            if command_type == 'kubectl':
                result = self._execute_kubectl_command(command, result)
            elif command_type == 'bash':
                result = self._execute_bash_command(command, result)
            elif command_type == 'config':
                result = self._execute_config_command(command_info, result)
            else:
                result['error'] = f"지원하지 않는 명령어 타입: {command_type}"
                
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"명령어 실행 오류: {e}")
        
        finally:
            result['execution_time'] = round(time.time() - start_time, 2)
        
        return result
    
    def _execute_kubectl_command(self, command: str, result: Dict) -> Dict:
        """kubectl 명령어 실행"""
        try:
            # kubectl 명령어 파싱 및 실행
            cmd_parts = command.split()
            
            if len(cmd_parts) < 2:
                result['error'] = "잘못된 kubectl 명령어"
                return result
            
            action = cmd_parts[1]  # get, describe, restart 등
            
            if action == 'restart' and len(cmd_parts) >= 4:
                # kubectl rollout restart deployment/logstash -n elk-stack
                resource_type = cmd_parts[3].split('/')[0]
                resource_name = cmd_parts[3].split('/')[1] if '/' in cmd_parts[3] else cmd_parts[4]
                
                if resource_type == 'deployment':
                    response = self.k8s_apps.patch_namespaced_deployment(
                        name=resource_name,
                        namespace=self.namespace,
                        body={'spec': {'template': {'metadata': {'annotations': {'kubectl.kubernetes.io/restartedAt': datetime.now().isoformat()}}}}}
                    )
                    result['success'] = True
                    result['output'] = f"Deployment {resource_name} 재시작됨"
                
            elif action == 'scale' and len(cmd_parts) >= 5:
                # kubectl scale deployment logstash --replicas=2 -n elk-stack
                resource_name = cmd_parts[3]
                replicas = int(cmd_parts[4].split('=')[1])
                
                response = self.k8s_apps.patch_namespaced_deployment_scale(
                    name=resource_name,
                    namespace=self.namespace,
                    body={'spec': {'replicas': replicas}}
                )
                result['success'] = True
                result['output'] = f"Deployment {resource_name} 스케일 조정: {replicas}개"
                
            else:
                # 일반 kubectl 명령어는 subprocess로 실행
                result = self._execute_bash_command(command, result)
                
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def _execute_bash_command(self, command: str, result: Dict) -> Dict:
        """bash 명령어 실행"""
        try:
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            result['output'] = process.stdout
            result['error'] = process.stderr
            result['success'] = process.returncode == 0
            
            if not result['success']:
                self.logger.warning(f"명령어 실행 실패 (exit code: {process.returncode}): {command}")
                
        except subprocess.TimeoutExpired:
            result['error'] = f"명령어 실행 시간 초과 ({self.timeout}초)"
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def _execute_config_command(self, command_info: Dict, result: Dict) -> Dict:
        """설정 변경 명령어 실행"""
        try:
            # 설정 파일 수정 등의 작업
            config_type = command_info.get('config_type', '')
            config_path = command_info.get('config_path', '')
            config_changes = command_info.get('config_changes', {})
            
            if config_type == 'yaml' and config_path and config_changes:
                # YAML 설정 파일 수정
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                # 설정 변경 적용
                for key, value in config_changes.items():
                    self._set_nested_dict(config_data, key, value)
                
                # 파일 저장
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
                
                result['success'] = True
                result['output'] = f"설정 파일 수정 완료: {config_path}"
            else:
                result['error'] = "지원하지 않는 설정 변경 형식"
                
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def _set_nested_dict(self, data: Dict, key_path: str, value: Any):
        """중첩된 딕셔너리에 값 설정"""
        keys = key_path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _post_execution_verification(self, analysis_result: Dict) -> bool:
        """
        실행 후 검증 (HTTPS 환경 지원)
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            검증 성공 여부
        """
        try:
            # Pod 상태 확인 (Kubernetes 관련 해결책의 경우)
            if analysis_result['solution_type'] == 'kubernetes' and self.k8s_v1:
                pods = self.k8s_v1.list_namespaced_pod(namespace=self.namespace)
                
                unhealthy_pods = []
                for pod in pods.items:
                    if pod.status.phase not in ['Running', 'Succeeded']:
                        unhealthy_pods.append(pod.metadata.name)
                
                if unhealthy_pods:
                    self.logger.warning(f"비정상 상태 Pod 발견: {unhealthy_pods}")
                    return False
                
                self.logger.info("모든 Pod가 정상 상태")
                
                # HTTPS Elasticsearch 연결 검증
                return self._verify_elasticsearch_https_connection()
            
            # 기본적으로 성공으로 간주
            return True
            
        except Exception as e:
            self.logger.error(f"실행 후 검증 오류: {e}")
            return False
    
    def _verify_elasticsearch_https_connection(self) -> bool:
        """HTTPS Elasticsearch 연결 검증"""
        try:
            from elasticsearch import Elasticsearch
            
            # 설정에서 Elasticsearch 정보 가져오기
            es_config = self.config.get('elasticsearch', {})
            use_ssl = es_config.get('use_ssl', False)
            
            if not use_ssl:
                self.logger.info("SSL 설정이 비활성화됨, 검증 건너뛰기")
                return True
            
            scheme = 'https'
            host = es_config.get('host', 'localhost')
            port = es_config.get('port', 9200)
            
            # HTTPS Elasticsearch 클라이언트 생성
            es_params = {
                'hosts': [f"{scheme}://{host}:{port}"],
                'verify_certs': False,
                'ssl_show_warn': False,
                'ssl_assert_hostname': False,
                'request_timeout': 10
            }
            
            username = es_config.get('username')
            password = es_config.get('password')
            if username and password:
                es_params['basic_auth'] = (username, password)
            
            es = Elasticsearch(**es_params)
            
            # 연결 테스트
            if es.ping():
                self.logger.info("HTTPS Elasticsearch 연결 검증 성공")
                return True
            else:
                self.logger.warning("HTTPS Elasticsearch 연결 검증 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"HTTPS Elasticsearch 검증 오류: {e}")
            return False
    
    def _record_execution_result(self, analysis_result: Dict, execution_result: Dict):
        """실행 결과를 데이터베이스에 기록"""
        try:
            if not self.db.connect():
                return
            
            execution_data = {
                'error_log_id': analysis_result.get('error_data', {}).get('error_id'),
                'solution_id': analysis_result.get('solution_id'),
                'execution_status': execution_result['status'],
                'execution_output': str(execution_result),
                'execution_time': timedelta(seconds=execution_result['execution_time'])
            }
            
            self.db.record_execution(execution_data)
            self.logger.info("실행 결과 데이터베이스 기록 완료")
            
        except Exception as e:
            self.logger.error(f"실행 결과 기록 실패: {e}")
        finally:
            self.db.disconnect()
    
    def resolve_multiple_errors(self, analysis_results: List[Dict]) -> List[Dict]:
        """
        여러 에러 일괄 해결
        
        Args:
            analysis_results: 분석 결과 리스트
            
        Returns:
            실행 결과 리스트
        """
        results = []
        
        # 우선순위별로 정렬 (high > medium > low)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        sorted_analyses = sorted(
            analysis_results, 
            key=lambda x: priority_order.get(x.get('priority', 'medium'), 1)
        )
        
        for analysis_result in sorted_analyses:
            try:
                self.logger.info(f"에러 해결 시작: {analysis_result.get('solution_type', 'unknown')}")
                
                execution_result = self.resolve_error(analysis_result)
                execution_result['analysis_result'] = analysis_result
                results.append(execution_result)
                
                # 실패한 경우 잠시 대기
                if not execution_result['success']:
                    time.sleep(5)
                    
            except Exception as e:
                self.logger.error(f"에러 해결 중 오류: {e}")
                continue
        
        self.logger.info(f"총 {len(results)}개 에러 해결 시도 완료")
        return results


# 사용 예제
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 자동 해결기 초기화
    resolver = AutoResolver()
    
    # 테스트 분석 결과
    test_analysis = {
        'solution_type': 'kubernetes',
        'description': 'Elasticsearch Pod 재시작',
        'commands': [
            {
                'type': 'kubectl',
                'command': 'kubectl rollout restart deployment/elasticsearch -n elk-stack',
                'description': 'Elasticsearch deployment 재시작',
                'safe': True
            }
        ],
        'priority': 'high'
    }
    
    # 에러 해결 테스트
    result = resolver.resolve_error(test_analysis)
    
    print("=== 에러 해결 결과 ===")
    print(f"성공 여부: {result['success']}")
    print(f"상태: {result['status']}")
    print(f"실행 시간: {result['execution_time']}초")
    if result['errors']:
        print(f"오류: {result['errors']}")