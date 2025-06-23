# data/examples/demo_code.py
# LLM Code Assistant - デモコードサンプル

"""
LLM Code Assistant - デモコードサンプル

このファイルは、LLM Code Assistantで使用するデモ用のPythonコードサンプルを提供します。
様々なプログラミングパターンや実装例を含んでいます。

作成者: LLM Code Assistant Team
バージョン: 1.0.0
作成日: 2024-01-01
"""

import os
import sys
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union, Callable
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from contextlib import contextmanager
from functools import wraps, lru_cache
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('demo.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# 1. 基本的なクラス定義のデモ
# =============================================================================

@dataclass
class User:
    """
    ユーザー情報を管理するデータクラス
    
    Attributes:
        id: ユーザーID
        name: ユーザー名
        email: メールアドレス
        created_at: 作成日時
        is_active: アクティブ状態
        metadata: 追加情報
    """
    id: int
    name: str
    email: str
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の処理"""
        if not self.email or '@' not in self.email:
            raise ValueError("有効なメールアドレスを入力してください")
        
        # メタデータの初期化
        if 'created_by' not in self.metadata:
            self.metadata['created_by'] = 'system'
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """辞書から User インスタンスを作成"""
        data = data.copy()
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)
    
    def update_metadata(self, key: str, value: Any) -> None:
        """メタデータを更新"""
        self.metadata[key] = value
        logger.info(f"ユーザー {self.name} のメタデータを更新: {key} = {value}")

# =============================================================================
# 2. 抽象基底クラスとインターフェースのデモ
# =============================================================================

class DataProcessor(ABC):
    """
    データ処理の抽象基底クラス
    """
    
    def __init__(self, name: str):
        self.name = name
        self.processed_count = 0
        self._lock = threading.Lock()
    
    @abstractmethod
    def process_item(self, item: Any) -> Any:
        """
        単一アイテムを処理する抽象メソッド
        
        Args:
            item: 処理対象のアイテム
            
        Returns:
            処理結果
        """
        pass
    
    @abstractmethod
    def validate_item(self, item: Any) -> bool:
        """
        アイテムの妥当性を検証する抽象メソッド
        
        Args:
            item: 検証対象のアイテム
            
        Returns:
            妥当性の判定結果
        """
        pass
    
    def process_batch(self, items: List[Any]) -> List[Any]:
        """
        バッチ処理を実行
        
        Args:
            items: 処理対象のアイテムリスト
            
        Returns:
            処理結果のリスト
        """
        results = []
        for item in items:
            try:
                if self.validate_item(item):
                    result = self.process_item(item)
                    results.append(result)
                    with self._lock:
                        self.processed_count += 1
                else:
                    logger.warning(f"無効なアイテムをスキップ: {item}")
            except Exception as e:
                logger.error(f"アイテム処理中にエラーが発生: {item}, エラー: {e}")
                continue
        
        logger.info(f"{self.name}: {len(results)}件のアイテムを処理しました")
        return results

class TextProcessor(DataProcessor):
    """
    テキスト処理の具象クラス
    """
    
    def __init__(self, name: str = "TextProcessor"):
        super().__init__(name)
        self.min_length = 1
        self.max_length = 1000
    
    def validate_item(self, item: Any) -> bool:
        """テキストの妥当性を検証"""
        if not isinstance(item, str):
            return False
        return self.min_length <= len(item) <= self.max_length
    
    def process_item(self, item: str) -> Dict[str, Any]:
        """テキストを処理"""
        return {
            'original': item,
            'length': len(item),
            'word_count': len(item.split()),
            'uppercase': item.upper(),
            'lowercase': item.lower(),
            'title_case': item.title(),
            'processed_at': datetime.now().isoformat()
        }

class NumberProcessor(DataProcessor):
    """
    数値処理の具象クラス
    """
    
    def __init__(self, name: str = "NumberProcessor"):
        super().__init__(name)
        self.min_value = float('-inf')
        self.max_value = float('inf')
    
    def validate_item(self, item: Any) -> bool:
        """数値の妥当性を検証"""
        try:
            num = float(item)
            return self.min_value <= num <= self.max_value
        except (ValueError, TypeError):
            return False
    
    def process_item(self, item: Union[int, float, str]) -> Dict[str, Any]:
        """数値を処理"""
        num = float(item)
        return {
            'original': item,
            'value': num,
            'squared': num ** 2,
            'sqrt': num ** 0.5 if num >= 0 else None,
            'is_positive': num > 0,
            'is_integer': num.is_integer(),
            'processed_at': datetime.now().isoformat()
        }

# =============================================================================
# 3. デコレータのデモ
# =============================================================================

def timer(func: Callable) -> Callable:
    """
    関数の実行時間を測定するデコレータ
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"{func.__name__} の実行時間: {duration:.4f}秒")
    return wrapper

