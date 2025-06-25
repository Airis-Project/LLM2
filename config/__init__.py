# scripts/init.py
"""
LLM Chat System Initialization Script
システムの初期化とセットアップを行うスクリプト
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import setup_logger
from src.core.config_manager import ConfigManager
from src.core.config_validator import ConfigValidator


class SystemInitializer:
    """システム初期化クラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.logger = setup_logger("SystemInitializer")
        
    def initialize(self, force: bool = False) -> bool:
        """システムを初期化"""
        try:
            self.logger.info("Starting system initialization...")
            
            # 1. ディレクトリ構造の作成
            self._create_directories()
            
            # 2. 設定ファイルの初期化
            self._initialize_config(force)
            
            # 3. 環境ファイルの作成
            self._create_env_file(force)
            
            # 4. ログディレクトリの準備
            self._prepare_logging()
            
            # 5. データディレクトリの準備
            self._prepare_data_directories()
            
            # 6. 権限の設定
            self._set_permissions()
            
            self.logger.info("System initialization completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            return False
    
    def _create_directories(self):
        """必要なディレクトリを作成"""
        directories = [
            "config",
            "config/backup",
            "config/examples",
            "logs",
            "data",
            "data/chat_history",
            "data/sessions",
            "temp",
            "cache",
            "scripts",
            "tests",
            "docs"
        ]
        
        for dir_path in directories:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {full_path}")
    
    def _initialize_config(self, force: bool = False):
        """設定ファイルを初期化"""
        config_path = self.project_root / "config" / "default_config.json"
        
        if config_path.exists() and not force:
            self.logger.info("Configuration file already exists, skipping...")
            return
        
        # デフォルト設定の作成
        default_config = self._get_default_config()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Created default configuration: {config_path}")
        
        # 設定の検証
        try:
            validator = ConfigValidator()
            validator.validate_config(default_config)
            self.logger.info("Configuration validation passed")
        except Exception as e:
            self.logger.warning(f"Configuration validation failed: {e}")
    
    def _create_env_file(self, force: bool = False):
        """環境ファイルを作成"""
        env_path = self.project_root / ".env"
        env_example_path = self.project_root / ".env.example"
        
        # .env.exampleが存在し、.envが存在しない場合のみ作成
        if env_example_path.exists() and (not env_path.exists() or force):
            shutil.copy2(env_example_path, env_path)
            self.logger.info("Created .env file from .env.example")
            self.logger.warning("Please edit .env file with your actual API keys!")
    
    def _prepare_logging(self):
        """ログシステムの準備"""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # ログファイルの初期化
        log_file = log_dir / "llm_chat.log"
        if not log_file.exists():
            log_file.touch()
        
        self.logger.info("Logging system prepared")
    
    def _prepare_data_directories(self):
        """データディレクトリの準備"""
        data_dirs = [
            "data/chat_history",
            "data/sessions",
            "data/exports",
            "data/imports"
        ]
        
        for dir_path in data_dirs:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            
            # README.mdを作成
            readme_path = full_path / "README.md"
            if not readme_path.exists():
                readme_content = f"# {dir_path.replace('/', ' ').title()}\n\nThis directory is used for {dir_path.split('/')[-1]}.\n"
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
    
    def _set_permissions(self):
        """ファイル権限の設定"""
        try:
            # Unixライクシステムでのみ実行
            if os.name == 'posix':
                # 実行可能ファイルの権限設定
                executable_files = [
                    "main.py",
                    "scripts/init.py",
                    "scripts/start.py"
                ]
                
                for file_path in executable_files:
                    full_path = self.project_root / file_path
                    if full_path.exists():
                        os.chmod(full_path, 0o755)
                        self.logger.debug(f"Set executable permission: {full_path}")
                
        except Exception as e:
            self.logger.warning(f"Failed to set permissions: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        return {
            "version": "1.0.0",
            "application": {
                "name": "LLM Chat System",
                "debug": False,
                "log_level": "INFO",
                "auto_save": True,
                "session_timeout": 3600
            },
            "llm": {
                "default_provider": "openai",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0,
                "providers": {
                    "openai": {
                        "enabled": True,
                        "api_key": "${OPENAI_API_KEY}",
                        "organization": "${OPENAI_ORG_ID}",
                        "base_url": "https://api.openai.com/v1",
                        "models": {
                            "default": "gpt-3.5-turbo",
                            "available": [
                                "gpt-3.5-turbo",
                                "gpt-3.5-turbo-16k",
                                "gpt-4",
                                "gpt-4-turbo-preview"
                            ]
                        },
                        "parameters": {
                            "temperature": 0.7,
                            "max_tokens": 2000,
                            "top_p": 1.0,
                            "frequency_penalty": 0.0,
                            "presence_penalty": 0.0
                        }
                    }
                }
            },
            "ui": {
                "default_interface": "cli",
                "cli": {
                    "prompt_style": "colorful",
                    "show_timestamps": True,
                    "auto_complete": True,
                    "history_size": 1000
                }
            },
            "logging": {
                "level": "INFO",
                "file_path": "logs/llm_chat.log",
                "max_file_size": "10MB",
                "backup_count": 5,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "console_output": True,
                "file_output": True
            },
            "storage": {
                "chat_history": {
                    "enabled": True,
                    "max_sessions": 100,
                    "auto_save_interval": 300,
                    "storage_path": "data/chat_history"
                }
            },
            "security": {
                "api_key_validation": True,
                "rate_limiting": {
                    "enabled": True,
                    "requests_per_minute": 60,
                    "burst_limit": 10
                },
                "input_sanitization": True
            }
        }
    
    def check_system_status(self) -> Dict[str, Any]:
        """システム状態をチェック"""
        status = {
            "directories": {},
            "configuration": {},
            "dependencies": {},
            "environment": {}
        }
        
        # ディレクトリチェック
        required_dirs = ["config", "logs", "data", "src"]
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            status["directories"][dir_name] = dir_path.exists()
        
        # 設定ファイルチェック
        config_files = [
            "config/default_config.json",
            "config/schema.json",
            ".env"
        ]
        for config_file in config_files:
            file_path = self.project_root / config_file
            status["configuration"][config_file] = file_path.exists()
        
        # 環境変数チェック
        env_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
        for env_var in env_vars:
            status["environment"][env_var] = bool(os.getenv(env_var))
        
        return status


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM Chat System Initializer")
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force initialization (overwrite existing files)"
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check system status only"
    )
    
    args = parser.parse_args()
    
    initializer = SystemInitializer()
    
    if args.check:
        # システム状態チェック
        status = initializer.check_system_status()
        
        print("\n🔍 System Status Check")
        print("=" * 50)
        
        for category, items in status.items():
            print(f"\n📁 {category.title()}:")
            for item, exists in items.items():
                icon = "✅" if exists else "❌"
                print(f"  {icon} {item}")
        
        return
    
    # システム初期化
    print("\n🚀 LLM Chat System Initializer")
    print("=" * 50)
    
    if args.force:
        print("⚠️  Force mode enabled - existing files will be overwritten")
    
    success = initializer.initialize(force=args.force)
    
    if success:
        print("\n✅ System initialization completed successfully!")
        print("\n📝 Next steps:")
        print("1. Edit .env file with your API keys")
        print("2. Review config/default_config.json")
        print("3. Run: python main.py")
    else:
        print("\n❌ System initialization failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
