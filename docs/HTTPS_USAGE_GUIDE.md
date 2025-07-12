# HTTPS ELK Auto Resolver 사용 가이드

## 개요
이 문서는 HTTPS/TLS가 적용된 ELK Stack 환경에서 ELK Auto Resolver를 사용하는 방법을 설명합니다.

## 🔒 HTTPS 환경 변경사항

### 주요 업데이트
- ✅ Elasticsearch HTTPS 연결 지원
- ✅ SSL 인증서 검증 비활성화 (self-signed 인증서)
- ✅ 사용자 인증 (elastic/elastic123)
- ✅ 포트 포워딩 자동 관리
- ✅ Kubernetes 서비스 연결 지원

### 설정 파일 변경사항
`config.yaml`에 다음 설정이 추가되었습니다:

```yaml
elasticsearch:
  host: "localhost"
  port: 9200
  index_pattern: "logstash-*"
  # HTTPS/TLS 설정
  use_ssl: true
  verify_certs: false  # self-signed 인증서 사용 시
  ssl_show_warn: false
  username: "elastic"
  password: "elastic123"
  # Kubernetes 내부 접근 (선택사항)
  k8s_service_host: "elasticsearch.elk-stack.svc.cluster.local"
  k8s_service_port: 9200
```

## 📋 사전 요구사항

### 1. Python 패키지 설치
```bash
cd /root/elk-auto-resolver
pip install -r requirements.txt
```

### 2. Kubernetes 접근 권한
```bash
# kubectl이 설치되어 있고 ELK 클러스터에 접근 가능해야 함
kubectl get pods -n elk-stack
```

### 3. ELK Stack HTTPS 설정 완료
- Elasticsearch: HTTPS 활성화
- Kibana: HTTPS 활성화 
- SSL 인증서: 적절한 키 사용법 설정
- 사용자 인증: elastic/elastic123

## 🚀 실행 방법

### 방법 1: 자동 관리 스크립트 사용 (권장)
```bash
cd /root/elk-auto-resolver
python3 start_https_resolver.py
```

**기능:**
- 자동 포트 포워딩 설정
- HTTPS 연결 테스트
- 에러 모니터링 시작
- 정리 작업 자동 수행

### 방법 2: 수동 설정
```bash
# 1. 포트 포워딩 설정
kubectl port-forward -n elk-stack svc/elasticsearch 9200:9200 &

# 2. 연결 테스트
python3 https_test.py

# 3. 에러 모니터 시작
python3 error_monitor.py
```

## 🔍 연결 테스트

### HTTPS 연결 테스트
```bash
cd /root/elk-auto-resolver
python3 https_test.py
```

**예상 출력:**
```
=== ELK HTTPS 연결 테스트 ===

Elasticsearch HTTPS 연결 테스트...
호스트: https://localhost:9200
사용자: elastic
✅ HTTPS 연결 성공!
클러스터 상태: green
노드 수: 1
Logstash 인덱스 수: 5

✅ ELK Auto Resolver가 HTTPS 환경에서 작동할 수 있습니다!
```

## 📊 모니터링 기능

### 에러 탐지
- **로그 레벨**: ERROR, FATAL, CRITICAL
- **키워드 기반**: error, exception, failed, crash, panic
- **시스템 로그**: kernel, systemd 오류
- **임계값**: 5개 이상 동일 에러 시 처리

### 에러 분류
- **Memory**: OOM, segmentation fault
- **Network**: connection refused, timeout, DNS
- **Storage**: disk full, no space left
- **Kubernetes**: pod, container, deployment 오류
- **Database**: connection pool, query 오류
- **Security**: permission denied, unauthorized
- **Configuration**: config 오류, syntax error

### AI 분석 및 자동 해결
- **Perplexity AI**: 에러 원인 분석
- **자동 해결**: Kubernetes 리소스 재시작, 스케일링
- **안전 모드**: 사전 승인된 명령어만 실행

## 🔧 트러블슈팅

### 1. HTTPS 연결 실패
```bash
# 포트 포워딩 확인
ps aux | grep port-forward

# 포트 포워딩 재설정
pkill -f "kubectl.*port-forward"
kubectl port-forward -n elk-stack svc/elasticsearch 9200:9200 &
```

### 2. 인증 오류
```bash
# Elasticsearch 사용자 확인
kubectl exec -n elk-stack elasticsearch-pod -- curl -k -u elastic:elastic123 https://localhost:9200
```

### 3. SSL 인증서 오류
```bash
# 인증서 상태 확인
kubectl get secret -n elk-stack elk-ssl-certs
kubectl exec -n elk-stack kibana-pod -- ls -la /usr/share/kibana/config/certs/
```

### 4. 로그 수집 확인
```bash
# Logstash 인덱스 확인
curl -k -u elastic:elastic123 "https://localhost:9200/_cat/indices?v" | grep logstash

# Filebeat 상태 확인
kubectl get pods -n elk-stack | grep filebeat
```

## 📝 로그 및 모니터링

### 로그 파일
```bash
# Auto Resolver 로그
tail -f /root/elk-auto-resolver/elk_auto_resolver.log

# 개별 모듈 로그
python3 -c "import logging; logging.basicConfig(level=logging.DEBUG)"
```

### 상태 확인 명령어
```bash
# ELK Stack 전체 상태
kubectl get all -n elk-stack

# Elasticsearch 클러스터 상태
curl -k -u elastic:elastic123 "https://localhost:9200/_cluster/health?pretty"

# Kibana 접속 확인
curl -k -I https://211.183.3.110:30050
```

## 🎯 사용 예시

### 기본 실행
```bash
cd /root/elk-auto-resolver
python3 start_https_resolver.py
```

### 디버그 모드 실행
```bash
cd /root/elk-auto-resolver
PYTHONPATH=. python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from start_https_resolver import HTTPSELKResolver
resolver = HTTPSELKResolver()
resolver.run()
"
```

### 개별 모듈 테스트
```bash
# 에러 모니터 테스트
python3 error_monitor.py

# AI 분석기 테스트
python3 ai_analyzer.py

# 자동 해결기 테스트
python3 auto_resolver.py
```

## ⚠️ 주의사항

### 보안
- Self-signed 인증서 사용으로 인한 경고는 정상
- 프로덕션 환경에서는 적절한 CA 인증서 사용 권장
- 기본 패스워드 변경 권장

### 네트워크
- 포트 포워딩은 일시적 연결 방법
- Kubernetes 클러스터 내에서 실행 시 직접 서비스 연결 가능
- 방화벽 설정 확인 필요

### 리소스
- 지속적인 모니터링으로 인한 리소스 사용
- Elasticsearch 쿼리 빈도 조절 가능
- 로그 파일 크기 모니터링 필요

## 🔄 업그레이드 정보

이 버전의 주요 변경사항:
- HTTP → HTTPS 연결 지원
- 사용자 인증 추가
- SSL 인증서 처리 개선
- 포트 포워딩 자동 관리
- Deprecated API 업데이트 (basic_auth, request_timeout)

이전 HTTP 버전과의 호환성을 위해 `use_ssl: false` 설정도 지원합니다.

---

**문제 발생 시 체크리스트:**
1. ✅ ELK Stack HTTPS 설정 완료
2. ✅ kubectl 접근 권한 확인
3. ✅ 포트 포워딩 설정
4. ✅ 인증 정보 확인 (elastic/elastic123)
5. ✅ Python 패키지 설치
6. ✅ 로그 파일 확인