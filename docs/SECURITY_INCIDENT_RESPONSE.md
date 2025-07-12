# 🚨 보안 사고 대응 가이드

## 개요

GitGuardian에서 다음 시크릿들이 GitHub에 노출되었음을 감지했습니다:
- **Perplexity API Key** (노출일: 2025-07-11 17:02:52 UTC)
- **RSA Private Key** (노출일: 2025-07-12 04:14:47 UTC)

## 🔧 즉시 조치 사항

### 1. API 키 교체 (긴급)

**Perplexity API 키 교체:**
```bash
# 1. Perplexity 계정에 로그인
# 2. API Settings에서 기존 키 비활성화/삭제
# 3. 새로운 API 키 생성
# 4. config/.env 파일에 새 키 설정

# 새 API 키로 업데이트
nano config/.env
# PERPLEXITY_API_KEY=새로운_API_키_입력
```

### 2. SSL 인증서 재생성 (권장)

**노출된 SSL 인증서 교체:**
```bash
# 기존 SSL 인증서 삭제
rm -rf elk/ssl-certs/

# 새로운 SSL 인증서 생성
cd elk/
./ssl-setup.sh

# 인증서가 .gitignore에 의해 추적되지 않는지 확인
git status
```

### 3. 환경 변수 보안 강화

**모든 사용자가 해야 할 조치:**
```bash
# 1. 기존 .env 파일 백업 및 삭제
cp config/.env config/.env.backup
rm config/.env

# 2. 새로운 .env 파일 생성
nano config/.env

# 3. 필수 환경 변수 설정
cat > config/.env << 'EOF'
# Perplexity AI API
PERPLEXITY_API_KEY=새로운_API_키_입력

# Slack 웹훅
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url

# 데이터베이스
DATABASE_PASSWORD=강력한_비밀번호

# Elasticsearch (HTTPS 사용시)
ELASTICSEARCH_PASSWORD=강력한_비밀번호
EOF

# 4. 파일 권한 제한
chmod 600 config/.env
```

## 🛡️ 예방 조치

### 1. .gitignore 업데이트 완료
다음 항목들이 추가되었습니다:
```gitignore
# SSL 인증서 및 Private Key (보안상 중요)
*.pem
*.key
*.crt
*.csr
ssl-certs/
*.p12
*.pfx

# API 키 및 설정 파일 (보안상 중요)
config/.env
**/config/.env
api_keys.txt
secrets.yaml
```

### 2. 사용자 안전 수칙

**✅ 해야 할 것:**
- 항상 `.env` 파일에 민감한 정보 저장
- API 키는 정기적으로 로테이션
- SSL 인증서는 로컬 생성 후 배포시에만 사용
- Git commit 전 `git status`로 민감한 파일 확인

**❌ 하지 말 것:**
- API 키를 코드에 하드코딩
- SSL private key를 Git에 커밋
- .env 파일을 Git에 추가
- 공개 채널에 민감한 정보 공유

### 3. 모니터링 설정

**GitGuardian 알림 처리:**
1. 알림 받으면 즉시 해당 키 비활성화
2. 새로운 키로 교체
3. Git 히스토리에서 민감한 정보 제거 (필요시)

**주기적 보안 체크:**
```bash
# 민감한 파일이 Git에 추적되고 있는지 확인
git ls-files | grep -E "\.(pem|key|env)$" || echo "보안 파일 없음 - 안전"

# .gitignore 작동 확인
git status --ignored
```

## 🔄 복구 프로세스

### 1. API 키 교체 후 테스트
```bash
# 시스템 재시작하여 새 API 키 적용 확인
./scripts/run.sh

# 로그에서 API 연결 상태 확인
tail -f elk_auto_resolver.log | grep -i "perplexity\|api"
```

### 2. SSL 인증서 교체 후 확인
```bash
# HTTPS ELK Stack 재배포
kubectl delete -f elk/elasticsearch-https-final.yaml
kubectl delete -f elk/logstash-https-final.yaml
kubectl delete -f elk/kibana-https-final.yaml
kubectl delete -f elk/filebeat-https-final.yaml

# 새 인증서로 재배포
kubectl apply -f elk/elasticsearch-https-final.yaml
kubectl apply -f elk/logstash-https-final.yaml
kubectl apply -f elk/kibana-https-final.yaml
kubectl apply -f elk/filebeat-https-final.yaml
```

## 📞 추가 지원

보안 관련 추가 문의사항이 있으면:
1. GitHub Issues에 [SECURITY] 태그로 문의
2. 민감한 정보는 절대 공개하지 말고 DM으로 문의
3. 의심스러운 활동 발견시 즉시 API 키 비활성화

---

**마지막 업데이트**: 2025-07-12  
**보안 등급**: 높음 - 즉시 조치 필요