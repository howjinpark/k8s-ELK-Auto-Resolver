# ELK Auto Resolver 머신러닝 업그레이드 가이드

## 1. 업그레이드 로드맵

### 1.1 단계별 업그레이드 계획

```
현재 (규칙기반) → 1단계 (하이브리드) → 2단계 (ML 기반) → 3단계 (딥러닝)
    ↓              ↓                    ↓                 ↓
 단순 규칙        텍스트 유사도         분류 알고리즘      신경망 모델
 해시 매칭        벡터 임베딩          랜덤포레스트       BERT/GPT
 통계 기반        퍼지 매칭           SVM/나이브베이즈    트랜스포머
```

### 1.2 업그레이드 타임라인

| 단계 | 기간 | 목표 | 예상 성능 향상 |
|------|------|------|----------------|
| **1단계** | 2-4주 | 텍스트 유사도 매칭 | 20-30% 향상 |
| **2단계** | 2-3개월 | 분류 알고리즘 도입 | 50-70% 향상 |
| **3단계** | 6개월+ | 딥러닝 모델 구축 | 80-95% 향상 |

## 2. 1단계: 하이브리드 시스템 구축

### 2.1 텍스트 유사도 매칭 도입

#### 필요한 라이브러리 설치
```bash
pip install -r requirements_ml.txt
```

#### requirements_ml.txt
```
scikit-learn>=1.3.0
nltk>=3.8
spacy>=3.6.0
numpy>=1.24.0
pandas>=2.0.0
sentence-transformers>=2.2.0
faiss-cpu>=1.7.4
```

