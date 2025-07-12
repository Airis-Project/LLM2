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

# グローバルログ設定
_global_config = LogConfig()
_loggers: Dict[str, Logger] = {}
_lock = threading.Lock()

def setup_logger(name: str, config: Optional[LogConfig] = None) -> Logger:
    """ログ設定 - 既存コードとの互換性のため"""
    return get_logger(name, config)

def get_logger(name: str, config: Optional[LogConfig] = None) -> Logger:
    """ログ取得"""
    with _lock:
        if name not in _loggers:
            _loggers[name] = Logger(name, config or _global_config)
        return _loggers[name]

def configure_logging(config: LogConfig):
    """グローバルログ設定"""
    global _global_config
    _global_config = config
    
    # 既存のロガーを再設定
    with _lock:
        for logger in _loggers.values():
            logger.config = config
            logger._setup_logger()

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

# エクスポート
__all__ = [
    'Logger', 'LogConfig', 'setup_logger', 'get_logger', 
    'configure_logging', '_setup_logging', 'AsyncLogger', 
    'get_async_logger', 'LogStats', 'get_log_stats',
    'initialize_logging', 'debug', 'info', 'warning', 
    'error', 'critical'
]
