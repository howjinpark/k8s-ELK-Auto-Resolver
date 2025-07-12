# ELK Auto Resolver 설치 전 준비사항

## 필수 선수조건

### 1. 🔧 **ELK Stack 설치 (필수)**

ELK Auto Resolver는 이미 구축된 ELK Stack과 연동하여 작동합니다.

#### ELK Stack 구성 요소
- **Elasticsearch**: 로그 데이터 저장 및 검색
- **Logstash**: 로그 데이터 수집 및 변환  
- **Kibana**: 로그 시각화 (선택사항)
- **Filebeat**: 로그 수집 에이전트

#### ELK Stack 설치 방법

##### 옵션 1: 프로젝트 포함 YAML 사용 (권장)
```bash
# 1. HTTP 버전 (개발환경)
kubectl apply -f elk/elasticsearch-simple.yaml
kubectl apply -f elk/logstash-simple.yaml  
kubectl apply -f elk/kibana-simple-new.yaml
kubectl apply -f elk/filebeat-simple.yaml

# 2. HTTPS 버전 (프로덕션)
kubectl apply -f elk/elasticsearch-https-final.yaml
kubectl apply -f elk/logstash-https-final.yaml
kubectl apply -f elk/kibana-https-final.yaml
kubectl apply -f elk/filebeat-https-final.yaml
```

##### 옵션 2: Helm 차트 사용
```bash
# Elastic Helm 레포지토리 추가
helm repo add elastic https://helm.elastic.co
helm repo update

# Elasticsearch 설치
helm install elasticsearch elastic/elasticsearch --namespace elk-stack --create-namespace

# Logstash 설치  
helm install logstash elastic/logstash --namespace elk-stack

# Kibana 설치
helm install kibana elastic/kibana --namespace elk-stack

# Filebeat 설치
helm install filebeat elastic/filebeat --namespace elk-stack
```

##### 옵션 3: 간단한 테스트 환경
```bash
# testelk 디렉토리의 간단한 설치 스크립트 사용
cd testelk/
./install-elk.sh
```

#### ELK Stack 설치 확인
```bash
# 모든 Pod가 Running 상태인지 확인
kubectl get pods -n elk-stack

# 서비스 확인  
kubectl get svc -n elk-stack

# Elasticsearch 접속 테스트
kubectl port-forward -n elk-stack service/elasticsearch 9200:9200 &
curl -k -u elastic:your_password "https://localhost:9200/_cluster/health"
```

### 2. 🔑 **API 키 발급 (필수)**