#### 구현 코드
```python
# enhanced_resolver.py
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import re
import logging

class EnhancedErrorResolver:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=2,
            max_df=0.8
        )
        self.lemmatizer = WordNetLemmatizer()
        self.similarity_threshold = 0.7
        self.error_vectors = None
        self.error_solutions = []
        self.error_texts = []
        
        # NLTK 데이터 다운로드
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')
            nltk.download('wordnet')
    
    def preprocess_text(self, text):
        """텍스트 전처리"""
        # 소문자 변환
        text = text.lower()
        
        # 특수문자 제거 (일부 유지)
        text = re.sub(r'[^a-zA-Z0-9\s\-_\.]', ' ', text)
        
        # 토큰화
        tokens = word_tokenize(text)
        
        # 불용어 제거 및 형태소 분석
        stop_words = set(stopwords.words('english'))
        tokens = [self.lemmatizer.lemmatize(token) for token in tokens 
                 if token not in stop_words and len(token) > 2]
        
        return ' '.join(tokens)
    
    def load_training_data(self, error_solution_pairs):
        """훈련 데이터 로드 및 벡터화"""
        self.error_texts = [pair['error'] for pair in error_solution_pairs]
        self.error_solutions = [pair['solution'] for pair in error_solution_pairs]
        
        # 텍스트 전처리
        preprocessed_texts = [self.preprocess_text(text) for text in self.error_texts]
        
        # 벡터화
        self.error_vectors = self.vectorizer.fit_transform(preprocessed_texts)
        
        logging.info(f"훈련 데이터 로드 완료: {len(self.error_texts)}개 샘플")
    
    def find_similar_errors(self, query_error, top_k=3):
        """유사한 에러 찾기"""
        if self.error_vectors is None:
            return []
        
        # 쿼리 전처리 및 벡터화
        preprocessed_query = self.preprocess_text(query_error)
        query_vector = self.vectorizer.transform([preprocessed_query])
        
        # 코사인 유사도 계산
        similarities = cosine_similarity(query_vector, self.error_vectors)[0]
        
        # 유사도 순으로 정렬
        similar_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in similar_indices:
            if similarities[idx] > self.similarity_threshold:
                results.append({
                    'error': self.error_texts[idx],
                    'solution': self.error_solutions[idx],
                    'similarity': float(similarities[idx])
                })
        
        return results
    
    def resolve_error(self, error_text):
        """에러 해결책 찾기"""
        # 1. 정확한 매칭 시도 (기존 규칙 기반)
        exact_match = self.exact_match_resolve(error_text)
        if exact_match:
            return {
                'solution': exact_match,
                'method': 'exact_match',
                'confidence': 1.0
            }
        
        # 2. 유사도 기반 매칭
        similar_errors = self.find_similar_errors(error_text)
        if similar_errors:
            best_match = similar_errors[0]
            return {
                'solution': best_match['solution'],
                'method': 'similarity_match',
                'confidence': best_match['similarity'],
                'similar_errors': similar_errors
            }
        
        # 3. 해결책 없음
        return {
            'solution': None,
            'method': 'no_match',
            'confidence': 0.0
        }
    
    def exact_match_resolve(self, error_text):
        """기존 규칙 기반 해결 (백워드 호환성)"""
        # 기존 규칙 기반 로직 유지
        patterns = {
            r'elasticsearch.*connection.*refused': 'kubectl restart deployment/elasticsearch',
            r'kibana.*memory.*heap': 'kubectl patch deployment/kibana -p "{\\"spec\\":{\\"template\\":{\\"spec\\":{\\"containers\\":[{\\"name\\":\\"kibana\\",\\"resources\\":{\\"limits\\":{\\"memory\\":\\"2Gi\\"}}}]}}}}"',
            r'logstash.*pipeline.*config': 'kubectl edit configmap logstash-config'
        }
        
        for pattern, solution in patterns.items():
            if re.search(pattern, error_text, re.IGNORECASE):
                return solution
        
        return None

# 사용 예시
if __name__ == "__main__":
    # 훈련 데이터 준비
    training_data = [
        {
            'error': 'elasticsearch connection refused port 9200',
            'solution': 'kubectl restart deployment/elasticsearch'
        },
        {
            'error': 'elasticsearch cluster health red status',
            'solution': 'kubectl scale deployment/elasticsearch --replicas=0 && kubectl scale deployment/elasticsearch --replicas=1'
        },
        {
            'error': 'kibana memory heap out of space error',
            'solution': 'kubectl patch deployment/kibana -p "{\\"spec\\":{\\"template\\":{\\"spec\\":{\\"containers\\":[{\\"name\\":\\"kibana\\",\\"resources\\":{\\"limits\\":{\\"memory\\":\\"2Gi\\"}}}]}}}}"'
        },
        {
            'error': 'kibana service timeout connecting to elasticsearch',
            'solution': 'kubectl get svc elasticsearch && kubectl exec -it kibana-pod -- curl elasticsearch:9200'
        },
        {
            'error': 'logstash pipeline configuration syntax error',
            'solution': 'kubectl edit configmap logstash-config'
        },
        {
            'error': 'logstash pipeline failed to start due to config',
            'solution': 'kubectl logs logstash-pod && kubectl edit configmap logstash-config'
        }
    ]
    
    # 해결기 초기화 및 훈련
    resolver = EnhancedErrorResolver()
    resolver.load_training_data(training_data)
    
    # 새로운 에러 해결 시도
    new_error = "elasticsearch service connection timeout on port 9200"
    result = resolver.resolve_error(new_error)
    
    print(f"에러: {new_error}")
    print(f"해결책: {result['solution']}")
    print(f"방법: {result['method']}")
    print(f"신뢰도: {result['confidence']:.2f}")
    
    if result.get('similar_errors'):
        print("\n유사한 에러들:")
        for similar in result['similar_errors']:
            print(f"- {similar['error']} (유사도: {similar['similarity']:.2f})")
```

### 2.2 데이터베이스 스키마 업데이트

```sql
-- 기존 테이블에 새 컬럼 추가
ALTER TABLE solutions ADD COLUMN embedding_vector TEXT;
ALTER TABLE solutions ADD COLUMN similarity_threshold REAL DEFAULT 0.7;
ALTER TABLE solutions ADD COLUMN ml_confidence REAL DEFAULT 0.0;

-- 새 테이블 생성
CREATE TABLE IF NOT EXISTS error_embeddings (
    id SERIAL PRIMARY KEY,
    error_hash VARCHAR(64) UNIQUE NOT NULL,
    embedding_vector TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS similarity_matches (
    id SERIAL PRIMARY KEY,
    query_error_hash VARCHAR(64) NOT NULL,
    matched_error_hash VARCHAR(64) NOT NULL,
    similarity_score REAL NOT NULL,
    solution_used TEXT NOT NULL,
    success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 3. 2단계: 머신러닝 모델 도입

### 3.1 분류 알고리즘 구현

```python
# ml_classifier.py
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
import logging

class MLErrorClassifier:
    def __init__(self):
        self.models = {
            'random_forest': Pipeline([
                ('tfidf', TfidfVectorizer(max_features=10000, ngram_range=(1, 3))),
                ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
            ]),
            'svm': Pipeline([
                ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
                ('classifier', SVC(kernel='rbf', probability=True, random_state=42))
            ]),
            'naive_bayes': Pipeline([
                ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
                ('classifier', MultinomialNB())
            ])
        }
        self.best_model = None
        self.best_score = 0.0
        self.solution_classes = []
    
    def prepare_data(self, error_solution_pairs):
        """데이터 준비"""
        df = pd.DataFrame(error_solution_pairs)
        X = df['error'].values
        y = df['solution'].values
        
        # 해결책 클래스 저장
        self.solution_classes = list(set(y))
        
        return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    def train_models(self, X_train, y_train):
        """모든 모델 훈련 및 최적 모델 선택"""
        results = {}
        
        for name, model in self.models.items():
            logging.info(f"{name} 모델 훈련 시작...")
            
            # 교차 검증
            cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
            mean_score = cv_scores.mean()
            
            # 모델 훈련
            model.fit(X_train, y_train)
            
            results[name] = {
                'model': model,
                'cv_score': mean_score,
                'cv_std': cv_scores.std()
            }
            
            logging.info(f"{name} - CV 점수: {mean_score:.3f} (±{cv_scores.std():.3f})")
            
            # 최적 모델 업데이트
            if mean_score > self.best_score:
                self.best_score = mean_score
                self.best_model = model
        
        return results
    
    def evaluate_model(self, X_test, y_test):
        """모델 평가"""
        if self.best_model is None:
            raise ValueError("모델이 훈련되지 않았습니다.")
        
        predictions = self.best_model.predict(X_test)
        probabilities = self.best_model.predict_proba(X_test)
        
        # 분류 리포트
        report = classification_report(y_test, predictions, output_dict=True)
        
        # 혼동 행렬
        cm = confusion_matrix(y_test, predictions)
        
        return {
            'predictions': predictions,
            'probabilities': probabilities,
            'classification_report': report,
            'confusion_matrix': cm,
            'accuracy': report['accuracy']
        }
    
    def predict_solution(self, error_text, confidence_threshold=0.7):
        """새로운 에러에 대한 해결책 예측"""
        if self.best_model is None:
            raise ValueError("모델이 훈련되지 않았습니다.")
        
        # 예측 및 확률 계산
        probabilities = self.best_model.predict_proba([error_text])[0]
        predicted_class = self.best_model.predict([error_text])[0]
        confidence = max(probabilities)
        
        # 신뢰도 기반 결정
        if confidence >= confidence_threshold:
            return {
                'solution': predicted_class,
                'confidence': confidence,
                'all_probabilities': dict(zip(self.best_model.classes_, probabilities)),
                'reliable': True
            }
        else:
            return {
                'solution': predicted_class,
                'confidence': confidence,
                'all_probabilities': dict(zip(self.best_model.classes_, probabilities)),
                'reliable': False
            }
    
    def save_model(self, filepath):
        """모델 저장"""
        if self.best_model is None:
            raise ValueError("저장할 모델이 없습니다.")
        
        model_data = {
            'model': self.best_model,
            'solution_classes': self.solution_classes,
            'best_score': self.best_score
        }
        
        joblib.dump(model_data, filepath)
        logging.info(f"모델이 {filepath}에 저장되었습니다.")
    
    def load_model(self, filepath):
        """모델 로드"""
        model_data = joblib.load(filepath)
        self.best_model = model_data['model']
        self.solution_classes = model_data['solution_classes']
        self.best_score = model_data['best_score']
        
        logging.info(f"모델이 {filepath}에서 로드되었습니다.")

# 사용 예시
if __name__ == "__main__":
    # 훈련 데이터 확장
    training_data = [
        # Elasticsearch 에러들
        {'error': 'elasticsearch connection refused port 9200', 'solution': 'restart_elasticsearch'},
        {'error': 'elasticsearch cluster health red status', 'solution': 'restart_elasticsearch'},
        {'error': 'elasticsearch service not responding', 'solution': 'restart_elasticsearch'},
        {'error': 'elasticsearch connection timeout', 'solution': 'restart_elasticsearch'},
        {'error': 'elasticsearch unable to connect', 'solution': 'restart_elasticsearch'},
        
        # Kibana 에러들
        {'error': 'kibana memory heap out of space', 'solution': 'increase_kibana_memory'},
        {'error': 'kibana out of memory error', 'solution': 'increase_kibana_memory'},
        {'error': 'kibana heap space exceeded', 'solution': 'increase_kibana_memory'},
        {'error': 'kibana memory allocation failed', 'solution': 'increase_kibana_memory'},
        
        # Logstash 에러들
        {'error': 'logstash pipeline configuration error', 'solution': 'fix_logstash_config'},
        {'error': 'logstash config syntax error', 'solution': 'fix_logstash_config'},
        {'error': 'logstash pipeline failed to start', 'solution': 'fix_logstash_config'},
        {'error': 'logstash configuration invalid', 'solution': 'fix_logstash_config'},
        
        # 권한 에러들
        {'error': 'filebeat permission denied accessing log', 'solution': 'fix_permissions'},
        {'error': 'permission denied reading log file', 'solution': 'fix_permissions'},
        {'error': 'access denied to log directory', 'solution': 'fix_permissions'},
        {'error': 'insufficient permissions for log access', 'solution': 'fix_permissions'},
        
        # 네트워크 에러들
        {'error': 'network connection failed', 'solution': 'check_network'},
        {'error': 'connection refused network error', 'solution': 'check_network'},
        {'error': 'network timeout error', 'solution': 'check_network'},
        {'error': 'network unreachable', 'solution': 'check_network'}
    ]
    
    # 분류기 초기화
    classifier = MLErrorClassifier()
    
    # 데이터 준비
    X_train, X_test, y_train, y_test = classifier.prepare_data(training_data)
    
    # 모델 훈련
    results = classifier.train_models(X_train, y_train)
    
    # 모델 평가
    evaluation = classifier.evaluate_model(X_test, y_test)
    print(f"최적 모델 정확도: {evaluation['accuracy']:.3f}")
    
    # 모델 저장
    classifier.save_model('elk_error_classifier.pkl')
    
    # 새로운 에러 예측
    new_error = "elasticsearch service connection failed on port 9200"
    prediction = classifier.predict_solution(new_error)
    
    print(f"\n새로운 에러: {new_error}")
    print(f"예측된 해결책: {prediction['solution']}")
    print(f"신뢰도: {prediction['confidence']:.3f}")
    print(f"신뢰할 수 있는 예측: {prediction['reliable']}")
```

### 3.2 성능 모니터링 시스템

```python
# monitoring.py
import time
import psutil
import logging
from datetime import datetime
import json

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'prediction_times': [],
            'memory_usage': [],
            'accuracy_scores': [],
            'confidence_scores': []
        }
    
    def start_prediction_timer(self):
        """예측 시간 측정 시작"""
        return time.time()
    
    def end_prediction_timer(self, start_time):
        """예측 시간 측정 종료"""
        duration = time.time() - start_time
        self.metrics['prediction_times'].append(duration)
        return duration
    
    def log_memory_usage(self):
        """메모리 사용량 로그"""
        memory_mb = psutil.virtual_memory().used / 1024 / 1024
        self.metrics['memory_usage'].append(memory_mb)
        return memory_mb
    
    def log_prediction_accuracy(self, predicted, actual):
        """예측 정확도 로그"""
        accuracy = 1.0 if predicted == actual else 0.0
        self.metrics['accuracy_scores'].append(accuracy)
        return accuracy
    
    def log_confidence_score(self, confidence):
        """신뢰도 점수 로그"""
        self.metrics['confidence_scores'].append(confidence)
    
    def get_performance_summary(self):
        """성능 요약 반환"""
        if not self.metrics['prediction_times']:
            return "성능 데이터 없음"
        
        return {
            'avg_prediction_time': np.mean(self.metrics['prediction_times']),
            'max_prediction_time': max(self.metrics['prediction_times']),
            'avg_memory_usage_mb': np.mean(self.metrics['memory_usage']),
            'avg_accuracy': np.mean(self.metrics['accuracy_scores']) if self.metrics['accuracy_scores'] else 0.0,
            'avg_confidence': np.mean(self.metrics['confidence_scores']) if self.metrics['confidence_scores'] else 0.0,
            'total_predictions': len(self.metrics['prediction_times'])
        }
    
    def save_metrics(self, filepath):
        """메트릭 저장"""
        with open(filepath, 'w') as f:
            json.dump(self.metrics, f, indent=2)
