# ELK Auto Resolver - 워크플로우 및 운영 가이드

## 🔄 시스템 워크플로우

### 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ELK Auto Resolver 워크플로우                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ELK Stack     │───▶│  Error Monitor  │───▶│  AI Analyzer    │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │Elasticsearch│ │    │ │로그 검색     │ │    │ │Perplexity   │ │
│ │  (9200)     │ │    │ │에러 분류     │ │    │ │API 분석     │ │
│ │             │ │    │ │임계값 체크   │ │    │ │해결책 생성   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │                 │    │                 │
│ │Logstash     │ │    │ 60초마다 실행    │    │ JSON 응답 파싱  │
│ │Kibana       │ │    │                 │    │                 │
│ │Filebeat     │ │    │                 │    │                 │
│ └─────────────┘ │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Log Collection  │    │   PostgreSQL    │    │  Auto Resolver  │
│                 │    │   Database      │    │                 │
│ • System Logs   │    │                 │    │ ┌─────────────┐ │
│ • App Logs      │    │ ┌─────────────┐ │    │ │Kubernetes   │ │
│ • Kernel Logs   │    │ │error_logs   │ │    │ │Commands     │ │
│ • Service Logs  │    │ │solutions    │ │    │ │             │ │
│                 │    │ │execution_   │ │    │ │Safe Mode    │ │
│                 │    │ │history      │ │    │ │Validation   │ │
│                 │    │ │error_       │ │    │ │             │ │
│                 │    │ │patterns     │ │    │ └─────────────┘ │
│                 │    │ │system_      │ │    │                 │
│                 │    │ │status       │ │    │ 결과 기록 및     │
│                 │    │ └─────────────┘ │    │ 성공률 업데이트  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 상세 워크플로우

#### 1단계: 에러 탐지 (Error Monitor)
```
┌─────────────────────────────────────────────────────────────┐
│                     Error Monitor                          │
├─────────────────────────────────────────────────────────────┤
│ 📍 위치: error_monitor.py                                   │
│ ⏰ 실행주기: 60초마다                                        │
│ 🔗 연결: Elasticsearch (localhost:9200)                    │
├─────────────────────────────────────────────────────────────┤
│ 과정:                                                       │
│ 1. Elasticsearch 연결 확인                                  │
│ 2. 최근 5분간 로그 검색                                      │
│ 3. 에러 키워드 매칭                                         │
│    • error, exception, failed, crash                       │
│    • panic, fatal, killed, timeout                         │
│    • 커널/시스템 에러 패턴                                   │
│ 4. 로그 파싱 및 구조화                                       │
│    • message 배열 → 문자열 변환                             │
│    • host 정보 추출                                         │
│    • 타임스탬프 정규화                                       │
│ 5. 에러 분류 실행                                           │
│    • configuration, application, system                     │
│    • network, storage, kubernetes 등                       │
│ 6. 임계값 체크 (기본: 5개 이상)                             │
│ 7. PostgreSQL 저장                                         │
└─────────────────────────────────────────────────────────────┘
```

#### 2단계: AI 분석 (AI Analyzer)
```
┌─────────────────────────────────────────────────────────────┐
│                    AI Analyzer                             │
├─────────────────────────────────────────────────────────────┤
│ 📍 위치: ai_analyzer.py                                     │
│ 🤖 AI API: Perplexity (sonar 모델)                         │
│ 🔗 연결: https://api.perplexity.ai                         │
├─────────────────────────────────────────────────────────────┤
│ 과정:                                                       │
│ 1. 기존 해결책 조회 (success_rate > 50%)                    │
│ 2. 새로운 에러인 경우 AI 분석 요청                           │
│ 3. 프롬프트 구성:                                           │
│    • 에러 정보 (타입, 메시지, 시스템)                        │
│    • 스택 트레이스 및 원시 로그                              │
│    • Kubernetes/ELK 환경 정보                              │
│ 4. AI 응답 수신 및 JSON 파싱                               │
│ 5. 해결책 검증:                                             │
│    • 안전한 명령어만 선별                                    │
│    • 위험한 명령어 필터링                                    │
│    • 필수 필드 검증                                         │
│ 6. PostgreSQL 저장                                         │
└─────────────────────────────────────────────────────────────┘
```

#### 3단계: 자동 해결 (Auto Resolver)
```
┌─────────────────────────────────────────────────────────────┐
│                   Auto Resolver                            │
├─────────────────────────────────────────────────────────────┤
│ 📍 위치: auto_resolver.py                                   │
│ 🔧 실행환경: Kubernetes 클러스터                            │
│ 🛡️ 안전모드: 기본 활성화                                    │
├─────────────────────────────────────────────────────────────┤
│ 과정:                                                       │
│ 1. 사전 검사:                                              │
│    • Kubernetes 연결 확인                                   │
│    • 네임스페이스 존재 확인                                  │
│    • 안전 모드 검증                                         │
│ 2. 명령어 순차 실행:                                        │
│    • kubectl 명령어 (restart, scale 등)                     │
│    • bash 명령어 (안전한 것만)                              │
│    • 설정 파일 수정                                         │
│ 3. 실행 모니터링:                                           │
│    • 타임아웃 관리 (기본 300초)                             │
│    • 출력 결과 캡처                                         │
│    • 오류 상황 처리                                         │
│ 4. 사후 검증:                                              │
│    • Pod 상태 확인                                          │
│    • 서비스 헬스체크                                        │
│    • 결과 검증                                              │
│ 5. 실행 결과 기록                                           │
│    • 성공/실패 상태                                         │
│    • 실행 시간 및 출력                                       │
│    • 성공률 자동 업데이트                                    │
└─────────────────────────────────────────────────────────────┘
```

