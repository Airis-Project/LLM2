#src/core/__init__.py
"""
コア機能パッケージ

このパッケージはLLM Code Assistantのコア機能を提供します：
- 設定管理 (ConfigManager)
- ログ管理 (Logger)
- 例外処理 (Exceptions)
- エラーハンドリング (ErrorHandler)
- イベントシステム (EventSystem)
"""

# 基本的なインポート（例外とロガー）
from .logger import get_logger, setup_logging
from .exceptions import (
    LLMCodeAssistantError,
    ConfigurationError,
    ValidationError,
    DatabaseError,
    LLMError,
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
    LLMQuotaExceededError,
    FileOperationError,
    UIError,
    EventSystemError,
    PluginError,
    SecurityError,
    NetworkError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ResourceNotFoundError,
    InvalidInputError,
    InvalidFormatError,
    MissingRequiredFieldError,
    DuplicateError,
    PermissionError,
    CompatibilityError,
    VersionError,
    InitializationError,
    ShutdownError,
    MaintenanceError,
    #LLMConfigurationError,
    #LLMAPIError,
    #LLMValidationError
)

# 条件付きインポート
CORE_AVAILABLE = True
_import_errors = []

try:
    from .config_manager import ConfigManager, get_config
except ImportError as e:
    ConfigManager = None
    get_config = None
    _import_errors.append(f"ConfigManager: {e}")
    CORE_AVAILABLE = False

try:
    from .error_handler import ErrorHandler
except ImportError as e:
    ErrorHandler = None
    _import_errors.append(f"ErrorHandler: {e}")
    CORE_AVAILABLE = False

try:
    from .event_system import EventSystem, Event
except ImportError as e:
    EventSystem = None
    Event = None
    _import_errors.append(f"EventSystem: {e}")
    CORE_AVAILABLE = False

# バージョン情報
__version__ = "1.0.0"

# エクスポートする要素
__all__ = [
    # 設定管理
    'ConfigManager',
    'get_config',
    
    # ログ管理
    'get_logger',
    'setup_logging',
    
    # 例外クラス
    'LLMCodeAssistantError',
    'ConfigurationError',
    'ValidationError',
    'DatabaseError',
    'LLMError',
    'LLMConnectionError',
    'LLMResponseError',
    'LLMTimeoutError',
    'LLMQuotaExceededError',
    'FileOperationError',
    'UIError',
    'EventSystemError',
    'PluginError',
    'SecurityError',
    'NetworkError',
    'AuthenticationError',
    'AuthorizationError',
    'RateLimitError',
    'ResourceNotFoundError',
    'InvalidInputError',
    'InvalidFormatError',
    'MissingRequiredFieldError',
    'DuplicateError',
    'PermissionError',
    'CompatibilityError',
    'VersionError',
    'InitializationError',
    'ShutdownError',
    'MaintenanceError',
    
    # エラーハンドリング
    'ErrorHandler',
    
    # イベントシステム
    'EventSystem',
    'Event',
    
    # ステータス
    'CORE_AVAILABLE',
    
    # バージョン情報
    '__version__'
]

# デフォルト設定
DEFAULT_LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'logs/llm_framework.log'
}

def initialize_core():
    """
    コア機能の初期化
    
    Returns:
        bool: 初期化成功フラグ
    """
    try:
        # ログシステムの初期化
        setup_logging()
        logger = get_logger(__name__)
        
        # インポートエラーがあれば警告
        if _import_errors:
            logger.warning("一部のコアモジュールが利用できません:")
            for error in _import_errors:
                logger.warning(f"  - {error}")
        
        # 設定管理の初期化
        if ConfigManager is not None:
            config_manager = ConfigManager()
            logger.info("ConfigManagerが初期化されました")
        
        logger.info(f"コア機能の初期化が完了しました (利用可能: {CORE_AVAILABLE})")
        return True
        
    except Exception as e:
        print(f"コア機能初期化エラー: {e}")
        return False

def get_core_info():
    """
    コア機能の情報を取得
    
    Returns:
        dict: コア機能情報
    """
    available_components = ['Logger', 'Exceptions']
    
    if ConfigManager is not None:
        available_components.append('ConfigManager')
    if ErrorHandler is not None:
        available_components.append('ErrorHandler')
    if EventSystem is not None:
        available_components.append('EventSystem')
    
    return {
        'version': __version__,
        'core_available': CORE_AVAILABLE,
        'available_components': available_components,
        'import_errors': _import_errors,
        'default_log_config': DEFAULT_LOG_CONFIG
    }

def get_core_status():
    """
    コア機能のステータスを取得
    
    Returns:
        dict: ステータス情報
    """
    return {
        'ConfigManager': ConfigManager is not None,
        'ErrorHandler': ErrorHandler is not None,
        'EventSystem': EventSystem is not None,
        'Logger': True,  # 常に利用可能
        'Exceptions': True  # 常に利用可能
    }

# パッケージ初期化（遅延実行）
def _delayed_init():
    """遅延初期化"""
    try:
        return initialize_core()
    except Exception:
        return False

# 初期化フラグ
_initialized = _delayed_init()