```

## 4. 3단계: 딥러닝 모델 구축

### 4.1 BERT 기반 분류기

```python
# bert_classifier.py
import torch
import torch.nn as nn
from transformers import BertTokenizer, BertForSequenceClassification
from transformers import Trainer, TrainingArguments
from torch.utils.data import Dataset, DataLoader
import numpy as np
from sklearn.metrics import accuracy_score

class ErrorDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

class BERTErrorClassifier:
    def __init__(self, model_name='bert-base-uncased', num_labels=5):
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.model = BertForSequenceClassification.from_pretrained(
            model_name,
            num_labels=num_labels
        )
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
    
    def prepare_data(self, texts, labels):
        """데이터 준비"""
        # 라벨 인코딩
        unique_labels = list(set(labels))
        label_to_id = {label: idx for idx, label in enumerate(unique_labels)}
        encoded_labels = [label_to_id[label] for label in labels]
        
        return texts, encoded_labels, label_to_id
    
    def train(self, train_texts, train_labels, val_texts, val_labels, epochs=3):
        """모델 훈련"""
        train_texts, train_labels, self.label_to_id = self.prepare_data(train_texts, train_labels)
        val_texts, val_labels, _ = self.prepare_data(val_texts, val_labels)
        
        # 데이터셋 생성
        train_dataset = ErrorDataset(train_texts, train_labels, self.tokenizer)
        val_dataset = ErrorDataset(val_texts, val_labels, self.tokenizer)
        
        # 훈련 설정
        training_args = TrainingArguments(
            output_dir='./results',
            num_train_epochs=epochs,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir='./logs',
            logging_steps=10,
            eval_steps=100,
            save_steps=500,
            evaluation_strategy='steps'
        )
        
        # 트레이너 생성
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=self.compute_metrics
        )
        
        # 훈련 실행
        trainer.train()
        
        return trainer
    
    def compute_metrics(self, eval_pred):
        """평가 메트릭 계산"""
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        return {'accuracy': accuracy_score(labels, predictions)}
    
    def predict(self, text):
        """예측 수행"""
        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            truncation=True,
            padding=True,
            max_length=512
        )
        
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            predicted_class = torch.argmax(predictions, dim=-1).item()
            confidence = predictions[0][predicted_class].item()
        
        # 라벨 디코딩
        id_to_label = {v: k for k, v in self.label_to_id.items()}
        predicted_label = id_to_label[predicted_class]
        
        return {
            'solution': predicted_label,
            'confidence': confidence,
            'all_probabilities': predictions[0].cpu().numpy()
        }
```

### 4.2 전체 시스템 통합

```python
# integrated_resolver.py
import logging
from typing import Dict, List, Optional
import json
from enhanced_resolver import EnhancedErrorResolver
from ml_classifier import MLErrorClassifier
from monitoring import PerformanceMonitor

