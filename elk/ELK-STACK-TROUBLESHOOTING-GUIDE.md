# ELK Stack 트러블슈팅 가이드

## 목차
1. [키바나 연결 문제](#1-키바나-연결-문제)
2. [DNS 해석 오류](#2-dns-해석-오류)
3. [노드 간 네트워킹 문제](#3-노드-간-네트워킹-문제)
4. [SSL/TLS 인증서 문제](#4-ssltls-인증서-문제)
5. [Readiness Probe 실패](#5-readiness-probe-실패)
6. [포트 포워딩 문제](#6-포트-포워딩-문제)
7. [보안 설정 문제](#7-보안-설정-문제)
8. [SSL 키 사용법 호환성 문제](#8-ssl-키-사용법-호환성-문제)
9. [NodePort 외부 접속 문제](#9-nodeport-외부-접속-문제)
10. [ELK Auto Resolver HTTPS 호환성 문제](#10-elk-auto-resolver-https-호환성-문제)
11. [데이터베이스 외래키 제약 오류](#11-데이터베이스-외래키-제약-오류)

---

## 1. 키바나 연결 문제

### 증상
```bash
kubectl get pods -n elk-stack
NAME                             READY   STATUS    RESTARTS      AGE
kibana-xxx                       0/1     Running   6 (7h20m ago) 10h
```

### 원인 분석
- 키바나가 Elasticsearch에 연결하지 못함
- HTTPS 연결 설정 오류
- 네트워크 정책 또는 DNS 문제

### 해결 과정

#### Step 1: 키바나 로그 확인
```bash
kubectl logs -n elk-stack kibana-pod --tail=50
```

**발견된 오류:**
```
{"type":"log","@timestamp":"2025-07-11T01:06:03+00:00","tags":["error","elasticsearch-service"],"pid":6,"message":"Unable to retrieve version information from Elasticsearch nodes. getaddrinfo EAI_AGAIN elasticsearch"}
```

#### Step 2: DNS 해석 문제 확인
```bash
kubectl exec -n elk-stack kibana-pod -- cat /etc/resolv.conf
kubectl exec -n elk-stack kibana-pod -- getent hosts elasticsearch
```

**결과:** DNS 해석 실패

#### Step 3: 해결 방법 적용
```yaml
# hostAliases를 키바나 배포에 추가
spec:
  template:
    spec:
      hostAliases:
      - ip: "10.106.80.20"
        hostnames: ["elasticsearch"]
```

### 해결 명령어
```bash
kubectl patch deployment -n elk-stack kibana --patch='
{
  "spec": {
    "template": {
      "spec": {
        "hostAliases": [
          {
            "ip": "10.106.80.20",
            "hostnames": ["elasticsearch"]
          }
        ]
      }
    }
  }
}'
```

---

## 2. DNS 해석 오류

### 증상
```
getaddrinfo EAI_AGAIN elasticsearch
```

### 원인
- CoreDNS 설정 문제
- 서비스 이름 해석 실패
- 네임스페이스 내 DNS 전파 지연

### 해결 방법

#### 방법 1: FQDN 사용
```yaml
# 짧은 이름 대신 완전한 FQDN 사용
elasticsearch → elasticsearch.elk-stack.svc.cluster.local
```

#### 방법 2: hostAliases 사용
```yaml
spec:
  template:
    spec:
      hostAliases:
      - ip: "SERVICE_IP"
        hostnames: ["SERVICE_NAME"]
```

#### 방법 3: IP 주소 직접 사용 (임시)
```yaml
env:
- name: ELASTICSEARCH_HOSTS
  value: "https://10.106.80.20:9200"
```

### 검증 명령어
```bash
# DNS 서비스 확인
kubectl get svc -n kube-system | grep dns

# CoreDNS 파드 상태 확인
kubectl get pods -n kube-system | grep coredns

# 서비스 IP 확인
kubectl get svc -n elk-stack elasticsearch
```

---

## 3. 노드 간 네트워킹 문제

### 증상
- 같은 노드의 파드끼리는 통신 가능
- 다른 노드의 파드끼리는 통신 불가

### 원인 분석
```bash
# 파드 노드 배치 확인
kubectl get pods -n elk-stack -o wide
NAME                   NODE       IP
elasticsearch-xxx      worker-1   10.244.1.37
kibana-xxx            worker-2   10.244.2.127  # 연결 실패
kibana-yyy            worker-1   10.244.1.41   # 연결 성공
```

### 해결 방법

#### nodeSelector 적용
```yaml
spec:
  template:
    spec:
      nodeSelector:
        kubernetes.io/hostname: "worker-1"
```

#### 실행 명령어
```bash
kubectl patch deployment -n elk-stack kibana --patch='
{
  "spec": {
    "template": {
      "spec": {
        "nodeSelector": {
          "kubernetes.io/hostname": "worker-1"
        }
      }
    }
  }
}'
```

### 네트워크 진단 명령어
```bash
# 노드 간 네트워크 연결 테스트
kubectl exec -n elk-stack pod-on-worker1 -- ping pod-ip-on-worker2

# CNI 플러그인 상태 확인
kubectl get pods -n kube-system | grep flannel

# 네트워크 정책 확인
kubectl get networkpolicy -A
```

---

## 4. SSL/TLS 인증서 문제

### 증상
```
curl: (35) SSL connect error
SSL certificate problem: unable to get local issuer certificate
```

### 해결 과정

#### Step 1: 인증서 존재 확인
```bash
kubectl get secret -n elk-stack elk-ssl-certs
kubectl exec -n elk-stack pod -- ls -la /usr/share/app/certs/
```

#### Step 2: 인증서 마운트 설정
```yaml
volumeMounts:
- name: ssl-certs
  mountPath: /usr/share/app/certs
  readOnly: true

volumes:
- name: ssl-certs
  secret:
    secretName: elk-ssl-certs
    defaultMode: 420
```

#### Step 3: SSL 설정 검증
```bash
# 인증서 유효성 확인
openssl x509 -in cert.pem -text -noout

# SSL 연결 테스트
openssl s_client -connect hostname:port -verify_return_error
```

### 인증서 생성 (필요시)
```bash
# CA 인증서 생성
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 365 -key ca-key.pem -out ca.pem

# 컴포넌트 인증서 생성
openssl genrsa -out component-key.pem 4096
openssl req -new -key component-key.pem -out component.csr
openssl x509 -req -in component.csr -CA ca.pem -CAkey ca-key.pem -out component.pem
```

---

## 5. Readiness Probe 실패

### 증상
```
Warning  Unhealthy  kibana-pod  Readiness probe failed: HTTP probe failed with statuscode: 401
```

### 원인
- `/api/status` 엔드포인트에 인증 필요
- SSL 설정으로 인한 프로브 실패

### 해결 방법

#### 방법 1: Probe 제거 (보안 환경)
```bash
kubectl patch deployment -n elk-stack kibana --type='json' -p='[
  {"op": "remove", "path": "/spec/template/spec/containers/0/readinessProbe"},
  {"op": "remove", "path": "/spec/template/spec/containers/0/livenessProbe"}
]'
```

#### 방법 2: 인증이 필요없는 엔드포인트 사용
```yaml
readinessProbe:
  httpGet:
    path: /status  # /api/status 대신 사용
    port: 5601
```

#### 방법 3: TCP 프로브 사용
```yaml
readinessProbe:
  tcpSocket:
    port: 5601
  initialDelaySeconds: 30
```

---

## 6. 포트 포워딩 문제

### 증상
```
Unable to listen on port 9200: address already in use
```

### 해결 방법

#### Step 1: 기존 프로세스 확인
```bash
lsof -i :9200
netstat -tlnp | grep :9200
```

#### Step 2: 포트 포워딩 정리
```bash
# 기존 포트 포워딩 종료
pkill -f "port-forward"

# 새로운 포트 포워딩 시작
kubectl port-forward -n elk-stack svc/elasticsearch 9200:9200 &
```

#### Step 3: 백그라운드 실행 관리
```bash
# 백그라운드 작업 확인
jobs

# 특정 작업 종료
kill %1
```

---

## 7. 보안 설정 문제

### TLS 설정 오류

#### Filebeat → Logstash TLS 연결 실패
```yaml
# Filebeat 설정
output.logstash:
  hosts: ["logstash.elk-stack.svc.cluster.local:5044"]
  ssl.enabled: true
  ssl.verification_mode: none
  ssl.certificate_authorities: ["/usr/share/filebeat/certs/ca.pem"]
  ssl.certificate: "/usr/share/filebeat/certs/filebeat.pem"
  ssl.key: "/usr/share/filebeat/certs/filebeat-key.pem"
```

```yaml
# Logstash 설정
input {
  beats {
    port => 5044
    ssl => true
    ssl_certificate => "/usr/share/logstash/certs/logstash.pem"
    ssl_key => "/usr/share/logstash/certs/logstash-key.pem"
    ssl_verify_mode => "none"
  }
}
```

### 인증 설정 오류

#### Elasticsearch 사용자 인증
```yaml
# 올바른 인증 설정
env:
- name: ELASTICSEARCH_USERNAME
  value: "elastic"
- name: ELASTICSEARCH_PASSWORD
  value: "elastic123"
```

---

## 진단 도구 모음

### 네트워크 연결 테스트
```bash
# 기본 연결 테스트
kubectl exec -n elk-stack pod -- curl -k -s https://target:port/

# TLS 연결 테스트
kubectl exec -n elk-stack pod -- openssl s_client -connect target:port

# 인증서 검증
kubectl exec -n elk-stack pod -- curl -k -s -I https://target:port/
```

### 로그 분석
```bash
# 실시간 로그 모니터링
kubectl logs -n elk-stack pod -f

# 특정 시간 범위 로그
kubectl logs -n elk-stack pod --since=1h

# 이전 컨테이너 로그
kubectl logs -n elk-stack pod --previous
```

### 리소스 상태 확인
```bash
# 파드 상세 정보
kubectl describe pod -n elk-stack pod-name

# 서비스 엔드포인트 확인
kubectl get endpoints -n elk-stack service-name

# 이벤트 확인
kubectl get events -n elk-stack --sort-by='.lastTimestamp'
```

---

## 예방 조치

### 1. 배포 전 체크리스트
- [ ] DNS 해석 가능성 확인
- [ ] SSL 인증서 유효성 검증
- [ ] 네트워크 정책 검토
- [ ] 리소스 할당량 확인

### 2. 모니터링 설정
```bash
# 자동 헬스 체크 스크립트
#!/bin/bash
kubectl get pods -n elk-stack --no-headers | grep -v Running | grep -v Completed
```

### 3. 백업 계획
```bash
# 설정 백업
kubectl get all -n elk-stack -o yaml > elk-backup.yaml
kubectl get secrets -n elk-stack -o yaml > elk-secrets-backup.yaml
```

---

## 8. SSL 키 사용법 호환성 문제

### 증상
```
ERR_SSL_KEY_USAGE_INCOMPATIBLE
이 페이지에 연결할 수 없습니다.
웹 페이지에 문제가 있거나 새 웹 주소로 영구히 이동되었을 수 있습니다.
```

### 원인 분석
- SSL 인증서의 키 사용법(Key Usage)이 HTTPS 서버용으로 적절하지 않음
- Digital Signature가 누락된 인증서
- 브라우저가 인증서를 신뢰하지 않음

### 해결 과정

#### Step 1: 현재 인증서 키 사용법 확인
```bash
kubectl exec -n elk-stack kibana-pod -- openssl x509 -in /usr/share/kibana/config/certs/kibana.pem -text -noout | grep -A5 "X509v3 Key Usage"
```

**문제가 있는 경우:**
```
X509v3 Key Usage: 
    Key Encipherment, Data Encipherment
```

**올바른 경우:**
```
X509v3 Key Usage: 
    Digital Signature, Key Encipherment, Data Encipherment
```

#### Step 2: 올바른 인증서 설정 파일 생성
```bash
mkdir -p /root/ssl-fix && cd /root/ssl-fix

cat > kibana-fix.conf << 'EOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = kibana

[v3_req]
keyUsage = keyEncipherment, dataEncipherment, digitalSignature
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = kibana
DNS.2 = kibana.elk-stack.svc.cluster.local
DNS.3 = localhost
IP.1 = 127.0.0.1
IP.2 = 211.183.3.110
EOF
```

#### Step 3: 기존 CA 인증서 추출
```bash
kubectl get secret -n elk-stack elk-ssl-certs -o jsonpath='{.data.ca\.pem}' | base64 -d > ca.pem
kubectl get secret -n elk-stack elk-ssl-certs -o jsonpath='{.data.ca-key\.pem}' | base64 -d > ca-key.pem
```

#### Step 4: 새로운 키바나 인증서 생성
```bash
# 개인키 생성
openssl genrsa -out kibana-key.pem 4096

# CSR 생성
openssl req -new -key kibana-key.pem -out kibana.csr -config kibana-fix.conf

# 올바른 키 사용법을 가진 인증서 생성
openssl x509 -req -in kibana.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial -out kibana.pem -days 365 -extensions v3_req -extfile kibana-fix.conf
```

#### Step 5: 인증서 검증
```bash
openssl x509 -in kibana.pem -text -noout | grep -A5 "X509v3 Key Usage"
```

**예상 출력:**
```
X509v3 Key Usage: 
    Digital Signature, Key Encipherment, Data Encipherment
X509v3 Extended Key Usage: 
    TLS Web Server Authentication
X509v3 Subject Alternative Name: 
    DNS:kibana, DNS:kibana.elk-stack.svc.cluster.local, DNS:localhost, IP Address:127.0.0.1, IP Address:211.183.3.110
```

#### Step 6: 시크릿 업데이트 및 재시작
```bash
# 시크릿 업데이트
kubectl patch secret -n elk-stack elk-ssl-certs --patch="$(cat <<EOF
data:
  kibana.pem: $(base64 -w 0 kibana.pem)
  kibana-key.pem: $(base64 -w 0 kibana-key.pem)
EOF
)"

# 키바나 재시작
kubectl rollout restart deployment -n elk-stack kibana
kubectl rollout status deployment -n elk-stack kibana --timeout=120s
```

#### Step 7: 연결 테스트
```bash
# 내부 연결 테스트
curl -k -I https://211.183.3.110:30050

# 인증서 확인
openssl s_client -connect 211.183.3.110:30050 -servername kibana 2>/dev/null | openssl x509 -text -noout | grep -A3 "X509v3 Key Usage"
```

---

## 9. NodePort 외부 접속 문제

### 증상
```
Connection timed out
ERR_CONNECTION_TIMED_OUT
```

### 원인
- NodePort 서비스의 externalTrafficPolicy가 Cluster로 설정되어 트래픽 라우팅 문제 발생
- 키바나 파드가 특정 노드에만 배치되어 있어 다른 노드에서 접속 불가

### 해결 방법

#### Step 1: 현재 서비스 정책 확인
```bash
kubectl get svc -n elk-stack kibana -o yaml | grep externalTrafficPolicy
```

#### Step 2: Local 정책으로 변경
```bash
kubectl patch svc -n elk-stack kibana -p '{"spec":{"externalTrafficPolicy":"Local"}}'
```

#### Step 3: 파드 위치 확인
```bash
kubectl get pods -n elk-stack -o wide | grep kibana
```

#### Step 4: 올바른 노드 IP로 접속
```bash
# 키바나 파드가 위치한 노드의 IP로 접속
curl -k -I https://KIBANA_NODE_IP:30050
```

### 검증 명령어
```bash
# 서비스 설정 확인
kubectl describe svc -n elk-stack kibana

# 엔드포인트 확인
kubectl get endpoints -n elk-stack kibana

# 연결 테스트
curl -k -I --connect-timeout 10 https://211.183.3.110:30050
```

---

## 10. ELK Auto Resolver HTTPS 호환성 문제

### 증상
```
AttributeError: 'NoneType' object has no attribute 'cursor'
DeprecationWarning: The 'http_auth' parameter is deprecated
DeprecationWarning: The 'timeout' parameter is deprecated
ConnectionRefusedError: [Errno 111] Connection refused
```

### 원인 분석
- Elasticsearch 8.x API 변경으로 인한 deprecated 경고
- HTTPS 환경에서 포트 포워딩 없이 직접 연결 시도
- 데이터베이스 연결 순서 문제

### 해결 과정

#### Step 1: Elasticsearch API 업데이트
```python
# 기존 (deprecated)
es_params = {
    'hosts': ['https://localhost:9200'],
    'http_auth': ('elastic', 'elastic123'),
    'timeout': 30
}

# 수정된 버전
es_params = {
    'hosts': ['https://localhost:9200'],
    'basic_auth': ('elastic', 'elastic123'),
    'request_timeout': 30
}
```

#### Step 2: HTTPS 설정 추가
```yaml
# config.yaml 업데이트
elasticsearch:
  host: "localhost"
  port: 9200
  index_pattern: "logstash-*"
  # HTTPS/TLS 설정 추가
  use_ssl: true
  verify_certs: false
  ssl_show_warn: false
  username: "elastic"
  password: "elastic123"
  # Kubernetes 서비스 연결
  k8s_service_host: "elasticsearch.elk-stack.svc.cluster.local"
  k8s_service_port: 9200
```

#### Step 3: 포트 포워딩 자동 관리
```python
# start_https_resolver.py 생성
def setup_port_forwarding(self):
    """Elasticsearch 포트 포워딩 설정"""
    cmd = [
        'kubectl', 'port-forward', 
        '-n', 'elk-stack', 
        'svc/elasticsearch', 
        '9200:9200'
    ]
    
    self.port_forward_process = subprocess.Popen(cmd)
    time.sleep(5)  # 연결 대기
    
    return self._test_connection()
```

#### Step 4: 연결 테스트 스크립트
```bash
# HTTPS 연결 테스트
python3 https_test.py

# 예상 출력
✅ HTTPS 연결 성공!
클러스터 상태: green
노드 수: 1
```

### 검증 명령어
```bash
# 1. HTTPS 연결 테스트
cd /root/elk-auto-resolver
python3 https_test.py

# 2. 자동 실행 테스트
python3 start_https_resolver.py

# 3. 개별 모듈 테스트
python3 error_monitor.py
```

---

## 11. 데이터베이스 외래키 제약 오류

### 증상
```
psycopg2.errors.ForeignKeyViolation: insert or update on table "solutions" 
violates foreign key constraint "solutions_error_hash_fkey"
DETAIL: Key (error_hash)=(abc123...) is not present in table "error_logs".
```

### 원인 분석
- AI 분석 결과를 solutions 테이블에 저장할 때 참조하는 error_hash가 error_logs 테이블에 없음
- 에러 로그를 데이터베이스에 저장하기 전에 AI 분석을 먼저 실행
- 외래키 제약 조건으로 인한 삽입 실패

### 해결 과정

#### Step 1: 실행 순서 변경
```python
# 기존 (잘못된 순서)
def process_errors(errors):
    for error in errors:
        # AI 분석 먼저 실행 (오류 발생)
        analysis_result = analyzer.analyze_error(error)
        # 에러 로그 나중에 저장
        error_id = db.insert_error_log(error)

# 수정된 순서
def process_errors(errors):
    for error in errors:
        # 1. 에러 로그 먼저 저장
        error_id = db.insert_error_log(error)
        if error_id:
            error['error_id'] = error_id
            # 2. AI 분석 나중에 실행
            analysis_result = analyzer.analyze_error(error)
```

#### Step 2: 에러 핸들링 강화
```python
def insert_error_log_safe(self, error_data):
    """안전한 에러 로그 삽입"""
    try:
        # 중복 체크
        existing_id = self.find_existing_error(error_data)
        if existing_id:
            return existing_id
            
        # 새로운 에러 로그 삽입
        return self.insert_error_log(error_data)
    except Exception as e:
        self.logger.error(f"에러 로그 삽입 실패: {e}")
        return None
```

#### Step 3: 통합 테스트
```python
# 완전한 워크플로우 테스트
def test_complete_workflow():
    # 1. 에러 검색
    errors = monitor.search_errors()
    
    # 2. 데이터베이스 저장
    for error in errors:
        error_id = db.insert_error_log(error)
        error['error_id'] = error_id
        
        # 3. AI 분석 (저장된 에러로)
        analysis = analyzer.analyze_error(error)
        
        # 4. 자동 해결
        if analysis and analysis.get('has_solution'):
            resolver.resolve_error(analysis)
```

### 검증 명령어
```bash
# 데이터베이스 상태 확인
python3 -c "
from database import DatabaseManager
db = DatabaseManager()
db.connect()
cursor = db.conn.cursor()
cursor.execute('SELECT COUNT(*) FROM error_logs')
print(f'에러 로그: {cursor.fetchone()[0]}개')
cursor.execute('SELECT COUNT(*) FROM solutions') 
print(f'해결책: {cursor.fetchone()[0]}개')
"

# 통합 테스트 실행
python3 -c "
from error_monitor import ErrorMonitor
monitor = ErrorMonitor()
if monitor.connect_elasticsearch():
    errors = monitor.search_errors()
    processed = monitor.process_errors(errors)
    print(f'처리된 에러: {len(processed)}개')
"
```

---

## 12. hostNetwork DNS 해석 간헐적 실패

### 증상
```
DNS lookup failure "logstash.elk-stack.svc.cluster.local": 
lookup logstash.elk-stack.svc.cluster.local: Temporary failure in name resolution
```

### 원인 분석
- **hostNetwork: true**와 **dnsPolicy: ClusterFirstWithHostNet** 조합 문제
- 파드가 호스트 네트워크 네임스페이스를 사용하여 DNS 해석이 불안정
- 호스트 DNS와 클러스터 DNS 간의 충돌로 인한 간헐적 실패

### 해결 과정

#### Step 1: 현재 설정 확인
```bash
kubectl get pod -n elk-stack filebeat-pod -o yaml | grep -A5 -B5 "hostNetwork\|dnsPolicy"
```

**문제 설정:**
```yaml
hostNetwork: true
dnsPolicy: ClusterFirstWithHostNet
```

#### Step 2: DNS 해석 테스트
```bash
# DNS 해석 자체는 정상 작동
kubectl exec -n elk-stack filebeat-pod -- getent hosts logstash.elk-stack.svc.cluster.local
# 결과: 10.100.3.49 logstash.elk-stack.svc.cluster.local
```

#### Step 3: 임시 해결책 - IP 직접 사용
```yaml
# filebeat-simple.yaml
output.logstash:
  hosts: ["10.100.3.49:5044"]  # 서비스 IP 직접 사용

# logstash-simple.yaml  
output {
  elasticsearch {
    hosts => ["https://10.106.80.20:9200"]  # 서비스 IP 직접 사용
  }
}
```

#### Step 4: 근본적 해결책 - DNS 정책 변경
```yaml
# 권장 설정 (hostNetwork 사용 시)
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: filebeat
spec:
  template:
    spec:
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
      # 또는 더 안정적인 설정
      dnsPolicy: ClusterFirst
      hostNetwork: false  # 가능한 경우
```

### 장기적 해결 방안

#### 방안 1: hostNetwork 제거 (권장)
```yaml
spec:
  template:
    spec:
      hostNetwork: false
      dnsPolicy: ClusterFirst
```

#### 방안 2: hostAliases 사용
```yaml
spec:
  template:
    spec:
      hostNetwork: true
      hostAliases:
      - ip: "10.100.3.49"
        hostnames: ["logstash.elk-stack.svc.cluster.local"]
      - ip: "10.106.80.20"
        hostnames: ["elasticsearch.elk-stack.svc.cluster.local"]
```

### 검증 명령어
```bash
# 1. DNS 해석 테스트
kubectl exec -n elk-stack filebeat-pod -- getent hosts logstash.elk-stack.svc.cluster.local

# 2. 연결 테스트
kubectl exec -n elk-stack filebeat-pod -- nc -zv logstash.elk-stack.svc.cluster.local 5044

# 3. 로그 확인
kubectl logs -n elk-stack filebeat-pod --tail=10 | grep -i "dns\|lookup\|resolution"
```

---

## 13. 실제 로그 데이터 수집 및 테스트 데이터 정리

### 증상
- Kibana에서 39,660개 로그 중 테스트 데이터만 4개, 나머지는 실제 시스템 로그
- 기존 테스트 인덱스에 가짜 데이터가 혼재하여 실제 로그 식별 어려움

### 해결 과정

#### Step 1: 기존 테스트 인덱스 삭제
```bash
curl -k -u elastic:elastic123 -X DELETE "https://localhost:9200/logstash-2025.07.11"
```

#### Step 2: 실제 로그 수집 상태 확인
```bash
# 로그 수집 파이프라인 검증
kubectl logs -n elk-stack logstash-pod --tail=20 | grep -E "(received|processing|elasticsearch)"
```

#### Step 3: 새로운 인덱스 생성 확인
```bash
# 실제 로그 수집 확인
curl -k -u elastic:elastic123 "https://localhost:9200/_cat/indices?v" | grep logstash
# 결과: logstash-2025.07.11 - 39,660 docs - 14.9mb
```

#### Step 4: 로그 소스 분석
```bash
# 주요 로그 소스 확인
tail -5 /var/log/syslog
# 결과: multipathd 프로세스의 실제 시스템 로그 확인

# 로그 개수 확인
grep -c "multipathd" /var/log/syslog
# 결과: 35,920개 (실제 시스템 로그)
```

### 최종 결과
- **전체 로그**: 39,660개
- **실제 시스템 로그**: 39,656개 (multipathd 등)
- **테스트 로그**: 4개만
- **로그 소스**: `/var/log/syslog`의 실제 시스템 로그

---

## 결론

이 트러블슈팅 가이드는 실제 ELK 스택 구축 과정에서 발생한 문제들과 해결책을 정리한 것입니다. 

### 주요 교훈
1. **DNS 문제**: hostAliases 또는 FQDN 사용으로 해결
2. **네트워킹 문제**: nodeSelector로 파드 배치 제어
3. **보안 설정**: 단계별 SSL/TLS 적용 필요
4. **프로브 설정**: 보안 환경에서는 프로브 조정 필요
5. **SSL 키 사용법**: HTTPS 서버용 인증서는 반드시 Digital Signature + Key Encipherment 필요
6. **NodePort 정책**: 특정 노드 배치 시 externalTrafficPolicy: Local 설정 필수
7. **Elasticsearch API**: 8.x 버전에서 basic_auth, request_timeout 사용 필요
8. **데이터베이스 순서**: 에러 로그 저장 후 AI 분석 실행하여 외래키 제약 준수
9. **HTTPS 연결**: 포트 포워딩 자동 관리로 연결 안정성 확보
10. **통합 테스트**: 전체 워크플로우 검증으로 안정성 확보
11. **hostNetwork DNS**: hostNetwork 사용 시 DNS 해석 불안정, IP 직접 사용 또는 hostAliases 권장
12. **실제 로그 수집**: 테스트 데이터 정리 후 실제 시스템 로그 수집 확인 필요

### 권장사항
- 단계별 배포 및 테스트
- 로그 모니터링 상시 운영
- 네트워크 구성 사전 검증
- 인증서 생명주기 관리