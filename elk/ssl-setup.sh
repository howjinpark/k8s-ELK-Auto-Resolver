#!/bin/bash

# SSL 인증서 생성 스크립트
echo "=== ELK Stack SSL 인증서 생성 ==="

# 인증서 디렉토리 생성
mkdir -p /root/elk/ssl-certs
cd /root/elk/ssl-certs

# 1. CA 인증서 생성
echo "1. CA 인증서 생성..."
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 365 -key ca-key.pem -out ca.pem -subj "/CN=ELK-CA"

# 2. Elasticsearch 인증서 생성
echo "2. Elasticsearch 인증서 생성..."
openssl genrsa -out elasticsearch-key.pem 4096
openssl req -new -key elasticsearch-key.pem -out elasticsearch.csr -subj "/CN=elasticsearch"

# SAN (Subject Alternative Names) 설정
cat > elasticsearch.conf << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = elasticsearch

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = elasticsearch
DNS.2 = elasticsearch.elk-stack.svc.cluster.local
DNS.3 = localhost
IP.1 = 127.0.0.1
IP.2 = 10.96.206.169
EOF

openssl x509 -req -in elasticsearch.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial -out elasticsearch.pem -days 365 -extensions v3_req -extfile elasticsearch.conf

# 3. Kibana 인증서 생성
echo "3. Kibana 인증서 생성..."
openssl genrsa -out kibana-key.pem 4096
openssl req -new -key kibana-key.pem -out kibana.csr -subj "/CN=kibana"

cat > kibana.conf << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = kibana

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = kibana
DNS.2 = kibana.elk-stack.svc.cluster.local
DNS.3 = localhost
IP.1 = 127.0.0.1
IP.2 = 211.183.3.110
EOF

openssl x509 -req -in kibana.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial -out kibana.pem -days 365 -extensions v3_req -extfile kibana.conf

# 4. Logstash 인증서 생성
echo "4. Logstash 인증서 생성..."
openssl genrsa -out logstash-key.pem 4096
openssl req -new -key logstash-key.pem -out logstash.csr -subj "/CN=logstash"
openssl x509 -req -in logstash.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial -out logstash.pem -days 365

# 5. Filebeat 인증서 생성
echo "5. Filebeat 인증서 생성..."
openssl genrsa -out filebeat-key.pem 4096
openssl req -new -key filebeat-key.pem -out filebeat.csr -subj "/CN=filebeat"
openssl x509 -req -in filebeat.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial -out filebeat.pem -days 365

# 6. 권한 설정
chmod 600 *.pem
chmod 644 *.conf

echo "=== SSL 인증서 생성 완료 ==="
echo "생성된 파일들:"
ls -la /root/elk/ssl-certs/

echo ""
echo "다음 단계: Kubernetes Secret 생성"
echo "kubectl create secret generic elk-ssl-certs --from-file=/root/elk/ssl-certs/ -n elk-stack"