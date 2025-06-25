"""
ログ機能を提供するモジュール
"""
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """カラー付きログフォーマッター"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # シアン
        'INFO': '\033[32m',     # 緑
        'WARNING': '\033[33m',  # 黄
        'ERROR': '\033[31m',    # 赤
        'CRITICAL': '\033[35m', # マゼンタ
        'RESET': '\033[0m'      # リセット
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> None:
    """
    ログシステムをセットアップする
    
    Args:
        log_level: ログレベル
        log_dir: ログディレクトリ
        max_bytes: ログファイルの最大サイズ
        backup_count: バックアップファイル数
        console_output: コンソール出力の有無
    """
    # ログディレクトリの作成
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 既存のハンドラーをクリア
    root_logger.handlers.clear()
    
    # ファイルハンドラーの設定
    log_file = log_path / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # コンソールハンドラーの設定
    if console_output:
        console_handler = logging.StreamHandler()
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得する
    
    Args:
        name: ロガー名
        
    Returns:
        logging.Logger: ロガーインスタンス
    """
    return logging.getLogger(name)

# デフォルトでログシステムをセットアップ
if not logging.getLogger().handlers:
    setup_logging()
