# ELK Auto Resolver 현재 시스템 아키텍처

## 1. 시스템 개요

### 1.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    ELK Auto Resolver System                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Error Monitor  │  │  AI Analyzer    │  │  Auto Resolver  │ │
│  │                 │  │                 │  │                 │ │
│  │ • Log Collection│  │ • Pattern Match │  │ • Solution Exec │ │
│  │ • Error Extract │  │ • AI Generation │  │ • Result Track  │ │
│  │ • Hash Generate │  │ • Safety Check  │  │ • Success Rate  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                       │                       │     │
│           ▼                       ▼                       ▼     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 PostgreSQL Database                         │ │
│  │                                                             │ │
│  │ • error_logs      • solutions      • execution_history     │ │
│  │ • error_patterns  • system_status                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 주요 구성 요소

| 구성 요소 | 역할 | 파일 경로 | 상태 |
|-----------|------|-----------|------|
| **Error Monitor** | 에러 감지 및 로그 수집 | `error_monitor.py` | ✅ 운영 중 |
| **AI Analyzer** | 에러 분석 및 해결책 생성 | `ai_analyzer.py` | ✅ 운영 중 |
| **Auto Resolver** | 해결책 실행 및 추적 | `auto_resolver.py` | ✅ 운영 중 |
| **Database Manager** | 데이터베이스 관리 | `database.py` | ✅ 운영 중 |
| **PostgreSQL DB** | 데이터 저장소 | `database_schema.sql` | ✅ 운영 중 |

## 2. 데이터베이스 아키텍처

### 2.1 테이블 구조

```sql
-- 에러 로그 테이블
CREATE TABLE error_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_hash VARCHAR(64) UNIQUE NOT NULL,
    error_message TEXT NOT NULL,
    error_type VARCHAR(100),
    pod_name VARCHAR(100),
    namespace VARCHAR(100),
    severity VARCHAR(20) DEFAULT 'medium',
    resolved BOOLEAN DEFAULT FALSE,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    occurrence_count INTEGER DEFAULT 1
);

-- 해결책 테이블
CREATE TABLE solutions (
    id SERIAL PRIMARY KEY,
    error_hash VARCHAR(64) NOT NULL,
    solution_text TEXT NOT NULL,
    solution_type VARCHAR(50) NOT NULL,
    commands JSON,
    success_rate REAL DEFAULT 0.0,
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    confidence_score REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(20) DEFAULT 'ai_generated'
);

-- 실행 기록 테이블
CREATE TABLE execution_history (
    id SERIAL PRIMARY KEY,
    solution_id INTEGER REFERENCES solutions(id),
    error_hash VARCHAR(64) NOT NULL,
    execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL,
    execution_duration REAL,
    error_message TEXT,
    output TEXT,
    executed_by VARCHAR(50) DEFAULT 'auto_resolver'
);

-- 에러 패턴 테이블
CREATE TABLE error_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(100) NOT NULL,
    regex_pattern TEXT NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 1,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 시스템 상태 테이블
CREATE TABLE system_status (
    id SERIAL PRIMARY KEY,
    component_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSON,
    namespace VARCHAR(100)
);
```

### 2.2 데이터 흐름

```
┌─────────────────┐
│   Log Sources   │
│                 │
│ • Elasticsearch │
│ • Kibana        │
│ • Logstash      │
│ • Filebeat      │
│ • Kubernetes    │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Error Monitor   │
│                 │
│ • Extract Error │
│ • Generate Hash │
│ • Classify Type │
│ • Store in DB   │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ AI Analyzer     │
│                 │
│ • Check Existing│
│ • Generate New  │
│ • Validate Safe │
│ • Store Solution│
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Auto Resolver   │
│                 │
│ • Execute Safe  │
│ • Track Result  │
│ • Update Success│
│ • Log History   │
└─────────────────┘
```

## 3. 컴포넌트 상세 아키텍처

### 3.1 Error Monitor 아키텍처

```python
class ErrorMonitor:
    """
    에러 감지 및 로그 수집 컴포넌트
    
    주요 기능:
    - Kubernetes 로그 모니터링
    - 에러 패턴 매칭
    - 중복 에러 필터링
    - 데이터베이스 저장
    """
    
    def __init__(self):
        self.k8s_client = kubernetes.client.CoreV1Api()
        self.db_manager = DatabaseManager()
        self.error_patterns = self.load_error_patterns()
        self.monitoring_namespaces = ['elk-stack']
    
    def monitor_logs(self):
        """로그 모니터링 메인 루프"""
        while True:
            for namespace in self.monitoring_namespaces:
                pods = self.get_pods(namespace)
                for pod in pods:
                    logs = self.get_pod_logs(pod)
                    errors = self.extract_errors(logs)
                    for error in errors:
                        self.process_error(error)
            
            time.sleep(60)  # 1분마다 체크
    
    def extract_errors(self, logs):
        """로그에서 에러 추출"""
        errors = []
        for line in logs.split('\n'):
            if self.is_error_line(line):
                error_info = self.parse_error_line(line)
                if error_info:
                    errors.append(error_info)
        return errors
    
    def is_error_line(self, line):
        """에러 라인 판별"""
        error_keywords = ['ERROR', 'FATAL', 'CRITICAL', 'Exception', 'failed', 'refused']
        return any(keyword in line for keyword in error_keywords)
    
    def generate_error_hash(self, error_message):
        """에러 해시 생성"""
        # 동적 정보 제거 (타임스탬프, IP 등)
        cleaned_message = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '', error_message)
        cleaned_message = re.sub(r'\d+\.\d+\.\d+\.\d+', 'X.X.X.X', cleaned_message)
        cleaned_message = re.sub(r'port \d+', 'port XXXX', cleaned_message)
        
        return hashlib.sha256(cleaned_message.encode()).hexdigest()
```

### 3.2 AI Analyzer 아키텍처

```python
class AIAnalyzer:
    """
    AI 기반 에러 분석 및 해결책 생성
    
    주요 기능:
    - 에러 분석
    - 해결책 생성
    - 안전성 검증
    - 기존 해결책 재사용
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.perplexity_client = PerplexityClient()
        self.safety_checker = SafetyChecker()
        self.success_threshold = 0.5
    
    def analyze_error(self, error_hash):
        """에러 분석 및 해결책 생성"""
        # 1. 기존 해결책 확인
        existing_solution = self.db_manager.get_solution_by_hash(error_hash)
        if existing_solution and existing_solution.success_rate > self.success_threshold:
            return existing_solution
        
        # 2. 새로운 해결책 생성
        error_info = self.db_manager.get_error_by_hash(error_hash)
        if not error_info:
            return None
        
        solution = self.generate_solution(error_info)
        if solution and self.safety_checker.is_safe(solution):
            return self.db_manager.store_solution(error_hash, solution)
        
        return None
    
    def generate_solution(self, error_info):
        """AI를 사용한 해결책 생성"""
        prompt = self.build_prompt(error_info)
        
        try:
            response = self.perplexity_client.generate(prompt)
            solution = self.parse_ai_response(response)
            return solution
        except Exception as e:
            logging.error(f"AI 해결책 생성 실패: {e}")
            return None
    
    def build_prompt(self, error_info):
        """AI 프롬프트 구성"""
        return f"""
        You are an expert Kubernetes and ELK Stack administrator. 
        
        Error Information:
        - Error Message: {error_info.error_message}
        - Pod Name: {error_info.pod_name}
        - Namespace: {error_info.namespace}
        - Error Type: {error_info.error_type}
        
        Please provide a solution in the following JSON format:
        {{
            "solution_type": "kubectl|bash|config",
            "commands": [
                {{
                    "type": "kubectl|bash|config",
                    "command": "actual command",
                    "description": "what this command does",
                    "safe": true,
                    "critical": false
                }}
            ],
            "explanation": "why this solution works",
            "confidence": 0.8
        }}
        
        Only suggest safe, non-destructive commands.
        """
```

### 3.3 Auto Resolver 아키텍처

```python
class AutoResolver:
    """
    자동 해결책 실행 및 추적
    
    주요 기능:
    - 안전한 명령 실행
    - 실행 결과 추적
    - 성공률 업데이트
    - 실행 기록 저장
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.k8s_client = kubernetes.client.CoreV1Api()
        self.safe_mode = True
        self.execution_timeout = 300  # 5분
    
    def resolve_error(self, error_hash):
        """에러 해결 실행"""
        solution = self.db_manager.get_solution_by_hash(error_hash)
        if not solution:
            return {'success': False, 'error': 'No solution found'}
        
        if self.safe_mode and not self.is_safe_solution(solution):
            return {'success': False, 'error': 'Unsafe solution blocked'}
        
        return self.execute_solution(solution)
    
    def execute_solution(self, solution):
        """해결책 실행"""
        start_time = time.time()
        results = []
        
        try:
            for command in solution.commands:
                result = self.execute_command(command)
                results.append(result)
                
                if not result['success']:
                    break
            
            # 전체 성공 여부 결정
            overall_success = all(r['success'] for r in results)
            
            # 실행 기록 저장
            execution_time = time.time() - start_time
            self.db_manager.record_execution(
                solution.id,
                solution.error_hash,
                overall_success,
                execution_time,
                results
            )
            
            # 성공률 업데이트
            self.db_manager.update_success_rate(solution.id, overall_success)
            
            return {
                'success': overall_success,
                'execution_time': execution_time,
                'results': results
            }
            
        except Exception as e:
            logging.error(f"해결책 실행 중 오류: {e}")
            return {'success': False, 'error': str(e)}
    
    def execute_command(self, command):
        """개별 명령 실행"""
        try:
            if command['type'] == 'kubectl':
                return self.execute_kubectl_command(command)
            elif command['type'] == 'bash':
                return self.execute_bash_command(command)
            elif command['type'] == 'config':
                return self.execute_config_command(command)
            else:
                return {'success': False, 'error': f"Unknown command type: {command['type']}"}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def execute_kubectl_command(self, command):
        """kubectl 명령 실행"""
        try:
            result = subprocess.run(
                command['command'].split(),
                capture_output=True,
                text=True,
                timeout=self.execution_timeout
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'command': command['command']
            }
        
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Command timed out'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
```

## 4. 현재 시스템 성능 및 메트릭

### 4.1 성능 지표

| 메트릭 | 현재 값 | 목표 값 | 상태 |
|--------|---------|---------|------|
| **에러 감지 시간** | 1-2분 | 30초 | ⚠️ 개선 필요 |
| **해결책 생성 시간** | 10-30초 | 5초 | ⚠️ 개선 필요 |
| **해결책 실행 시간** | 30-60초 | 10초 | ⚠️ 개선 필요 |
| **전체 해결 시간** | 2-5분 | 1분 | ⚠️ 개선 필요 |
| **해결 성공률** | 0% (미실행) | 80% | ❌ 실행 필요 |
| **메모리 사용량** | 100-200MB | 500MB | ✅ 양호 |
| **CPU 사용률** | 5-10% | 50% | ✅ 양호 |

### 4.2 데이터 현황

```sql
-- 현재 데이터베이스 상태
SELECT 
    'error_logs' as table_name, 
    COUNT(*) as record_count,
    MIN(timestamp) as first_record,
    MAX(timestamp) as last_record
FROM error_logs
UNION ALL
SELECT 
    'solutions' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as first_record,
    MAX(created_at) as last_record
FROM solutions
UNION ALL
SELECT 
    'execution_history' as table_name,
    COUNT(*) as record_count,
    MIN(execution_time) as first_record,
    MAX(execution_time) as last_record
FROM execution_history;

-- 결과 예시:
-- table_name     | record_count | first_record        | last_record
-- error_logs     | 100          | 2024-01-01 09:00:00 | 2024-01-10 15:30:00
-- solutions      | 4            | 2024-01-01 10:00:00 | 2024-01-02 11:00:00
-- execution_history | 0         | NULL                | NULL
```

