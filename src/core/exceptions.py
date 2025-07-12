#!/usr/bin/env python3
"""
例外処理システム - 統合例外管理
"""

import traceback
import sys
from typing import Optional, Dict, Any, List, Type, Callable
from dataclasses import dataclass
from datetime import datetime
import logging

# ベース例外クラス
class LLMSystemError(Exception):
    """LLMシステム基底例外"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で出力"""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }

# 設定関連例外
class ConfigError(LLMSystemError):
    """設定エラー"""
    pass

class ConfigValidationError(ConfigError):
    """設定検証エラー"""
    pass

class ConfigFileError(ConfigError):
    """設定ファイルエラー"""
    pass

# LLM関連例外
class LLMError(LLMSystemError):
    """LLM基底エラー"""
    pass

class LLMConnectionError(LLMError):
    """LLM接続エラー"""
    pass

class LLMAuthenticationError(LLMError):
    """LLM認証エラー"""
    pass

class LLMRateLimitError(LLMError):
    """LLMレート制限エラー"""
    pass

class LLMTimeoutError(LLMError):
    """LLMタイムアウトエラー"""
    pass

class LLMModelError(LLMError):
    """LLMモデルエラー"""
    pass

class LLMResponseError(LLMError):
    """LLMレスポンスエラー"""
    pass

class LLMChatError(LLMError):
    """LLMチャットエラー"""
    pass

# UI関連例外
class UIError(LLMSystemError):
    """UI基底エラー"""
    pass

class UIComponentError(UIError):
    """UIコンポーネントエラー"""
    pass

class UIRenderError(UIError):
    """UI描画エラー"""
    pass

# ファイル関連例外
class FileError(LLMSystemError):
    """ファイル基底エラー"""
    pass

class FileNotFoundError(FileError):
    """ファイル未発見エラー"""
    pass

class FilePermissionError(FileError):
    """ファイル権限エラー"""
    pass

class FileFormatError(FileError):
    """ファイル形式エラー"""
    pass

class FileServiceError(FileError):
    """ファイルサービスエラー"""
    pass

class FileSizeError(FileError):
    """ファイルサイズエラー"""
    pass

class FileTypeError(FileError):
    """ファイルタイプエラー"""
    pass

#プロジェクト関連例外
class ProjectServiceError(LLMSystemError):
    """プロジェクトサービスエラー"""
    pass

class ProjectNotFoundError(LLMSystemError):
    """プロジェクトNotFoundエラー"""
    pass

class ProjectConfigError(LLMSystemError):
    """プロジェクトNotFoundエラー"""
    pass

# ネットワーク関連例外
class NetworkError(LLMSystemError):
    """ネットワーク基底エラー"""
    pass

class ConnectionError(NetworkError):
    """接続エラー"""
    pass

class TimeoutError(NetworkError):
    """タイムアウトエラー"""
    pass

# 復旧可能エラー判定
RECOVERABLE_ERRORS = {
    LLMTimeoutError,
    LLMRateLimitError,
    NetworkError,
    ConnectionError,
    TimeoutError
}

def is_recoverable_error(error: Exception) -> bool:
    """復旧可能エラー判定"""
    return type(error) in RECOVERABLE_ERRORS or any(
        isinstance(error, recoverable_type) for recoverable_type in RECOVERABLE_ERRORS
    )

@dataclass
class ErrorContext:
    """エラーコンテキスト"""
    function_name: str
    module_name: str
    line_number: int
    local_vars: Dict[str, Any]
    timestamp: datetime

