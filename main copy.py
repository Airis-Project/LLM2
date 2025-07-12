# main.py
"""
LLM Chat System - Main Entry Point
統合されたLLMチャットシステムのメインエントリーポイント
"""

import sys
import os
import argparse
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.logger import setup_logger
from src.core.config_manager import ConfigManager
from src.core.exceptions import LLMChatError
from src.ui.cli import CLIInterface


def setup_application():
    """アプリケーションの初期設定"""
    try:
        # ロガーの初期化
        logger = setup_logger()
        logger.info("LLM Chat System starting...")
        
        # 設定管理の初期化
        config_manager = ConfigManager()
        
        # 必要なディレクトリの作成
        os.makedirs("logs", exist_ok=True)
        os.makedirs("config/backup", exist_ok=True)
        
        return logger, config_manager
        
    except Exception as e:
        print(f"Application setup failed: {e}")
        sys.exit(1)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="LLM Chat System - Multi-provider LLM chat interface"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config/default_config.json",
        help="Configuration file path"
    )
    parser.add_argument(
        "--interface", "-i",
        choices=["cli", "gui"],
        default="cli",
        help="User interface type"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="LLM Chat System 1.0.0"
    )
    
    args = parser.parse_args()
    
    try:
        # アプリケーション初期化
        logger, config_manager = setup_application()
        
        # 設定ファイルの読み込み
        if os.path.exists(args.config):
            config_manager.load_config(args.config)
            logger.info(f"Configuration loaded from: {args.config}")
        else:
            logger.warning(f"Configuration file not found: {args.config}")
            logger.info("Using default configuration")
        
        # デバッグモードの設定
        if args.debug:
            logger.setLevel("DEBUG")
            logger.debug("Debug mode enabled")
        
        # インターフェースの起動
        if args.interface == "cli":
            cli = CLIInterface(config_manager, logger)
            cli.run()
        elif args.interface == "gui":
            try:
                from src.ui.gui import GUIInterface
                gui = GUIInterface(config_manager, logger)
                gui.run()
            except ImportError:
                logger.error("GUI interface not available. Please install GUI dependencies.")
                sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except LLMChatError as e:
        print(f"Application error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
