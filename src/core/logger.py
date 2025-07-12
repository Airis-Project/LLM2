#!/usr/bin/env python3
"""
ログシステム - 統合ログ管理
"""

import logging
import logging.handlers
import sys
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict
import threading
import queue
import asyncio
from concurrent.futures import ThreadPoolExecutor

# ログレベル定義
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

@dataclass
class LogConfig:
    """ログ設定"""
    level: str = 'INFO'
    format_type: str = 'detailed'
    console_enabled: bool = True
    file_enabled: bool = True
    json_enabled: bool = False
    async_enabled: bool = False
    log_dir: str = 'logs'
    log_file: str = 'llm_system.log'
    error_file: str = 'llm_errors.log'
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    encoding: str = 'utf-8'

class Logger:
    """統合ログクラス"""
    
    def __init__(self, name: str, config: Optional[LogConfig] = None):
        self.name = name
        self.config = config or LogConfig()
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """ログ設定"""
        self.logger.setLevel(LOG_LEVELS.get(self.config.level, logging.INFO))
        
        # 既存のハンドラーをクリア
        self.logger.handlers.clear()
        
        # コンソールハンドラー
        if self.config.console_enabled:
            self._add_console_handler()
        
        # ファイルハンドラー
        if self.config.file_enabled:
            self._add_file_handler()
    
    def _add_console_handler(self):
        """コンソールハンドラー追加"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self._get_formatter())
        self.logger.addHandler(handler)
    
    def _add_file_handler(self):
        """ファイルハンドラー追加"""
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(exist_ok=True)
        
        # 通常ログファイル
        log_file = log_dir / self.config.log_file
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding=self.config.encoding
        )
        handler.setFormatter(self._get_formatter())
        self.logger.addHandler(handler)
        
        # エラーログファイル
        error_file = log_dir / self.config.error_file
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding=self.config.encoding
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self._get_formatter())
        self.logger.addHandler(error_handler)
    
    def _get_formatter(self) -> logging.Formatter:
        """フォーマッター取得"""
        if self.config.format_type == 'simple':
            return logging.Formatter('%(levelname)s - %(message)s')
        elif self.config.format_type == 'detailed':
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
        elif self.config.format_type == 'json':
            return JsonFormatter()
        else:
            return logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def debug(self, message: str, **kwargs):
        """デバッグログ"""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """情報ログ"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告ログ"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """エラーログ"""
        self.logger.error(message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """重大エラーログ"""
        self.logger.critical(message, exc_info=exc_info, **kwargs)

class JsonFormatter(logging.Formatter):
    """JSON形式フォーマッター"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage()
        }
        
        if record.exc_info:
            log_data['exception'] = traceback.format_exception(*record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)
    
def shutdown_logging():
    """ログシステム終了処理"""
    try:
        # 全てのハンドラーを閉じる
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
        
        # ログレベルをリセット
        root_logger.setLevel(logging.WARNING)
        
        # ログファイルのフラッシュ
        logging.shutdown()
        
    except Exception as e:
        print(f"ログ終了処理エラー: {e}")

class LoggerManager:
    """ログマネージャー"""
    
    def __init__(self):
        self.loggers: Dict[str, Logger] = {}
        self.config = LogConfig()
        self._lock = threading.Lock()
    
    def get_logger(self, name: str, config: Optional[LogConfig] = None) -> Logger:
        """ログ取得"""
        with self._lock:
            if name not in self.loggers:
                self.loggers[name] = Logger(name, config or self.config)
            return self.loggers[name]
    
    def configure_all(self, config: LogConfig):
        """全ログ設定"""
        self.config = config
        with self._lock:
            for logger in self.loggers.values():
                logger.config = config
                logger._setup_logger()
    
    def get_all_loggers(self) -> Dict[str, Logger]:
        """全ログ取得"""
        with self._lock:
            return self.loggers.copy()
    
    def shutdown_all(self):
        """全ログ終了"""
        with self._lock:
            shutdown_logging()
            self.loggers.clear()

# グローバルログマネージャー
_global_logger_manager = LoggerManager()

def get_logger_manager() -> LoggerManager:
    """ログマネージャー取得"""
    return _global_logger_manager

def setup_logger(name: str, config: Optional[LogConfig] = None) -> Logger:
    """ログ設定 - 既存コードとの互換性のため"""
    return get_logger(name, config)

def get_logger(name: str, config: Optional[LogConfig] = None) -> Logger:
    """ログ取得"""
    return _global_logger_manager.get_logger(name, config)

def configure_logging(config: LogConfig):
    """グローバルログ設定"""
    _global_logger_manager.configure_all(config)

def _setup_logging(config: Optional[Dict[str, Any]] = None):
    """内部ログ設定 - main.pyとの互換性のため"""
    if config:
        log_config = LogConfig(**config)
        configure_logging(log_config)
    return get_logger(__name__)

# 標準ログ関数
def debug(message: str, logger_name: str = __name__):
    """デバッグログ"""
    get_logger(logger_name).debug(message)

def info(message: str, logger_name: str = __name__):
    """情報ログ"""
    get_logger(logger_name).info(message)

def warning(message: str, logger_name: str = __name__):
    """警告ログ"""
    get_logger(logger_name).warning(message)

def error(message: str, exc_info: bool = False, logger_name: str = __name__):
    """エラーログ"""
    get_logger(logger_name).error(message, exc_info=exc_info)

def critical(message: str, exc_info: bool = False, logger_name: str = __name__):
    """重大エラーログ"""
    get_logger(logger_name).critical(message, exc_info=exc_info)

# 非同期ログ機能
class AsyncLogger:
    """非同期ログクラス"""
    
    def __init__(self, base_logger: Logger):
        self.base_logger = base_logger
        self.queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.running = True
        self._start_worker()
    
    def _start_worker(self):
        """ワーカー開始"""
        def worker():
            while self.running:
                try:
                    item = self.queue.get(timeout=1)
                    if item is None:
                        break
                    
                    level, message, kwargs = item
                    getattr(self.base_logger, level)(message, **kwargs)
                    self.queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Async logger error: {e}")
        
        self.executor.submit(worker)
    
    def log(self, level: str, message: str, **kwargs):
        """非同期ログ"""
        if self.running:
            self.queue.put((level, message, kwargs))
    
    def debug(self, message: str, **kwargs):
        self.log('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self.log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.log('critical', message, **kwargs)
    
    def shutdown(self):
        """シャットダウン"""
        self.running = False
        self.queue.put(None)
        self.executor.shutdown(wait=True)

def get_async_logger(name: str, config: Optional[LogConfig] = None) -> AsyncLogger:
    """非同期ログ取得"""
    base_logger = get_logger(name, config)
    return AsyncLogger(base_logger)

# ログ統計
class LogStats:
    """ログ統計"""
    
    def __init__(self):
        self.stats = {
            'DEBUG': 0,
            'INFO': 0,
            'WARNING': 0,
            'ERROR': 0,
            'CRITICAL': 0
        }
        self.start_time = datetime.now()
    
    def increment(self, level: str):
        """カウント増加"""
        if level in self.stats:
            self.stats[level] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """統計取得"""
        return {
            'stats': self.stats.copy(),
            'total': sum(self.stats.values()),
            'uptime': (datetime.now() - self.start_time).total_seconds(),
            'start_time': self.start_time.isoformat()
        }

# グローバル統計
_global_stats = LogStats()

class StatsHandler(logging.Handler):
    """統計ハンドラー"""
    
    def emit(self, record):
        _global_stats.increment(record.levelname)

def get_log_stats() -> Dict[str, Any]:
    """ログ統計取得"""
    return _global_stats.get_stats()

# 初期化
def initialize_logging(config: Optional[Dict[str, Any]] = None) -> Logger:
    """ログシステム初期化"""
    if config:
        log_config = LogConfig(**config)
        configure_logging(log_config)
    
    # 統計ハンドラー追加
    stats_handler = StatsHandler()
    logging.getLogger().addHandler(stats_handler)
    
    return get_logger(__name__)

# デフォルトロガー
default_logger = get_logger(__name__)

def log_function_call(func):
    """関数呼び出しログ装飾子"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"関数呼び出し: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"関数完了: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"関数エラー: {func.__name__} - {e}")
            raise
    return wrapper

def log_async_function_call(func):
    """非同期関数呼び出しログ装飾子"""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"非同期関数呼び出し: {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"非同期関数完了: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"非同期関数エラー: {func.__name__} - {e}")
            raise
    return wrapper

