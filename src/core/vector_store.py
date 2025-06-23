# src/core/vector_store.py
"""
ベクトルストア - コードチャンクの埋め込みと類似検索
"""

import logging
import json
import numpy as np
import pickle
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime
import hashlib
import sqlite3
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
import re

@dataclass
class SearchResult:
    """検索結果を表すデータクラス"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    file_path: str
    line_start: int
    line_end: int

class VectorStore:
    """
    ベクトルストアクラス
    コードチャンクの埋め込み生成、保存、類似検索を行う
    """
    
    def __init__(self, 
                 store_path: str = "vector_store.db",
                 embedding_dim: int = 300,
                 use_tfidf: bool = True,
                 use_code_features: bool = True):
        """
        初期化
        
        Args:
            store_path: ストアファイルのパス
            embedding_dim: 埋め込みベクトルの次元数
            use_tfidf: TF-IDFベクトル化を使用するか
            use_code_features: コード固有の特徴量を使用するか
        """
        self.logger = logging.getLogger(__name__)
        self.store_path = Path(store_path)
        self.embedding_dim = embedding_dim
        self.use_tfidf = use_tfidf
        self.use_code_features = use_code_features
        
        # ベクトライザーの初期化
        self.tfidf_vectorizer = None
        self.svd_reducer = None
        
        # インメモリキャッシュ
        self.chunk_cache = {}
        self.vector_cache = {}
        
        # データベース接続
        self.db_connection = None
        
        # 初期化
        self._initialize_store()
        self._initialize_vectorizers()
        
        self.logger.info(f"VectorStore初期化完了: {store_path}")
    
    def _initialize_store(self):
        """ストアの初期化"""
        try:
            self.db_connection = sqlite3.connect(str(self.store_path), check_same_thread=False)
            self.db_connection.row_factory = sqlite3.Row
            
            # テーブル作成
            self._create_tables()
            
        except Exception as e:
            self.logger.error(f"ストア初期化エラー: {e}")
            raise
    
    def _create_tables(self):
        """データベーステーブルの作成"""
        cursor = self.db_connection.cursor()
        
        # チャンクテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                metadata TEXT NOT NULL,
                file_path TEXT NOT NULL,
                language TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # ベクトルテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                chunk_id TEXT PRIMARY KEY,
                vector_data BLOB NOT NULL,
                vector_type TEXT NOT NULL,
                dimension INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chunk_id) REFERENCES chunks (id)
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks (file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_language ON chunks (language)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks (chunk_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks (content_hash)")
        
        self.db_connection.commit()
    
    def _initialize_vectorizers(self):
        """ベクトライザーの初期化"""
        if self.use_tfidf:
            # TF-IDFベクトライザー（コード用にカスタマイズ）
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=10000,
                stop_words=None,  # コードでは停止語を使わない
                ngram_range=(1, 2),
                token_pattern=r'\b\w+\b',
                lowercase=True,
                max_df=0.95,
                min_df=2
            )
            
            # 次元削減用
            self.svd_reducer = TruncatedSVD(
                n_components=min(self.embedding_dim, 300),
                random_state=42
            )
    
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """
        チャンクを追加してベクトル化
        
        Args:
            chunks: チャンクのリスト
            
        Returns:
            追加されたチャンクのIDリスト
        """
        added_ids = []
        
        try:
            for chunk in chunks:
                chunk_id = self._add_single_chunk(chunk)
                if chunk_id:
                    added_ids.append(chunk_id)
            
            # ベクトライザーの再訓練（必要に応じて）
            if added_ids:
                self._retrain_vectorizers()
            
            self.logger.info(f"チャンク追加完了: {len(added_ids)} 個")
            return added_ids
            
        except Exception as e:
            self.logger.error(f"チャンク追加エラー: {e}")
            return []
    
    def _add_single_chunk(self, chunk: Dict[str, Any]) -> Optional[str]:
        """単一チャンクの追加"""
        try:
            # チャンクIDの生成
            chunk_id = self._generate_chunk_id(chunk)
            
            # 重複チェック
            if self._chunk_exists(chunk_id):
                self.logger.debug(f"チャンクは既に存在します: {chunk_id}")
                return chunk_id
            
            # 内容のハッシュ化
            content = chunk.get('content', '')
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # メタデータの準備
            metadata = {
                'function_name': chunk.get('function_name', ''),
                'class_name': chunk.get('class_name', ''),
                'docstring': chunk.get('docstring', ''),
                'keywords': chunk.get('keywords', []),
                'parameters': chunk.get('parameters', [])
            }
            
            # データベースに挿入
            cursor = self.db_connection.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO chunks (
                    id, content, content_hash, metadata, file_path, 
                    language, chunk_type, line_start, line_end, 
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk_id,
                content,
                content_hash,
                json.dumps(metadata, ensure_ascii=False),
                chunk.get('file_path', ''),
                chunk.get('language', 'text'),
                chunk.get('type', 'unknown'),
                chunk.get('line_start', 0),
                chunk.get('line_end', 0),
                now,
                now
            ))
            
            # ベクトル生成と保存
            vector = self._generate_vector(chunk)
            if vector is not None:
                self._save_vector(chunk_id, vector)
            
            self.db_connection.commit()
            
            # キャッシュに追加
            self.chunk_cache[chunk_id] = chunk
            if vector is not None:
                self.vector_cache[chunk_id] = vector
            
            return chunk_id
            
        except Exception as e:
            self.logger.error(f"チャンク追加エラー: {e}")
            return None
    
    def _generate_chunk_id(self, chunk: Dict[str, Any]) -> str:
        """チャンクIDの生成"""
        # ファイルパス、行番号、内容のハッシュからIDを生成
        file_path = chunk.get('file_path', '')
        line_start = chunk.get('line_start', 0)
        line_end = chunk.get('line_end', 0)
        content = chunk.get('content', '')
        
        id_string = f"{file_path}:{line_start}-{line_end}:{hashlib.md5(content.encode()).hexdigest()[:8]}"
        return hashlib.sha256(id_string.encode()).hexdigest()[:16]
    
    def _chunk_exists(self, chunk_id: str) -> bool:
        """チャンクの存在確認"""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT 1 FROM chunks WHERE id = ?", (chunk_id,))
        return cursor.fetchone() is not None
    
    def _generate_vector(self, chunk: Dict[str, Any]) -> Optional[np.ndarray]:
        """チャンクからベクトルを生成"""
        try:
            # テキスト特徴量の抽出
            text_features = self._extract_text_features(chunk)
            
            # コード特徴量の抽出
            code_features = []
            if self.use_code_features:
                code_features = self._extract_code_features(chunk)
            
            # 特徴量の結合
            if self.use_tfidf and self.tfidf_vectorizer is not None:
                # TF-IDFベクトル化（後で実行される場合はスキップ）
                return None  # 後でバッチ処理
            else:
                # 基本的な特徴量ベクトル
                features = text_features + code_features
                
                # 固定長にパディング/切り詰め
                if len(features) < self.embedding_dim:
                    features.extend([0.0] * (self.embedding_dim - len(features)))
                else:
                    features = features[:self.embedding_dim]
                
                return np.array(features, dtype=np.float32)
            
        except Exception as e:
            self.logger.error(f"ベクトル生成エラー: {e}")
            return None
    
    def _extract_text_features(self, chunk: Dict[str, Any]) -> List[float]:
        """テキスト特徴量の抽出"""
        content = chunk.get('content', '')
        
        features = []
        
        # 基本的な統計量
        features.append(len(content))  # 文字数
        features.append(len(content.split('\n')))  # 行数
        features.append(len(content.split()))  # 単語数
        
        # 文字種の比率
        if content:
            alpha_ratio = sum(c.isalpha() for c in content) / len(content)
            digit_ratio = sum(c.isdigit() for c in content) / len(content)
            space_ratio = sum(c.isspace() for c in content) / len(content)
            special_ratio = sum(not c.isalnum() and not c.isspace() for c in content) / len(content)
            
            features.extend([alpha_ratio, digit_ratio, space_ratio, special_ratio])
        else:
            features.extend([0.0, 0.0, 0.0, 0.0])
        
        return features
    
    def _extract_code_features(self, chunk: Dict[str, Any]) -> List[float]:
        """コード固有の特徴量を抽出"""
        content = chunk.get('content', '')
        language = chunk.get('language', 'text')
        
        features = []
        
        # 言語固有の特徴量
        if language == 'python':
            features.extend(self._extract_python_features(content))
        elif language in ['javascript', 'typescript']:
            features.extend(self._extract_js_features(content))
        elif language == 'java':
            features.extend(self._extract_java_features(content))
        else:
            features.extend([0.0] * 10)  # デフォルト値
        
        # 一般的なコード特徴量
        features.extend(self._extract_general_code_features(content))
        
        return features
    
    def _extract_python_features(self, content: str) -> List[float]:
        """Python固有の特徴量"""
        features = []
        
        # キーワードの出現回数
        python_keywords = ['def', 'class', 'import', 'from', 'if', 'for', 'while', 'try', 'except']
        for keyword in python_keywords:
            count = len(re.findall(r'\b' + keyword + r'\b', content))
            features.append(float(count))
        
        # インデントレベル
        lines = content.split('\n')
        indent_levels = []
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                indent_levels.append(indent)
        
        avg_indent = np.mean(indent_levels) if indent_levels else 0
        features.append(avg_indent)
        
        return features
    
    def _extract_js_features(self, content: str) -> List[float]:
        """JavaScript/TypeScript固有の特徴量"""
        features = []
        
        # キーワードの出現回数
        js_keywords = ['function', 'var', 'let', 'const', 'if', 'for', 'while', 'try', 'catch', 'class']
        for keyword in js_keywords:
            count = len(re.findall(r'\b' + keyword + r'\b', content))
            features.append(float(count))
        
        return features
    
    def _extract_java_features(self, content: str) -> List[float]:
        """Java固有の特徴量"""
        features = []
        
        # キーワードの出現回数
        java_keywords = ['public', 'private', 'protected', 'class', 'interface', 'extends', 'implements', 'import', 'package', 'static']
        for keyword in java_keywords:
            count = len(re.findall(r'\b' + keyword + r'\b', content))
            features.append(float(count))
        
        return features
    
    def _extract_general_code_features(self, content: str) -> List[float]:
        """一般的なコード特徴量"""
        features = []
        
        # 括弧の使用頻度
        features.append(float(content.count('(')))
        features.append(float(content.count('{')))
        features.append(float(content.count('[')))
        
        # コメントの検出
        comment_patterns = [r'//.*', r'/\*.*?\*/', r'#.*', r'""".*?"""', r"'''.*?'''"]
        comment_count = 0
        for pattern in comment_patterns:
            comment_count += len(re.findall(pattern, content, re.DOTALL))
        features.append(float(comment_count))
        
        # 文字列リテラルの数
        string_patterns = [r'"[^"]*"', r"'[^']*'", r'`[^`]*`']
        string_count = 0
        for pattern in string_patterns:
            string_count += len(re.findall(pattern, content))
        features.append(float(string_count))
        
        return features
    
    def _save_vector(self, chunk_id: str, vector: np.ndarray):
        """ベクトルをデータベースに保存"""
        try:
            cursor = self.db_connection.cursor()
            
            # ベクトルをバイナリ形式で保存
            vector_data = pickle.dumps(vector)
            
            cursor.execute("""
                INSERT OR REPLACE INTO vectors (
                    chunk_id, vector_data, vector_type, dimension, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                chunk_id,
                vector_data,
                'tfidf' if self.use_tfidf else 'custom',
                len(vector),
                datetime.now().isoformat()
            ))
            
        except Exception as e:
            self.logger.error(f"ベクトル保存エラー: {e}")
    
    def _retrain_vectorizers(self):
        """ベクトライザーの再訓練"""
        if not self.use_tfidf:
            return
        
        try:
            # 全チャンクの内容を取得
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT id, content FROM chunks")
            rows = cursor.fetchall()
            
            if len(rows) < 2:
                return
            
            # テキストデータの準備
            texts = []
            chunk_ids = []
            
            for row in rows:
                chunk_id, content = row
                processed_text = self._preprocess_text_for_tfidf(content)
                texts.append(processed_text)
                chunk_ids.append(chunk_id)
            
            # TF-IDFベクトル化
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # 次元削減
            if self.svd_reducer:
                reduced_vectors = self.svd_reducer.fit_transform(tfidf_matrix)
            else:
                reduced_vectors = tfidf_matrix.toarray()
            
            # ベクトルを保存
            for chunk_id, vector in zip(chunk_ids, reduced_vectors):
                self._save_vector(chunk_id, vector)
                self.vector_cache[chunk_id] = vector
            
            self.db_connection.commit()
            self.logger.info(f"ベクトライザー再訓練完了: {len(chunk_ids)} チャンク")
            
        except Exception as e:
            self.logger.error(f"ベクトライザー再訓練エラー: {e}")
    
    def _preprocess_text_for_tfidf(self, content: str) -> str:
        """TF-IDF用のテキスト前処理"""
        # コメントを除去
        content = re.sub(r'//.*', '', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'#.*', '', content)
        
        # 文字列リテラルを除去
        content = re.sub(r'"[^"]*"', 'STRING_LITERAL', content)
        content = re.sub(r"'[^']*'", 'STRING_LITERAL', content)
        
        # 数値を正規化
        content = re.sub(r'\b\d+\b', 'NUMBER', content)
        
        # 記号を空白に置換
        content = re.sub(r'[^\w\s]', ' ', content)
        
        # 複数の空白を単一に
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip().lower()
    
    def search_similar(self, 
                      query: str, 
                      top_k: int = 5,
                      language_filter: Optional[str] = None,
                      file_path_filter: Optional[str] = None,
                      min_similarity: float = 0.1) -> List[SearchResult]:
        """
        類似チャンクの検索
        
        Args:
            query: 検索クエリ
            top_k: 返す結果の最大数
            language_filter: 言語フィルター
            file_path_filter: ファイルパスフィルター
            min_similarity: 最小類似度閾値
            
        Returns:
            検索結果のリスト
        """
        try:
            # クエリベクトルの生成
            query_vector = self._generate_query_vector(query)
            if query_vector is None:
                return []
            
            # 候補チャンクの取得
            candidates = self._get_candidate_chunks(language_filter, file_path_filter)
            
            # 類似度計算
            similarities = []
            for chunk_id, chunk_data in candidates:
                vector = self._get_chunk_vector(chunk_id)
                if vector is not None:
                    similarity = self._calculate_similarity(query_vector, vector)
                    if similarity >= min_similarity:
                        similarities.append((chunk_id, similarity, chunk_data))
            
            # 類似度順にソート
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 結果の構築
            results = []
            for chunk_id, similarity, chunk_data in similarities[:top_k]:
                result = SearchResult(
                    chunk_id=chunk_id,
                    content=chunk_data['content'],
                    metadata=json.loads(chunk_data['metadata']),
                    similarity_score=similarity,
                    file_path=chunk_data['file_path'],
                    line_start=chunk_data['line_start'],
                    line_end=chunk_data['line_end']
                )
                results.append(result)
            
            self.logger.debug(f"検索完了: {len(results)} 件の結果")
            return results
            
        except Exception as e:
            self.logger.error(f"検索エラー: {e}")
            return []
    
    def _generate_query_vector(self, query: str) -> Optional[np.ndarray]:
        """クエリからベクトルを生成"""
        try:
            if self.use_tfidf and self.tfidf_vectorizer is not None:
                # TF-IDFベクトル化
                processed_query = self._preprocess_text_for_tfidf(query)
                tfidf_vector = self.tfidf_vectorizer.transform([processed_query])
                
                if self.svd_reducer:
                    return self.svd_reducer.transform(tfidf_vector)[0]
                else:
                    return tfidf_vector.toarray()[0]
            else:
                # 基本的な特徴量ベクトル
                fake_chunk = {
                    'content': query,
                    'language': 'text',
                    'type': 'query'
                }
                return self._generate_vector(fake_chunk)
                
        except Exception as e:
            self.logger.error(f"クエリベクトル生成エラー: {e}")
            return None
    
    def _get_candidate_chunks(self, 
                             language_filter: Optional[str] = None,
                             file_path_filter: Optional[str] = None) -> List[Tuple[str, Dict]]:
        """候補チャンクの取得"""
        cursor = self.db_connection.cursor()
        
        # クエリの構築
        query = "SELECT id, content, metadata, file_path, line_start, line_end FROM chunks WHERE 1=1"
        params = []
        
        if language_filter:
            query += " AND language = ?"
            params.append(language_filter)
        
        if file_path_filter:
            query += " AND file_path LIKE ?"
            params.append(f"%{file_path_filter}%")
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        candidates = []
        for row in rows:
            chunk_data = {
                'content': row['content'],
                'metadata': row['metadata'],
                'file_path': row['file_path'],
                'line_start': row['line_start'],
                'line_end': row['line_end']
            }
            candidates.append((row['id'], chunk_data))
        
        return candidates
    
    def _get_chunk_vector(self, chunk_id: str) -> Optional[np.ndarray]:
        """チャンクのベクトルを取得"""
        # キャッシュから取得を試行
        if chunk_id in self.vector_cache:
            return self.vector_cache[chunk_id]
        
        # データベースから取得
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT vector_data FROM vectors WHERE chunk_id = ?", (chunk_id,))
            row = cursor.fetchone()
            
            if row:
                vector = pickle.loads(row['vector_data'])
                self.vector_cache[chunk_id] = vector
                return vector
            
        except Exception as e:
            self.logger.error(f"ベクトル取得エラー: {e}")
        
        return None
    
    def _calculate_similarity(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """ベクトル間の類似度を計算"""
        try:
            # コサイン類似度
            similarity = cosine_similarity([vector1], [vector2])[0][0]
            return float(similarity)
        except Exception:
            # フォールバック: ユークリッド距離ベース
            try:
                distance = np.linalg.norm(vector1 - vector2)
                similarity = 1.0 / (1.0 + distance)
                return float(similarity)
            except Exception:
                return 0.0
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """IDでチャンクを取得"""
        # キャッシュから取得を試行
        if chunk_id in self.chunk_cache:
            return self.chunk_cache[chunk_id]
        
        # データベースから取得
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT * FROM chunks WHERE id = ?
            """, (chunk_id,))
            row = cursor.fetchone()
            
            if row:
                chunk = dict(row)
                chunk['metadata'] = json.loads(chunk['metadata'])
                self.chunk_cache[chunk_id] = chunk
                return chunk
                
        except Exception as e:
            self.logger.error(f"チャンク取得エラー: {e}")
        
        return None
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """チャンクを削除"""
        try:
            cursor = self.db_connection.cursor()
            
            # ベクトルを削除
            cursor.execute("DELETE FROM vectors WHERE chunk_id = ?", (chunk_id,))
            
            # チャンクを削除
            cursor.execute("DELETE FROM chunks WHERE id = ?", (chunk_id,))
            
            self.db_connection.commit()
            
            # キャッシュからも削除
            self.chunk_cache.pop(chunk_id, None)
            self.vector_cache.pop(chunk_id, None)
            
            self.logger.info(f"チャンク削除完了: {chunk_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"チャンク削除エラー: {e}")
            return False
    
    def update_chunk(self, chunk_id: str, updated_chunk: Dict[str, Any]) -> bool:
        """チャンクを更新"""
        try:
            # 既存チャンクの確認
            if not self._chunk_exists(chunk_id):
                self.logger.warning(f"更新対象のチャンクが見つかりません: {chunk_id}")
                return False
            
            # 新しいベクトルを生成
            new_vector = self._generate_vector(updated_chunk)
            
            # データベースを更新
            cursor = self.db_connection.cursor()
            
            content = updated_chunk.get('content', '')
            content_hash = hashlib.md5(content.encode()).hexdigest()
            metadata = {
                'function_name': updated_chunk.get('function_name', ''),
                'class_name': updated_chunk.get('class_name', ''),
                'docstring': updated_chunk.get('docstring', ''),
                'keywords': updated_chunk.get('keywords', []),
                'parameters': updated_chunk.get('parameters', [])
            }
            
            cursor.execute("""
                UPDATE chunks SET 
                    content = ?, content_hash = ?, metadata = ?, 
                    file_path = ?, language = ?, chunk_type = ?,
                    line_start = ?, line_end = ?, updated_at = ?
                WHERE id = ?
            """, (
                content,
                content_hash,
                json.dumps(metadata, ensure_ascii=False),
                updated_chunk.get('file_path', ''),
                updated_chunk.get('language', 'text'),
                updated_chunk.get('type', 'unknown'),
                updated_chunk.get('line_start', 0),
                updated_chunk.get('line_end', 0),
                datetime.now().isoformat(),
                chunk_id
            ))
            
            # ベクトルを更新
            if new_vector is not None:
                self._save_vector(chunk_id, new_vector)
            
            self.db_connection.commit()
            
            # キャッシュを更新
            self.chunk_cache[chunk_id] = updated_chunk
            
            if new_vector is not None:
                self.vector_cache[chunk_id] = new_vector
            
            self.logger.info(f"チャンク更新完了: {chunk_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"チャンク更新エラー: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """ストアの統計情報を取得"""
        try:
            cursor = self.db_connection.cursor()
            
            # 基本統計
            cursor.execute("SELECT COUNT(*) as total_chunks FROM chunks")
            total_chunks = cursor.fetchone()['total_chunks']
            
            cursor.execute("SELECT COUNT(*) as total_vectors FROM vectors")
            total_vectors = cursor.fetchone()['total_vectors']
            
            # 言語別統計
            cursor.execute("""
                SELECT language, COUNT(*) as count 
                FROM chunks 
                GROUP BY language 
                ORDER BY count DESC
            """)
            language_stats = dict(cursor.fetchall())
            
            # タイプ別統計
            cursor.execute("""
                SELECT chunk_type, COUNT(*) as count 
                FROM chunks 
                GROUP BY chunk_type 
                ORDER BY count DESC
            """)
            type_stats = dict(cursor.fetchall())
            
            # ファイル別統計
            cursor.execute("""
                SELECT file_path, COUNT(*) as count 
                FROM chunks 
                GROUP BY file_path 
                ORDER BY count DESC 
                LIMIT 10
            """)
            file_stats = dict(cursor.fetchall())
            
            # ベクトル次元統計
            cursor.execute("""
                SELECT dimension, COUNT(*) as count 
                FROM vectors 
                GROUP BY dimension
            """)
            dimension_stats = dict(cursor.fetchall())
            
            return {
                'total_chunks': total_chunks,
                'total_vectors': total_vectors,
                'language_distribution': language_stats,
                'type_distribution': type_stats,
                'top_files': file_stats,
                'vector_dimensions': dimension_stats,
                'cache_size': {
                    'chunks': len(self.chunk_cache),
                    'vectors': len(self.vector_cache)
                },
                'store_path': str(self.store_path),
                'embedding_dim': self.embedding_dim,
                'use_tfidf': self.use_tfidf,
                'use_code_features': self.use_code_features
            }
            
        except Exception as e:
            self.logger.error(f"統計情報取得エラー: {e}")
            return {}
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self.chunk_cache.clear()
        self.vector_cache.clear()
        self.logger.info("キャッシュをクリアしました")
    
    def rebuild_vectors(self) -> bool:
        """全ベクトルを再構築"""
        try:
            self.logger.info("ベクトル再構築を開始します...")
            
            # 既存のベクトルを削除
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM vectors")
            
            # 全チャンクを取得
            cursor.execute("SELECT id, content, metadata, file_path, language, chunk_type, line_start, line_end FROM chunks")
            rows = cursor.fetchall()
            
            # ベクトライザーをリセット
            self._initialize_vectorizers()
            self.vector_cache.clear()
            
            # チャンクを再構築
            chunks = []
            for row in rows:
                chunk = {
                    'content': row['content'],
                    'file_path': row['file_path'],
                    'language': row['language'],
                    'type': row['chunk_type'],
                    'line_start': row['line_start'],
                    'line_end': row['line_end']
                }
                
                # メタデータを復元
                try:
                    metadata = json.loads(row['metadata'])
                    chunk.update(metadata)
                except:
                    pass
                
                chunks.append((row['id'], chunk))
            
            # TF-IDFベクトル化（一括処理）
            if self.use_tfidf and chunks:
                texts = []
                chunk_ids = []
                
                for chunk_id, chunk in chunks:
                    processed_text = self._preprocess_text_for_tfidf(chunk['content'])
                    texts.append(processed_text)
                    chunk_ids.append(chunk_id)
                
                # TF-IDFベクトル化
                tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
                
                # 次元削減
                if self.svd_reducer:
                    reduced_vectors = self.svd_reducer.fit_transform(tfidf_matrix)
                else:
                    reduced_vectors = tfidf_matrix.toarray()
                
                # ベクトルを保存
                for chunk_id, vector in zip(chunk_ids, reduced_vectors):
                    self._save_vector(chunk_id, vector)
                    self.vector_cache[chunk_id] = vector
            
            # 非TF-IDFベクトル化
            else:
                for chunk_id, chunk in chunks:
                    vector = self._generate_vector(chunk)
                    if vector is not None:
                        self._save_vector(chunk_id, vector)
                        self.vector_cache[chunk_id] = vector
            
            self.db_connection.commit()
            self.logger.info(f"ベクトル再構築完了: {len(chunks)} チャンク")
            return True
            
        except Exception as e:
            self.logger.error(f"ベクトル再構築エラー: {e}")
            return False
    
    def export_data(self, export_path: str) -> bool:
        """データをエクスポート"""
        try:
            cursor = self.db_connection.cursor()
            
            # チャンクデータを取得
            cursor.execute("""
                SELECT c.*, v.vector_data, v.vector_type, v.dimension
                FROM chunks c
                LEFT JOIN vectors v ON c.id = v.chunk_id
            """)
            rows = cursor.fetchall()
            
            export_data = {
                'metadata': {
                    'export_timestamp': datetime.now().isoformat(),
                    'total_chunks': len(rows),
                    'store_config': {
                        'embedding_dim': self.embedding_dim,
                        'use_tfidf': self.use_tfidf,
                        'use_code_features': self.use_code_features
                    }
                },
                'chunks': []
            }
            
            for row in rows:
                chunk_data = {
                    'id': row['id'],
                    'content': row['content'],
                    'content_hash': row['content_hash'],
                    'metadata': json.loads(row['metadata']),
                    'file_path': row['file_path'],
                    'language': row['language'],
                    'chunk_type': row['chunk_type'],
                    'line_start': row['line_start'],
                    'line_end': row['line_end'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                
                # ベクトルデータ（バイナリなので除外）
                if row['vector_data']:
                    chunk_data['has_vector'] = True
                    chunk_data['vector_type'] = row['vector_type']
                    chunk_data['vector_dimension'] = row['dimension']
                else:
                    chunk_data['has_vector'] = False
                
                export_data['chunks'].append(chunk_data)
            
            # JSONファイルに保存
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"データエクスポート完了: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"データエクスポートエラー: {e}")
            return False
    
    def import_data(self, import_path: str) -> bool:
        """データをインポート"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            chunks_data = import_data.get('chunks', [])
            
            # 既存データのクリア（オプション）
            # cursor = self.db_connection.cursor()
            # cursor.execute("DELETE FROM vectors")
            # cursor.execute("DELETE FROM chunks")
            
            imported_count = 0
            for chunk_data in chunks_data:
                # チャンクを再構築
                chunk = {
                    'content': chunk_data['content'],
                    'file_path': chunk_data['file_path'],
                    'language': chunk_data['language'],
                    'type': chunk_data['chunk_type'],
                    'line_start': chunk_data['line_start'],
                    'line_end': chunk_data['line_end']
                }
                chunk.update(chunk_data['metadata'])
                
                # チャンクを追加
                chunk_id = self._add_single_chunk(chunk)
                if chunk_id:
                    imported_count += 1
            
            # ベクトルを再構築
            if imported_count > 0:
                self._retrain_vectorizers()
            
            self.logger.info(f"データインポート完了: {imported_count} チャンク")
            return True
            
        except Exception as e:
            self.logger.error(f"データインポートエラー: {e}")
            return False
    
    def search_by_metadata(self, 
                          metadata_filters: Dict[str, Any],
                          top_k: int = 10) -> List[SearchResult]:
        """メタデータによる検索"""
        try:
            cursor = self.db_connection.cursor()
            
            # 全チャンクを取得してフィルタリング
            cursor.execute("SELECT * FROM chunks")
            rows = cursor.fetchall()
            
            matching_chunks = []
            for row in rows:
                try:
                    metadata = json.loads(row['metadata'])
                    
                    # フィルター条件をチェック
                    match = True
                    for key, value in metadata_filters.items():
                        if key not in metadata:
                            match = False
                            break
                        
                        if isinstance(value, str):
                            if value.lower() not in str(metadata[key]).lower():
                                match = False
                                break
                        elif metadata[key] != value:
                            match = False
                            break
                    
                    if match:
                        result = SearchResult(
                            chunk_id=row['id'],
                            content=row['content'],
                            metadata=metadata,
                            similarity_score=1.0,  # メタデータ検索では固定
                            file_path=row['file_path'],
                            line_start=row['line_start'],
                            line_end=row['line_end']
                        )
                        matching_chunks.append(result)
                
                except Exception:
                    continue
            
            return matching_chunks[:top_k]
            
        except Exception as e:
            self.logger.error(f"メタデータ検索エラー: {e}")
            return []
    
    def get_similar_chunks(self, 
                          chunk_id: str, 
                          top_k: int = 5,
                          exclude_same_file: bool = False) -> List[SearchResult]:
        """指定されたチャンクに類似するチャンクを検索"""
        try:
            # 対象チャンクを取得
            target_chunk = self.get_chunk_by_id(chunk_id)
            if not target_chunk:
                return []
            
            # 対象チャンクのベクトルを取得
            target_vector = self._get_chunk_vector(chunk_id)
            if target_vector is None:
                return []
            
            # 候補チャンクを取得
            candidates = self._get_candidate_chunks()
            
            # 類似度計算
            similarities = []
            for candidate_id, chunk_data in candidates:
                # 自分自身は除外
                if candidate_id == chunk_id:
                    continue
                
                # 同じファイルを除外するオプション
                if exclude_same_file and chunk_data['file_path'] == target_chunk['file_path']:
                    continue
                
                vector = self._get_chunk_vector(candidate_id)
                if vector is not None:
                    similarity = self._calculate_similarity(target_vector, vector)
                    similarities.append((candidate_id, similarity, chunk_data))
            
            # 類似度順にソート
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 結果の構築
            results = []
            for candidate_id, similarity, chunk_data in similarities[:top_k]:
                result = SearchResult(
                    chunk_id=candidate_id,
                    content=chunk_data['content'],
                    metadata=json.loads(chunk_data['metadata']),
                    similarity_score=similarity,
                    file_path=chunk_data['file_path'],
                    line_start=chunk_data['line_start'],
                    line_end=chunk_data['line_end']
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"類似チャンク検索エラー: {e}")
            return []
    
    def close(self):
        """リソースのクリーンアップ"""
        try:
            if self.db_connection:
                self.db_connection.close()
            
            self.clear_cache()
            self.logger.info("VectorStoreを閉じました")
            
        except Exception as e:
            self.logger.error(f"クローズエラー: {e}")
    
    def __enter__(self):
        """コンテキストマネージャー対応"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー対応"""
        self.close()
    
    def __str__(self) -> str:
        stats = self.get_statistics()
        return f"VectorStore(chunks={stats.get('total_chunks', 0)}, vectors={stats.get('total_vectors', 0)})"
    
    def __repr__(self) -> str:
        return self.__str__()


# 使用例とテスト関数
def example_usage():
    """VectorStoreの使用例"""
    
    # VectorStoreの初期化
    with VectorStore("example_vector_store.db", embedding_dim=200) as store:
        
        # サンプルチャンクの追加
        sample_chunks = [
            {
                'content': '''def calculate_fibonacci(n):
    """フィボナッチ数列のn番目を計算"""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)''',
                'file_path': 'math_utils.py',
                'language': 'python',
                'type': 'function',
                'function_name': 'calculate_fibonacci',
                'line_start': 1,
                'line_end': 5,
                'docstring': 'フィボナッチ数列のn番目を計算',
                'keywords': ['fibonacci', 'recursive', 'math']
            },
            {
                'content': '''def factorial(n):
    """階乗を計算する関数"""
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)''',
                'file_path': 'math_utils.py',
                'language': 'python',
                'type': 'function',
                'function_name': 'factorial',
                'line_start': 7,
                'line_end': 11,
                'docstring': '階乗を計算する関数',
                'keywords': ['factorial', 'recursive', 'math']
            },
            {
                'content': '''class Calculator:
    """基本的な計算機クラス"""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result''',
                'file_path': 'calculator.py',
                'language': 'python',
                'type': 'class',
                'class_name': 'Calculator',
                'line_start': 1,
                'line_end': 10,
                'docstring': '基本的な計算機クラス',
                'keywords': ['calculator', 'math', 'class']
            }
        ]
        
        # チャンクを追加
        print("=== チャンクの追加 ===")
        added_ids = store.add_chunks(sample_chunks)
        print(f"追加されたチャンク数: {len(added_ids)}")
        
        # 統計情報の表示
        print("\n=== 統計情報 ===")
        stats = store.get_statistics()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # 類似検索のテスト
        print("\n=== 類似検索テスト ===")
        search_queries = [
            "再帰的な数学関数",
            "計算機クラス",
            "フィボナッチ数列"
        ]
        
        for query in search_queries:
            print(f"\nクエリ: '{query}'")
            results = store.search_similar(query, top_k=3)
            
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.file_path} (類似度: {result.similarity_score:.3f})")
                print(f"     関数: {result.metadata.get('function_name', 'N/A')}")
                print(f"     内容: {result.content[:100]}...")
        
        # メタデータ検索のテスト
        print("\n=== メタデータ検索テスト ===")
        metadata_results = store.search_by_metadata({
            'keywords': 'recursive'
        })
        
        print(f"再帰関数の検索結果: {len(metadata_results)} 件")
        for result in metadata_results:
            print(f"  - {result.metadata.get('function_name', 'N/A')} in {result.file_path}")
        
        # 類似チャンク検索のテスト
        if added_ids:
            print("\n=== 類似チャンク検索テスト ===")
            similar_results = store.get_similar_chunks(added_ids[0], top_k=2)
            print(f"類似チャンク: {len(similar_results)} 件")
            for result in similar_results:
                print(f"  - {result.file_path} (類似度: {result.similarity_score:.3f})")


if __name__ == "__main__":
    example_usage()

