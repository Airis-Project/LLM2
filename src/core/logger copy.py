# src/core/logger.py
"""
統合ログ管理システム
LLMシステム全体で使用される高機能ログ管理
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from datetime import datetime, timezone
import json
import traceback
from enum import Enum
import threading
from functools import wraps
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    from loguru import logger as loguru_logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


class LogLevel(Enum):
    """ログレベル定義"""
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0


class LogFormat(Enum):
    """ログフォーマット種類"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    STRUCTURED = "structured"
    COLORED = "colored"


class LoggerConfig:
    """ログ設定クラス"""
    
    def __init__(self):
        self.level: LogLevel = LogLevel.INFO
        self.format_type: LogFormat = LogFormat.DETAILED
        self.console_enabled: bool = True
        self.file_enabled: bool = True
        self.json_enabled: bool = False
        self.colored_enabled: bool = True
        self.async_enabled: bool = False
        
        # ファイル設定
        self.log_dir: Path = Path("logs")
        self.log_file: str = "llm_system.log"
        self.error_file: str = "llm_errors.log"
        self.max_file_size: int = 10 * 1024 * 1024  # 10MB
        self.backup_count: int = 5
        
        # フォーマット設定
        self.date_format: str = "%Y-%m-%d %H:%M:%S"
        self.timezone = timezone.utc
        
        # フィルタ設定
        self.include_modules: List[str] = []
        self.exclude_modules: List[str] = []
        self.sensitive_fields: List[str] = ['password', 'token', 'api_key', 'secret']
        
        # パフォーマンス設定
        self.buffer_size: int = 1000
        self.flush_interval: float = 1.0
        
        # 環境変数から設定を読み込み
        self._load_from_env()
    
    def _load_from_env(self):
        """環境変数から設定を読み込み"""
        try:
            # ログレベル
            if env_level := os.getenv('LOG_LEVEL'):
                try:
                    self.level = LogLevel[env_level.upper()]
                except KeyError:
                    pass
            
            # ログディレクトリ
            if env_dir := os.getenv('LOG_DIR'):
                self.log_dir = Path(env_dir)
            
            # ファイル有効/無効
            if env_file := os.getenv('LOG_FILE_ENABLED'):
                self.file_enabled = env_file.lower() == 'true'
            
            # コンソール有効/無効
            if env_console := os.getenv('LOG_CONSOLE_ENABLED'):
                self.console_enabled = env_console.lower() == 'true'
            
            # JSON形式有効/無効
            if env_json := os.getenv('LOG_JSON_ENABLED'):
                self.json_enabled = env_json.lower() == 'true'
            
            # 非同期有効/無効
            if env_async := os.getenv('LOG_ASYNC_ENABLED'):
                self.async_enabled = env_async.lower() == 'true'
                
        except Exception as e:
            # 環境変数読み込みエラーは無視
            pass


class LogFormatter:
    """ログフォーマッター"""
    
    @staticmethod
    def get_formatter(format_type: LogFormat, colored: bool = False) -> logging.Formatter:
        """フォーマッターを取得"""
        
        if format_type == LogFormat.SIMPLE:
            fmt = "%(levelname)s - %(message)s"
        elif format_type == LogFormat.DETAILED:
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        elif format_type == LogFormat.JSON:
            return JsonFormatter()
        elif format_type == LogFormat.STRUCTURED:
            fmt = "[%(asctime)s] %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s"
        else:
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        if colored and COLORLOG_AVAILABLE:
            return colorlog.ColoredFormatter(
                f"%(log_color)s{fmt}%(reset)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            return logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")