class IntegratedErrorResolver:
    def __init__(self):
        self.enhanced_resolver = EnhancedErrorResolver()
        self.ml_classifier = MLErrorClassifier()
        self.monitor = PerformanceMonitor()
        
        # 설정
        self.confidence_thresholds = {
            'exact_match': 1.0,
            'similarity_match': 0.7,
            'ml_prediction': 0.8,
            'bert_prediction': 0.85
        }
        
        # 모델 로드
        self.load_models()
    
    def load_models(self):
        """저장된 모델 로드"""
        try:
            self.ml_classifier.load_model('elk_error_classifier.pkl')
            logging.info("ML 분류기 로드 완료")
        except Exception as e:
            logging.warning(f"ML 분류기 로드 실패: {e}")
    
    def resolve_error(self, error_text: str, method_preference: str = 'auto') -> Dict:
        """
        통합 에러 해결 시스템
        
        Args:
            error_text: 에러 텍스트
            method_preference: 'auto', 'rule_based', 'ml_only', 'bert_only'
        
        Returns:
            해결책 정보 딕셔너리
        """
        start_time = self.monitor.start_prediction_timer()
        memory_before = self.monitor.log_memory_usage()
        
        result = {
            'error_text': error_text,
            'solutions': [],
            'final_solution': None,
            'confidence': 0.0,
            'method_used': None,
            'processing_time': 0.0,
            'memory_usage': memory_before
        }
        
        try:
            if method_preference == 'auto':
                # 단계별 해결 시도
                result = self._resolve_with_cascade(error_text)
            elif method_preference == 'rule_based':
                result = self._resolve_with_rules(error_text)
            elif method_preference == 'ml_only':
                result = self._resolve_with_ml(error_text)
            elif method_preference == 'bert_only':
                result = self._resolve_with_bert(error_text)
            else:
                result = self._resolve_with_cascade(error_text)
            
        except Exception as e:
            logging.error(f"에러 해결 중 오류 발생: {e}")
            result['error'] = str(e)
        
        finally:
            # 성능 메트릭 업데이트
            processing_time = self.monitor.end_prediction_timer(start_time)
            result['processing_time'] = processing_time
            
            if result.get('confidence'):
                self.monitor.log_confidence_score(result['confidence'])
        
        return result
    
    def _resolve_with_cascade(self, error_text: str) -> Dict:
        """계단식 해결 방식 (우선순위 순)"""
        
        # 1. 정확한 규칙 매칭
        exact_result = self.enhanced_resolver.resolve_error(error_text)
        if exact_result['method'] == 'exact_match':
            return {
                'final_solution': exact_result['solution'],
                'confidence': exact_result['confidence'],
                'method_used': 'exact_match',
                'solutions': [exact_result]
            }
        
        # 2. 유사도 기반 매칭
        if exact_result['method'] == 'similarity_match' and \
           exact_result['confidence'] >= self.confidence_thresholds['similarity_match']:
            return {
                'final_solution': exact_result['solution'],
                'confidence': exact_result['confidence'],
                'method_used': 'similarity_match',
                'solutions': [exact_result]
            }
        
        # 3. ML 분류기 사용
        try:
            ml_result = self.ml_classifier.predict_solution(error_text)
            if ml_result['confidence'] >= self.confidence_thresholds['ml_prediction']:
                return {
                    'final_solution': ml_result['solution'],
                    'confidence': ml_result['confidence'],
                    'method_used': 'ml_prediction',
                    'solutions': [exact_result, ml_result]
                }
        except Exception as e:
            logging.warning(f"ML 예측 실패: {e}")
        
        # 4. 가장 신뢰할 수 있는 결과 선택
        all_solutions = [exact_result]
        if 'ml_result' in locals():
            all_solutions.append(ml_result)
        
        best_solution = max(all_solutions, key=lambda x: x.get('confidence', 0))
        
        return {
            'final_solution': best_solution.get('solution'),
            'confidence': best_solution.get('confidence', 0),
            'method_used': best_solution.get('method', 'unknown'),
            'solutions': all_solutions
        }
    
    def _resolve_with_rules(self, error_text: str) -> Dict:
        """규칙 기반 해결"""
        result = self.enhanced_resolver.resolve_error(error_text)
        return {
            'final_solution': result['solution'],
            'confidence': result['confidence'],
            'method_used': result['method'],
            'solutions': [result]
        }
    
    def _resolve_with_ml(self, error_text: str) -> Dict:
        """ML 기반 해결"""
        result = self.ml_classifier.predict_solution(error_text)
        return {
            'final_solution': result['solution'],
            'confidence': result['confidence'],
            'method_used': 'ml_prediction',
            'solutions': [result]
        }
    
    def _resolve_with_bert(self, error_text: str) -> Dict:
        """BERT 기반 해결 (구현 예정)"""
        # BERT 모델 구현 후 추가
        return {
            'final_solution': None,
            'confidence': 0.0,
            'method_used': 'bert_not_implemented',
            'solutions': []
        }
    
    def get_performance_summary(self) -> Dict:
        """성능 요약 반환"""
        return self.monitor.get_performance_summary()
    
    def save_performance_metrics(self, filepath: str):
        """성능 메트릭 저장"""
        self.monitor.save_metrics(filepath)