def retry(max_attempts: int = 3, delay: float = 1.0):
    """
    関数の実行をリトライするデコレータ
    
    Args:
        max_attempts: 最大試行回数
        delay: リトライ間隔（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"{func.__name__} の実行に失敗 (試行 {attempt + 1}/{max_attempts}): {e}")
                        if delay > 0:
                            import time
                            time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} の実行に失敗 (最大試行回数に到達): {e}")
            
            raise last_exception
        return wrapper
    return decorator

def validate_types(**type_hints):
    """
    引数の型を検証するデコレータ
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 位置引数の型チェック
            func_args = func.__code__.co_varnames[:func.__code__.co_argcount]
            for i, (arg_name, arg_value) in enumerate(zip(func_args, args)):
                if arg_name in type_hints:
                    expected_type = type_hints[arg_name]
                    if not isinstance(arg_value, expected_type):
                        raise TypeError(
                            f"引数 '{arg_name}' は {expected_type.__name__} 型である必要があります。"
                            f"実際の型: {type(arg_value).__name__}"
                        )
            
            # キーワード引数の型チェック
            for arg_name, arg_value in kwargs.items():
                if arg_name in type_hints:
                    expected_type = type_hints[arg_name]
                    if not isinstance(arg_value, expected_type):
                        raise TypeError(
                            f"引数 '{arg_name}' は {expected_type.__name__} 型である必要があります。"
                            f"実際の型: {type(arg_value).__name__}"
                        )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# =============================================================================
# 4. コンテキストマネージャーのデモ
# =============================================================================