class JsonFormatter(logging.Formatter):
    """JSON形式フォーマッター"""
    
    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをJSON形式でフォーマット"""
        try:
            log_data = {
                'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'message': record.getMessage(),
                'thread_id': record.thread,
                'thread_name': record.threadName,
                'process_id': record.process,
            }
            
            # 例外情報があれば追加
            if record.exc_info:
                log_data['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'traceback': traceback.format_exception(*record.exc_info)
                }
            
            # 追加フィールドがあれば追加
            if hasattr(record, 'extra_fields'):
                log_data.update(record.extra_fields)
            
            return json.dumps(log_data, ensure_ascii=False, default=str)
            
        except Exception as e:
            # フォーマットエラーの場合は基本形式で出力
            return f"JSON_FORMAT_ERROR: {record.getMessage()} | Error: {e}"


class SensitiveDataFilter(logging.Filter):
    """機密データフィルター"""
    
    def __init__(self, sensitive_fields: List[str]):
        super().__init__()
        self.sensitive_fields = [field.lower() for field in sensitive_fields]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """機密データをマスク"""
        try:
            message = record.getMessage()
            
            # 機密フィールドをマスク
            for field in self.sensitive_fields:
                if field in message.lower():
                    # 簡単なマスク処理（実際はより高度な処理が必要）
                    message = message.replace(field, f"{field}=***")
            
            # メッセージを更新
            record.msg = message
            record.args = ()
            
            return True
            
        except Exception:
            return True


class AsyncLogHandler(logging.Handler):
    """非同期ログハンドラー"""
    
    def __init__(self, target_handler: logging.Handler, buffer_size: int = 1000):
        super().__init__()
        self.target_handler = target_handler
        self.buffer_size = buffer_size
        self.buffer = []
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="AsyncLogger")
        self.shutdown_event = threading.Event()
        
        # バッファフラッシュ用タイマー
        self.flush_timer = None
        self._start_flush_timer()
    
    def emit(self, record: logging.LogRecord):
        """ログレコードをバッファに追加"""
        try:
            with self.lock:
                self.buffer.append(record)
                
                if len(self.buffer) >= self.buffer_size:
                    self._flush_buffer()
                    
        except Exception:
            self.handleError(record)
    
    def _flush_buffer(self):
        """バッファをフラッシュ"""
        if not self.buffer:
            return
        
        buffer_copy = self.buffer.copy()
        self.buffer.clear()
        
        # 非同期でログを処理
        self.executor.submit(self._process_buffer, buffer_copy)
    
    def _process_buffer(self, records: List[logging.LogRecord]):
        """バッファ内のレコードを処理"""
        try:
            for record in records:
                self.target_handler.emit(record)
            self.target_handler.flush()
        except Exception as e:
            print(f"AsyncLogHandler error: {e}", file=sys.stderr)
    
    def _start_flush_timer(self):
        """フラッシュタイマーを開始"""
        def flush_periodically():
            if not self.shutdown_event.is_set():
                with self.lock:
                    if self.buffer:
                        self._flush_buffer()
                self.flush_timer = threading.Timer(1.0, flush_periodically)
                self.flush_timer.start()
        
        self.flush_timer = threading.Timer(1.0, flush_periodically)
        self.flush_timer.start()
    
    def close(self):
        """ハンドラーを閉じる"""
        self.shutdown_event.set()
        
        if self.flush_timer:
            self.flush_timer.cancel()
        
        with self.lock:
            self._flush_buffer()
        
        self.executor.shutdown(wait=True)
        self.target_handler.close()
        super().close()


class LLMLogger:
    """LLMシステム専用ログ管理クラス"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.config = LoggerConfig()
        self.loggers: Dict[str, logging.Logger] = {}
        self.handlers: List[logging.Handler] = []
        self._setup_logging()
    
    def _setup_logging(self):
        """ログ設定を初期化"""
        try:
            # ログディレクトリを作成
            self.config.log_dir.mkdir(parents=True, exist_ok=True)
            
            # ルートロガー設定
            root_logger = logging.getLogger()
            root_logger.setLevel(self.config.level.value)
            
            # 既存ハンドラーをクリア
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # コンソールハンドラー
            if self.config.console_enabled:
                self._add_console_handler()
            
            # ファイルハンドラー
            if self.config.file_enabled:
                self._add_file_handlers()
            
            # JSON ハンドラー
            if self.config.json_enabled:
                self._add_json_handler()
            
        except Exception as e:
            print(f"ログ設定エラー: {e}", file=sys.stderr)
            # フォールバック設定
            self._setup_fallback_logging()
    
    def _add_console_handler(self):
        """コンソールハンドラーを追加"""
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.config.level.value)
            
            formatter = LogFormatter.get_formatter(
                self.config.format_type,
                colored=self.config.colored_enabled
            )
            console_handler.setFormatter(formatter)
            
            # 機密データフィルター
            if self.config.sensitive_fields:
                console_handler.addFilter(
                    SensitiveDataFilter(self.config.sensitive_fields)
                )
            
            # 非同期ハンドラーでラップ
            if self.config.async_enabled:
                console_handler = AsyncLogHandler(console_handler, self.config.buffer_size)
            
            logging.getLogger().addHandler(console_handler)
            self.handlers.append(console_handler)
            
        except Exception as e:
            print(f"コンソールハンドラー設定エラー: {e}", file=sys.stderr)
    
    def _add_file_handlers(self):
        """ファイルハンドラーを追加"""
        try:
            # 通常ログファイル
            file_handler = logging.handlers.RotatingFileHandler(
                self.config.log_dir / self.config.log_file,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.config.level.value)
            
            formatter = LogFormatter.get_formatter(LogFormat.DETAILED)
            file_handler.setFormatter(formatter)
            
            # エラー専用ログファイル
            error_handler = logging.handlers.RotatingFileHandler(
                self.config.log_dir / self.config.error_file,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            
            # 機密データフィルター
            if self.config.sensitive_fields:
                sensitive_filter = SensitiveDataFilter(self.config.sensitive_fields)
                file_handler.addFilter(sensitive_filter)
                error_handler.addFilter(sensitive_filter)
            
            # 非同期ハンドラーでラップ
            if self.config.async_enabled:
                file_handler = AsyncLogHandler(file_handler, self.config.buffer_size)
                error_handler = AsyncLogHandler(error_handler, self.config.buffer_size)
            
            logging.getLogger().addHandler(file_handler)
            logging.getLogger().addHandler(error_handler)
            self.handlers.extend([file_handler, error_handler])
            
        except Exception as e:
            print(f"ファイルハンドラー設定エラー: {e}", file=sys.stderr)
    
    def _add_json_handler(self):
        """JSONハンドラーを追加"""
        try:
            json_file = self.config.log_dir / "llm_system.json"
            json_handler = logging.handlers.RotatingFileHandler(
                json_file,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
            json_handler.setLevel(self.config.level.value)
            json_handler.setFormatter(JsonFormatter())
            
            # 非同期ハンドラーでラップ
            if self.config.async_enabled:
                json_handler = AsyncLogHandler(json_handler, self.config.buffer_size)
            
            logging.getLogger().addHandler(json_handler)
            self.handlers.append(json_handler)
            
        except Exception as e:
            print(f"JSONハンドラー設定エラー: {e}", file=sys.stderr)
    
    def _setup_fallback_logging(self):
        """フォールバックログ設定"""
        try:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logging.getLogger().addHandler(handler)
            self.handlers.append(handler)
            
        except Exception as e:
            print(f"フォールバックログ設定エラー: {e}", file=sys.stderr)
    
    def get_logger(self, name: str) -> logging.Logger:
        """指定名のロガーを取得"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            
            # モジュールフィルタリング
            if self.config.include_modules and name not in self.config.include_modules:
                logger.setLevel(logging.CRITICAL + 1)  # 実質無効化
            elif name in self.config.exclude_modules:
                logger.setLevel(logging.CRITICAL + 1)  # 実質無効化
            
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def update_config(self, **kwargs):
        """設定を更新"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # ログ設定を再初期化
            self._cleanup_handlers()
            self._setup_logging()
            
        except Exception as e:
            print(f"設定更新エラー: {e}", file=sys.stderr)
    
    def _cleanup_handlers(self):
        """既存ハンドラーをクリーンアップ"""
        try:
            root_logger = logging.getLogger()
            for handler in self.handlers:
                root_logger.removeHandler(handler)
                handler.close()
            self.handlers.clear()
            
        except Exception as e:
            print(f"ハンドラークリーンアップエラー: {e}", file=sys.stderr)
    
    def shutdown(self):
        """ログシステムを終了"""
        try:
            self._cleanup_handlers()
            logging.shutdown()
            
        except Exception as e:
            print(f"ログシステム終了エラー: {e}", file=sys.stderr)


# グローバルロガーインスタンス
_logger_manager = None


def get_logger_manager() -> LLMLogger:
    """ログマネージャーを取得"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LLMLogger()
    return _logger_manager


def get_logger(name: str = None) -> logging.Logger:
    """ロガーを取得（メイン関数）"""
    if name is None:
        # 呼び出し元のモジュール名を自動取得
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    return get_logger_manager().get_logger(name)


def configure_logging(**kwargs):
    """ログ設定を更新"""
    get_logger_manager().update_config(**kwargs)


def shutdown_logging():
    """ログシステムを終了"""
    global _logger_manager
    if _logger_manager:
        _logger_manager.shutdown()
        _logger_manager = None


# デコレータ関数
def log_function_call(logger: logging.Logger = None, level: int = logging.INFO):
    """関数呼び出しをログ出力するデコレータ"""
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            logger.log(level, f"関数呼び出し開始: {func_name}")
            
            try:
                start_time = datetime.now()
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                logger.log(level, f"関数呼び出し完了: {func_name} (実行時間: {duration:.3f}秒)")
                return result
                
            except Exception as e:
                logger.error(f"関数呼び出しエラー: {func_name} - {e}")
                raise
        
        return wrapper
    return decorator


def log_async_function_call(logger: logging.Logger = None, level: int = logging.INFO):
    """非同期関数呼び出しをログ出力するデコレータ"""
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            logger.log(level, f"非同期関数呼び出し開始: {func_name}")
            
            try:
                start_time = datetime.now()
                result = await func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                logger.log(level, f"非同期関数呼び出し完了: {func_name} (実行時間: {duration:.3f}秒)")
                return result
                
            except Exception as e:
                logger.error(f"非同期関数呼び出しエラー: {func_name} - {e}")
                raise
        
        return wrapper
    return decorator


# 便利関数
def log_exception(logger: logging.Logger, message: str = "例外が発生しました"):
    """例外情報をログ出力"""
    logger.error(message, exc_info=True)


def log_performance(logger: logging.Logger, operation: str, duration: float, 
                   threshold: float = 1.0):
    """パフォーマンス情報をログ出力"""
    if duration > threshold:
        logger.warning(f"パフォーマンス警告: {operation} - {duration:.3f}秒 (閾値: {threshold}秒)")
    else:
        logger.info(f"パフォーマンス: {operation} - {duration:.3f}秒")


def log_api_call(logger: logging.Logger, endpoint: str, method: str, 
                status_code: int = None, duration: float = None):
    """API呼び出し情報をログ出力"""
    message = f"API呼び出し: {method} {endpoint}"
    
    if status_code is not None:
        message += f" - ステータス: {status_code}"
    
    if duration is not None:
        message += f" - 実行時間: {duration:.3f}秒"
    
    if status_code and status_code >= 400:
        logger.error(message)
    else:
        logger.info(message)


# 初期化チェック
def is_logging_configured() -> bool:
    """ログが設定済みかチェック"""
    return _logger_manager is not None


# 設定情報取得
def get_logging_config() -> dict:
    """現在のログ設定を取得"""
    try:
        manager = get_logger_manager()
        config = manager.config
        
        return {
            'level': config.level.name,
            'format_type': config.format_type.value,
            'console_enabled': config.console_enabled,
            'file_enabled': config.file_enabled,
            'json_enabled': config.json_enabled,
            'async_enabled': config.async_enabled,
            'log_dir': str(config.log_dir),
            'log_file': config.log_file,
            'error_file': config.error_file,
            'handlers_count': len(manager.handlers),
            'loggers_count': len(manager.loggers)
        }
        
    except Exception as e:
        return {'error': str(e)}


# 使用例
if __name__ == "__main__":
    # 基本使用例
    logger = get_logger(__name__)
    logger.info("ログシステムテスト開始")
    
    # 設定変更例
    configure_logging(
        level=LogLevel.DEBUG,
        format_type=LogFormat.JSON,
        async_enabled=True
    )
    
    # デコレータ使用例
    @log_function_call()
    def test_function():
        logger.debug("テスト関数実行中")
        return "テスト完了"
    
    result = test_function()
    logger.info(f"結果: {result}")
    
    # 設定情報表示
    config_info = get_logging_config()
    logger.info(f"現在の設定: {config_info}")
    
    # 終了
    logger.info("ログシステムテスト完了")
    shutdown_logging()