### 4.3 에러 분포

```sql
-- 에러 유형별 분포
SELECT 
    error_type,
    COUNT(*) as count,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM error_logs) as percentage
FROM error_logs
GROUP BY error_type
ORDER BY count DESC;

-- 결과 예시:
-- error_type        | count | percentage
-- configuration     | 67    | 67.0
-- application       | 33    | 33.0
```

## 5. 시스템 제약사항 및 한계

### 5.1 현재 제약사항

#### 기술적 제약사항
- **단순한 패턴 매칭**: 정규표현식 기반의 제한적 에러 인식
- **정확한 매칭 의존성**: 해시 기반 중복 제거로 인한 유연성 부족
- **제한된 학습 능력**: 통계적 성공률 추적만 가능
- **AI 의존성**: Perplexity API 외부 의존성

#### 운영적 제약사항
- **수동 패턴 관리**: 새로운 에러 패턴 수동 추가 필요
- **안전성 우선**: 보수적 접근으로 인한 제한된 자동화
- **실행 기록 부족**: 실제 해결책 실행 데이터 부족
- **모니터링 범위**: ELK Stack 컴포넌트로 제한

### 5.2 확장성 한계

#### 데이터 확장성
- **에러 증가 시 성능 저하**: 선형 검색으로 인한 속도 저하
- **데이터베이스 크기**: 인덱스 없이 증가하는 데이터량
- **메모리 사용량**: 모든 패턴을 메모리에 로드

#### 기능 확장성
- **새로운 에러 유형**: 패턴 기반 접근의 한계
- **복잡한 에러 시나리오**: 다단계 해결책 처리 어려움
- **다양한 환경**: Kubernetes 외 환경 지원 제한

## 6. 보안 및 안전성

### 6.1 보안 아키텍처

```python
class SafetyChecker:
    """
    해결책 안전성 검증
    
    주요 기능:
    - 위험한 명령 차단
    - 권한 검증
    - 실행 범위 제한
    """
    
    def __init__(self):
        self.dangerous_commands = [
            'rm -rf', 'rm -f', 'delete', 'destroy',
            'format', 'mkfs', 'dd if=', 'chmod 777',
            'shutdown', 'reboot', 'halt'
        ]
        
        self.safe_kubectl_commands = [
            'get', 'describe', 'logs', 'exec',
            'restart', 'rollout restart', 'scale',
            'patch', 'annotate', 'label'
        ]
    
    def is_safe(self, solution):
        """해결책 안전성 검증"""
        if not solution.commands:
            return False
        
        for command in solution.commands:
            if not self.is_safe_command(command):
                return False
        
        return True
    
    def is_safe_command(self, command):
        """개별 명령 안전성 검증"""
        cmd_text = command.get('command', '').lower()
        
        # 위험한 명령 차단
        for dangerous in self.dangerous_commands:
            if dangerous in cmd_text:
                return False
        
        # kubectl 명령 검증
        if command.get('type') == 'kubectl':
            return self.is_safe_kubectl_command(cmd_text)
        
        # bash 명령 검증
        if command.get('type') == 'bash':
            return self.is_safe_bash_command(cmd_text)
        
        return command.get('safe', False)
    
    def is_safe_kubectl_command(self, cmd_text):
        """kubectl 명령 안전성 검증"""
        # 읽기 전용 명령은 안전
        readonly_commands = ['get', 'describe', 'logs', 'explain']
        if any(readonly in cmd_text for readonly in readonly_commands):
            return True
        
        # 허용된 수정 명령 확인
        return any(safe in cmd_text for safe in self.safe_kubectl_commands)
```

### 6.2 권한 관리