def log_exception(exc: Exception, logger_name: str = __name__):
    """例外ログ"""
    get_logger(logger_name).error(f"例外発生: {exc}", exc_info=True)

def log_performance(func_name: str, duration: float, logger_name: str = __name__):
    """パフォーマンスログ"""
    get_logger(logger_name).info(f"パフォーマンス: {func_name} - {duration:.3f}秒")

def log_api_call(api_name: str, status: str, duration: float = None, logger_name: str = __name__):
    """API呼び出しログ"""
    logger = get_logger(logger_name)
    if duration:
        logger.info(f"API呼び出し: {api_name} - {status} ({duration:.3f}秒)")
    else:
        logger.info(f"API呼び出し: {api_name} - {status}")

def is_logging_configured() -> bool:
    """ログ設定済みかチェック"""
    return len(_global_logger_manager.loggers) > 0

def get_logging_config() -> Dict[str, Any]:
    """現在のログ設定を取得"""
    return {
        'level': _global_logger_manager.config.level,
        'format_type': _global_logger_manager.config.format_type,
        'console_enabled': _global_logger_manager.config.console_enabled,
        'file_enabled': _global_logger_manager.config.file_enabled,
        'handlers_count': len(logging.getLogger().handlers)
    }

# ログレベルとフォーマット定義（core/__init__.pyで使用）
class LogLevel:
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'

class LogFormat:
    SIMPLE = 'simple'
    DETAILED = 'detailed'
    JSON = 'json'

# エクスポートリストを統一
__all__ = [
    # 基本ログ機能
    'Logger', 'LogConfig', 'LoggerManager', 'JsonFormatter',
    'get_logger', 'get_logger_manager', 'setup_logger', 'configure_logging', 
    'shutdown_logging', 'initialize_logging', '_setup_logging',
    
    # 非同期ログ
    'AsyncLogger', 'get_async_logger',
    
    # ログ統計
    'LogStats', 'get_log_stats', 'StatsHandler',
    
    # ログ装飾子
    'log_function_call', 'log_async_function_call', 'log_exception', 
    'log_performance', 'log_api_call',
    
    # ログ設定
    'is_logging_configured', 'get_logging_config',
    'LogLevel', 'LogFormat',
    
    # 標準ログ関数
    'debug', 'info', 'warning', 'error', 'critical'
]