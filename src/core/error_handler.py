"""
エラーハンドリングシステム
"""
import traceback
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from .exceptions import (
    LLMCodeAssistantError,
    is_recoverable_error,
    format_error_message,
    get_error_category
)
from .logger import get_logger

class ErrorHandler:
    """統合エラーハンドラー"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._error_callbacks: Dict[str, List[Callable]] = {}
        self._error_stats: Dict[str, int] = {}
        self._last_errors: List[Dict[str, Any]] = []
        self._max_error_history = 100
        
    def register_error_callback(self, error_type: str, callback: Callable):
        """
        エラータイプに対するコールバックを登録
        
        Args:
            error_type: エラータイプ名
            callback: コールバック関数
        """
        if error_type not in self._error_callbacks:
            self._error_callbacks[error_type] = []
        self._error_callbacks[error_type].append(callback)
        
    def handle_error(self, 
                    exception: Exception, 
                    context: Optional[Dict[str, Any]] = None,
                    reraise: bool = False) -> bool:
        """
        エラーを処理する
        
        Args:
            exception: 発生した例外
            context: エラーコンテキスト
            reraise: 例外を再発生させるかどうか
            
        Returns:
            bool: エラー処理が成功したかどうか
        """
        try:
            # エラー情報を記録
            error_info = self._create_error_info(exception, context)
            self._record_error(error_info)
            
            # ログ出力
            self._log_error(exception, context)
            
            # コールバック実行
            self._execute_callbacks(exception, context)
            
            # 回復可能エラーの場合の処理
            if is_recoverable_error(exception):
                self.logger.info(f"回復可能エラーを検出: {type(exception).__name__}")
                return True
            
            if reraise:
                raise exception
                
            return True
            
        except Exception as e:
            self.logger.error(f"エラーハンドリング中にエラーが発生: {e}")
            if reraise:
                raise exception
            return False
    
    def _create_error_info(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """エラー情報を作成"""
        return {
            'timestamp': datetime.now().isoformat(),
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'category': get_error_category(exception),
            'recoverable': is_recoverable_error(exception),
            'context': context or {},
            'traceback': traceback.format_exc()
        }
    
    def _record_error(self, error_info: Dict[str, Any]):
        """エラーを記録"""
        # 統計更新
        error_type = error_info['exception_type']
        self._error_stats[error_type] = self._error_stats.get(error_type, 0) + 1
        
        # 履歴に追加
        self._last_errors.append(error_info)
        if len(self._last_errors) > self._max_error_history:
            self._last_errors.pop(0)
    
    def _log_error(self, exception: Exception, context: Optional[Dict[str, Any]] = None):
        """エラーをログ出力"""
        message = format_error_message(exception, include_traceback=False)
        
        if context:
            message += f"\nContext: {context}"
        
        if isinstance(exception, LLMCodeAssistantError):
            self.logger.error(message)
        else:
            self.logger.error(message, exc_info=True)
    
    def _execute_callbacks(self, exception: Exception, context: Optional[Dict[str, Any]] = None):
        """エラーコールバックを実行"""
        error_type = type(exception).__name__
        category = get_error_category(exception)
        
        # 特定エラータイプのコールバック
        for callback in self._error_callbacks.get(error_type, []):
            try:
                callback(exception, context)
            except Exception as e:
                self.logger.error(f"エラーコールバック実行中にエラー: {e}")
        
        # カテゴリコールバック
        for callback in self._error_callbacks.get(category, []):
            try:
                callback(exception, context)
            except Exception as e:
                self.logger.error(f"カテゴリコールバック実行中にエラー: {e}")
    
    def get_error_stats(self) -> Dict[str, int]:
        """エラー統計を取得"""
        return self._error_stats.copy()
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """最近のエラーを取得"""
        return self._last_errors[-limit:]
    
    def clear_error_history(self):
        """エラー履歴をクリア"""
        self._last_errors.clear()
        self._error_stats.clear()
    
    def context_manager(self, context: Optional[Dict[str, Any]] = None, reraise: bool = False):
        """
        コンテキストマネージャーとして使用
        
        Args:
            context: エラーコンテキスト
            reraise: 例外を再発生させるかどうか
        """
        return ErrorContextManager(self, context, reraise)

class ErrorContextManager:
    """エラーハンドリング用コンテキストマネージャー"""
    
    def __init__(self, error_handler: ErrorHandler, context: Optional[Dict[str, Any]] = None, reraise: bool = False):
        self.error_handler = error_handler
        self.context = context
        self.reraise = reraise
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.error_handler.handle_error(exc_val, self.context, self.reraise)
            return not self.reraise
        return False

# グローバルエラーハンドラー
_global_error_handler = None

def get_error_handler() -> ErrorHandler:
    """グローバルエラーハンドラーを取得"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler

def handle_error(exception: Exception, context: Optional[Dict[str, Any]] = None, reraise: bool = False) -> bool:
    """グローバルエラーハンドラーでエラーを処理"""
    return get_error_handler().handle_error(exception, context, reraise)

def error_context(context: Optional[Dict[str, Any]] = None, reraise: bool = False):
    """エラーハンドリング用デコレータ/コンテキストマネージャー"""
    return get_error_handler().context_manager(context, reraise)
