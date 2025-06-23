# src/llm/base_llm.py
"""
ベースLLMクラスモジュール
全てのLLMクライアントの基底クラスを定義
共通インターフェースと基本機能を提供
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, AsyncGenerator, Generator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import time
import asyncio
from pathlib import Path

from ..core.logger import get_logger
from ..core.config_manager import get_config
from ..core.event_system import get_event_system, Event
from ..utils.validation_utils import ValidationUtils
from ..utils.text_utils import TextUtils

logger = get_logger(__name__)

class LLMRole(Enum):
    """LLMロール定義"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

class LLMStatus(Enum):
    """LLM状態定義"""
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"
    UNAVAILABLE = "unavailable"

@dataclass
class LLMMessage:
    """LLMメッセージクラス"""
    role: LLMRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'role': self.role.value,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMMessage':
        """辞書からメッセージを作成"""
        return cls(
            role=LLMRole(data['role']),
            content=data['content'],
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            metadata=data.get('metadata', {})
        )

@dataclass
class LLMResponse:
    """LLM応答クラス"""
    content: str
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""
    response_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'content': self.content,
            'model': self.model,
            'usage': self.usage,
            'finish_reason': self.finish_reason,
            'response_time': self.response_time,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMResponse':
        """辞書から応答を作成"""
        return cls(
            content=data['content'],
            model=data.get('model', ''),
            usage=data.get('usage', {}),
            finish_reason=data.get('finish_reason', ''),
            response_time=data.get('response_time', 0.0),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            metadata=data.get('metadata', {})
        )

@dataclass
class LLMConfig:
    """LLM設定クラス"""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)
    system_prompt: str = ""
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'top_p': self.top_p,
            'frequency_penalty': self.frequency_penalty,
            'presence_penalty': self.presence_penalty,
            'stop_sequences': self.stop_sequences,
            'system_prompt': self.system_prompt,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'retry_delay': self.retry_delay
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        """辞書から設定を作成"""
        return cls(
            model=data.get('model', ''),
            temperature=data.get('temperature', 0.7),
            max_tokens=data.get('max_tokens', 1000),
            top_p=data.get('top_p', 1.0),
            frequency_penalty=data.get('frequency_penalty', 0.0),
            presence_penalty=data.get('presence_penalty', 0.0),
            stop_sequences=data.get('stop_sequences', []),
            system_prompt=data.get('system_prompt', ''),
            timeout=data.get('timeout', 30.0),
            retry_count=data.get('retry_count', 3),
            retry_delay=data.get('retry_delay', 1.0)
        )