```yaml
# rbac.yaml - 최소 권한 원칙
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: elk-stack
  name: elk-auto-resolver
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch", "patch", "update"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "patch", "update"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods/exec"]
  verbs: ["create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: elk-auto-resolver-binding
  namespace: elk-stack
subjects:
- kind: ServiceAccount
  name: elk-auto-resolver
  namespace: elk-stack
roleRef:
  kind: Role
  name: elk-auto-resolver
  apiGroup: rbac.authorization.k8s.io
```

## 7. 모니터링 및 로깅

### 7.1 시스템 모니터링

```python
class SystemMonitor:
    """
    시스템 상태 모니터링
    
    주요 기능:
    - 컴포넌트 상태 추적
    - 성능 메트릭 수집
    - 알림 시스템
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.components = ['elasticsearch', 'kibana', 'logstash', 'filebeat']
        self.metrics = {
            'errors_detected': 0,
            'solutions_generated': 0,
            'solutions_executed': 0,
            'success_rate': 0.0,
            'avg_resolution_time': 0.0
        }
    
    def check_system_health(self):
        """시스템 전체 상태 확인"""
        health_status = {}
        
        for component in self.components:
            health_status[component] = self.check_component_health(component)
        
        # 데이터베이스 상태 확인
        health_status['database'] = self.check_database_health()
        
        # 전체 상태 저장
        self.db_manager.update_system_status(health_status)
        
        return health_status
    
    def check_component_health(self, component):
        """개별 컴포넌트 상태 확인"""
        try:
            pods = self.k8s_client.list_namespaced_pod(
                namespace='elk-stack',
                label_selector=f'app={component}'
            )
            
            if not pods.items:
                return {'status': 'ERROR', 'message': 'No pods found'}
            
            pod = pods.items[0]
            if pod.status.phase == 'Running':
                return {'status': 'OK', 'message': 'Pod is running'}
            else:
                return {'status': 'ERROR', 'message': f'Pod status: {pod.status.phase}'}
        
        except Exception as e:
            return {'status': 'ERROR', 'message': str(e)}
    
    def collect_metrics(self):
        """성능 메트릭 수집"""
        # 데이터베이스에서 메트릭 수집
        metrics = self.db_manager.get_system_metrics()
        
        self.metrics.update({
            'errors_detected': metrics.get('total_errors', 0),
            'solutions_generated': metrics.get('total_solutions', 0),
            'solutions_executed': metrics.get('total_executions', 0),
            'success_rate': metrics.get('success_rate', 0.0),
            'avg_resolution_time': metrics.get('avg_resolution_time', 0.0)
        })
        
        return self.metrics
```

### 7.2 로깅 전략

```python
# logging_config.py
import logging
import json
from datetime import datetime

class StructuredLogger:
    """
    구조화된 로깅
    
    주요 기능:
    - JSON 형식 로그
    - 컨텍스트 정보 포함
    - 성능 메트릭 추적
    """
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 핸들러 설정
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_error_detected(self, error_info):
        """에러 감지 로그"""
        log_data = {
            'event': 'error_detected',
            'timestamp': datetime.now().isoformat(),
            'error_hash': error_info.get('error_hash'),
            'error_type': error_info.get('error_type'),
            'pod_name': error_info.get('pod_name'),
            'namespace': error_info.get('namespace')
        }
        
        self.logger.info(json.dumps(log_data))
    
    def log_solution_generated(self, solution_info):
        """해결책 생성 로그"""
        log_data = {
            'event': 'solution_generated',
            'timestamp': datetime.now().isoformat(),
            'error_hash': solution_info.get('error_hash'),
            'solution_type': solution_info.get('solution_type'),
            'confidence': solution_info.get('confidence'),
            'source': solution_info.get('source')
        }
        
        self.logger.info(json.dumps(log_data))
    
    def log_solution_executed(self, execution_info):
        """해결책 실행 로그"""
        log_data = {
            'event': 'solution_executed',
            'timestamp': datetime.now().isoformat(),
            'solution_id': execution_info.get('solution_id'),
            'success': execution_info.get('success'),
            'execution_time': execution_info.get('execution_time'),
            'error_message': execution_info.get('error_message')
        }
        
        self.logger.info(json.dumps(log_data))
```