## 🔌 시스템 연결 정보

### 외부 서비스 연결
```yaml
연결 서비스:
  Elasticsearch:
    주소: localhost:9200 (포트포워딩)
    원본: 10.96.206.169:9200 (ClusterIP)
    인덱스: logstash-*
    
  PostgreSQL:
    주소: localhost:5432
    데이터베이스: elk_resolver
    사용자: postgres
    비밀번호: elk_resolver_2024
    
  Perplexity AI:
    API: https://api.perplexity.ai
    모델: sonar
    인증: Bearer Token
    
  Kubernetes:
    설정: ~/.kube/config
    네임스페이스: elk-stack
    클라이언트: kubectl + Python kubernetes 라이브러리
```

### 포트 및 네트워크
```bash
# 필요한 포트 포워딩
kubectl port-forward -n elk-stack svc/elasticsearch 9200:9200 &

# 서비스 상태 확인
kubectl get svc -n elk-stack
kubectl get pods -n elk-stack

# 네트워크 연결 테스트
curl http://localhost:9200/_cluster/health
```

## 📊 데이터 플로우

### 데이터 변환 과정
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ ELK 원시 로그    │───▶│ 파싱된 에러      │───▶│ 구조화된 데이터  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
│                      │                      │
│ • message: []        │ • message: string    │ • error_logs 테이블
│ • host: object       │ • host: string       │ • hash_signature
│ • @timestamp         │ • timestamp          │ • error_type
│ • program            │ • source_system      │ • severity
│ • event.original     │ • error_type         │
│                      │ • severity           │
│                      │                      │
▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ AI 분석 요청     │───▶│ 해결책 생성      │───▶│ 실행 및 결과     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
│                      │                      │
│ • 프롬프트 구성       │ • solutions 테이블   │ • execution_history
│ • 컨텍스트 정보       │ • solution_commands  │ • success_rate 업데이트
│ • 안전성 요구사항     │ • ai_analysis        │ • 통계 데이터
│                      │ • safety validation  │
```

## 🚀 실행 방법

### 기본 실행
```bash
# 디렉토리 이동
cd /root/elk-auto-resolver

# 포트포워딩 설정
kubectl port-forward -n elk-stack svc/elasticsearch 9200:9200 &

# 일회성 테스트
python3 main.py --once

# 지속적 실행
python3 main.py

# 백그라운드 실행
./run.sh --daemon
```

### 모니터링
```bash
# 로그 확인
tail -f /var/log/elk-auto-resolver.log

# 프로세스 상태
ps aux | grep main.py

# 포트 상태
netstat -tulpn | grep 9200
```

## 📈 성능 및 통계

### 실행 통계 확인
```bash
# 시스템 통계 (매 5분마다 출력)
=== 통계 정보 ===
가동 시간: 0:05:23
탐지된 에러: 100개
분석된 에러: 15개
해결된 에러: 12개
해결 실패: 3개
해결 성공률: 80.0%
```

### 리소스 사용량
```bash
# 메모리 사용량 확인
ps aux | grep python3 | grep main.py

# CPU 사용량 모니터링
top -p $(pgrep -f main.py)
```

## 🔧 설정 조정

### config.yaml 주요 설정
```yaml
monitoring:
  check_interval: 60      # 검색 주기 (초)
  error_threshold: 5      # 처리 임계값

resolver:
  max_retries: 3         # 최대 재시도
  timeout: 300           # 명령어 타임아웃
  safe_mode: true        # 안전 모드

perplexity:
  model: "sonar"         # AI 모델
  api_key: "pplx-..."    # API 키
```

### 임계값 조정
```bash
# 더 민감한 탐지 (임계값 낮춤)
monitoring:
  error_threshold: 2

# 덜 민감한 탐지 (임계값 높임)  
monitoring:
  error_threshold: 10
```

## ⚠️ 주의사항

### 안전성 고려사항
1. **Safe Mode**: 항상 활성화 권장
2. **API 비용**: 퍼플렉시티 API 사용량 모니터링
3. **권한 관리**: Kubernetes 권한 최소화
4. **백업**: 데이터베이스 정기 백업

### 문제 해결
```bash
# Elasticsearch 연결 실패
kubectl get pods -n elk-stack
kubectl port-forward -n elk-stack svc/elasticsearch 9200:9200

# PostgreSQL 연결 실패
sudo systemctl status postgresql
sudo -u postgres psql elk_resolver -c "SELECT 1;"

# AI API 오류
curl -H "Authorization: Bearer pplx-..." https://api.perplexity.ai/chat/completions
```

이 워크플로우 가이드를 통해 시스템의 전체적인 동작 방식과 각 구성요소의 역할을 이해할 수 있습니다.