# 사용 예시
if __name__ == "__main__":
    # 통합 해결기 초기화
    resolver = IntegratedErrorResolver()
    
    # 테스트 케이스
    test_errors = [
        "elasticsearch connection refused port 9200",
        "kibana memory heap space error",
        "logstash pipeline configuration syntax error",
        "filebeat permission denied log access",
        "unknown service timeout error"
    ]
    
    for error in test_errors:
        result = resolver.resolve_error(error, method_preference='auto')
        
        print(f"\n에러: {error}")
        print(f"해결책: {result['final_solution']}")
        print(f"신뢰도: {result['confidence']:.3f}")
        print(f"사용 방법: {result['method_used']}")
        print(f"처리 시간: {result['processing_time']:.3f}초")
    
    # 성능 요약
    performance = resolver.get_performance_summary()
    print(f"\n성능 요약: {performance}")
```

## 5. 배포 및 운영

### 5.1 Docker 컨테이너화

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements_ml.txt .
RUN pip install --no-cache-dir -r requirements_ml.txt

# 모델 및 코드 복사
COPY . .

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV MODEL_PATH=/app/models
ENV LOG_LEVEL=INFO

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 실행 명령
CMD ["python", "api_server.py"]
```

### 5.2 API 서버

```python
# api_server.py
from flask import Flask, request, jsonify
import logging
import os
from integrated_resolver import IntegratedErrorResolver

app = Flask(__name__)
resolver = IntegratedErrorResolver()

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, os.environ.get('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'version': '1.0.0'})

@app.route('/resolve', methods=['POST'])
def resolve_error():
    try:
        data = request.json
        error_text = data.get('error_text', '')
        method_preference = data.get('method_preference', 'auto')
        
        if not error_text:
            return jsonify({'error': 'error_text는 필수입니다'}), 400
        
        result = resolver.resolve_error(error_text, method_preference)
        return jsonify(result)
    
    except Exception as e:
        logging.error(f"API 요청 처리 중 오류: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    try:
        metrics = resolver.get_performance_summary()
        return jsonify(metrics)
    except Exception as e:
        logging.error(f"메트릭 요청 처리 중 오류: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
```

### 5.3 Kubernetes 배포

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elk-ml-resolver
  namespace: elk-stack
spec:
  replicas: 2
  selector:
    matchLabels:
      app: elk-ml-resolver
  template:
    metadata:
      labels:
        app: elk-ml-resolver
    spec:
      containers:
      - name: resolver
        image: elk-ml-resolver:latest
        ports:
        - containerPort: 8000
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: MODEL_PATH
          value: "/app/models"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        volumeMounts:
        - name: models
          mountPath: /app/models
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ml-models-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: elk-ml-resolver-service
  namespace: elk-stack
spec:
  selector:
    app: elk-ml-resolver
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: ClusterIP
```

## 6. 성능 최적화 및 모니터링

### 6.1 성능 최적화 전략

1. **모델 캐싱**
   - 자주 사용되는 예측 결과 캐시
   - Redis를 활용한 분산 캐싱

2. **배치 처리**
   - 여러 에러를 한 번에 처리
   - GPU 활용 시 배치 크기 최적화

3. **모델 경량화**
   - 모델 압축 (pruning, quantization)
   - ONNX 변환으로 추론 속도 향상

4. **비동기 처리**
   - 복잡한 ML 모델은 별도 워커에서 처리
   - 실시간 응답이 필요한 경우 규칙 기반 우선 사용

### 6.2 모니터링 대시보드

```python
# monitoring_dashboard.py
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import pandas as pd
import json