## 8. 배포 및 환경 설정

### 8.1 배포 아키텍처

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elk-auto-resolver
  namespace: elk-stack
spec:
  replicas: 1
  selector:
    matchLabels:
      app: elk-auto-resolver
  template:
    metadata:
      labels:
        app: elk-auto-resolver
    spec:
      serviceAccountName: elk-auto-resolver
      containers:
      - name: resolver
        image: elk-auto-resolver:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: PERPLEXITY_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secret
              key: perplexity-key
        - name: SAFE_MODE
          value: "true"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: config
          mountPath: /app/config
      volumes:
      - name: config
        configMap:
          name: elk-resolver-config
```

### 8.2 환경 설정

```yaml
# config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: elk-resolver-config
  namespace: elk-stack
data:
  config.yaml: |
    database:
      host: "postgresql-service"
      port: 5432
      database: "elk_resolver"
      username: "resolver_user"
      # password는 Secret에서 관리
    
    monitoring:
      namespaces:
        - "elk-stack"
      check_interval: 60
      log_retention_days: 30
    
    ai:
      provider: "perplexity"
      model: "llama-3.1-sonar-large-128k-online"
      timeout: 30
      max_retries: 3
    
    safety:
      enabled: true
      dangerous_commands:
        - "rm -rf"
        - "delete"
        - "destroy"
      safe_kubectl_commands:
        - "get"
        - "describe"
        - "restart"
        - "scale"
    
    execution:
      timeout: 300
      max_concurrent: 3
      retry_count: 2
```

## 9. 개발 및 운영 가이드

### 9.1 개발 환경 설정

```bash
# 개발 환경 설정
git clone <repository>
cd elk-auto-resolver

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
export DATABASE_URL="postgresql://user:pass@localhost:5432/elk_resolver"
export PERPLEXITY_API_KEY="your-api-key"
export SAFE_MODE="true"
export LOG_LEVEL="DEBUG"

# 데이터베이스 초기화
psql -f database_schema.sql

# 테스트 실행
python -m pytest tests/

# 개발 서버 실행
python main.py
```

### 9.2 운영 절차

```bash
# 시스템 상태 확인
kubectl get pods -n elk-stack
kubectl logs -n elk-stack deployment/elk-auto-resolver

# 데이터베이스 상태 확인
kubectl exec -it postgresql-pod -- psql -U resolver_user -d elk_resolver

# 메트릭 확인
curl http://elk-resolver-service:8080/metrics

# 로그 확인
kubectl logs -n elk-stack -l app=elk-auto-resolver --tail=100

# 설정 업데이트
kubectl apply -f config.yaml
kubectl rollout restart deployment/elk-auto-resolver -n elk-stack
```

## 10. 결론

### 10.1 현재 시스템 요약

ELK Auto Resolver는 **규칙기반 AI 시스템**으로서:

**장점:**
- ✅ 안정적이고 예측 가능한 동작
- ✅ 빠른 응답 시간
- ✅ 낮은 리소스 사용량
- ✅ 명확한 의사결정 과정

**한계:**
- ❌ 제한된 학습 능력
- ❌ 정확한 매칭에만 의존
- ❌ 복잡한 에러 패턴 처리 어려움
- ❌ 수동 규칙 관리 필요

### 10.2 개선 방향

1. **단기 개선 (1-2개월)**
   - 텍스트 유사도 매칭 도입
   - 성능 모니터링 강화
   - 실행 기록 데이터 축적

2. **중기 개선 (3-6개월)**
   - 머신러닝 분류기 통합
   - 자동 패턴 학습 기능
   - 다양한 환경 지원

3. **장기 개선 (6개월+)**
   - 딥러닝 모델 도입
   - 강화학습 기반 최적화
   - 완전 자동화 시스템

---

**문서 작성일**: 2025-07-10  
**버전**: 1.0  
**마지막 업데이트**: 2025-07-10  
**다음 리뷰**: 2025-07-17