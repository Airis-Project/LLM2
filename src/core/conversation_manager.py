# src/core/conversation_manager.py
"""
会話管理システム - 対話履歴の管理と文脈維持
"""

import logging
import json
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import uuid

class MessageRole(Enum):
    """メッセージの役割"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class ConversationStatus(Enum):
    """会話の状態"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

@dataclass
class Message:
    """メッセージを表すデータクラス"""
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    tokens: int = 0
    context_used: List[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.context_used is None:
            self.context_used = []
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['role'] = self.role.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """辞書から復元"""
        data = data.copy()
        data['role'] = MessageRole(data['role'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class Conversation:
    """会話を表すデータクラス"""
    id: str
    title: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = None
    total_messages: int = 0
    total_tokens: int = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """辞書から復元"""
        data = data.copy()
        data['status'] = ConversationStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)

class ConversationManager:
    """
    会話管理クラス
    対話履歴の保存、検索、文脈管理を行う
    """
    
    def __init__(self, 
                 db_path: str = "conversations.db",
                 max_context_messages: int = 20,
                 max_context_tokens: int = 4000,
                 auto_archive_days: int = 30):
        """
        初期化
        
        Args:
            db_path: データベースファイルのパス
            max_context_messages: 文脈として保持する最大メッセージ数
            max_context_tokens: 文脈として保持する最大トークン数
            auto_archive_days: 自動アーカイブする日数
        """
        self.logger = logging.getLogger(__name__)
        self.db_path = Path(db_path)
        self.max_context_messages = max_context_messages
        self.max_context_tokens = max_context_tokens
        self.auto_archive_days = auto_archive_days
        
        # データベース接続
        self.db_connection = None
        
        # 現在の会話
        self.current_conversation_id = None
        
        # メッセージキャッシュ
        self.message_cache = {}
        self.conversation_cache = {}
        
        # 初期化
        self._initialize_database()
        
        self.logger.info(f"ConversationManager初期化完了: {db_path}")
    
    def _initialize_database(self):
        """データベースの初期化"""
        try:
            self.db_connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.db_connection.row_factory = sqlite3.Row
            
            self._create_tables()
            
        except Exception as e:
            self.logger.error(f"データベース初期化エラー: {e}")
            raise
    
    def _create_tables(self):
        """データベーステーブルの作成"""
        cursor = self.db_connection.cursor()
        
        # 会話テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT NOT NULL,
                total_messages INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0
            )
        """)
        
        # メッセージテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT NOT NULL,
                tokens INTEGER DEFAULT 0,
                context_used TEXT NOT NULL,
                message_order INTEGER NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations (updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_role ON messages (role)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_order ON messages (conversation_id, message_order)")
        
        self.db_connection.commit()
    
    def create_conversation(self, 
                          title: str = None,
                          metadata: Dict[str, Any] = None) -> str:
        """
        新しい会話を作成
        
        Args:
            title: 会話のタイトル
            metadata: メタデータ
            
        Returns:
            会話ID
        """
        try:
            conversation_id = str(uuid.uuid4())
            now = datetime.now()
            
            if title is None:
                title = f"会話 {now.strftime('%Y-%m-%d %H:%M')}"
            
            conversation = Conversation(
                id=conversation_id,
                title=title,
                status=ConversationStatus.ACTIVE,
                created_at=now,
                updated_at=now,
                metadata=metadata or {}
            )
            
            # データベースに保存
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO conversations (
                    id, title, status, created_at, updated_at, metadata, total_messages, total_tokens
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation.id,
                conversation.title,
                conversation.status.value,
                conversation.created_at.isoformat(),
                conversation.updated_at.isoformat(),
                json.dumps(conversation.metadata, ensure_ascii=False),
                0,
                0
            ))
            
            self.db_connection.commit()
            
            # キャッシュに追加
            self.conversation_cache[conversation_id] = conversation
            
            # 現在の会話として設定
            self.current_conversation_id = conversation_id
            
            self.logger.info(f"新しい会話を作成しました: {conversation_id} - {title}")
            return conversation_id
            
        except Exception as e:
            self.logger.error(f"会話作成エラー: {e}")
            return None
    
    def add_message(self, 
                   role: MessageRole,
                   content: str,
                   conversation_id: str = None,
                   metadata: Dict[str, Any] = None,
                   context_used: List[str] = None) -> str:
        """
        メッセージを追加
        
        Args:
            role: メッセージの役割
            content: メッセージ内容
            conversation_id: 会話ID（Noneの場合は現在の会話）
            metadata: メタデータ
            context_used: 使用されたコンテキストのリスト
            
        Returns:
            メッセージID
        """
        try:
            # 会話IDの決定
            if conversation_id is None:
                if self.current_conversation_id is None:
                    conversation_id = self.create_conversation()
                else:
                    conversation_id = self.current_conversation_id
            
            # メッセージID生成
            message_id = str(uuid.uuid4())
            
            # トークン数の推定
            tokens = self._estimate_tokens(content)
            
            # メッセージ順序の取得
            message_order = self._get_next_message_order(conversation_id)
            
            message = Message(
                id=message_id,
                role=role,
                content=content,
                timestamp=datetime.now(),
                metadata=metadata or {},
                tokens=tokens,
                context_used=context_used or []
            )
            
            # データベースに保存
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO messages (
                    id, conversation_id, role, content, timestamp, metadata, 
                    tokens, context_used, message_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                conversation_id,
                message.role.value,
                message.content,
                message.timestamp.isoformat(),
                json.dumps(message.metadata, ensure_ascii=False),
                message.tokens,
                json.dumps(message.context_used),
                message_order
            ))
            
            # 会話の統計を更新
            self._update_conversation_stats(conversation_id, tokens)
            
            self.db_connection.commit()
            
            # キャッシュに追加
            cache_key = f"{conversation_id}:{message_id}"
            self.message_cache[cache_key] = message
            
            self.logger.debug(f"メッセージを追加しました: {message_id}")
            return message_id
            
        except Exception as e:
            self.logger.error(f"メッセージ追加エラー: {e}")
            return None
    
    def get_conversation_history(self, 
                               conversation_id: str = None,
                               limit: int = None,
                               include_system: bool = False) -> List[Message]:
        """
        会話履歴を取得
        
        Args:
            conversation_id: 会話ID（Noneの場合は現在の会話）
            limit: 取得するメッセージ数の上限
            include_system: システムメッセージを含めるか
            
        Returns:
            メッセージのリスト
        """
        try:
            if conversation_id is None:
                conversation_id = self.current_conversation_id
            
            if conversation_id is None:
                return []
            
            cursor = self.db_connection.cursor()
            
            # クエリの構築
            query = """
                SELECT * FROM messages 
                WHERE conversation_id = ?
            """
            params = [conversation_id]
            
            if not include_system:
                query += " AND role != ?"
                params.append(MessageRole.SYSTEM.value)
            
            query += " ORDER BY message_order ASC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                message = Message(
                    id=row['id'],
                    role=MessageRole(row['role']),
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    metadata=json.loads(row['metadata']),
                    tokens=row['tokens'],
                    context_used=json.loads(row['context_used'])
                )
                messages.append(message)
            
            return messages
            
        except Exception as e:
            self.logger.error(f"会話履歴取得エラー: {e}")
            return []
    
    def get_context_messages(self, 
                           conversation_id: str = None,
                           max_messages: int = None,
                           max_tokens: int = None) -> List[Message]:
        """
        文脈として使用するメッセージを取得
        
        Args:
            conversation_id: 会話ID
            max_messages: 最大メッセージ数
            max_tokens: 最大トークン数
            
        Returns:
            文脈メッセージのリスト
        """
        if max_messages is None:
            max_messages = self.max_context_messages
        if max_tokens is None:
            max_tokens = self.max_context_tokens
        
        # 全履歴を取得
        all_messages = self.get_conversation_history(conversation_id)
        
        # 最新のメッセージから逆順で選択
        context_messages = []
        total_tokens = 0
        
        for message in reversed(all_messages):
            # システムメッセージはスキップ
            if message.role == MessageRole.SYSTEM:
                continue
            
            # トークン数とメッセージ数の制限をチェック
            if (len(context_messages) >= max_messages or 
                total_tokens + message.tokens > max_tokens):
                break
            
            context_messages.append(message)
            total_tokens += message.tokens
        
        # 元の順序に戻す
        context_messages.reverse()
        
        return context_messages
    
    def search_messages(self, 
                       query: str,
                       conversation_id: str = None,
                       role_filter: MessageRole = None,
                       date_from: datetime = None,
                       date_to: datetime = None,
                       limit: int = 50) -> List[Message]:
        """
        メッセージを検索
        
        Args:
            query: 検索クエリ
            conversation_id: 会話ID（Noneの場合は全会話）
            role_filter: 役割フィルター
            date_from: 開始日時
            date_to: 終了日時
            limit: 結果の上限
            
        Returns:
            検索結果のメッセージリスト
        """
        try:
            cursor = self.db_connection.cursor()
            
            # クエリの構築
            sql_query = "SELECT * FROM messages WHERE content LIKE ?"
            params = [f"%{query}%"]
            
            if conversation_id:
                sql_query += " AND conversation_id = ?"
                params.append(conversation_id)
            
            if role_filter:
                sql_query += " AND role = ?"
                params.append(role_filter.value)
            
            if date_from:
                sql_query += " AND timestamp >= ?"
                params.append(date_from.isoformat())
            
            if date_to:
                sql_query += " AND timestamp <= ?"
                params.append(date_to.isoformat())
            
            sql_query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                message = Message(
                    id=row['id'],
                    role=MessageRole(row['role']),
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    metadata=json.loads(row['metadata']),
                    tokens=row['tokens'],
                    context_used=json.loads(row['context_used'])
                )
                messages.append(message)
            
            return messages
            
        except Exception as e:
            self.logger.error(f"メッセージ検索エラー: {e}")
            return []
    
    def get_conversations(self, 
                         status_filter: ConversationStatus = None,
                         limit: int = 100,
                         offset: int = 0) -> List[Conversation]:
        """
        会話一覧を取得
        
        Args:
            status_filter: 状態フィルター
            limit: 取得数の上限
            offset: オフセット
            
        Returns:
            会話のリスト
        """
        try:
            cursor = self.db_connection.cursor()
            
            query = "SELECT * FROM conversations"
            params = []
            
            if status_filter:
                query += " WHERE status = ?"
                params.append(status_filter.value)
            
            query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            conversations = []
            for row in rows:
                conversation = Conversation(
                    id=row['id'],
                    title=row['title'],
                    status=ConversationStatus(row['status']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    metadata=json.loads(row['metadata']),
                    total_messages=row['total_messages'],
                    total_tokens=row['total_tokens']
                )
                conversations.append(conversation)
            
            return conversations
            
        except Exception as e:
            self.logger.error(f"会話一覧取得エラー: {e}")
            return []
    
    def update_conversation(self, 
                          conversation_id: str,
                          title: str = None,
                          status: ConversationStatus = None,
                          metadata: Dict[str, Any] = None) -> bool:
        """
        会話情報を更新
        
        Args:
            conversation_id: 会話ID
            title: 新しいタイトル
            status: 新しい状態
            metadata: 新しいメタデータ
            
        Returns:
            更新成功フラグ
        """
        try:
            cursor = self.db_connection.cursor()
            
            # 現在の会話情報を取得
            cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
            row = cursor.fetchone()
            
            if not row:
                self.logger.warning(f"会話が見つかりません: {conversation_id}")
                return False
            
            # 更新データの準備
            updates = []
            params = []
            
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            
            if status is not None:
                updates.append("status = ?")
                params.append(status.value)
            
            if metadata is not None:
                updates.append("metadata = ?")
                params.append(json.dumps(metadata, ensure_ascii=False))
            
            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(conversation_id)
                
                query = f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                self.db_connection.commit()
                
                # キャッシュを更新
                if conversation_id in self.conversation_cache:
                    conversation = self.conversation_cache[conversation_id]
                    if title is not None:
                        conversation.title = title
                    if status is not None:
                        conversation.status = status
                    if metadata is not None:
                        conversation.metadata = metadata
                    conversation.updated_at = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"会話更新エラー: {e}")
            return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        会話を削除
        
        Args:
            conversation_id: 会話ID
            
        Returns:
            削除成功フラグ
        """
        try:
            cursor = self.db_connection.cursor()
            
            # メッセージを削除
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            
            # 会話を削除
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            
            self.db_connection.commit()
            
            # キャッシュから削除
            self.conversation_cache.pop(conversation_id, None)
            
            # 現在の会話だった場合はクリア
            if self.current_conversation_id == conversation_id:
                self.current_conversation_id = None
            
            # メッセージキャッシュからも削除
            keys_to_remove = [key for key in self.message_cache.keys() if key.startswith(f"{conversation_id}:")]
            for key in keys_to_remove:
                del self.message_cache[key]
            
            self.logger.info(f"会話を削除しました: {conversation_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"会話削除エラー: {e}")
            return False
    
    def set_current_conversation(self, conversation_id: str) -> bool:
        """
        現在の会話を設定
        
        Args:
            conversation_id: 会話ID
            
        Returns:
            設定成功フラグ
        """
        try:
            # 会話の存在確認
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,))
            
            if cursor.fetchone():
                self.current_conversation_id = conversation_id
                self.logger.info(f"現在の会話を設定しました: {conversation_id}")
                return True
            else:
                self.logger.warning(f"会話が見つかりません: {conversation_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"現在の会話設定エラー: {e}")
            return False
    
    def get_conversation_summary(self, conversation_id: str = None) -> Dict[str, Any]:
        """
        会話の要約情報を取得
        
        Args:
            conversation_id: 会話ID
            
        Returns:
            要約情報の辞書
        """
        try:
            if conversation_id is None:
                conversation_id = self.current_conversation_id
            
            if conversation_id is None:
                return {}
            
            cursor = self.db_connection.cursor()
            
            # 会話情報を取得
            cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
            conv_row = cursor.fetchone()
            
            if not conv_row:
                return {}
            
            # メッセージ統計を取得
            cursor.execute("""
                SELECT 
                    role,
                    COUNT(*) as count,
                    SUM(tokens) as total_tokens,
                    MIN(timestamp) as first_message,
                    MAX(timestamp) as last_message
                FROM messages 
                WHERE conversation_id = ? 
                GROUP BY role
            """, (conversation_id,))
            
            role_stats = {}
            for row in cursor.fetchall():
                role_stats[row['role']] = {
                    'count': row['count'],
                    'total_tokens': row['total_tokens'],
                    'first_message': row['first_message'],
                    'last_message': row['last_message']
                }
            
            # 最近のメッセージを取得
            recent_messages = self.get_conversation_history(conversation_id, limit=5)
            
            summary = {
                'conversation_id': conversation_id,
                'title': conv_row['title'],
                'status': conv_row['status'],
                'created_at': conv_row['created_at'],
                'updated_at': conv_row['updated_at'],
                'total_messages': conv_row['total_messages'],
                'total_tokens': conv_row['total_tokens'],
                'role_statistics': role_stats,
                'recent_messages': [msg.to_dict() for msg in recent_messages[-3:]],
                'metadata': json.loads(conv_row['metadata'])
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"会話要約取得エラー: {e}")
            return {}
    
    def auto_archive_old_conversations(self) -> int:
        """
        古い会話を自動アーカイブ
        
        Returns:
            アーカイブした会話数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.auto_archive_days)
            
            cursor = self.db_connection.cursor()
            cursor.execute("""
                UPDATE conversations 
                SET status = ?, updated_at = ?
                WHERE status = ? AND updated_at < ?
            """, (
                ConversationStatus.ARCHIVED.value,
                datetime.now().isoformat(),
                ConversationStatus.COMPLETED.value,
                cutoff_date.isoformat()
            ))
            
            archived_count = cursor.rowcount
            self.db_connection.commit()
            
            if archived_count > 0:
                self.logger.info(f"古い会話をアーカイブしました: {archived_count} 件")
            
            return archived_count
            
        except Exception as e:
            self.logger.error(f"自動アーカイブエラー: {e}")
            return 0
    
    def export_conversation(self, conversation_id: str, export_path: str) -> bool:
        """
        会話をエクスポート
        
        Args:
            conversation_id: 会話ID
            export_path: エクスポート先パス
            
        Returns:
            エクスポート成功フラグ
        """
        try:
            # 会話情報を取得
            summary = self.get_conversation_summary(conversation_id)
            if not summary:
                return False
            
            # 全メッセージを取得
            messages = self.get_conversation_history(conversation_id, include_system=True)
            
            export_data = {
                'conversation': summary,
                'messages': [msg.to_dict() for msg in messages],
                'exported_at': datetime.now().isoformat(),
                'export_version': '1.0'
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"会話をエクスポートしました: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"会話エクスポートエラー: {e}")
            return False
    
    def _estimate_tokens(self, text: str) -> int:
        """トークン数を推定"""
        # 簡易的な推定（実際のトークナイザーを使用することを推奨）
        words = text.split()
        return int(len(words) * 1.3)  # 英語の場合の概算
    
    def _get_next_message_order(self, conversation_id: str) -> int:
        """次のメッセージ順序を取得"""
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT COALESCE(MAX(message_order), 0) + 1 
            FROM messages 
            WHERE conversation_id = ?
        """, (conversation_id,))
        
        return cursor.fetchone()[0]
    
    def _update_conversation_stats(self, conversation_id: str, tokens: int):
        """会話の統計情報を更新"""
        cursor = self.db_connection.cursor()
        cursor.execute("""
            UPDATE conversations 
            SET total_messages = total_messages + 1,
                total_tokens = total_tokens + ?,
                updated_at = ?
            WHERE id = ?
        """, (tokens, datetime.now().isoformat(), conversation_id))
    
    def get_statistics(self) -> Dict[str, Any]:
        """全体の統計情報を取得"""
        try:
            cursor = self.db_connection.cursor()
            
            # 会話統計
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    SUM(total_messages) as total_messages,
                    SUM(total_tokens) as total_tokens
                FROM conversations 
                GROUP BY status
            """)
            
            conversation_stats = {}
            for row in cursor.fetchall():
                conversation_stats[row['status']] = {
                    'count': row['count'],
                    'total_messages': row['total_messages'] or 0,
                    'total_tokens': row['total_tokens'] or 0
                }
            
            # メッセージ統計
            cursor.execute("""
                SELECT 
                    role,
                    COUNT(*) as count,
                    SUM(tokens) as total_tokens,
                    AVG(tokens) as avg_tokens
                FROM messages 
                GROUP BY role
            """)
            
            message_stats = {}
            for row in cursor.fetchall():
                message_stats[row['role']] = {
                    'count': row['count'],
                    'total_tokens': row['total_tokens'] or 0,
                    'avg_tokens': round(row['avg_tokens'] or 0, 2)
                }
            
            # 日別統計
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as conversations_created
                FROM conversations 
                WHERE created_at >= date('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            
            daily_stats = []
            for row in cursor.fetchall():
                daily_stats.append({
                    'date': row['date'],
                    'conversations_created': row['conversations_created']
                })
            
            # 全体統計
            cursor.execute("SELECT COUNT(*) FROM conversations")
            total_conversations = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(total_tokens) FROM conversations")
            total_tokens = cursor.fetchone()[0] or 0
            
            return {
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'total_tokens': total_tokens,
                'conversation_by_status': conversation_stats,
                'messages_by_role': message_stats,
                'daily_activity': daily_stats,
                'cache_size': {
                    'conversations': len(self.conversation_cache),
                    'messages': len(self.message_cache)
                },
                'current_conversation_id': self.current_conversation_id
            }
            
        except Exception as e:
            self.logger.error(f"統計情報取得エラー: {e}")
            return {}
    
    def cleanup_cache(self, max_age_minutes: int = 60):
        """古いキャッシュエントリをクリーンアップ"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
            
            # メッセージキャッシュのクリーンアップ
            keys_to_remove = []
            for key, message in self.message_cache.items():
                if hasattr(message, 'timestamp') and message.timestamp < cutoff_time:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.message_cache[key]
            
            # 会話キャッシュのクリーンアップ
            keys_to_remove = []
            for key, conversation in self.conversation_cache.items():
                if hasattr(conversation, 'updated_at') and conversation.updated_at < cutoff_time:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.conversation_cache[key]
            
            if keys_to_remove:
                self.logger.info(f"キャッシュクリーンアップ完了: {len(keys_to_remove)} エントリ削除")
            
        except Exception as e:
            self.logger.error(f"キャッシュクリーンアップエラー: {e}")
    
    def get_conversation_context_summary(self, conversation_id: str = None) -> str:
        """
        会話の文脈要約を生成
        
        Args:
            conversation_id: 会話ID
            
        Returns:
            文脈要約テキスト
        """
        try:
            context_messages = self.get_context_messages(conversation_id)
            
            if not context_messages:
                return "会話履歴がありません。"
            
            summary_parts = []
            
            # 会話の基本情報
            summary_parts.append(f"会話履歴: {len(context_messages)} メッセージ")
            
            # 主要なトピックの抽出
            user_messages = [msg for msg in context_messages if msg.role == MessageRole.USER]
            if user_messages:
                recent_topics = []
                for msg in user_messages[-3:]:  # 最近の3つのユーザーメッセージ
                    # 簡単なキーワード抽出
                    words = msg.content.split()
                    if len(words) > 5:
                        recent_topics.append(words[:5])  # 最初の5単語
                
                if recent_topics:
                    summary_parts.append("最近のトピック: " + ", ".join([" ".join(topic) for topic in recent_topics]))
            
            # 使用されたコンテキスト
            all_context_used = []
            for msg in context_messages:
                all_context_used.extend(msg.context_used)
            
            unique_context = list(set(all_context_used))
            if unique_context:
                summary_parts.append(f"参照されたファイル: {', '.join(unique_context[:5])}")
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            self.logger.error(f"文脈要約生成エラー: {e}")
            return "文脈要約の生成に失敗しました。"
    
    def merge_conversations(self, source_id: str, target_id: str) -> bool:
        """
        会話をマージ
        
        Args:
            source_id: マージ元の会話ID
            target_id: マージ先の会話ID
            
        Returns:
            マージ成功フラグ
        """
        try:
            cursor = self.db_connection.cursor()
            
            # 両方の会話が存在することを確認
            cursor.execute("SELECT COUNT(*) FROM conversations WHERE id IN (?, ?)", (source_id, target_id))
            if cursor.fetchone()[0] != 2:
                self.logger.error("マージ対象の会話が見つかりません")
                return False
            
            # ソース会話のメッセージを取得
            source_messages = self.get_conversation_history(source_id, include_system=True)
            
            # ターゲット会話の最大メッセージ順序を取得
            cursor.execute("SELECT COALESCE(MAX(message_order), 0) FROM messages WHERE conversation_id = ?", (target_id,))
            max_order = cursor.fetchone()[0]
            
            # メッセージをターゲット会話に移動
            for i, message in enumerate(source_messages):
                cursor.execute("""
                    UPDATE messages 
                    SET conversation_id = ?, message_order = ?
                    WHERE id = ?
                """, (target_id, max_order + i + 1, message.id))
            
            # ターゲット会話の統計を更新
            cursor.execute("""
                UPDATE conversations 
                SET total_messages = (
                    SELECT COUNT(*) FROM messages WHERE conversation_id = ?
                ),
                total_tokens = (
                    SELECT SUM(tokens) FROM messages WHERE conversation_id = ?
                ),
                updated_at = ?
                WHERE id = ?
            """, (target_id, target_id, datetime.now().isoformat(), target_id))
            
            # ソース会話を削除
            cursor.execute("DELETE FROM conversations WHERE id = ?", (source_id,))
            
            self.db_connection.commit()
            
            # キャッシュをクリア
            self.conversation_cache.pop(source_id, None)
            keys_to_remove = [key for key in self.message_cache.keys() if key.startswith(f"{source_id}:")]
            for key in keys_to_remove:
                del self.message_cache[key]
            
            self.logger.info(f"会話をマージしました: {source_id} -> {target_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"会話マージエラー: {e}")
            return False
    
    def close(self):
        """リソースのクリーンアップ"""
        try:
            if self.db_connection:
                self.db_connection.close()
            
            self.message_cache.clear()
            self.conversation_cache.clear()
            
            self.logger.info("ConversationManagerを閉じました")
            
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
        return f"ConversationManager(conversations={stats.get('total_conversations', 0)}, messages={stats.get('total_messages', 0)})"
    
    def __repr__(self) -> str:
        return self.__str__()


    # 使用例とテスト関数
    def example_usage():
        """ConversationManagerの使用例"""
        
        with ConversationManager("example_conversations.db") as manager:
            
            # 新しい会話を作成
            print("=== 会話の作成 ===")
            conv_id = manager.create_conversation(
                title="Pythonプログラミング相談",
                metadata={"topic": "programming", "language": "python"}
            )
            print(f"会話ID: {conv_id}")
            
            # メッセージを追加
            print("\n=== メッセージの追加 ===")
            
            # ユーザーメッセージ
            user_msg_id = manager.add_message(
                role=MessageRole.USER,
                content="Pythonでフィボナッチ数列を計算する関数を作りたいです",
                metadata={"intent": "code_request"}
            )
            print(f"ユーザーメッセージID: {user_msg_id}")
            
            # アシスタントメッセージ
            assistant_msg_id = manager.add_message(
                role=MessageRole.ASSISTANT,
                content="""フィボナッチ数列を計算する関数をいくつかの方法で実装できます：

            ```python
            def fibonacci_recursive(n):
                if n <= 1:
                    return n
                return fibonacci_recursive(n-1) + fibonacci_recursive(n-2)

            def fibonacci_iterative(n):
                if n <= 1:
                    return n
                a, b = 0, 1
                for _ in range(2, n + 1):
                    a, b = b, a + b
                return b
            再帰版は理解しやすいですが、反復版の方が効率的です。""",
            metadata={"code_provided": True, "languages": ["python"]},
            context_used=["math_utils.py", "algorithms.py"]
            )
            print(f"アシスタントメッセージID: {assistant_msg_id}")
                # 会話履歴の取得
            print("\n=== 会話履歴 ===")
            history = manager.get_conversation_history()
            for msg in history:
                print(f"{msg.role.value}: {msg.content[:50]}...")
            
            # 文脈メッセージの取得
            print("\n=== 文脈メッセージ ===")
            context = manager.get_context_messages()
            print(f"文脈メッセージ数: {len(context)}")
            
            # 会話要約
            print("\n=== 会話要約 ===")
            summary = manager.get_conversation_summary()
            print(f"タイトル: {summary['title']}")
            print(f"総メッセージ数: {summary['total_messages']}")
            print(f"総トークン数: {summary['total_tokens']}")
            
            # 追加のユーザー質問
            manager.add_message(
                role=MessageRole.USER,
                content="メモ化を使った最適化版も教えてください"
            )
            
            manager.add_message(
                role=MessageRole.ASSISTANT,
                content="""メモ化を使った最適化版です：
            def fibonacci_memoized(n, memo={}):
            if n in memo:
                return memo[n]
            if n <= 1:
                return n
            memo[n] = fibonacci_memoized(n-1, memo) + fibonacci_memoized(n-2, memo)
            return memo[n]

            # または functools.lru_cache を使用
            from functools import lru_cache

            @lru_cache(maxsize=None)
            def fibonacci_cached(n):
                if n <= 1:
                    return n
                return fibonacci_cached(n-1) + fibonacci_cached(n-2)
            これにより計算済みの値を再利用でき、大幅に高速化されます。""",
            metadata={"optimization": True, "technique": "memoization"}
            )
                # メッセージ検索
            print("\n=== メッセージ検索 ===")
            search_results = manager.search_messages("最適化")
            print(f"検索結果: {len(search_results)} 件")
            for result in search_results:
                print(f"  - {result.content[:30]}...")
            
            # 会話一覧
            print("\n=== 会話一覧 ===")
            conversations = manager.get_conversations()
            for conv in conversations:
                print(f"  - {conv.title} ({conv.status.value}) - {conv.total_messages} messages")
            
            # 統計情報
            print("\n=== 統計情報 ===")
            stats = manager.get_statistics()
            print(f"総会話数: {stats['total_conversations']}")
            print(f"総メッセージ数: {stats['total_messages']}")
            print(f"総トークン数: {stats['total_tokens']}")
            
            # 文脈要約
            print("\n=== 文脈要約 ===")
            context_summary = manager.get_conversation_context_summary()
            print(context_summary)
            
            # 会話のエクスポート
            print("\n=== 会話エクスポート ===")
            export_success = manager.export_conversation(conv_id, "exported_conversation.json")
            print(f"エクスポート成功: {export_success}")