class ErrorHandler:
    """エラーハンドラー"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_callbacks: List[Callable[[Exception, ErrorContext], None]] = []
    
    def add_callback(self, callback: Callable[[Exception, ErrorContext], None]):
        """エラーコールバック追加"""
        self.error_callbacks.append(callback)
    
    def handle_error(self, error: Exception, context: Optional[ErrorContext] = None):
        """エラー処理"""
        try:
            # コンテキスト生成
            if context is None:
                context = self._create_context()
            
            # ログ出力
            self._log_error(error, context)
            
            # コールバック実行
            for callback in self.error_callbacks:
                try:
                    callback(error, context)
                except Exception as callback_error:
                    self.logger.error(f"Error callback failed: {callback_error}")
            
        except Exception as handler_error:
            # ハンドラー自体でエラーが発生した場合
            self.logger.critical(f"Error handler failed: {handler_error}")
    
    def _create_context(self) -> ErrorContext:
        """エラーコンテキスト作成"""
        frame = sys._getframe(2)  # 呼び出し元のフレーム
        
        return ErrorContext(
            function_name=frame.f_code.co_name,
            module_name=frame.f_globals.get('__name__', 'unknown'),
            line_number=frame.f_lineno,
            local_vars=dict(frame.f_locals),
            timestamp=datetime.now()
        )
    
    def _log_error(self, error: Exception, context: ErrorContext):
        """エラーログ出力"""
        error_info = {
            'error_type': type(error).__name__,
            'message': str(error),
            'function': context.function_name,
            'module': context.module_name,
            'line': context.line_number,
            'timestamp': context.timestamp.isoformat()
        }
        
        if isinstance(error, LLMSystemError):
            error_info.update(error.to_dict())
        
        self.logger.error(f"Error occurred: {error_info}", exc_info=True)

# グローバルエラーハンドラー
_global_error_handler = ErrorHandler()

def set_global_error_handler(handler: ErrorHandler):
    """グローバルエラーハンドラー設定"""
    global _global_error_handler
    _global_error_handler = handler

def handle_error(error: Exception, context: Optional[ErrorContext] = None):
    """グローバルエラー処理"""
    _global_error_handler.handle_error(error, context)

def add_error_callback(callback: Callable[[Exception, ErrorContext], None]):
    """グローバルエラーコールバック追加"""
    _global_error_handler.add_callback(callback)

# デコレーター
def error_handler(recoverable: bool = False, 
                 default_return: Any = None,
                 log_level: str = 'ERROR'):
    """エラーハンドリングデコレーター"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # エラー処理
                handle_error(e)
                
                # 復旧可能エラーの場合は再発生
                if not recoverable or not is_recoverable_error(e):
                    if default_return is not None:
                        return default_return
                    raise
                
                # 復旧可能エラーはデフォルト値を返す
                return default_return
        
        return wrapper
    return decorator

