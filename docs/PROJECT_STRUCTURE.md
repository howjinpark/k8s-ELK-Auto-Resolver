# ELK Auto Resolver 프로젝트 구조

## 📁 디렉토리 구조

```
k8s-ELK-Auto-Resolver/
├── 📄 README.md                    # 프로젝트 메인 문서
├── 📄 requirements.txt             # Python 패키지 의존성
├── 📄 CHANGELOG.md                 # 버전 변경 이력
│
├── 📁 config/                      # 설정 파일
│   ├── 📄 config.yaml             # 메인 설정 파일
│   └── 📄 .env.example            # 환경 변수 템플릿
│
├── 📁 src/                         # 소스 코드
│   ├── 📄 __init__.py
│   ├── 📄 load_env.py             # 환경 변수 로더
│   ├── 📄 error_monitor.py        # 에러 모니터링
│   ├── 📄 ai_analyzer.py          # AI 분석기
│   ├── 📄 auto_resolver.py        # 자동 해결기
│   ├── 📄 slack_notifier.py       # Slack 알림
│   ├── 📄 database.py             # 데이터베이스 관리
│   ├── 📄 start_https_resolver.py # HTTPS 환경 시작점
│   └── 📄 log_cleanup_scheduler.py # 로그 정리 스케줄러
│
├── 📁 scripts/                     # 실행 스크립트
│   ├── 📄 install.sh              # 자동 설치 스크립트
│   ├── 📄 run.sh                  # 간편 실행 스크립트
│   ├── 📄 run-background.sh       # 백그라운드 실행 스크립트
│   ├── 📄 deploy.tar.gz.sh        # 배포 패키지 생성 스크립트
│   ├── 📄 start_resolver.py       # 메인 실행 스크립트
│   └── 📄 start_log_cleanup.py    # 로그 정리 실행 스크립트
│
├── 📁 docs/                        # 문서
│   ├── 📄 PREREQUISITES.md        # 설치 전 필수 확인사항
│   ├── 📄 GITHUB_INSTALL_GUIDE.md # GitHub 설치 가이드
│   ├── 📄 DEPLOYMENT_GUIDE.md     # 배포 가이드
│   ├── 📄 LOG_MANAGEMENT_GUIDE.md # 로그 관리 가이드
│   ├── 📄 PROJECT_STRUCTURE.md    # 프로젝트 구조 설명
│   ├── 📄 github_issues_template.md # GitHub 이슈 템플릿
│   └── 📄 ... (기타 문서들)
│
├── 📁 sql/                         # 데이터베이스 스키마
│   ├── 📄 create_schema.sql       # 테이블 생성 스크립트
│   ├── 📄 insert_initial_data.sql # 초기 데이터
│   └── 📄 ... (기타 SQL 파일들)
│
├── 📁 elk/                         # ELK Stack 배포 파일
│   ├── 📄 elasticsearch-simple.yaml
│   ├── 📄 elasticsearch-https-final.yaml
│   ├── 📄 logstash-simple.yaml
│   ├── 📄 logstash-https-final.yaml
│   ├── 📄 kibana-simple-new.yaml
│   ├── 📄 kibana-https-final.yaml
│   ├── 📄 filebeat-simple.yaml
│   └── 📄 filebeat-https-final.yaml
│
├── 📁 kubernetes/                  # Kubernetes 매니페스트
│   └── 📄 multipath-cleanup-daemonset.yaml
│
├── 📁 tests/                       # 테스트 파일
│   ├── 📄 test_shutdown.py        # 종료 테스트
│   ├── 📄 test-error-service.yaml # 에러 서비스 테스트
│   └── 📄 test-runtime-error-service.yaml
│
└── 📁 testelk/                     # ELK 테스트 환경
    └── 📄 ... (간단한 ELK 설치 파일들)
```

## 📂 디렉토리별 설명

### 🔧 **config/** - 설정 파일
- **config.yaml**: 메인 설정 파일 (DB, ELK, API 설정)
- **.env.example**: 환경 변수 템플릿 (사용자가 .env로 복사 후 수정)

### 💻 **src/** - 핵심 소스 코드
- **error_monitor.py**: Elasticsearch 로그 모니터링 및 에러 감지
- **ai_analyzer.py**: Perplexity AI를 이용한 에러 분석
- **auto_resolver.py**: Kubernetes 환경에서 자동 해결 실행
- **slack_notifier.py**: Slack 알림 전송
- **database.py**: PostgreSQL 데이터베이스 관리
- **log_cleanup_scheduler.py**: 자동 로그 정리 시스템

### 🚀 **scripts/** - 실행 스크립트
- **install.sh**: 시스템 전체 설치 (한 번만 실행)
- **run.sh**: ELK Auto Resolver 실행 (매번 실행)
- **run-background.sh**: 백그라운드 실행
- **deploy.tar.gz.sh**: 배포용 패키지 생성
- **start_resolver.py**: Python 메인 실행 스크립트

### 📚 **docs/** - 문서
- **PREREQUISITES.md**: 설치 전 준비사항
- **GITHUB_INSTALL_GUIDE.md**: 4단계 간단 설치 가이드
- **DEPLOYMENT_GUIDE.md**: 상세 수동 설치 방법
- **LOG_MANAGEMENT_GUIDE.md**: 로그 관리 및 정리

### 🗄️ **sql/** - 데이터베이스
- **create_schema.sql**: PostgreSQL 테이블 생성
- **insert_initial_data.sql**: 기본 에러 패턴 등 초기 데이터

### ☸️ **elk/** - ELK Stack 배포
- **simple 버전**: HTTP 기반 개발/테스트 환경
- **https-final 버전**: HTTPS 기반 프로덕션 환경

### 🧪 **tests/** - 테스트 도구
- **test-*-service.yaml**: 의도적 에러 생성용 테스트 서비스
- **test_shutdown.py**: 종료 처리 테스트

## 🎯 **파일 역할별 분류**

### 📋 **사용자가 직접 실행하는 파일**
```bash
scripts/install.sh        # 최초 설치
scripts/run.sh            # 일반 실행
scripts/run-background.sh # 백그라운드 실행
```

### ⚙️ **사용자가 설정하는 파일**
```bash
config/.env              # API 키 등 환경 변수 (사용자 생성)
config/config.yaml       # 시스템 설정 (필요시 수정)
```

### 📖 **사용자가 참고하는 문서**
```bash
README.md                 # 시작 가이드
docs/PREREQUISITES.md     # 설치 전 확인사항
docs/GITHUB_INSTALL_GUIDE.md # 설치 방법
```

### 🔧 **시스템이 사용하는 파일**
```bash
src/*.py                  # Python 소스 코드
sql/*.sql                 # 데이터베이스 스키마
elk/*.yaml               # ELK Stack 배포 파일
```

## 🚀 **정리된 설치 과정**

```bash
# 1. 프로젝트 다운로드
git clone https://github.com/howjinpark/k8s-ELK-Auto-Resolver.git
cd k8s-ELK-Auto-Resolver

# 2. 설치 (scripts 디렉토리에서)
chmod +x scripts/install.sh
./scripts/install.sh

# 3. 설정 (config 디렉토리에서)
nano config/.env

# 4. 실행 (scripts 디렉토리에서)
./scripts/run.sh
```

이제 모든 파일이 목적에 맞는 디렉토리에 정리되어 있어 프로젝트 구조가 훨씬 깔끔하고 이해하기 쉽습니다!