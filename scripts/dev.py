# scripts/dev.py
"""
Development Utilities Script
開発用ユーティリティスクリプト
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import setup_logger


class DevelopmentTools:
    """開発ツールクラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.logger = setup_logger("DevelopmentTools")
        
    def setup_dev_environment(self) -> bool:
        """開発環境をセットアップ"""
        try:
            self.logger.info("Setting up development environment...")
            
            # 1. 仮想環境の作成
            self._create_virtual_environment()
            
            # 2. 開発依存関係のインストール
            self._install_dev_dependencies()
            
            # 3. プリコミットフックの設定
            self._setup_pre_commit_hooks()
            
            # 4. 開発用設定ファイルの作成
            self._create_dev_config()
            
            # 5. テストデータの準備
            self._prepare_test_data()
            
            self.logger.info("Development environment setup completed!")
            return True
            
        except Exception as e:
            self.logger.error(f"Development environment setup failed: {e}")
            return False
    
    def _create_virtual_environment(self):
        """仮想環境を作成"""
        venv_path = self.project_root / "venv"
        
        if venv_path.exists():
            self.logger.info("Virtual environment already exists")
            return
        
        self.logger.info("Creating virtual environment...")
        subprocess.run([
            sys.executable, "-m", "venv", str(venv_path)
        ], check=True)
        
        self.logger.info("Virtual environment created successfully")
    
    def _install_dev_dependencies(self):
        """開発依存関係をインストール"""
        self.logger.info("Installing development dependencies...")
        
        # 基本依存関係
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        
        # 開発専用依存関係
        dev_packages = [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0"
        ]
        
        for package in dev_packages:
            subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], check=True)
        
        self.logger.info("Development dependencies installed")
    
    def _setup_pre_commit_hooks(self):
        """プリコミットフックを設定"""
        pre_commit_config = {
            "repos": [
                {
                    "repo": "https://github.com/psf/black",
                    "rev": "23.0.0",
                    "hooks": [{"id": "black"}]
                },
                {
                    "repo": "https://github.com/pycqa/flake8",
                    "rev": "6.0.0",
                    "hooks": [{"id": "flake8"}]
                },
                {
                    "repo": "https://github.com/pre-commit/mirrors-mypy",
                    "rev": "v1.0.0",
                    "hooks": [{"id": "mypy"}]
                }
            ]
        }
        
        config_path = self.project_root / ".pre-commit-config.yaml"
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(pre_commit_config, f)
        
        # プリコミットフックをインストール
        try:
            subprocess.run(["pre-commit", "install"], check=True)
            self.logger.info("Pre-commit hooks installed")
        except subprocess.CalledProcessError:
            self.logger.warning("Failed to install pre-commit hooks")
    
    def _create_dev_config(self):
        """開発用設定ファイルを作成"""
        dev_config = {
            "version": "1.0.0",
            "application": {
                "name": "LLM Chat System - Development",
                "debug": True,
                "log_level": "DEBUG",
                "auto_save": True
            },
            "llm": {
                "default_provider": "openai",
                "timeout": 10,
                "max_retries": 1,
                "providers": {
                    "openai": {
                        "enabled": True,
                        "api_key": "${OPENAI_API_KEY}",
                        "models": {
                            "default": "gpt-3.5-turbo",
                            "available": ["gpt-3.5-turbo"]
                        },
                        "parameters": {
                            "temperature": 0.1,
                            "max_tokens": 100
                        }
                    }
                }
            },
            "ui": {
                "default_interface": "cli",
                "cli": {
                    "prompt_style": "simple",
                    "show_timestamps": True
                }
            },
            "logging": {
                "level": "DEBUG",
                "console_output": True,
                "file_output": True
            }
        }
        
        dev_config_path = self.project_root / "config" / "dev_config.json"
        with open(dev_config_path, 'w', encoding='utf-8') as f:
            json.dump(dev_config, f, indent=2, ensure_ascii=False)
        
        self.logger.info("Development configuration created")
    
    def _prepare_test_data(self):
        """テストデータを準備"""
        test_data_dir = self.project_root / "tests" / "data"
        test_data_dir.mkdir(parents=True, exist_ok=True)
        
        # サンプル設定ファイル
        sample_configs = {
            "valid_config.json": {
                "version": "1.0.0",
                "application": {"name": "Test App"},
                "llm": {
                    "default_provider": "test",
                    "providers": {
                        "test": {
                            "enabled": True,
                            "api_key": "test_key",
                            "models": {
                                "default": "test-model",
                                "available": ["test-model"]
                            }
                        }
                    }
                }
            },
            "invalid_config.json": {
                "version": "invalid_version",
                "application": {}
            }
        }
        
        for filename, config in sample_configs.items():
            config_path = test_data_dir / filename
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        
        self.logger.info("Test data prepared")
    
    def run_tests(self, coverage: bool = False, verbose: bool = False) -> bool:
        """テストを実行"""
        try:
            cmd = [sys.executable, "-m", "pytest"]
            
            if coverage:
                cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
            
            if verbose:
                cmd.append("-v")
            
            cmd.append("tests/")
            
            self.logger.info(f"Running tests: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.project_root)
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            return False
    
    def run_linting(self) -> bool:
        """リンティングを実行"""
        try:
            # Black (コードフォーマット)
            self.logger.info("Running Black...")
            subprocess.run([
                sys.executable, "-m", "black", "src/", "tests/", "scripts/"
            ], check=True)
            
            # Flake8 (スタイルチェック)
            self.logger.info("Running Flake8...")
            subprocess.run([
                sys.executable, "-m", "flake8", "src/", "tests/", "scripts/"
            ], check=True)
            
            # MyPy (型チェック)
            self.logger.info("Running MyPy...")
            try:
                subprocess.run([
                    sys.executable, "-m", "mypy", "src/"
                ], check=True)
            except subprocess.CalledProcessError:
                self.logger.warning("MyPy found type issues")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Linting failed: {e}")
            return False
    
    def build_docs(self) -> bool:
        """ドキュメントをビルド"""
        try:
            docs_dir = self.project_root / "docs"
            build_dir = docs_dir / "_build"
            
            # Sphinxドキュメントのビルド
            subprocess.run([
                "sphinx-build", "-b", "html", str(docs_dir), str(build_dir)
            ], check=True)
            
            self.logger.info(f"Documentation built successfully: {build_dir}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Documentation build failed: {e}")
            return False
        except FileNotFoundError:
            self.logger.error("Sphinx not found. Please install sphinx.")
            return False
    
    def clean_project(self):
        """プロジェクトをクリーンアップ"""
        import shutil
        
        cleanup_patterns = [
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".pytest_cache",
            ".coverage",
            "htmlcov",
            ".mypy_cache",
            "dist",
            "build",
            "*.egg-info"
        ]
        
        for pattern in cleanup_patterns:
            if pattern.startswith("*."):
                # ファイルパターン
                for file_path in self.project_root.rglob(pattern):
                    if file_path.is_file():
                        file_path.unlink()
                        self.logger.debug(f"Removed file: {file_path}")
            else:
                # ディレクトリパターン
                for dir_path in self.project_root.rglob(pattern):
                    if dir_path.is_dir():
                        shutil.rmtree(dir_path)
                        self.logger.debug(f"Removed directory: {dir_path}")
        
        self.logger.info("Project cleanup completed")


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Development Tools")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # セットアップコマンド
    subparsers.add_parser("setup", help="Setup development environment")
    
    # テストコマンド
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    test_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # リンティングコマンド
    subparsers.add_parser("lint", help="Run linting tools")
    
    # ドキュメントコマンド
    subparsers.add_parser("docs", help="Build documentation")
    
    # クリーンアップコマンド
    subparsers.add_parser("clean", help="Clean project files")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    dev_tools = DevelopmentTools()
    
    if args.command == "setup":
        success = dev_tools.setup_dev_environment()
        sys.exit(0 if success else 1)
    
    elif args.command == "test":
        success = dev_tools.run_tests(
            coverage=args.coverage,
            verbose=args.verbose
        )
        sys.exit(0 if success else 1)
    
    elif args.command == "lint":
        success = dev_tools.run_linting()
        sys.exit(0 if success else 1)
    
    elif args.command == "docs":
        success = dev_tools.build_docs()
        sys.exit(0 if success else 1)
    
    elif args.command == "clean":
        dev_tools.clean_project()


if __name__ == "__main__":
    main()
