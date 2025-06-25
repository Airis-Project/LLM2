"""
データベース管理モジュール
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from ..core.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """データベース管理クラス"""
    
    def __init__(self, db_path: str = "data/app.db"):
        """
        初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection: Optional[sqlite3.Connection] = None
        logger.info(f"DatabaseManager初期化: {self.db_path}")
    
    def connect(self) -> sqlite3.Connection:
        """データベースに接続"""
        if self.connection is None:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row
            logger.info("データベースに接続しました")
        return self.connection
    
    def disconnect(self):
        """データベースから切断"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("データベースから切断しました")
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """クエリを実行して結果を返す"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.commit()
        return results
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """更新クエリを実行して影響行数を返す"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
    
    def initialize_tables(self):
        """テーブルを初期化"""
        # 基本的なテーブル作成
        tables = [
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
            """
        ]
        
        for table_sql in tables:
            self.execute_update(table_sql)
        
        logger.info("データベーステーブルを初期化しました")
