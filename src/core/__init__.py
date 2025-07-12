# src/core/__init__.py
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
from .logger import (
    get_logger, 
    configure_logging,
    get_logger_manager,
    shutdown_logging,
    log_function_call,
    log_async_function_call,
    log_exception,
    log_performance,
    log_api_call,
    is_logging_configured,
    get_logging_config,
    LogLevel,
    LogFormat
)

# 後方互換性のためのエイリアス
setup_logging = configure_logging

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
)

# 条件付きインポート
CORE_AVAILABLE = True
_import_errors = []

# ログ設定
try:
    from .logger import get_logger, get_logger_manager, LogConfig, configure_logging
    logger = get_logger(__name__)
    logger_available = True
except ImportError as e:
    print(f"Logger import error: {e}")
    logger = None
    logger_available = False
"""
# 設定管理
try:
    from .config_manager import ConfigManager, get_config
except ImportError as e:
    ConfigManager = None
    get_config = None
    _import_errors.append(f"ConfigManager: {e}")
    CORE_AVAILABLE = False
"""
def get_config_manager():
    try:
        from .config_manager import ConfigManager
        return ConfigManager()
    except ImportError as e:
        _import_errors.append(f"ConfigManager: {e}")
        return None

def get_config(*args, **kwargs):
    try:
        from .config_manager import get_config
        return get_config(*args, **kwargs)
    except ImportError as e:
        _import_errors.append(f"get_config: {e}")
        return None

# 例外処理
try:
    from .error_handler import ErrorHandler
except ImportError as e:
    ErrorHandler = None
    _import_errors.append(f"ErrorHandler: {e}")
    CORE_AVAILABLE = False

# イベントシステム
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
    'get_config_manager',
    
    # ログ管理
    'get_logger',
    'setup_logging',  # 後方互換性
    'configure_logging',
    'get_logger_manager',
    'shutdown_logging',
    'log_function_call',
    'log_async_function_call',
    'log_exception',
    'log_performance',
    'log_api_call',
    'is_logging_configured',
    'get_logging_config',
    'LogLevel',
    'LogFormat',
    
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

# デフォルト設定（新しいログシステムに対応）
DEFAULT_LOG_CONFIG = {
    'level': LogLevel.INFO,
    'format_type': LogFormat.DETAILED,
    'console_enabled': True,
    'file_enabled': True,
    'log_dir': 'logs',
    'log_file': 'llm_framework.log'
}

def initialize_core():
    """
    コア機能の初期化
    
    Returns:
        bool: 初期化成功フラグ
    """
    try:
        # 新しいログシステムの初期化
        from .logger import LogConfig
        log_config = LogConfig(
            level=LogLevel.INFO,
            format_type=LogFormat.DETAILED,
            console_enabled=True,
            file_enabled=True
        )
        configure_logging(log_config)
        
        logger = get_logger(__name__)
        logger.info("新しいログシステムが初期化されました")
        
        # インポートエラーがあれば警告
        if _import_errors:
            logger.warning("一部のコアモジュールが利用できません:")
            for error in _import_errors:
                logger.warning(f"  - {error}")
        
        # 設定管理の初期化
        if get_config_manager is not None:
            config_manager = get_config_manager()
            logger.info("ConfigManagerが初期化されました")
        
        # ログ設定情報を表示
        log_config = get_logging_config()
        logger.info(f"ログ設定: {log_config}")
        
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
    
    if get_config_manager is not None:
        available_components.append('ConfigManager')
    if ErrorHandler is not None:
        available_components.append('ErrorHandler')
    if EventSystem is not None:
        available_components.append('EventSystem')
    
    # ログ設定情報を追加
    log_config = {}
    try:
        log_config = get_logging_config()
    except Exception:
        pass
    
    return {
        'version': __version__,
        'core_available': CORE_AVAILABLE,
        'available_components': available_components,
        'import_errors': _import_errors,
        'default_log_config': DEFAULT_LOG_CONFIG,
        'current_log_config': log_config,
        'logging_configured': is_logging_configured()
    }

def get_core_status():
    """
    コア機能のステータスを取得
    
    Returns:
        dict: ステータス情報
    """
    return {
        'ConfigManager': get_config_manager is not None,
        'ErrorHandler': ErrorHandler is not None,
        'EventSystem': EventSystem is not None,
        'Logger': True,  # 常に利用可能
        'Exceptions': True,  # 常に利用可能
        'LoggingConfigured': is_logging_configured(),
        'LoggingHandlers': get_logging_config().get('handlers_count', 0) if is_logging_configured() else 0
    }

def shutdown_core():
    """
    コア機能の終了処理
    """
    try:
        logger = get_logger(__name__)
        logger.info("コア機能の終了処理を開始します")
        
        # ログシステムの終了
        shutdown_logging()
        
        print("コア機能の終了処理が完了しました")
        
    except Exception as e:
        print(f"コア機能終了エラー: {e}")

# パッケージ初期化（遅延実行）
def _delayed_init():
    """遅延初期化"""
    try:
        return initialize_core()
    except Exception as e:
        print(f"遅延初期化エラー: {e}")
        return False

# 初期化フラグ
_initialized = _delayed_init()

# クリーンアップ処理の登録
import atexit
atexit.register(shutdown_core)
