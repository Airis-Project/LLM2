#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ロガーモジュール - LLM Code Assistant

アプリケーション全体のログ管理を行うモジュール
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

@dataclass
class LogConfig:
    """ログ設定クラス"""
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_dir: str = "logs"
    log_file: str = "app.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    file_output: bool = True
    json_format: bool = False

class Logger:
    """
    アプリケーション用ロガークラス
    
    シングルトンパターンでロガーインスタンスを管理し、
    統一されたログ出力を提供します。
    """
    
    _instance: Optional['Logger'] = None
    _loggers: Dict[str, logging.Logger] = {}
    _initialized: bool = False
    
    def __new__(cls, config: Optional[LogConfig] = None) -> 'Logger':
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[LogConfig] = None):
        """
        ロガーの初期化
        
        Args:
            config: ログ設定
        """
        if self._initialized:
            return
            
        self.config = config or LogConfig()
        self._setup_logging()
        self._initialized = True
    
    def _setup_logging(self):
        """ログ設定のセットアップ"""
        try:
            # ログディレクトリの作成
            log_dir = Path(self.config.log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # ログレベルの設定
            log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
            
            # ルートロガーの設定
            root_logger = logging.getLogger()
            root_logger.setLevel(log_level)
            
            # 既存のハンドラーをクリア
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # フォーマッターの作成
            if self.config.json_format:
                formatter = self._create_json_formatter()
            else:
                formatter = logging.Formatter(
                    self.config.log_format,
                    datefmt=self.config.date_format
                )
            
            # コンソールハンドラーの設定
            if self.config.console_output:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(log_level)
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)
            
            # ファイルハンドラーの設定
            if self.config.file_output:
                log_file_path = log_dir / self.config.log_file
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file_path,
                    maxBytes=self.config.max_file_size,
                    backupCount=self.config.backup_count,
                    encoding='utf-8'
                )
                file_handler.setLevel(log_level)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                
        except Exception as e:
            print(f"ログ設定の初期化に失敗: {e}", file=sys.stderr)
            # フォールバック設定
            logging.basicConfig(
                level=logging.INFO,
                format=self.config.log_format,
                datefmt=self.config.date_format
            )
    
    def _create_json_formatter(self) -> logging.Formatter:
        """JSONフォーマッターの作成"""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                
                if record.exc_info:
                    log_entry['exception'] = self.formatException(record.exc_info)
                
                return json.dumps(log_entry, ensure_ascii=False)
        
        return JsonFormatter()
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        指定された名前のロガーを取得
        
        Args:
            name: ロガー名
            
        Returns:
            logging.Logger: ロガーインスタンス
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def set_level(self, level: str):
        """
        ログレベルの動的変更
        
        Args:
            level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        try:
            log_level = getattr(logging, level.upper(), logging.INFO)
            
            # ルートロガーのレベル変更
            root_logger = logging.getLogger()
            root_logger.setLevel(log_level)
            
            # 全ハンドラーのレベル変更
            for handler in root_logger.handlers:
                handler.setLevel(log_level)
                
            self.config.log_level = level.upper()
            
        except Exception as e:
            print(f"ログレベルの変更に失敗: {e}", file=sys.stderr)
    
    def add_handler(self, handler: logging.Handler):
        """
        カスタムハンドラーの追加
        
        Args:
            handler: ログハンドラー
        """
        try:
            root_logger = logging.getLogger()
            root_logger.addHandler(handler)
        except Exception as e:
            print(f"ハンドラーの追加に失敗: {e}", file=sys.stderr)
    
    def remove_handler(self, handler: logging.Handler):
        """
        ハンドラーの削除
        
        Args:
            handler: ログハンドラー
        """
        try:
            root_logger = logging.getLogger()
            root_logger.removeHandler(handler)
        except Exception as e:
            print(f"ハンドラーの削除に失敗: {e}", file=sys.stderr)

# グローバルロガーインスタンス
_logger_instance: Optional[Logger] = None

def get_logger(name: str = __name__) -> logging.Logger:
    """
    ロガーインスタンスを取得する便利関数
    
    Args:
        name: ロガー名（デフォルトは呼び出し元のモジュール名）
        
    Returns:
        logging.Logger: ロガーインスタンス
    """
    global _logger_instance
    
    if _logger_instance is None:
        # デフォルト設定でロガーを初期化
        _logger_instance = Logger()
    
    return _logger_instance.get_logger(name)

def setup_logger(config: Optional[LogConfig] = None) -> Logger:
    """
    ロガーのセットアップ
    
    Args:
        config: ログ設定
        
    Returns:
        Logger: ロガーインスタンス
    """
    global _logger_instance
    _logger_instance = Logger(config)
    return _logger_instance

def set_log_level(level: str):
    """
    ログレベルの設定
    
    Args:
        level: ログレベル
    """
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = Logger()
    
    _logger_instance.set_level(level)

# デバッグ用の便利関数
def debug(message: str, logger_name: str = __name__):
    """デバッグログ出力"""
    get_logger(logger_name).debug(message)

def info(message: str, logger_name: str = __name__):
    """情報ログ出力"""
    get_logger(logger_name).info(message)

def warning(message: str, logger_name: str = __name__):
    """警告ログ出力"""
    get_logger(logger_name).warning(message)

def error(message: str, logger_name: str = __name__):
    """エラーログ出力"""
    get_logger(logger_name).error(message)

def critical(message: str, logger_name: str = __name__):
    """重大エラーログ出力"""
    get_logger(logger_name).critical(message)

# 初期化時の自動セットアップ
try:
    # 環境変数からログレベルを取得
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_dir = os.getenv('LOG_DIR', 'logs')
    
    # デフォルト設定でロガーを初期化
    default_config = LogConfig(
        log_level=log_level,
        log_dir=log_dir
    )
    setup_logger(default_config)
    
except Exception as e:
    # フォールバック設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    print(f"ロガーの初期化でエラーが発生しました（フォールバック設定を使用）: {e}", file=sys.stderr)
