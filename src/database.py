#!/usr/bin/env python3
"""
PostgreSQL 데이터베이스 연결 및 관리 모듈
"""

import psycopg2
import psycopg2.extras
import yaml
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

class DatabaseManager:
    """PostgreSQL 데이터베이스 관리 클래스"""
    
    def __init__(self, config_path: str = None):
        """
        데이터베이스 연결 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.conn = None
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드 (환경 변수 포함)"""
        try:
            from .load_env import load_config_with_env
            return load_config_with_env(config_path)
        except Exception as e:
            raise Exception(f"설정 파일을 읽을 수 없습니다: {e}")
    
    def connect(self) -> bool:
        """데이터베이스 연결"""
        try:
            db_config = self.config['database']
            self.conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['name'],
                user=db_config['user'],
                password=db_config['password']
            )
            self.conn.autocommit = False
            self.logger.info("데이터베이스 연결 성공")
            return True
        except Exception as e:
            self.logger.error(f"데이터베이스 연결 실패: {e}")
            return False
    
    def disconnect(self):
        """데이터베이스 연결 해제"""
        if self.conn:
            self.conn.close()
            self.logger.info("데이터베이스 연결 해제")
    
    def create_hash_signature(self, error_type: str, error_message: str) -> str:
        """에러 해시 시그니처 생성 (중복 방지용)"""
        combined = f"{error_type}:{error_message}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def insert_error_log(self, error_data: Dict) -> Optional[int]:
        """
        에러 로그 삽입
        
        Args:
            error_data: 에러 정보 딕셔너리
            
        Returns:
            에러 로그 ID 또는 None
        """
        try:
            cursor = self.conn.cursor()
            
            # 해시 시그니처 생성
            hash_signature = self.create_hash_signature(
                error_data['error_type'], 
                error_data['error_message']
            )
            
            # 중복 체크
            cursor.execute(
                "SELECT id FROM error_logs WHERE hash_signature = %s",
                (hash_signature,)
            )
            
            if cursor.fetchone():
                self.logger.info(f"중복 에러 로그 무시: {hash_signature}")
                return None
            
            # 에러 로그 삽입
            insert_query = """
                INSERT INTO error_logs (
                    error_type, error_message, source_system, severity,
                    stack_trace, elasticsearch_id, raw_log_data, hash_signature
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            cursor.execute(insert_query, (
                error_data['error_type'],
                error_data['error_message'],
                error_data.get('source_system', 'unknown'),
                error_data.get('severity', 'ERROR'),
                error_data.get('stack_trace'),
                error_data.get('elasticsearch_id'),
                json.dumps(error_data.get('raw_log_data', {})),
                hash_signature
            ))
            
            error_id = cursor.fetchone()[0]
            self.conn.commit()
            self.logger.info(f"에러 로그 삽입 완료: ID={error_id}")
            return error_id
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"에러 로그 삽입 실패: {e}")
            return None
    
    def get_solution_by_error_hash(self, error_hash: str) -> Optional[Dict]:
        """
        에러 해시로 해결책 조회
        
        Args:
            error_hash: 에러 해시 시그니처
            
        Returns:
            해결책 정보 또는 None
        """
        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT * FROM solutions 
                WHERE error_hash = %s 
                ORDER BY success_rate DESC, execution_count DESC
                LIMIT 1
            """
            
            cursor.execute(query, (error_hash,))
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            self.logger.error(f"해결책 조회 실패: {e}")
            return None
    
    def insert_solution(self, solution_data: Dict) -> Optional[int]:
        """
        해결책 삽입
        
        Args:
            solution_data: 해결책 정보
            
        Returns:
            해결책 ID 또는 None
        """
        try:
            cursor = self.conn.cursor()
            
            insert_query = """
                INSERT INTO solutions (
                    error_hash, solution_type, solution_description,
                    solution_commands, ai_analysis
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """
            
            cursor.execute(insert_query, (
                solution_data['error_hash'],
                solution_data['solution_type'],
                solution_data['solution_description'],
                json.dumps(solution_data['solution_commands']),
                solution_data.get('ai_analysis', '')
            ))
            
            solution_id = cursor.fetchone()[0]
            self.conn.commit()
            self.logger.info(f"해결책 삽입 완료: ID={solution_id}")
            return solution_id
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"해결책 삽입 실패: {e}")
            return None
    
    def record_execution(self, execution_data: Dict) -> bool:
        """
        실행 이력 기록
        
        Args:
            execution_data: 실행 정보
            
        Returns:
            성공 여부
        """
        try:
            cursor = self.conn.cursor()
            
            insert_query = """
                INSERT INTO execution_history (
                    error_log_id, solution_id, execution_status,
                    execution_output, execution_time
                ) VALUES (%s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                execution_data['error_log_id'],
                execution_data['solution_id'],
                execution_data['execution_status'],
                execution_data.get('execution_output', ''),
                execution_data.get('execution_time')
            ))
            
            self.conn.commit()
            self.logger.info("실행 이력 기록 완료")
            return True
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"실행 이력 기록 실패: {e}")
            return False
    
    def get_error_patterns(self) -> List[Dict]:
        """에러 패턴 조회"""
        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT * FROM error_patterns 
                ORDER BY priority ASC
            """
            
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            self.logger.error(f"에러 패턴 조회 실패: {e}")
            return []
    
    def update_system_status(self, component: str, status: str, error_count: int = 0) -> bool:
        """
        시스템 상태 업데이트
        
        Args:
            component: 컴포넌트 명
            status: 상태 ('healthy', 'warning', 'error')
            error_count: 에러 카운트
            
        Returns:
            성공 여부
        """
        try:
            cursor = self.conn.cursor()
            
            update_query = """
                UPDATE system_status 
                SET status = %s, error_count = %s, last_check = CURRENT_TIMESTAMP
                WHERE component_name = %s
            """
            
            cursor.execute(update_query, (status, error_count, component))
            
            if cursor.rowcount == 0:
                # 컴포넌트가 없으면 삽입
                insert_query = """
                    INSERT INTO system_status (component_name, status, error_count)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(insert_query, (component, status, error_count))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"시스템 상태 업데이트 실패: {e}")
            return False
    
    def get_system_status(self) -> List[Dict]:
        """전체 시스템 상태 조회"""
        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = "SELECT * FROM system_status ORDER BY component_name"
            cursor.execute(query)
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            self.logger.error(f"시스템 상태 조회 실패: {e}")
            return []
    
    def cleanup_old_error_logs(self, retention_days: int = 7) -> bool:
        """
        오래된 에러 로그 및 관련 데이터 정리
        
        Args:
            retention_days: 보관 기간 (일)
            
        Returns:
            성공 여부
        """
        try:
            cursor = self.conn.cursor()
            
            # 오래된 실행 이력 삭제 (가장 오래된 데이터부터)
            delete_execution_query = """
                DELETE FROM execution_history 
                WHERE created_at < NOW() - INTERVAL '%s days'
            """
            cursor.execute(delete_execution_query, (retention_days,))
            execution_deleted = cursor.rowcount
            
            # 오래된 해결책 삭제 (참조되지 않는 것만)
            delete_solutions_query = """
                DELETE FROM solutions 
                WHERE created_at < NOW() - INTERVAL '%s days'
                AND id NOT IN (
                    SELECT DISTINCT solution_id FROM execution_history 
                    WHERE solution_id IS NOT NULL
                )
            """
            cursor.execute(delete_solutions_query, (retention_days,))
            solutions_deleted = cursor.rowcount
            
            # 오래된 에러 로그 삭제 (가장 오래된 데이터부터)
            delete_errors_query = """
                DELETE FROM error_logs 
                WHERE created_at < NOW() - INTERVAL '%s days'
            """
            cursor.execute(delete_errors_query, (retention_days,))
            errors_deleted = cursor.rowcount
            
            self.conn.commit()
            
            self.logger.info(f"데이터베이스 정리 완료: 에러로그 {errors_deleted}개, 해결책 {solutions_deleted}개, 실행이력 {execution_deleted}개 삭제")
            return True
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"데이터베이스 정리 실패: {e}")
            return False


# 사용 예제
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 데이터베이스 연결 테스트
    db = DatabaseManager()
    
    if db.connect():
        # 시스템 상태 확인
        status = db.get_system_status()
        print("시스템 상태:", status)
        
        # 에러 패턴 확인
        patterns = db.get_error_patterns()
        print("에러 패턴:", len(patterns), "개")
        
        db.disconnect()
    else:
        print("데이터베이스 연결 실패")