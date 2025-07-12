# src/core/exceptions.py
"""
LLM Code Assistant カスタム例外クラス
アプリケーション全体で使用される例外の定義
"""

from typing import Optional, Dict, Any
from datetime import datetime


class LLMCodeAssistantError(Exception):
    """LLM Code Assistant 基底例外クラス"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        """
        基底例外の初期化
        
        Args:
            message: エラーメッセージ
            error_code: エラーコード
            details: 詳細情報
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """例外情報を辞書形式で返す"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


# === 設定関連例外 ===
class ConfigurationError(LLMCodeAssistantError):
    """追記分"""
    pass
class LLMError(LLMCodeAssistantError):
    """追記分"""
    pass
class EventSystemError(LLMCodeAssistantError):
    """追記分"""
    pass
class PluginError(LLMCodeAssistantError):
    """追記分"""
    pass
class SecurityError(LLMCodeAssistantError):
    """追記分"""
    pass
class RateLimitError(LLMCodeAssistantError):
    """追記分"""
    pass
class ResourceNotFoundError(LLMCodeAssistantError):
    """追記分"""
    pass
class MissingRequiredFieldError(LLMCodeAssistantError):
    """追記分"""
    pass
class DuplicateError(LLMCodeAssistantError):
    """追記分"""
    pass
class CompatibilityError(LLMCodeAssistantError):
    """追記分"""
    pass
class VersionError(LLMCodeAssistantError):
    """追記分"""
    pass
class InitializationError(LLMCodeAssistantError):
    """追記分"""
    pass
class ShutdownError(LLMCodeAssistantError):
    """追記分"""
    pass
class MaintenanceError(LLMCodeAssistantError):
    """追記分"""
    pass
class InvalidInputError(LLMCodeAssistantError):
    """追記分"""
    pass
class PermissionError(LLMCodeAssistantError):
    """追記分"""
    pass

class ConfigError(LLMCodeAssistantError):
    """設定関連の例外"""
    pass
class InvalidFormatError(LLMCodeAssistantError):
    """設定関連の例外"""
    pass



class ConfigValidationError(ConfigError):
    """設定値検証エラー"""
    pass


class ConfigFileError(ConfigError):
    """設定ファイル関連エラー"""
    pass


class ConfigNotFoundError(ConfigError):
    """設定が見つからないエラー"""
    pass


# === ファイル操作関連例外 ===
class FileServiceError(LLMCodeAssistantError):
    """ファイルサービス関連の例外"""
    pass


class FileNotFoundError(FileServiceError):
    """ファイルが見つからないエラー"""
    pass


class FilePermissionError(FileServiceError):
    """ファイル権限エラー"""
    pass


class FileOperationError(FileServiceError):
    """ファイル操作エラー"""
    pass


class FileValidationError(FileServiceError):
    """ファイル検証エラー"""
    pass


class BackupError(FileServiceError):
    """バックアップ関連エラー"""
    pass


class FileTypeError(FileServiceError):
    """ファイルタイプ関連エラー"""
    pass


class FileSizeError(FileServiceError):
    """ファイルサイズ関連エラー"""
    pass


class FileEncodingError(FileServiceError):
    """ファイルエンコーディングエラー"""
    pass


# === プロジェクト管理関連例外 ===
class ProjectServiceError(LLMCodeAssistantError):
    """プロジェクトサービス関連の例外"""
    pass


class ProjectNotFoundError(ProjectServiceError):
    """プロジェクトが見つからないエラー"""
    pass


class ProjectConfigError(ProjectServiceError):
    """プロジェクト設定エラー"""
    pass


class ProjectCreationError(ProjectServiceError):
    """プロジェクト作成エラー"""
    pass


class ProjectAnalysisError(ProjectServiceError):
    """プロジェクト解析エラー"""
    pass


class ProjectTemplateError(ProjectServiceError):
    """プロジェクトテンプレート関連エラー"""
    pass


class ProjectImportError(ProjectServiceError):
    """プロジェクトインポートエラー"""
    pass


class ProjectExportError(ProjectServiceError):
    """プロジェクトエクスポートエラー"""
    pass


class ProjectArchiveError(ProjectServiceError):
    """プロジェクトアーカイブエラー"""
    pass


class ProjectValidationError(ProjectServiceError):
    """プロジェクト検証エラー"""
    pass


# === LLM関連例外 ===
class LLMServiceError(LLMCodeAssistantError):
    """LLMサービス関連の例外"""
    pass


class LLMConnectionError(LLMServiceError):
    """LLM接続エラー"""
    pass


class LLMAuthenticationError(LLMServiceError):
    """LLM認証エラー"""
    pass


class LLMRateLimitError(LLMServiceError):
    """LLMレート制限エラー"""
    pass


class LLMResponseError(LLMServiceError):
    """LLMレスポンスエラー"""
    pass


class LLMTimeoutError(LLMServiceError):
    """LLMタイムアウトエラー"""
    pass


class LLMQuotaExceededError(LLMServiceError):
    """LLMクォータ超過エラー"""
    pass


class LLMModelError(LLMServiceError):
    """LLMモデル関連エラー"""
    pass


class LLMPromptError(LLMServiceError):
    """LLMプロンプト関連エラー"""
    pass


# === コード生成関連例外 ===
class CodeGenerationError(LLMCodeAssistantError):
    """コード生成関連の例外"""
    pass


class CodeAnalysisError(CodeGenerationError):
    """コード解析エラー"""
    pass


class CodeValidationError(CodeGenerationError):
    """コード検証エラー"""
    pass


class CodeFormattingError(CodeGenerationError):
    """コードフォーマットエラー"""
    pass


class CodeOptimizationError(CodeGenerationError):
    """コード最適化エラー"""
    pass


class CodeRefactoringError(CodeGenerationError):
    """コードリファクタリングエラー"""
    pass


class CodeDocumentationError(CodeGenerationError):
    """コードドキュメント生成エラー"""
    pass


class CodeTestGenerationError(CodeGenerationError):
    """テストコード生成エラー"""
    pass


# === UI関連例外 ===
class UIError(LLMCodeAssistantError):
    """UI関連の例外"""
    pass


class UIComponentError(UIError):
    """UIコンポーネントエラー"""
    pass


class UIRenderingError(UIError):
    """UIレンダリングエラー"""
    pass


class UIEventError(UIError):
    """UIイベント処理エラー"""
    pass


class UIValidationError(UIError):
    """UI入力検証エラー"""
    pass


class UIThemeError(UIError):
    """UIテーマ関連エラー"""
    pass


class UILayoutError(UIError):
    """UIレイアウトエラー"""
    pass


# === データベース関連例外 ===
class DatabaseError(LLMCodeAssistantError):
    """データベース関連の例外"""
    pass


class DatabaseConnectionError(DatabaseError):
    """データベース接続エラー"""
    pass


class DatabaseQueryError(DatabaseError):
    """データベースクエリエラー"""
    pass


class DatabaseMigrationError(DatabaseError):
    """データベースマイグレーションエラー"""
    pass


class DatabaseIntegrityError(DatabaseError):
    """データベース整合性エラー"""
    pass


class DatabaseTimeoutError(DatabaseError):
    """データベースタイムアウトエラー"""
    pass


# === ネットワーク関連例外 ===
class NetworkError(LLMCodeAssistantError):
    """ネットワーク関連の例外"""
    pass


class NetworkConnectionError(NetworkError):
    """ネットワーク接続エラー"""
    pass


class NetworkTimeoutError(NetworkError):
    """ネットワークタイムアウトエラー"""
    pass


class NetworkAuthenticationError(NetworkError):
    """ネットワーク認証エラー"""
    pass


class NetworkPermissionError(NetworkError):
    """ネットワーク権限エラー"""
    pass


# === 認証・認可関連例外 ===
class AuthenticationError(LLMCodeAssistantError):
    """認証関連の例外"""
    pass


class AuthorizationError(LLMCodeAssistantError):
    """認可関連の例外"""
    pass


class TokenError(AuthenticationError):
    """トークン関連エラー"""
    pass


class SessionError(AuthenticationError):
    """セッション関連エラー"""
    pass


class PermissionDeniedError(AuthorizationError):
    """権限拒否エラー"""
    pass


# === バリデーション関連例外 ===
class ValidationError(LLMCodeAssistantError):
    """バリデーション関連の例外"""
    pass


class InputValidationError(ValidationError):
    """入力検証エラー"""
    pass


class DataValidationError(ValidationError):
    """データ検証エラー"""
    pass


class SchemaValidationError(ValidationError):
    """スキーマ検証エラー"""
    pass


class FormatValidationError(ValidationError):
    """フォーマット検証エラー"""
    pass


# === パフォーマンス関連例外 ===
class PerformanceError(LLMCodeAssistantError):
    """パフォーマンス関連の例外"""
    pass


class MemoryError(PerformanceError):
    """メモリ関連エラー"""
    pass


class TimeoutError(PerformanceError):
    """タイムアウトエラー"""
    pass


class ResourceExhaustedError(PerformanceError):
    """リソース枯渇エラー"""
    pass


class ConcurrencyError(PerformanceError):
    """並行処理エラー"""
    pass


# === 外部サービス関連例外 ===
class ExternalServiceError(LLMCodeAssistantError):
    """外部サービス関連の例外"""
    pass


class APIError(ExternalServiceError):
    """API関連エラー"""
    pass


class WebhookError(ExternalServiceError):
    """Webhook関連エラー"""
    pass


class IntegrationError(ExternalServiceError):
    """統合関連エラー"""
    pass


# === 開発・デバッグ関連例外 ===
class DevelopmentError(LLMCodeAssistantError):
    """開発関連の例外"""
    pass


class DebugError(DevelopmentError):
    """デバッグ関連エラー"""
    pass


class TestError(DevelopmentError):
    """テスト関連エラー"""
    pass


class MockError(DevelopmentError):
    """モック関連エラー"""
    pass


# === 例外ハンドリングユーティリティ ===
class ExceptionHandler:
    """例外ハンドリングユーティリティクラス"""
    
    @staticmethod
    def format_exception(exception: Exception) -> Dict[str, Any]:
        """例外情報をフォーマット"""
        if isinstance(exception, LLMCodeAssistantError):
            return exception.to_dict()
        
        return {
            'error_type': exception.__class__.__name__,
            'message': str(exception),
            'error_code': None,
            'details': {},
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def is_retryable_error(exception: Exception) -> bool:
        """再試行可能なエラーかどうかを判定"""
        retryable_errors = [
            NetworkTimeoutError,
            LLMTimeoutError,
            DatabaseTimeoutError,
            NetworkConnectionError,
            LLMConnectionError,
            DatabaseConnectionError,
            ResourceExhaustedError
        ]
        
        return any(isinstance(exception, error_type) for error_type in retryable_errors)
    
    @staticmethod
    def is_user_error(exception: Exception) -> bool:
        """ユーザー起因のエラーかどうかを判定"""
        user_errors = [
            ValidationError,
            InputValidationError,
            FileNotFoundError,
            ProjectNotFoundError,
            AuthenticationError,
            PermissionDeniedError,
            ConfigValidationError
        ]
        
        return any(isinstance(exception, error_type) for error_type in user_errors)
    
    @staticmethod
    def get_error_severity(exception: Exception) -> str:
        """エラーの重要度を取得"""
        critical_errors = [
            DatabaseError,
            FilePermissionError,
            AuthenticationError,
            AuthorizationError
        ]
        
        warning_errors = [
            ValidationError,
            UIError,
            NetworkTimeoutError
        ]
        
        if any(isinstance(exception, error_type) for error_type in critical_errors):
            return "critical"
        elif any(isinstance(exception, error_type) for error_type in warning_errors):
            return "warning"
        else:
            return "error"


# === 例外ファクトリ関数 ===
def create_project_error(error_type: str, message: str, **kwargs) -> ProjectServiceError:
    """プロジェクト関連例外の作成"""
    error_classes = {
        'not_found': ProjectNotFoundError,
        'config': ProjectConfigError,
        'creation': ProjectCreationError,
        'analysis': ProjectAnalysisError,
        'template': ProjectTemplateError,
        'import': ProjectImportError,
        'export': ProjectExportError,
        'archive': ProjectArchiveError,
        'validation': ProjectValidationError
    }
    
    error_class = error_classes.get(error_type, ProjectServiceError)
    return error_class(message, **kwargs)


def create_file_error(error_type: str, message: str, **kwargs) -> FileServiceError:
    """ファイル関連例外の作成"""
    error_classes = {
        'not_found': FileNotFoundError,
        'permission': FilePermissionError,
        'operation': FileOperationError,
        'validation': FileValidationError,
        'backup': BackupError,
        'type': FileTypeError,
        'size': FileSizeError,
        'encoding': FileEncodingError
    }
    
    error_class = error_classes.get(error_type, FileServiceError)
    return error_class(message, **kwargs)


def create_llm_error(error_type: str, message: str, **kwargs) -> LLMServiceError:
    """LLM関連例外の作成"""
    error_classes = {
        'connection': LLMConnectionError,
        'authentication': LLMAuthenticationError,
        'rate_limit': LLMRateLimitError,
        'response': LLMResponseError,
        'timeout': LLMTimeoutError,
        'quota': LLMQuotaExceededError,
        'model': LLMModelError,
        'prompt': LLMPromptError
    }
    
    error_class = error_classes.get(error_type, LLMServiceError)
    return error_class(message, **kwargs)


# === 例外デコレータ ===
def handle_exceptions(default_return=None, reraise=True):
    """例外処理デコレータ"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # ログ出力などの処理をここに追加
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


def async_handle_exceptions(default_return=None, reraise=True):
    """非同期関数用例外処理デコレータ"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # ログ出力などの処理をここに追加
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator
