#!/usr/bin/env python3
"""
HTTPS ELK 연결 테스트 스크립트
"""

import yaml
import sys
import urllib3
from elasticsearch import Elasticsearch

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_elasticsearch_https():
    """HTTPS Elasticsearch 연결 테스트"""
    try:
        # 설정 파일 로드
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        es_config = config['elasticsearch']
        
        # HTTPS 연결 설정
        es_params = {
            'hosts': [f"https://{es_config['host']}:{es_config['port']}"],
            'verify_certs': False,
            'ssl_show_warn': False,
            'ssl_assert_hostname': False,
            'request_timeout': 30,
            'basic_auth': (es_config['username'], es_config['password'])
        }
        
        print(f"Elasticsearch HTTPS 연결 테스트...")
        print(f"호스트: https://{es_config['host']}:{es_config['port']}")
        print(f"사용자: {es_config['username']}")
        
        es = Elasticsearch(**es_params)
        
        # 연결 테스트
        if es.ping():
            print("✅ HTTPS 연결 성공!")
            
            # 클러스터 상태 확인
            health = es.cluster.health()
            print(f"클러스터 상태: {health['status']}")
            print(f"노드 수: {health['number_of_nodes']}")
            
            # 인덱스 목록 확인
            indices = es.cat.indices(format='json')
            logstash_indices = [idx for idx in indices if idx['index'].startswith('logstash-')]
            print(f"Logstash 인덱스 수: {len(logstash_indices)}")
            
            if logstash_indices:
                latest_index = sorted(logstash_indices, key=lambda x: x['index'])[-1]
                print(f"최신 인덱스: {latest_index['index']} (문서 수: {latest_index['docs.count']})")
            
            return True
        else:
            print("❌ HTTPS 연결 실패")
            return False
            
    except Exception as e:
        print(f"❌ 연결 오류: {e}")
        return False

def test_kubernetes_service():
    """Kubernetes 서비스를 통한 연결 테스트"""
    try:
        # 설정 파일 로드
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        es_config = config['elasticsearch']
        k8s_host = es_config.get('k8s_service_host')
        k8s_port = es_config.get('k8s_service_port')
        
        if not k8s_host:
            print("Kubernetes 서비스 호스트가 설정되지 않음")
            return False
        
        print(f"\nKubernetes 서비스 연결 테스트...")
        print(f"호스트: https://{k8s_host}:{k8s_port}")
        
        es_params = {
            'hosts': [f"https://{k8s_host}:{k8s_port}"],
            'verify_certs': False,
            'ssl_show_warn': False,
            'ssl_assert_hostname': False,
            'request_timeout': 30,
            'basic_auth': (es_config['username'], es_config['password'])
        }
        
        es = Elasticsearch(**es_params)
        
        if es.ping():
            print("✅ Kubernetes 서비스 HTTPS 연결 성공!")
            return True
        else:
            print("❌ Kubernetes 서비스 HTTPS 연결 실패")
            return False
            
    except Exception as e:
        print(f"❌ Kubernetes 서비스 연결 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("=== ELK HTTPS 연결 테스트 ===\n")
    
    # localhost HTTPS 테스트
    localhost_success = test_elasticsearch_https()
    
    # Kubernetes 서비스 테스트
    k8s_success = test_kubernetes_service()
    
    print(f"\n=== 테스트 결과 ===")
    print(f"Localhost HTTPS: {'✅' if localhost_success else '❌'}")
    print(f"Kubernetes Service: {'✅' if k8s_success else '❌'}")
    
    if localhost_success or k8s_success:
        print("\n✅ ELK Auto Resolver가 HTTPS 환경에서 작동할 수 있습니다!")
        return 0
    else:
        print("\n❌ HTTPS 연결 문제가 있습니다. 포트 포워딩을 확인하세요:")
        print("kubectl port-forward -n elk-stack svc/elasticsearch 9200:9200")
        return 1

if __name__ == "__main__":
    sys.exit(main())