class LLMMetrics:
    """LLMメトリクス管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.reset()
    
    def reset(self):
        """メトリクスをリセット"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens = 0
        self.total_response_time = 0.0
        self.start_time = datetime.now()
    
    def record_request(self, success: bool, tokens: int = 0, response_time: float = 0.0):
        """リクエストを記録"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_tokens += tokens
        self.total_response_time += response_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.successful_requests / max(self.total_requests, 1),
            'total_tokens': self.total_tokens,
            'average_tokens_per_request': self.total_tokens / max(self.successful_requests, 1),
            'total_response_time': self.total_response_time,
            'average_response_time': self.total_response_time / max(self.successful_requests, 1),
            'requests_per_minute': (self.total_requests / max(uptime, 1)) * 60,
            'uptime_seconds': uptime
        }

class BaseLLM(ABC):
    """ベースLLMクラス"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初期化
        
        Args:
            config: LLM設定
        """
        self.config = config or LLMConfig()
        self.status = LLMStatus.IDLE
        self.metrics = LLMMetrics()
        self.conversation_history: List[LLMMessage] = []
        
        # ユーティリティ
        self.validation_utils = ValidationUtils()
        self.text_utils = TextUtils()
        
        # イベントシステム
        self.event_system = get_event_system()
        
        # ロガー
        self.logger = get_logger(self.__class__.__name__)
        
        # 設定を検証
        self._validate_config()
        
        self.logger.info(f"{self.__class__.__name__}を初期化しました")
    
    @abstractmethod
    async def generate_async(self, 
                           messages: List[LLMMessage], 
                           config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        非同期でテキストを生成
        
        Args:
            messages: メッセージリスト
            config: 生成設定
            
        Returns:
            LLMResponse: 生成結果
        """
        pass
    
    @abstractmethod
    async def generate_stream_async(self, 
                                  messages: List[LLMMessage], 
                                  config: Optional[LLMConfig] = None) -> AsyncGenerator[str, None]:
        """
        非同期でストリーミング生成
        
        Args:
            messages: メッセージリスト
            config: 生成設定
            
        Yields:
            str: 生成されたテキストの断片
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        LLMが利用可能かチェック
        
        Returns:
            bool: 利用可能フラグ
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        モデル情報を取得
        
        Returns:
            Dict[str, Any]: モデル情報
        """
        pass
    
    def generate(self, 
                messages: List[LLMMessage], 
                config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        同期でテキストを生成
        
        Args:
            messages: メッセージリスト
            config: 生成設定
            
        Returns:
            LLMResponse: 生成結果
        """
        try:
            # 新しいイベントループを作成して実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.generate_async(messages, config))
            finally:
                loop.close()
        except Exception as e:
            self.logger.error(f"同期生成エラー: {e}")
            raise
    
    def generate_stream(self, 
                       messages: List[LLMMessage], 
                       config: Optional[LLMConfig] = None) -> Generator[str, None, None]:
        """
        同期でストリーミング生成
        
        Args:
            messages: メッセージリスト
            config: 生成設定
            
        Yields:
            str: 生成されたテキストの断片
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async_gen = self.generate_stream_async(messages, config)
                
                async def run_async_generator():
                    async for chunk in async_gen:
                        yield chunk
                
                # 非同期ジェネレーターを同期的に実行
                async def collect_chunks():
                    chunks = []
                    async for chunk in async_gen:
                        chunks.append(chunk)
                    return chunks
                
                chunks = loop.run_until_complete(collect_chunks())
                for chunk in chunks:
                    yield chunk
                    
            finally:
                loop.close()
        except Exception as e:
            self.logger.error(f"同期ストリーミング生成エラー: {e}")
            raise
    
    async def chat_async(self, 
                        message: str, 
                        role: LLMRole = LLMRole.USER,
                        config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        非同期でチャット
        
        Args:
            message: メッセージ
            role: メッセージロール
            config: 生成設定
            
        Returns:
            LLMResponse: 応答
        """
        try:
            # メッセージを履歴に追加
            user_message = LLMMessage(role=role, content=message)
            self.conversation_history.append(user_message)
            
            # システムプロンプトを追加
            messages = []
            effective_config = config or self.config
            
            if effective_config.system_prompt:
                messages.append(LLMMessage(
                    role=LLMRole.SYSTEM, 
                    content=effective_config.system_prompt
                ))
            
            messages.extend(self.conversation_history)
            
            # 生成実行
            response = await self.generate_async(messages, config)
            
            # 応答を履歴に追加
            assistant_message = LLMMessage(
                role=LLMRole.ASSISTANT, 
                content=response.content
            )
            self.conversation_history.append(assistant_message)
            
            return response
            
        except Exception as e:
            self.logger.error(f"チャットエラー: {e}")
            raise
    
    def chat(self, 
            message: str, 
            role: LLMRole = LLMRole.USER,
            config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        同期でチャット
        
        Args:
            message: メッセージ
            role: メッセージロール
            config: 生成設定
            
        Returns:
            LLMResponse: 応答
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.chat_async(message, role, config))
            finally:
                loop.close()
        except Exception as e:
            self.logger.error(f"同期チャットエラー: {e}")
            raise
    
    def clear_conversation(self):
        """会話履歴をクリア"""
        self.conversation_history.clear()
        self.logger.debug("会話履歴をクリアしました")
    
    def get_conversation_history(self) -> List[LLMMessage]:
        """会話履歴を取得"""
        return self.conversation_history.copy()
    
    def set_conversation_history(self, history: List[LLMMessage]):
        """会話履歴を設定"""
        self.conversation_history = history.copy()
    
    def export_conversation(self, file_path: Union[str, Path]) -> bool:
        """
        会話履歴をエクスポート
        
        Args:
            file_path: 出力ファイルパス
            
        Returns:
            bool: エクスポート成功フラグ
        """
        try:
            file_path = Path(file_path)
            
            # 履歴を辞書形式に変換
            history_data = {
                'conversation_history': [msg.to_dict() for msg in self.conversation_history],
                'model_info': self.get_model_info(),
                'config': self.config.to_dict(),
                'exported_at': datetime.now().isoformat()
            }
            
            # JSONファイルとして保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"会話履歴をエクスポートしました: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"会話履歴エクスポートエラー: {e}")
            return False
    
    def import_conversation(self, file_path: Union[str, Path]) -> bool:
        """
        会話履歴をインポート
        
        Args:
            file_path: 入力ファイルパス
            
        Returns:
            bool: インポート成功フラグ
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                self.logger.error(f"ファイルが存在しません: {file_path}")
                return False
            
            # JSONファイルを読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            # 履歴を復元
            self.conversation_history = [
                LLMMessage.from_dict(msg_data) 
                for msg_data in history_data.get('conversation_history', [])
            ]
            
            self.logger.info(f"会話履歴をインポートしました: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"会話履歴インポートエラー: {e}")
            return False
    
    def update_config(self, config: LLMConfig):
        """
        設定を更新
        
        Args:
            config: 新しい設定
        """
        self.config = config
        self._validate_config()
        self.logger.info("設定を更新しました")
    
    def get_config(self) -> LLMConfig:
        """設定を取得"""
        return self.config
    
    def get_status(self) -> LLMStatus:
        """状態を取得"""
        return self.status
    
    def get_metrics(self) -> Dict[str, Any]:
        """メトリクスを取得"""
        return self.metrics.get_statistics()
    
    def reset_metrics(self):
        """メトリクスをリセット"""
        self.metrics.reset()
        self.logger.info("メトリクスをリセットしました")
    
    def _validate_config(self):
        """設定を検証"""
        try:
            # 温度の検証
            if not 0.0 <= self.config.temperature <= 2.0:
                raise ValueError(f"温度は0.0-2.0の範囲で設定してください: {self.config.temperature}")
            
            # トークン数の検証
            if self.config.max_tokens <= 0:
                raise ValueError(f"最大トークン数は正の値で設定してください: {self.config.max_tokens}")
            
            # top_pの検証
            if not 0.0 <= self.config.top_p <= 1.0:
                raise ValueError(f"top_pは0.0-1.0の範囲で設定してください: {self.config.top_p}")
            
            # ペナルティの検証
            if not -2.0 <= self.config.frequency_penalty <= 2.0:
                raise ValueError(f"frequency_penaltyは-2.0-2.0の範囲で設定してください: {self.config.frequency_penalty}")
            
            if not -2.0 <= self.config.presence_penalty <= 2.0:
                raise ValueError(f"presence_penaltyは-2.0-2.0の範囲で設定してください: {self.config.presence_penalty}")
            
            # タイムアウトの検証
            if self.config.timeout <= 0:
                raise ValueError(f"タイムアウトは正の値で設定してください: {self.config.timeout}")
            
            # リトライ設定の検証
            if self.config.retry_count < 0:
                raise ValueError(f"リトライ回数は0以上で設定してください: {self.config.retry_count}")
            
            if self.config.retry_delay < 0:
                raise ValueError(f"リトライ遅延は0以上で設定してください: {self.config.retry_delay}")
            
        except Exception as e:
            self.logger.error(f"設定検証エラー: {e}")
            raise
    
    def _set_status(self, status: LLMStatus):
        """状態を設定"""
        old_status = self.status
        self.status = status
        
        # 状態変更イベントを発行
        self.event_system.emit(Event(
            'llm_status_changed',
            {
                'llm_class': self.__class__.__name__,
                'old_status': old_status.value,
                'new_status': status.value
            }
        ))
    
    def _record_request(self, success: bool, tokens: int = 0, response_time: float = 0.0):
        """リクエストを記録"""
        self.metrics.record_request(success, tokens, response_time)
        
        # メトリクスイベントを発行
        self.event_system.emit(Event(
            'llm_request_completed',
            {
                'llm_class': self.__class__.__name__,
                'success': success,
                'tokens': tokens,
                'response_time': response_time,
                'metrics': self.metrics.get_statistics()
            }
        ))
    
    async def _execute_with_retry(self, 
                                 func, 
                                 *args, 
                                 config: Optional[LLMConfig] = None,
                                 **kwargs):
        """
        リトライ機能付きで関数を実行
        
        Args:
            func: 実行する関数
            *args: 引数
            config: 設定
            **kwargs: キーワード引数
            
        Returns:
            Any: 関数の実行結果
        """
        effective_config = config or self.config
        last_exception = None
        
        for attempt in range(effective_config.retry_count + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"リトライ {attempt}/{effective_config.retry_count}")
                    await asyncio.sleep(effective_config.retry_delay * attempt)
                
                return await func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"実行失敗 (試行 {attempt + 1}): {e}")
                
                if attempt == effective_config.retry_count:
                    break
        
        # 全てのリトライが失敗した場合
        self.logger.error(f"全てのリトライが失敗しました: {last_exception}")
        raise last_exception
    
    def __enter__(self):
        """コンテキストマネージャーエントリー"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーエグジット"""
        # リソースのクリーンアップ
        pass
    
    def __repr__(self) -> str:
        """文字列表現"""
        return f"{self.__class__.__name__}(model={self.config.model}, status={self.status.value})"
