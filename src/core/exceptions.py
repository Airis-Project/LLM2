"""
カスタム例外クラス定義
"""

class LLMCodeAssistantError(Exception):
    """LLM Code Assistant 基底例外クラス"""
    pass

class ConfigurationError(LLMCodeAssistantError):
    """設定関連のエラー"""
    pass

class ValidationError(LLMCodeAssistantError):
    """バリデーション関連のエラー"""
    pass

class DatabaseError(LLMCodeAssistantError):
    """データベース関連のエラー"""
    pass

class LLMError(LLMCodeAssistantError):
    """LLM関連のエラー"""
    pass

class LLMConnectionError(LLMError):
    """LLM接続エラー"""
    pass

class LLMResponseError(LLMError):
    """LLMレスポンスエラー"""
    pass

class LLMTimeoutError(LLMError):
    """LLMタイムアウトエラー"""
    pass

class LLMQuotaExceededError(LLMError):
    """LLMクォータ超過エラー"""
    pass

class FileOperationError(LLMCodeAssistantError):
    """ファイル操作関連のエラー"""
    pass

class UIError(LLMCodeAssistantError):
    """UI関連のエラー"""
    pass

class EventSystemError(LLMCodeAssistantError):
    """イベントシステム関連のエラー"""
    pass

class PluginError(LLMCodeAssistantError):
    """プラグイン関連のエラー"""
    pass

class SecurityError(LLMCodeAssistantError):
    """セキュリティ関連のエラー"""
    pass

class NetworkError(LLMCodeAssistantError):
    """ネットワーク関連のエラー"""
    pass

class AuthenticationError(LLMCodeAssistantError):
    """認証関連のエラー"""
    pass

class AuthorizationError(LLMCodeAssistantError):
    """認可関連のエラー"""
    pass

class RateLimitError(LLMCodeAssistantError):
    """レート制限エラー"""
    pass

class ResourceNotFoundError(LLMCodeAssistantError):
    """リソースが見つからないエラー"""
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

class DuplicateError(LLMCodeAssistantError):
    """重複エラー"""
    pass

class PermissionError(LLMCodeAssistantError):
    """権限エラー"""
    pass

class CompatibilityError(LLMCodeAssistantError):
    """互換性エラー"""
    pass

class VersionError(LLMCodeAssistantError):
    """バージョン関連エラー"""
    pass

class InitializationError(LLMCodeAssistantError):
    """初期化エラー"""
    pass

class ShutdownError(LLMCodeAssistantError):
    """シャットダウンエラー"""
    pass

class MaintenanceError(LLMCodeAssistantError):
    """メンテナンス関連エラー"""
    pass
class LLMConfigurationError(ConfigurationError):
    """LLM設定エラー"""
    pass

class LLMAPIError(LLMError):
    """LLM API エラー"""
    pass

class LLMValidationError(ValidationError):
    """LLM バリデーションエラー"""
    pass

# エラーカテゴリ別の例外マッピング
ERROR_CATEGORIES = {
    'config': [ConfigurationError],
    'validation': [ValidationError, InvalidInputError, InvalidFormatError, MissingRequiredFieldError],
    'database': [DatabaseError],
    'llm': [LLMError, LLMConnectionError, LLMResponseError, LLMTimeoutError, LLMQuotaExceededError],
    'file': [FileOperationError],
    'ui': [UIError],
    'event': [EventSystemError],
    'plugin': [PluginError],
    'security': [SecurityError, AuthenticationError, AuthorizationError],
    'network': [NetworkError, RateLimitError],
    'resource': [ResourceNotFoundError, DuplicateError],
    'permission': [PermissionError],
    'system': [InitializationError, ShutdownError, MaintenanceError, CompatibilityError, VersionError]
}

def get_error_category(exception: Exception) -> str:
    """
    例外のカテゴリを取得する
    
    Args:
        exception: 例外インスタンス
        
    Returns:
        str: エラーカテゴリ名
    """
    exception_type = type(exception)
    
    for category, exception_types in ERROR_CATEGORIES.items():
        if exception_type in exception_types:
            return category
    
    return 'unknown'

def is_recoverable_error(exception: Exception) -> bool:
    """
    例外が回復可能かどうかを判定する
    
    Args:
        exception: 例外インスタンス
        
    Returns:
        bool: 回復可能な場合True
    """
    recoverable_types = [
        LLMConnectionError,
        LLMTimeoutError,
        NetworkError,
        RateLimitError,
        FileOperationError
    ]
    
    return type(exception) in recoverable_types

def format_error_message(exception: Exception, include_traceback: bool = False) -> str:
    """
    エラーメッセージをフォーマットする
    
    Args:
        exception: 例外インスタンス
        include_traceback: トレースバックを含めるかどうか
        
    Returns:
        str: フォーマットされたエラーメッセージ
    """
    import traceback
    
    category = get_error_category(exception)
    recoverable = is_recoverable_error(exception)
    
    message = f"[{category.upper()}] {type(exception).__name__}: {str(exception)}"
    
    if recoverable:
        message += " (回復可能)"
    
    if include_traceback:
        message += f"\n\nTraceback:\n{traceback.format_exc()}"
    
    return message