@contextmanager
def database_connection(db_path: str):
    """
    データベース接続のコンテキストマネージャー
    
    Args:
        db_path: データベースファイルのパス
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
        logger.info(f"データベースに接続しました: {db_path}")
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"データベース操作中にエラーが発生: {e}")
        raise
    finally:
        if conn:
            conn.close()
            logger.info("データベース接続を閉じました")

@contextmanager
def temporary_file(suffix: str = '.tmp', prefix: str = 'temp_'):
    """
    一時ファイルのコンテキストマネージャー
    
    Args:
        suffix: ファイルの拡張子
        prefix: ファイル名のプレフィックス
    """
    import tempfile
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(
            mode='w+', 
            suffix=suffix, 
            prefix=prefix, 
            delete=False,
            encoding='utf-8'
        )
        logger.info(f"一時ファイルを作成しました: {temp_file.name}")
        yield temp_file
    finally:
        if temp_file:
            temp_file.close()
            try:
                os.unlink(temp_file.name)
                logger.info(f"一時ファイルを削除しました: {temp_file.name}")
            except OSError as e:
                logger.warning(f"一時ファイルの削除に失敗: {e}")

# =============================================================================
# 5. 非同期処理のデモ
# =============================================================================

class AsyncDataFetcher:
    """
    非同期データ取得クラス
    """
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.session = None
    
    async def fetch_data(self, url: str) -> Dict[str, Any]:
        """
        単一URLからデータを取得
        
        Args:
            url: 取得対象のURL
            
        Returns:
            取得したデータ
        """
        # 実際のHTTPリクエストの代わりにシミュレーション
        await asyncio.sleep(0.1)  # ネットワーク遅延をシミュレート
        
        return {
            'url': url,
            'status': 200,
            'data': f"Data from {url}",
            'timestamp': datetime.now().isoformat(),
            'size': len(url) * 10  # サイズをシミュレート
        }
    
    async def fetch_multiple(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        複数URLから並行してデータを取得
        
        Args:
            urls: 取得対象のURLリスト
            
        Returns:
            取得したデータのリスト
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def fetch_with_semaphore(url: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    return await self.fetch_data(url)
                except Exception as e:
                    logger.error(f"データ取得エラー ({url}): {e}")
                    return {
                        'url': url,
                        'status': 500,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外を処理
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"タスク実行エラー: {result}")
            else:
                processed_results.append(result)
        
        logger.info(f"{len(processed_results)}件のデータを取得しました")
        return processed_results

# =============================================================================
# 6. ファイル操作のデモ
# =============================================================================

class FileManager:
    """
    ファイル操作を管理するクラス
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.cwd()
        self.encoding = 'utf-8'
    
    @timer
    @retry(max_attempts=3, delay=0.5)
    def read_file(self, file_path: Union[str, Path]) -> str:
        """
        ファイルを読み込み
        
        Args:
            file_path: ファイルパス
            
        Returns:
            ファイルの内容
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.base_path / path
        
        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {path}")
        
        try:
            with open(path, 'r', encoding=self.encoding) as f:
                content = f.read()
            logger.info(f"ファイルを読み込みました: {path} ({len(content)}文字)")
            return content
        except UnicodeDecodeError as e:
            logger.error(f"ファイルの文字エンコーディングエラー: {e}")
            raise
    
    @timer
    def write_file(self, file_path: Union[str, Path], content: str, 
                   create_dirs: bool = True) -> None:
        """
        ファイルに書き込み
        
        Args:
            file_path: ファイルパス
            content: 書き込む内容
            create_dirs: ディレクトリを自動作成するか
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.base_path / path
        
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(path, 'w', encoding=self.encoding) as f:
                f.write(content)
            logger.info(f"ファイルに書き込みました: {path} ({len(content)}文字)")
        except Exception as e:
            logger.error(f"ファイル書き込みエラー: {e}")
            raise
    
    def backup_file(self, file_path: Union[str, Path]) -> Path:
        """
        ファイルのバックアップを作成
        
        Args:
            file_path: バックアップ対象のファイルパス
            
        Returns:
            バックアップファイルのパス
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.base_path / path
        
        if not path.exists():
            raise FileNotFoundError(f"バックアップ対象ファイルが見つかりません: {path}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_suffix(f".{timestamp}{path.suffix}.bak")
        
        import shutil
        shutil.copy2(path, backup_path)
        logger.info(f"バックアップを作成しました: {backup_path}")
        return backup_path

# =============================================================================
# 7. データベース操作のデモ
# =============================================================================

class UserRepository:
    """
    ユーザーデータのリポジトリクラス
    """
    
    def __init__(self, db_path: str = "demo.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self) -> None:
        """データベースを初期化"""
        with database_connection(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    metadata TEXT
                )
            ''')
            conn.commit()
            logger.info("データベースを初期化しました")
    
    def create_user(self, user: User) -> int:
        """
        ユーザーを作成
        
        Args:
            user: 作成するユーザー
            
        Returns:
            作成されたユーザーのID
        """
        with database_connection(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO users (name, email, created_at, is_active, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user.name,
                user.email,
                user.created_at.isoformat(),
                1 if user.is_active else 0,
                json.dumps(user.metadata, ensure_ascii=False)
            ))
            conn.commit()
            user_id = cursor.lastrowid
            logger.info(f"ユーザーを作成しました: ID={user_id}, Name={user.name}")
            return user_id
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        ユーザーを取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            ユーザー情報（存在しない場合はNone）
        """
        with database_connection(self.db_path) as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE id = ?', (user_id,)
            ).fetchone()
            
            if row:
                return User(
                    id=row['id'],
                    name=row['name'],
                    email=row['email'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    is_active=bool(row['is_active']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
            return None
    
    def list_users(self, active_only: bool = True) -> List[User]:
        """
        ユーザー一覧を取得
        
        Args:
            active_only: アクティブユーザーのみを取得するか
            
        Returns:
            ユーザーのリスト
        """
        query = 'SELECT * FROM users'
        params = ()
        
        if active_only:
            query += ' WHERE is_active = ?'
            params = (1,)
        
        query += ' ORDER BY created_at DESC'
        
        with database_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            
            users = []
            for row in rows:
                user = User(
                    id=row['id'],
                    name=row['name'],
                    email=row['email'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    is_active=bool(row['is_active']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                users.append(user)
            
            logger.info(f"{len(users)}件のユーザーを取得しました")
            return users

# =============================================================================
# 8. 並行処理のデモ
# =============================================================================

class ConcurrentProcessor:
    """
    並行処理を管理するクラス
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    @timer
    def process_items_concurrent(self, items: List[Any], 
                               processor: Callable[[Any], Any]) -> List[Any]:
        """
        アイテムを並行処理
        
        Args:
            items: 処理対象のアイテムリスト
            processor: 処理関数
            
        Returns:
            処理結果のリスト
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # タスクを投入
            future_to_item = {
                executor.submit(processor, item): item 
                for item in items
            }
            
            # 結果を収集
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"並行処理エラー (item: {item}): {e}")
        
        logger.info(f"並行処理完了: {len(results)}/{len(items)}件成功")
        return results

# =============================================================================
# 9. キャッシュのデモ
# =============================================================================

class DataCache:
    """
    データキャッシュクラス
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        キャッシュからデータを取得
        
        Args:
            key: キャッシュキー
            
        Returns:
            キャッシュされたデータ（存在しない場合はNone）
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # TTLチェック
            if datetime.now() > entry['expires_at']:
                del self._cache[key]
                logger.debug(f"キャッシュが期限切れです: {key}")
                return None
            
            logger.debug(f"キャッシュヒット: {key}")
            return entry['data']
    
    def set(self, key: str, data: Any) -> None:
        """
        データをキャッシュに保存
        
        Args:
            key: キャッシュキー
            data: 保存するデータ
        """
        with self._lock:
            # サイズ制限チェック
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            self._cache[key] = {
                'data': data,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(seconds=self.ttl_seconds)
            }
            logger.debug(f"キャッシュに保存: {key}")
    
    def _evict_oldest(self) -> None:
        """最も古いキャッシュエントリを削除"""
        if not self._cache:
            return
        
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k]['created_at']
        )
        del self._cache[oldest_key]
        logger.debug(f"古いキャッシュを削除: {oldest_key}")
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        with self._lock:
            self._cache.clear()
            logger.info("キャッシュをクリアしました")

# =============================================================================
# 10. 使用例とデモ実行関数
# =============================================================================

@lru_cache(maxsize=128)
def expensive_calculation(n: int) -> int:
    """
    重い計算をシミュレート（キャッシュ付き）
    
    Args:
        n: 計算対象の数値
        
    Returns:
        計算結果
    """
    import time
    time.sleep(0.1)  # 重い処理をシミュレート
    return n * n + n

def demo_basic_usage():
    """基本的な使用例のデモ"""
    logger.info("=== 基本的な使用例のデモ ===")
    
    # ユーザー作成
    user = User(
        id=1,
        name="テストユーザー",
        email="test@example.com"
    )
    user.update_metadata("role", "admin")
    
    print(f"ユーザー情報: {user.to_dict()}")
    
    # データ処理
    text_processor = TextProcessor()
    number_processor = NumberProcessor()
    
    texts = ["Hello World", "Python プログラミング", "データ処理のテスト"]
    numbers = [1, 2.5, "3.14", 100]
    
    text_results = text_processor.process_batch(texts)
    number_results = number_processor.process_batch(numbers)
    
    print(f"テキスト処理結果: {len(text_results)}件")
    print(f"数値処理結果: {len(number_results)}件")

async def demo_async_processing():
    """非同期処理のデモ"""
    logger.info("=== 非同期処理のデモ ===")
    
    fetcher = AsyncDataFetcher(max_concurrent=3)
    urls = [
        "https://api.example.com/data1",
        "https://api.example.com/data2",
        "https://api.example.com/data3",
        "https://api.example.com/data4",
        "https://api.example.com/data5"
    ]
    
    results = await fetcher.fetch_multiple(urls)
    print(f"非同期データ取得結果: {len(results)}件")
    
    for result in results:
        print(f"  - {result['url']}: Status {result['status']}")

def demo_database_operations():
    """データベース操作のデモ"""
    logger.info("=== データベース操作のデモ ===")
    
    repo = UserRepository("demo_users.db")
    
    # ユーザー作成
    users = [
        User(id=0, name="田中太郎", email="tanaka@example.com"),
        User(id=0, name="佐藤花子", email="sato@example.com"),
        User(id=0, name="山田次郎", email="yamada@example.com")
    ]
    
    created_ids = []
    for user in users:
        user_id = repo.create_user(user)
        created_ids.append(user_id)
    
    # ユーザー取得
    all_users = repo.list_users()
    print(f"登録済みユーザー数: {len(all_users)}")
    
    for user in all_users:
        print(f"  - {user.name} ({user.email})")

def demo_concurrent_processing():
    """並行処理のデモ"""
    logger.info("=== 並行処理のデモ ===")
    
    processor = ConcurrentProcessor(max_workers=4)
    
    # 重い計算を並行実行
    numbers = list(range(1, 21))  # 1から20まで
    
    def heavy_calculation(n: int) -> Dict[str, Any]:
        """重い計算をシミュレート"""
        result = expensive_calculation(n)
        return {
            'input': n,
            'result': result,
            'processed_at': datetime.now().isoformat()
        }
    
    results = processor.process_items_concurrent(numbers, heavy_calculation)
    print(f"並行処理結果: {len(results)}件")
    
    # 結果の一部を表示
    for result in results[:5]:
        print(f"  - {result['input']} -> {result['result']}")

def demo_file_operations():
    """ファイル操作のデモ"""
    logger.info("=== ファイル操作のデモ ===")
    
    file_manager = FileManager()
    
    # 一時ファイルでのデモ
    with temporary_file(suffix='.txt', prefix='demo_') as temp_file:
        content = """# デモファイル

これはLLM Code Assistantのデモファイルです。

## 機能一覧
- ファイル読み書き
- バックアップ作成
- エラーハンドリング
- ログ出力

作成日時: {}
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # ファイルに書き込み
        temp_file.write(content)
        temp_file.flush()
        
        # ファイルを読み込み
        read_content = file_manager.read_file(temp_file.name)
        print(f"ファイル読み込み成功: {len(read_content)}文字")
        
        # バックアップ作成
        backup_path = file_manager.backup_file(temp_file.name)
        print(f"バックアップ作成: {backup_path}")

def demo_caching():
    """キャッシュのデモ"""
    logger.info("=== キャッシュのデモ ===")
    
    cache = DataCache(max_size=5, ttl_seconds=10)
    
    # キャッシュにデータを保存
    test_data = [
        ("user:1", {"name": "田中太郎", "age": 30}),
        ("user:2", {"name": "佐藤花子", "age": 25}),
        ("config:app", {"theme": "dark", "language": "ja"}),
        ("stats:daily", {"visits": 1000, "users": 500}),
    ]
    
    for key, data in test_data:
        cache.set(key, data)
        print(f"キャッシュに保存: {key}")
    
    # キャッシュからデータを取得
    for key, _ in test_data:
        cached_data = cache.get(key)
        if cached_data:
            print(f"キャッシュから取得: {key} -> {cached_data}")
        else:
            print(f"キャッシュミス: {key}")

@validate_types(message=str, level=str)
def demo_decorated_function(message: str, level: str = "info") -> None:
    """
    デコレータ付き関数のデモ
    
    Args:
        message: ログメッセージ
        level: ログレベル
    """
    log_levels = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error
    }
    
    log_func = log_levels.get(level.lower(), logger.info)
    log_func(f"デコレータテスト: {message}")

def demo_error_handling():
    """エラーハンドリングのデモ"""
    logger.info("=== エラーハンドリングのデモ ===")
    
    # 型検証エラーのテスト
    try:
        demo_decorated_function(123, "info")  # 型エラーが発生するはず
    except TypeError as e:
        print(f"型検証エラーをキャッチ: {e}")
    
    # ファイル読み込みエラーのテスト
    file_manager = FileManager()
    try:
        file_manager.read_file("存在しないファイル.txt")
    except FileNotFoundError as e:
        print(f"ファイル未発見エラーをキャッチ: {e}")
    
    # リトライ機能のテスト
    @retry(max_attempts=3, delay=0.1)
    def unreliable_function():
        import random
        if random.random() < 0.7:  # 70%の確率で失敗
            raise Exception("ランダムエラー")
        return "成功"
    
    try:
        result = unreliable_function()
        print(f"リトライ成功: {result}")
    except Exception as e:
        print(f"リトライ失敗: {e}")

def run_all_demos():
    """全てのデモを実行"""
    logger.info("LLM Code Assistant - デモコード実行開始")
    
    try:
        # 基本的な使用例
        demo_basic_usage()
        print("-" * 50)
        
        # データベース操作
        demo_database_operations()
        print("-" * 50)
        
        # 並行処理
        demo_concurrent_processing()
        print("-" * 50)
        
        # ファイル操作
        demo_file_operations()
        print("-" * 50)
        
        # キャッシュ
        demo_caching()
        print("-" * 50)
        
        # エラーハンドリング
        demo_error_handling()
        print("-" * 50)
        
        # 非同期処理
        print("非同期処理のデモを実行中...")
        asyncio.run(demo_async_processing())
        
        logger.info("全てのデモが正常に完了しました")
        
    except Exception as e:
        logger.error(f"デモ実行中にエラーが発生: {e}")
        raise

# =============================================================================
# 11. ユーティリティ関数
# =============================================================================

def format_file_size(size_bytes: int) -> str:
    """
    ファイルサイズを人間が読みやすい形式でフォーマット
    
    Args:
        size_bytes: バイト数
        
    Returns:
        フォーマットされたサイズ文字列
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def generate_random_data(count: int = 100) -> List[Dict[str, Any]]:
    """
    テスト用のランダムデータを生成
    
    Args:
        count: 生成するデータ数
        
    Returns:
        ランダムデータのリスト
    """
    import random
    import string
    
    data = []
    for i in range(count):
        item = {
            'id': i + 1,
            'name': ''.join(random.choices(string.ascii_letters, k=10)),
            'value': random.randint(1, 1000),
            'score': round(random.uniform(0, 100), 2),
            'active': random.choice([True, False]),
            'category': random.choice(['A', 'B', 'C', 'D']),
            'created_at': datetime.now() - timedelta(
                days=random.randint(0, 365)
            ),
            'tags': random.sample(['tag1', 'tag2', 'tag3', 'tag4', 'tag5'], 
                                 k=random.randint(1, 3))
        }
        data.append(item)
    
    return data

def benchmark_function(func: Callable, *args, iterations: int = 100, **kwargs) -> Dict[str, Any]:
    """
    関数のベンチマークを実行
    
    Args:
        func: ベンチマーク対象の関数
        *args: 関数の位置引数
        iterations: 実行回数
        **kwargs: 関数のキーワード引数
        
    Returns:
        ベンチマーク結果
    """
    import time
    import statistics
    
    execution_times = []
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            logger.error(f"ベンチマーク実行エラー: {e}")
            continue
        end_time = time.perf_counter()
        execution_times.append(end_time - start_time)
    
    if not execution_times:
        return {"error": "全ての実行が失敗しました"}
    
    return {
        'function_name': func.__name__,
        'iterations': len(execution_times),
        'total_time': sum(execution_times),
        'average_time': statistics.mean(execution_times),
        'median_time': statistics.median(execution_times),
        'min_time': min(execution_times),
        'max_time': max(execution_times),
        'std_deviation': statistics.stdev(execution_times) if len(execution_times) > 1 else 0
    }

def create_project_structure(base_path: str, structure: Dict[str, Any]) -> None:
    """
    プロジェクト構造を作成
    
    Args:
        base_path: ベースディレクトリのパス
        structure: プロジェクト構造の定義
    """
    base = Path(base_path)
    base.mkdir(parents=True, exist_ok=True)
    
    def create_items(current_path: Path, items: Dict[str, Any]):
        for name, config in items.items():
            item_path = current_path / name
            
            if isinstance(config, dict):
                if config.get('type') == 'directory':
                    item_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"ディレクトリを作成: {item_path}")
                    
                    if 'files' in config:
                        create_items(item_path, config['files'])
                elif config.get('type') == 'file':
                    item_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    content = config.get('content', '')
                    if config.get('language') == 'python':
                        content = f"# {item_path.name}\n# {config.get('description', '')}\n\n{content}"
                    
                    with open(item_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"ファイルを作成: {item_path}")
                else:
                    # 辞書だがtype指定がない場合はディレクトリとして扱う
                    item_path.mkdir(parents=True, exist_ok=True)
                    create_items(item_path, config)
            else:
                # 文字列の場合はファイルとして作成
                with open(item_path, 'w', encoding='utf-8') as f:
                    f.write(str(config))
                logger.info(f"ファイルを作成: {item_path}")
    
    create_items(base, structure)

# =============================================================================
# メイン実行部分
# =============================================================================

if __name__ == "__main__":
    print("LLM Code Assistant - デモコードサンプル")
    print("=" * 60)
    
    # コマンドライン引数の処理
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM Code Assistant デモコード")
    parser.add_argument(
        '--demo', 
        choices=['all', 'basic', 'async', 'db', 'concurrent', 'file', 'cache', 'error'],
        default='all',
        help='実行するデモを選択'
    )
    parser.add_argument(
        '--benchmark',
        action='store_true',
        help='ベンチマークを実行'
    )
    parser.add_argument(
        '--generate-data',
        type=int,
        metavar='COUNT',
        help='テストデータを生成'
    )
    
    args = parser.parse_args()
    
    try:
        if args.benchmark:
            # ベンチマークの実行
            print("ベンチマーク実行中...")
            
            # expensive_calculation のベンチマーク
            benchmark_result = benchmark_function(expensive_calculation, 10, iterations=50)
            print(f"expensive_calculation のベンチマーク結果:")
            for key, value in benchmark_result.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.6f}")
                else:
                    print(f"  {key}: {value}")
        
        elif args.generate_data:
            # テストデータの生成
            print(f"{args.generate_data}件のテストデータを生成中...")
            data = generate_random_data(args.generate_data)
            
            # JSONファイルに保存
            output_file = f"test_data_{args.generate_data}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"テストデータを保存しました: {output_file}")
            print(f"ファイルサイズ: {format_file_size(os.path.getsize(output_file))}")
        
        else:
            # デモの実行
            if args.demo == 'all':
                run_all_demos()
            elif args.demo == 'basic':
                demo_basic_usage()
            elif args.demo == 'async':
                asyncio.run(demo_async_processing())
            elif args.demo == 'db':
                demo_database_operations()
            elif args.demo == 'concurrent':
                demo_concurrent_processing()
            elif args.demo == 'file':
                demo_file_operations()
            elif args.demo == 'cache':
                demo_caching()
            elif args.demo == 'error':
                demo_error_handling()
    
    except KeyboardInterrupt:
        print("\n実行が中断されました")
        sys.exit(1)
    except Exception as e:
        logger.error(f"実行エラー: {e}")
        sys.exit(1)
    
    print("\nデモコードの実行が完了しました")