#### Perplexity AI API 키
1. [Perplexity AI](https://www.perplexity.ai/) 접속
2. 회원가입/로그인
3. Settings → API → Generate new API key
4. 생성된 키 복사 (예: `pplx-xxxxxxxxxxxxx`)

#### Slack 웹훅 URL  
1. Slack 워크스페이스 → Apps → Browse App Directory
2. "Incoming Webhooks" 검색 후 설치
3. 알림받을 채널 선택
4. 웹훅 URL 복사 (예: `https://hooks.slack.com/services/...`)

### 3. 🖥️ **시스템 요구사항**

#### 최소 요구사항
- **OS**: Ubuntu 20.04+ (또는 호환 Linux)
- **CPU**: 2 Core 이상
- **메모리**: 4GB RAM 이상  
- **디스크**: 20GB 여유 공간
- **네트워크**: 인터넷 연결

#### 권장 요구사항
- **CPU**: 4 Core 이상
- **메모리**: 8GB RAM 이상
- **디스크**: 50GB 여유 공간
- **SSD**: 성능 향상을 위해 권장

### 4. 🐳 **Kubernetes 환경 (필수)**

#### Kubernetes 클러스터
- **버전**: v1.20+ 권장
- **노드**: 최소 1개 (권장 3개 이상)
- **권한**: cluster-admin 또는 필요한 RBAC 권한

#### kubectl 설정
```bash
# kubectl 설치 확인
kubectl version --client

# 클러스터 연결 확인
kubectl cluster-info
kubectl get nodes

# 필요한 네임스페이스 확인
kubectl get namespace elk-stack
```

## 설치 프로세스

### 단계별 설치 순서

#### 1단계: ELK Stack 설치
```bash
# ELK Stack이 없는 경우
git clone https://github.com/howjinpark/k8s-ELK-Auto-Resolver.git
cd k8s-ELK-Auto-Resolver

# HTTP 버전 설치 (간단한 테스트용)
kubectl apply -f elk/elasticsearch-simple.yaml
kubectl apply -f elk/logstash-simple.yaml
kubectl apply -f elk/kibana-simple-new.yaml  
kubectl apply -f elk/filebeat-simple.yaml

# 설치 확인
kubectl get pods -n elk-stack
```

#### 2단계: API 키 준비
- Perplexity AI API 키 발급
- Slack 웹훅 URL 생성

#### 3단계: ELK Auto Resolver 설치
```bash
# 자동 설치 실행
./install.sh

# API 키 설정
nano config/.env
```

#### 4단계: 실행 및 테스트
```bash
# 실행
source venv/bin/activate
python3 scripts/start_resolver.py
```

## 환경 변수 설정 가이드

### config/.env 파일 작성
```bash
# 필수 항목들 (사용자가 직접 입력해야 함)

# Perplexity AI API 키 (필수)
PERPLEXITY_API_KEY=pplx-your-actual-api-key-here

# Slack 웹훅 URL (필수)  
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/ACTUAL/WEBHOOK

# Elasticsearch 비밀번호 (필수)
ELASTICSEARCH_PASSWORD=your_elasticsearch_password

# 데이터베이스 비밀번호 (install.sh가 자동 생성하지만 변경 가능)
DATABASE_PASSWORD=your_secure_database_password
```

### API 키 찾는 방법

#### Perplexity API 키
```bash
# 발급 후 키 형태 확인
# 올바른 형태: pplx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 잘못된 형태: "api_key": "xxx" (따옴표나 JSON 형태 아님)
```

#### Slack 웹훅 테스트
```bash
# 웹훅이 올바른지 테스트
curl -X POST -H 'Content-type: application/json' \
--data '{"text":"ELK Auto Resolver 테스트 메시지"}' \
YOUR_SLACK_WEBHOOK_URL
```

### 일반적인 실수들

❌ **자주하는 실수들**
```bash
# 잘못된 API 키 형태
PERPLEXITY_API_KEY="pplx-xxx"  # 따옴표 불필요
PERPLEXITY_API_KEY=your_api_key_here  # 실제 키로 교체 안함

# 잘못된 웹훅 URL
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/  # 불완전한 URL
SLACK_WEBHOOK_URL="https://..."  # 따옴표 불필요
```

✅ **올바른 형태**
```bash
PERPLEXITY_API_KEY=pplx-actual-long-key-string-here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T123/B456/complete-webhook-url
ELASTICSEARCH_PASSWORD=elastic123
DATABASE_PASSWORD=secure_password_123
```

## 설치 확인 체크리스트

### ✅ 설치 전 체크리스트
- [ ] Kubernetes 클러스터 접근 가능
- [ ] ELK Stack 설치 완료 및 정상 작동
- [ ] Perplexity AI API 키 발급 완료
- [ ] Slack 웹훅 URL 생성 완료
- [ ] 시스템 요구사항 확인 (메모리, 디스크)

### ✅ 설치 후 체크리스트  
- [ ] Python 가상환경 생성 확인
- [ ] PostgreSQL 데이터베이스 생성 확인
- [ ] .env 파일 올바른 API 키 설정
- [ ] Elasticsearch 연결 테스트 성공
- [ ] Slack 알림 테스트 성공
- [ ] ELK Auto Resolver 정상 실행

## 문제 해결

### ELK Stack 관련 문제
```bash
# ELK Stack Pod 상태 확인
kubectl get pods -n elk-stack
kubectl describe pod <pod-name> -n elk-stack

# Elasticsearch 접속 문제
kubectl port-forward -n elk-stack service/elasticsearch 9200:9200
curl -k "https://localhost:9200/_cluster/health"
```

### API 키 관련 문제
```bash
# Perplexity API 키 테스트
curl -X POST "https://api.perplexity.ai/chat/completions" \
-H "Authorization: Bearer YOUR_API_KEY" \
-H "Content-Type: application/json" \
-d '{"model": "sonar", "messages": [{"role": "user", "content": "test"}]}'

# Slack 웹훅 테스트  
curl -X POST -H 'Content-type: application/json' \
--data '{"text":"테스트 메시지"}' \
YOUR_SLACK_WEBHOOK_URL
```

이 가이드를 따라하면 ELK Auto Resolver를 성공적으로 설치할 수 있습니다!