def safe_execute(func: Callable, *args, default_return: Any = None, **kwargs) -> Any:
    """安全実行"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_error(e)
        return default_return

# 例外情報取得
def get_exception_info(error: Exception) -> Dict[str, Any]:
    """例外情報取得"""
    return {
        'type': type(error).__name__,
        'message': str(error),
        'traceback': traceback.format_exc(),
        'is_recoverable': is_recoverable_error(error),
        'timestamp': datetime.now().isoformat()
    }

def format_exception(error: Exception) -> str:
    """例外フォーマット"""
    if isinstance(error, LLMSystemError):
        return f"{error.error_code}: {error.message}"
    return f"{type(error).__name__}: {str(error)}"

# システム例外フック
def install_exception_hook():
    """システム例外フック設定"""
    def exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Ctrl+C は通常処理
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # その他の例外はハンドラーで処理
        handle_error(exc_value)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_hook

# 初期化
def initialize_error_handling(logger: Optional[logging.Logger] = None):
    """エラーハンドリング初期化"""
    global _global_error_handler
    _global_error_handler = ErrorHandler(logger)
    install_exception_hook()
    return _global_error_handler
# 互換性のためのエイリアス
LLMCodeAssistantError = LLMSystemError

# 追加の例外クラス（既存システムとの互換性）
class ValidationError(LLMSystemError):
    """検証エラー"""
    pass

class DatabaseError(LLMSystemError):
    """データベースエラー"""
    pass

class PluginError(LLMSystemError):
    """プラグインエラー"""
    pass

class EventSystemError(LLMSystemError):
    """イベントシステムエラー"""
    pass

class SecurityError(LLMSystemError):
    """セキュリティエラー"""
    pass

class AuthenticationError(LLMSystemError):
    """認証エラー"""
    pass

class AuthorizationError(LLMSystemError):
    """認可エラー"""
    pass

class RateLimitError(LLMSystemError):
    """レート制限エラー"""
    pass

class ResourceNotFoundError(LLMSystemError):
    """リソース未発見エラー"""
    pass

class InvalidInputError(ValidationError):
    """無効な入力エラー"""
    pass

class InvalidFormatError(ValidationError):
    """無効なフォーマットエラー"""
    pass

class MissingRequiredFieldError(ValidationError):
    """必須フィールド不足エラー"""
    pass

class DuplicateError(LLMSystemError):
    """重複エラー"""
    pass

class PermissionError(LLMSystemError):
    """権限エラー"""
    pass

class CompatibilityError(LLMSystemError):
    """互換性エラー"""
    pass

class VersionError(LLMSystemError):
    """バージョンエラー"""
    pass

class InitializationError(LLMSystemError):
    """初期化エラー"""
    pass

class ShutdownError(LLMSystemError):
    """終了処理エラー"""
    pass

class MaintenanceError(LLMSystemError):
    """メンテナンスエラー"""
    pass

# 基底例外クラス（エイリアス）
class LLMCodeAssistantError(LLMSystemError):
    """LLMコードアシスタント基底例外（互換性エイリアス）"""
    pass

class ConfigurationError(ConfigError):
    """設定例外（互換性エイリアス）"""
    pass

# 検証・データベース関連
class ValidationError(LLMSystemError):
    """検証エラー"""
    pass

class DatabaseError(LLMSystemError):
    """データベースエラー"""
    pass

# LLM関連の追加例外
class LLMException(LLMError):
    """LLM例外（互換性エイリアス）"""
    pass

class LLMQuotaExceededError(LLMError):
    """LLMクォータ超過エラー"""
    pass

class LLMValidationError(LLMError):
    """LLM検証エラー"""
    pass

# ファイル操作関連
class FileOperationError(FileError):
    """ファイル操作エラー（互換性エイリアス）"""
    pass

# システム関連
class EventSystemError(LLMSystemError):
    """イベントシステムエラー"""
    pass

class PluginError(LLMSystemError):
    """プラグインエラー"""
    pass

class SecurityError(LLMSystemError):
    """セキュリティエラー"""
    pass

# 認証・認可関連
class AuthenticationError(LLMSystemError):
    """認証エラー"""
    pass

class AuthorizationError(LLMSystemError):
    """認可エラー"""
    pass

# リソース・制限関連
class RateLimitError(LLMSystemError):
    """レート制限エラー"""
    pass

class ResourceNotFoundError(LLMSystemError):
    """リソース未発見エラー"""
    pass

# 入力検証関連
class InvalidInputError(ValidationError):
    """無効な入力エラー"""
    pass

class InvalidFormatError(ValidationError):
    """無効なフォーマットエラー"""
    pass

class MissingRequiredFieldError(ValidationError):
    """必須フィールド不足エラー"""
    pass

# その他のシステムエラー
class DuplicateError(LLMSystemError):
    """重複エラー"""
    pass

class PermissionError(LLMSystemError):
    """権限エラー"""
    pass

class CompatibilityError(LLMSystemError):
    """互換性エラー"""
    pass

class VersionError(LLMSystemError):
    """バージョンエラー"""
    pass

class InitializationError(LLMSystemError):
    """初期化エラー"""
    pass

class ShutdownError(LLMSystemError):
    """終了処理エラー"""
    pass

class MaintenanceError(LLMSystemError):
    """メンテナンスエラー"""
    pass

# エクスポートリストを更新
__all__ = [
    # 既存の例外クラス
    'LLMSystemError', 'ConfigError', 'ConfigValidationError', 'ConfigFileError',
    'LLMError', 'LLMConnectionError', 'LLMAuthenticationError', 'LLMRateLimitError',
    'LLMTimeoutError', 'LLMModelError', 'LLMResponseError',
    'UIError', 'UIComponentError', 'UIRenderError',
    'FileError', 'FileNotFoundError', 'FilePermissionError', 'FileFormatError',
    'NetworkError', 'ConnectionError', 'TimeoutError',
    
    # 互換性のための追加例外クラス
    'LLMCodeAssistantError', 'ConfigurationError', 'ValidationError', 'DatabaseError',
    'LLMException', 'LLMQuotaExceededError', 'LLMValidationError',
    'FileOperationError', 'EventSystemError', 'PluginError', 'SecurityError',
    'AuthenticationError', 'AuthorizationError', 'RateLimitError',
    'ResourceNotFoundError', 'InvalidInputError', 'InvalidFormatError',
    'MissingRequiredFieldError', 'DuplicateError', 'PermissionError',
    'CompatibilityError', 'VersionError', 'InitializationError',
    'ShutdownError', 'MaintenanceError',
    
    # 関数
    'is_recoverable_error', 'handle_error', 'add_error_callback',
    'safe_execute', 'get_exception_info', 'format_exception',
    'install_exception_hook', 'initialize_error_handling',
    
    # クラス
    'ErrorHandler', 'ErrorContext',
    
    # デコレーター
    'error_handler'
]
def format_error_message(exception: Exception, include_traceback: bool = True) -> str:
    """
    エラーメッセージをフォーマット
    
    Args:
        exception: 例外オブジェクト
        include_traceback: トレースバックを含めるか
        
    Returns:
        str: フォーマットされたエラーメッセージ
    """
    import traceback
    
    message = f"{type(exception).__name__}: {str(exception)}"
    
    if include_traceback:
        message += f"\n\nTraceback:\n{traceback.format_exc()}"
    
    return message

def get_error_category(exception: Exception) -> str:
    """
    例外のカテゴリを取得
    
    Args:
        exception: 例外オブジェクト
        
    Returns:
        str: エラーカテゴリ
    """
    if isinstance(exception, LLMCodeAssistantError):
        if isinstance(exception, ConfigError):
            return "config"
        elif isinstance(exception, LLMError):
            return "llm"
        elif isinstance(exception, UIError):
            return "ui"
        elif isinstance(exception, ValidationError):
            return "validation"
        elif isinstance(exception, FileError):
            return "file"
        elif isinstance(exception, NetworkError):
            return "network"
        elif isinstance(exception, AuthenticationError):
            return "authentication"
        elif isinstance(exception, PermissionError):
            return "permission"
        elif isinstance(exception, TimeoutError):
            return "timeout"
        elif isinstance(exception, CompatibilityError):
            return "compatibility"
        else:
            return "system"
    else:
        # 標準例外のカテゴリ分類
        if isinstance(exception, (ValueError, TypeError)):
            return "validation"
        elif isinstance(exception, (FileNotFoundError, PermissionError, IOError)):
            return "file"
        elif isinstance(exception, (ConnectionError, TimeoutError)):
            return "network"
        elif isinstance(exception, MemoryError):
            return "resource"
        else:
            return "unknown"

def format_error_message(exception: Exception, include_traceback: bool = True) -> str:
    """
    エラーメッセージをフォーマット
    
    Args:
        exception: 例外オブジェクト
        include_traceback: トレースバックを含めるか
        
    Returns:
        str: フォーマットされたエラーメッセージ
    """
    import traceback
    
    message = f"{type(exception).__name__}: {str(exception)}"
    
    if include_traceback:
        message += f"\n\nTraceback:\n{traceback.format_exc()}"
    
    return message

def is_recoverable_error(exception: Exception) -> bool:
    """
    エラーが回復可能かどうかを判定
    
    Args:
        exception: 例外オブジェクト
        
    Returns:
        bool: 回復可能な場合True
    """
    # 回復可能なエラーの定義
    recoverable_errors = (
        NetworkError,
        TimeoutError,
        ConnectionError,
        # 一時的なリソース不足
        MemoryError,
    )
    
    # LLMCodeAssistantError の場合
    if isinstance(exception, LLMCodeAssistantError):
        return isinstance(exception, recoverable_errors)
    
    # 標準例外の場合
    standard_recoverable = (
        ConnectionError,
        TimeoutError,
        MemoryError,
    )
    
    return isinstance(exception, standard_recoverable)