class MonitoringDashboard:
    def __init__(self):
        self.app = dash.Dash(__name__)
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        self.app.layout = html.Div([
            html.H1("ELK ML Resolver 모니터링"),
            
            # 성능 메트릭
            html.Div([
                html.H3("성능 메트릭"),
                dcc.Graph(id='performance-metrics'),
                dcc.Interval(
                    id='interval-component',
                    interval=10*1000,  # 10초마다 업데이트
                    n_intervals=0
                )
            ]),
            
            # 정확도 트렌드
            html.Div([
                html.H3("정확도 트렌드"),
                dcc.Graph(id='accuracy-trend')
            ]),
            
            # 해결 방법 분포
            html.Div([
                html.H3("해결 방법 분포"),
                dcc.Graph(id='method-distribution')
            ])
        ])
    
    def setup_callbacks(self):
        @self.app.callback(
            [Output('performance-metrics', 'figure'),
             Output('accuracy-trend', 'figure'),
             Output('method-distribution', 'figure')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_graphs(n):
            # 실제 데이터 로드 (여기서는 더미 데이터)
            performance_data = self.load_performance_data()
            accuracy_data = self.load_accuracy_data()
            method_data = self.load_method_data()
            
            # 성능 메트릭 그래프
            perf_fig = go.Figure()
            perf_fig.add_trace(go.Scatter(
                x=performance_data['timestamp'],
                y=performance_data['response_time'],
                mode='lines+markers',
                name='응답 시간 (ms)'
            ))
            perf_fig.update_layout(title='응답 시간 트렌드')
            
            # 정확도 트렌드 그래프
            acc_fig = go.Figure()
            acc_fig.add_trace(go.Scatter(
                x=accuracy_data['timestamp'],
                y=accuracy_data['accuracy'],
                mode='lines+markers',
                name='정확도'
            ))
            acc_fig.update_layout(title='정확도 트렌드')
            
            # 방법 분포 파이 차트
            method_fig = go.Figure(data=[go.Pie(
                labels=method_data['method'],
                values=method_data['count']
            )])
            method_fig.update_layout(title='해결 방법 분포')
            
            return perf_fig, acc_fig, method_fig
    
    def load_performance_data(self):
        # 실제 구현에서는 데이터베이스에서 로드
        return pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='H'),
            'response_time': [50 + i*0.5 for i in range(100)]
        })
    
    def load_accuracy_data(self):
        return pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='H'),
            'accuracy': [0.8 + (i % 20) * 0.01 for i in range(100)]
        })
    
    def load_method_data(self):
        return pd.DataFrame({
            'method': ['exact_match', 'similarity_match', 'ml_prediction', 'manual'],
            'count': [45, 30, 20, 5]
        })
    
    def run(self, host='0.0.0.0', port=8050):
        self.app.run_server(host=host, port=port, debug=False)

if __name__ == '__main__':
    dashboard = MonitoringDashboard()
    dashboard.run()
```

## 7. 결론 및 다음 단계

### 7.1 업그레이드 효과 예상

| 단계 | 현재 대비 성능 향상 | 예상 정확도 | 개발 기간 |
|------|-------------------|-------------|-----------|
| **1단계** | 30% 향상 | 65-75% | 2-4주 |
| **2단계** | 70% 향상 | 80-90% | 2-3개월 |
| **3단계** | 150% 향상 | 90-95% | 6개월+ |

### 7.2 다음 단계 계획

1. **즉시 시작 (1-2주)**
   - 텍스트 유사도 매칭 구현
   - 성능 모니터링 시스템 구축

2. **단기 목표 (1-2개월)**
   - ML 분류기 통합
   - API 서버 구축 및 배포

3. **중기 목표 (3-6개월)**
   - BERT 모델 통합
   - 자동 재학습 시스템 구축

4. **장기 목표 (6개월+)**
   - 강화학습 도입
   - 자동 규칙 생성 시스템

---

**문서 작성일**: 2025-07-10  
**다음 업데이트**: 2025-07-17  
**담당자**: ML 개발팀