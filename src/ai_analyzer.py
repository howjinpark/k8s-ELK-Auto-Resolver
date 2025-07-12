#!/usr/bin/env python3
"""
AI Analyzer 모듈 - 퍼플렉시티 API를 사용한 에러 분석 및 해결책 생성
"""

import yaml
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any
from openai import OpenAI
from .database import DatabaseManager

class AIAnalyzer:
    """퍼플렉시티 AI를 사용한 에러 분석 클래스"""
    
    def __init__(self, config_path: str = None):
        """
        AI 분석기 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.db = DatabaseManager(config_path)
        self.logger = logging.getLogger(__name__)
        
        # 퍼플렉시티 클라이언트 초기화 (OpenAI 호환)
        perplexity_config = self.config['perplexity']
        self.client = OpenAI(
            api_key=perplexity_config['api_key'],
            base_url=perplexity_config['base_url']
        )
        self.model = perplexity_config['model']
        
    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드 (환경 변수 포함)"""
        try:
            from .load_env import load_config_with_env
            return load_config_with_env(config_path)
        except Exception as e:
            raise Exception(f"설정 파일을 읽을 수 없습니다: {e}")
    
    def analyze_error(self, error_data: Dict) -> Optional[Dict]:
        """
        단일 에러 분석
        
        Args:
            error_data: 에러 정보
            
        Returns:
            분석 결과 및 해결책
        """
        try:
            # 기존 해결책이 있는지 확인
            error_hash = self.db.create_hash_signature(
                error_data['error_type'], 
                error_data['error_message']
            )
            
            if self.db.connect():
                existing_solution = self.db.get_solution_by_error_hash(error_hash)
                if existing_solution and existing_solution['success_rate'] > 50:
                    self.logger.info(f"📚 기존 해결책 발견 (성공률: {existing_solution['success_rate']}%) - AI 분석 없이 DB에서 재사용")
                    # 기존 해결책 재사용 표시
                    existing_solution['is_reused'] = True
                    existing_solution['reuse_source'] = 'database'
                    return existing_solution
            
            # AI 분석 요청
            analysis_result = self._request_ai_analysis(error_data)
            
            if analysis_result:
                # 해결책을 데이터베이스에 저장
                solution_data = {
                    'error_hash': error_hash,
                    'solution_type': analysis_result['solution_type'],
                    'solution_description': analysis_result['description'],
                    'solution_commands': analysis_result['commands'],
                    'ai_analysis': analysis_result['analysis']
                }
                
                solution_id = self.db.insert_solution(solution_data)
                if solution_id:
                    analysis_result['solution_id'] = solution_id
                    self.logger.info(f"🤖 새로운 해결책 저장됨: ID={solution_id} - AI 분석 결과")
                
                # 새로운 AI 분석 결과 표시
                analysis_result['is_reused'] = False
                analysis_result['reuse_source'] = 'ai_analysis'
                
                return analysis_result
            
            return None
            
        except Exception as e:
            self.logger.error(f"에러 분석 실패: {e}")
            return None
        finally:
            self.db.disconnect()
    
    def _request_ai_analysis(self, error_data: Dict) -> Optional[Dict]:
        """
        퍼플렉시티 AI에 에러 분석 요청
        
        Args:
            error_data: 에러 정보
            
        Returns:
            AI 분석 결과
        """
        try:
            # 프롬프트 구성
            prompt = self._build_analysis_prompt(error_data)
            
            # 퍼플렉시티 API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 Kubernetes와 ELK Stack 전문가입니다. 에러 로그를 분석하고 실행 가능한 해결책을 JSON 형태로 제공해주세요."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            # 응답 파싱
            ai_response = response.choices[0].message.content
            self.logger.info("AI 분석 완료")
            
            # JSON 응답 파싱
            return self._parse_ai_response(ai_response, error_data)
            
        except Exception as e:
            self.logger.error(f"AI 분석 요청 실패: {e}")
            return None
    
    def _build_analysis_prompt(self, error_data: Dict) -> str:
        """
        AI 분석용 프롬프트 구성
        
        Args:
            error_data: 에러 정보
            
        Returns:
            구성된 프롬프트
        """
        prompt = f"""
다음 에러를 분석하고 해결책을 제공해주세요:

## 에러 정보
- **에러 타입**: {error_data['error_type']}
- **에러 메시지**: {error_data['error_message']}
- **소스 시스템**: {error_data['source_system']}
- **심각도**: {error_data['severity']}

## 추가 정보
"""
        
        if error_data.get('stack_trace'):
            prompt += f"- **스택 트레이스**: {error_data['stack_trace'][:500]}...\n"
        
        if error_data.get('raw_log_data'):
            raw_data = error_data['raw_log_data']
            if isinstance(raw_data, dict):
                prompt += f"- **원시 로그**: {json.dumps(raw_data, indent=2)[:1000]}...\n"
        
        prompt += """

## 요청사항
다음 JSON 형식으로 응답해주세요:

```json
{
    "analysis": "에러의 원인과 상황에 대한 상세 분석",
    "solution_type": "kubernetes|config_fix|restart|scaling|network|storage",
    "description": "해결책에 대한 설명",
    "commands": [
        {
            "type": "kubectl|bash|config",
            "command": "실행할 명령어",
            "description": "명령어 설명",
            "safe": true|false
        }
    ],
    "priority": "high|medium|low",
    "estimated_time": "예상 해결 시간 (분)",
    "success_probability": "성공 확률 (0-100)"
}
```

## 중요사항
1. Kubernetes 환경 (네임스페이스: elk-stack)
2. ELK Stack 컴포넌트 (Elasticsearch, Logstash, Kibana, Filebeat)
3. 안전한 명령어만 제안 (safe_mode: true)
4. 단계별 실행 가능한 명령어 제공
5. 데이터 손실 방지에 우선순위

최신 Kubernetes와 ELK Stack 지식을 바탕으로 분석해주세요.
"""
        
        return prompt
    
    def _parse_ai_response(self, ai_response: str, error_data: Dict) -> Optional[Dict]:
        """
        AI 응답 파싱
        
        Args:
            ai_response: AI 응답 텍스트
            error_data: 원본 에러 데이터
            
        Returns:
            파싱된 분석 결과
        """
        try:
            # JSON 부분 추출
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                self.logger.error("AI 응답에서 JSON을 찾을 수 없음")
                return None
            
            json_str = ai_response[json_start:json_end]
            analysis_result = json.loads(json_str)
            
            # 필수 필드 검증
            required_fields = ['analysis', 'solution_type', 'description', 'commands']
            for field in required_fields:
                if field not in analysis_result:
                    self.logger.error(f"필수 필드 누락: {field}")
                    return None
            
            # 명령어 안전성 검증
            safe_commands = []
            for cmd in analysis_result['commands']:
                if self._is_safe_command(cmd):
                    safe_commands.append(cmd)
                else:
                    self.logger.warning(f"안전하지 않은 명령어 제외: {cmd.get('command', '')}")
            
            analysis_result['commands'] = safe_commands
            
            # 기본값 설정
            analysis_result.setdefault('priority', 'medium')
            analysis_result.setdefault('estimated_time', '10')
            analysis_result.setdefault('success_probability', '70')
            
            # AutoResolver가 필요로 하는 추가 필드 설정
            analysis_result['error_data'] = error_data
            analysis_result['has_solution'] = True  # 해결책이 있음을 명시
            
            self.logger.info("AI 응답 파싱 완료")
            return analysis_result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 실패: {e}")
            return None
        except Exception as e:
            self.logger.error(f"AI 응답 파싱 오류: {e}")
            return None
    
    def _is_safe_command(self, command_info: Dict) -> bool:
        """
        명령어 안전성 검증
        
        Args:
            command_info: 명령어 정보
            
        Returns:
            안전 여부
        """
        if not self.config['resolver']['safe_mode']:
            return True
        
        command = command_info.get('command', '').lower()
        
        # 위험한 명령어 패턴
        dangerous_patterns = [
            'rm -rf', 'dd if=', 'mkfs', 'fdisk', 'format',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'rm /', 'chmod 777', 'chown -R',
            'iptables -F', 'ufw --force',
            'drop database', 'truncate table', 'delete from'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command:
                return False
        
        # 안전한 명령어 패턴
        safe_patterns = [
            'kubectl get', 'kubectl describe', 'kubectl logs',
            'kubectl rollout restart', 'kubectl scale',
            'curl -s', 'systemctl restart', 'systemctl status',
            'docker restart', 'helm upgrade'
        ]
        
        for pattern in safe_patterns:
            if command.startswith(pattern):
                return True
        
        # 기본적으로 안전하지 않다고 판단
        return command_info.get('safe', False)
    
    def analyze_multiple_errors(self, errors_list: List[Dict]) -> List[Dict]:
        """
        여러 에러 일괄 분석
        
        Args:
            errors_list: 에러 리스트
            
        Returns:
            분석 결과 리스트
        """
        results = []
        
        for error_data in errors_list:
            try:
                self.logger.info(f"에러 분석 중: {error_data['error_type']}")
                
                analysis_result = self.analyze_error(error_data)
                
                if analysis_result:
                    analysis_result['error_data'] = error_data
                    results.append(analysis_result)
                    self.logger.info(f"에러 분석 완료: {error_data['error_type']}")
                else:
                    self.logger.warning(f"에러 분석 실패: {error_data['error_type']}")
                    
            except Exception as e:
                self.logger.error(f"에러 분석 중 오류 발생: {e}")
                continue
        
        self.logger.info(f"총 {len(results)}개 에러 분석 완료")
        return results
    
    def get_analysis_stats(self) -> Dict:
        """
        분석 통계 조회
        
        Returns:
            통계 정보
        """
        try:
            if not self.db.connect():
                return {}
            
            # 통계 쿼리는 여기서 구현
            # 예: 해결책 성공률, 에러 타입별 통계 등
            
            stats = {
                'total_solutions': 0,
                'avg_success_rate': 0,
                'top_error_types': []
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"통계 조회 실패: {e}")
            return {}
        finally:
            self.db.disconnect()


# 사용 예제
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # AI 분석기 초기화
    analyzer = AIAnalyzer()
    
    # 테스트 에러 데이터
    test_error = {
        'error_type': 'kubernetes',
        'error_message': 'pod "elasticsearch-0" is in CrashLoopBackOff state',
        'source_system': 'k8s-cluster',
        'severity': 'ERROR',
        'stack_trace': 'Container failed to start: OOMKilled'
    }
    
    # 에러 분석 테스트
    result = analyzer.analyze_error(test_error)
    
    if result:
        print("=== AI 분석 결과 ===")
        print(f"해결책 타입: {result['solution_type']}")
        print(f"설명: {result['description']}")
        print(f"명령어 개수: {len(result['commands'])}")
        for i, cmd in enumerate(result['commands'], 1):
            print(f"  {i}. {cmd['command']}")
    else:
        print("에러 분석 실패")