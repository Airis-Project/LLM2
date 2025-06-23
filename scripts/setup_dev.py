#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/setup_dev.py - 開発環境セットアップスクリプト

LLM Code Assistantの開発環境を自動的にセットアップするスクリプト
"""

import os
import sys
import subprocess
import argparse
import json
import shutil
import venv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import platform
import urllib.request
import zipfile
import tempfile

# プロジェクトルートディレクトリの設定
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

class SetupError(Exception):
    """セットアップエラー"""
    pass

class DevEnvironmentSetup:
    """開発環境セットアップクラス"""
    
    def __init__(self, config: Dict):
        """
        初期化
        
        Args:
            config: セットアップ設定
        """
        self.config = config
        self.project_root = PROJECT_ROOT
        self.venv_path = self.project_root / "venv"
        self.platform = platform.system().lower()
        
        # ログ設定
        self.setup_logging()
        
    def setup_logging(self):
        """ログ設定"""
        import logging
        
        # ログディレクトリの作成
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # ログファイル名
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"setup_dev_{timestamp}.log"
        
        # ロガーの設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def check_system_requirements(self):
        """システム要件のチェック"""
        self.logger.info("システム要件をチェックしています...")
        
        # Python バージョンチェック
        python_version = sys.version_info
        required_version = (3, 11)
        
        if python_version[:2] < required_version:
            raise SetupError(
                f"Python {required_version[0]}.{required_version[1]}以上が必要です。"
                f"現在のバージョン: {python_version.major}.{python_version.minor}"
            )
            
        self.logger.info(f"Python バージョン: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # 必要なシステムコマンドの確認
        required_commands = ['git', 'pip']
        
        for cmd in required_commands:
            try:
                result = subprocess.run([cmd, '--version'], 
                                      capture_output=True, check=True)
                self.logger.debug(f"{cmd} が利用可能です")
            except (subprocess.CalledProcessError, FileNotFoundError):
                if cmd == 'git':
                    self.logger.warning(f"{cmd} が見つかりません。Gitのインストールを推奨します。")
                else:
                    raise SetupError(f"{cmd} が見つかりません")
                    
        # ディスク容量チェック
        free_space = shutil.disk_usage(self.project_root).free
        required_space = 2 * 1024 * 1024 * 1024  # 2GB
        
        if free_space < required_space:
            self.logger.warning(
                f"ディスク容量が不足している可能性があります。"
                f"利用可能: {free_space // (1024**3)}GB, 推奨: {required_space // (1024**3)}GB"
            )
            
        self.logger.info("システム要件のチェックが完了しました")
        
    def create_virtual_environment(self):
        """仮想環境の作成"""
        if self.venv_path.exists() and not self.config.get('force_recreate', False):
            self.logger.info("仮想環境が既に存在します")
            if not self.config.get('skip_venv_prompt', False):
                response = input("仮想環境を再作成しますか？ (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    return
                    
        if self.venv_path.exists():
            self.logger.info("既存の仮想環境を削除しています...")
            shutil.rmtree(self.venv_path)
            
        self.logger.info("仮想環境を作成しています...")
        
        try:
            venv.create(self.venv_path, with_pip=True)
            self.logger.info(f"仮想環境を作成しました: {self.venv_path}")
        except Exception as e:
            raise SetupError(f"仮想環境の作成に失敗しました: {e}")
            
    def get_venv_python(self) -> str:
        """仮想環境のPythonパスを取得"""
        if self.platform == 'windows':
            return str(self.venv_path / "Scripts" / "python.exe")
        else:
            return str(self.venv_path / "bin" / "python")
            
    def get_venv_pip(self) -> str:
        """仮想環境のpipパスを取得"""
        if self.platform == 'windows':
            return str(self.venv_path / "Scripts" / "pip.exe")
        else:
            return str(self.venv_path / "bin" / "pip")
            
    def upgrade_pip(self):
        """pipのアップグレード"""
        self.logger.info("pipをアップグレードしています...")
        
        try:
            subprocess.run([
                self.get_venv_python(), '-m', 'pip', 'install', '--upgrade', 'pip'
            ], check=True, capture_output=True)
            self.logger.info("pipのアップグレードが完了しました")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"pipのアップグレードに失敗しました: {e}")
            
    def install_dependencies(self):
        """依存関係のインストール"""
        self.logger.info("依存関係をインストールしています...")
        
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            self.logger.warning("requirements.txtが見つかりません。基本的な依存関係をインストールします。")
            self._install_basic_dependencies()
            return
            
        try:
            subprocess.run([
                self.get_venv_pip(), 'install', '-r', str(requirements_file)
            ], check=True)
            self.logger.info("依存関係のインストールが完了しました")
        except subprocess.CalledProcessError as e:
            raise SetupError(f"依存関係のインストールに失敗しました: {e}")
            
    def _install_basic_dependencies(self):
        """基本的な依存関係のインストール"""
        basic_packages = [
            'PyQt5>=5.15.0',
            'openai>=1.0.0',
            'anthropic>=0.7.0',
            'transformers>=4.30.0',
            'torch>=2.0.0',
            'numpy>=1.24.0',
            'pandas>=2.0.0',
            'requests>=2.31.0',
            'python-dotenv>=1.0.0',
            'pyyaml>=6.0',
            'jinja2>=3.1.0',
            'cryptography>=41.0.0',
            'pytest>=7.4.0',
            'pytest-qt>=4.2.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0'
        ]
        
        for package in basic_packages:
            try:
                self.logger.info(f"インストール中: {package}")
                subprocess.run([
                    self.get_venv_pip(), 'install', package
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"{package}のインストールに失敗しました: {e}")
                
    def install_development_tools(self):
        """開発ツールのインストール"""
        if not self.config.get('install_dev_tools', True):
            return
            
        self.logger.info("開発ツールをインストールしています...")
        
        dev_packages = [
            'pytest-cov>=4.1.0',
            'pytest-mock>=3.11.0',
            'sphinx>=7.1.0',
            'sphinx-rtd-theme>=1.3.0',
            'pre-commit>=3.3.0',
            'pyinstaller>=5.13.0',
            'wheel>=0.41.0',
            'twine>=4.0.0'
        ]
        
        for package in dev_packages:
            try:
                self.logger.info(f"開発ツールをインストール中: {package}")
                subprocess.run([
                    self.get_venv_pip(), 'install', package
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"{package}のインストールに失敗しました: {e}")
                
    def setup_git_hooks(self):
        """Gitフックのセットアップ"""
        if not self.config.get('setup_git_hooks', True):
            return
            
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            self.logger.info("Gitリポジトリが初期化されていません。Gitフックのセットアップをスキップします。")
            return
            
        self.logger.info("Gitフックをセットアップしています...")
        
        # pre-commitの設定
        precommit_config = self.project_root / ".pre-commit-config.yaml"
        if not precommit_config.exists():
            self._create_precommit_config()
            
        try:
            subprocess.run([
                self.get_venv_python(), '-m', 'pre_commit', 'install'
            ], cwd=self.project_root, check=True, capture_output=True)
            self.logger.info("pre-commitフックをインストールしました")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"pre-commitフックのインストールに失敗しました: {e}")
            
    def _create_precommit_config(self):
        """pre-commit設定ファイルの作成"""
        config_content = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements
      - id: requirements-txt-fixer

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
"""
        
        precommit_config = self.project_root / ".pre-commit-config.yaml"
        with open(precommit_config, 'w', encoding='utf-8') as f:
            f.write(config_content)
            
        self.logger.info("pre-commit設定ファイルを作成しました")
        
    def create_environment_file(self):
        """環境変数ファイルの作成"""
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if env_file.exists() and not self.config.get('overwrite_env', False):
            self.logger.info(".envファイルが既に存在します")
            return
            
        if env_example.exists():
            # .env.exampleから.envを作成
            shutil.copy2(env_example, env_file)
            self.logger.info(".env.exampleから.envファイルを作成しました")
        else:
            # デフォルトの.envファイルを作成
            self._create_default_env_file()
            
    def _create_default_env_file(self):
        """デフォルトの環境変数ファイルを作成"""
        env_content = """# LLM Code Assistant 環境変数設定

# OpenAI API設定
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Anthropic Claude API設定
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# ローカルLLM設定
LOCAL_LLM_MODEL_PATH=models/
LOCAL_LLM_MODEL_NAME=llama-2-7b-chat

# データベース設定
DATABASE_URL=sqlite:///data/llm_assistant.db
VECTOR_DB_PATH=data/vector_db/

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# UI設定
THEME=dark
LANGUAGE=ja

# セキュリティ設定
SECRET_KEY=your_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here

# 開発設定
DEBUG=True
DEVELOPMENT_MODE=True
"""
        
        env_file = self.project_root / ".env"
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
            
        self.logger.info("デフォルトの.envファイルを作成しました")
        
    def setup_ide_configuration(self):
        """IDE設定のセットアップ"""
        if not self.config.get('setup_ide', True):
            return
            
        self.logger.info("IDE設定をセットアップしています...")
        
        # VS Code設定
        if self.config.get('setup_vscode', True):
            self._setup_vscode_config()
            
        # PyCharm設定
        if self.config.get('setup_pycharm', False):
            self._setup_pycharm_config()
            
    def _setup_vscode_config(self):
        """VS Code設定のセットアップ"""
        vscode_dir = self.project_root / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        
        # settings.json
        settings = {
            "python.defaultInterpreterPath": str(self.get_venv_python()),
            "python.linting.enabled": True,
            "python.linting.flake8Enabled": True,
            "python.linting.mypyEnabled": True,
            "python.formatting.provider": "black",
            "python.testing.pytestEnabled": True,
            "python.testing.pytestArgs": ["tests"],
            "files.exclude": {
                "**/__pycache__": True,
                "**/*.pyc": True,
                "**/venv": True,
                "**/build": True,
                "**/dist": True
            },
            "editor.formatOnSave": True,
            "editor.codeActionsOnSave": {
                "source.organizeImports": True
            }
        }
        
        settings_file = vscode_dir / "settings.json"
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            
        # launch.json
        launch_config = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "LLM Code Assistant",
                    "type": "python",
                    "request": "launch",
                    "program": "${workspaceFolder}/src/main.py",
                    "console": "integratedTerminal",
                    "cwd": "${workspaceFolder}",
                    "env": {
                        "PYTHONPATH": "${workspaceFolder}/src"
                    }
                },
                {
                    "name": "Run Tests",
                    "type": "python",
                    "request": "launch",
                    "module": "pytest",
                    "args": ["tests/", "-v"],
                    "console": "integratedTerminal",
                    "cwd": "${workspaceFolder}"
                }
            ]
        }
        
        launch_file = vscode_dir / "launch.json"
        with open(launch_file, 'w', encoding='utf-8') as f:
            json.dump(launch_config, f, indent=2, ensure_ascii=False)
            
        # extensions.json
        extensions = {
            "recommendations": [
                "ms-python.python",
                "ms-python.flake8",
                "ms-python.mypy-type-checker",
                "ms-python.black-formatter",
                "ms-python.isort",
                "ms-vscode.vscode-json",
                "redhat.vscode-yaml",
                "ms-vscode.test-adapter-converter"
            ]
        }
        
        extensions_file = vscode_dir / "extensions.json"
        with open(extensions_file, 'w', encoding='utf-8') as f:
            json.dump(extensions, f, indent=2, ensure_ascii=False)
            
        self.logger.info("VS Code設定を作成しました")
        
    def _setup_pycharm_config(self):
        """PyCharm設定のセットアップ"""
        idea_dir = self.project_root / ".idea"
        if not idea_dir.exists():
            self.logger.info("PyCharmプロジェクトが見つかりません")
            return
            
        # 基本的な設定のみ
        self.logger.info("PyCharm設定をセットアップしました")
        
    def create_necessary_directories(self):
        """必要なディレクトリの作成"""
        self.logger.info("必要なディレクトリを作成しています...")
        
        directories = [
            "logs",
            "data/vector_db",
            "data/models",
            "data/cache",
            "test_reports",
            "docs/_build"
        ]
        
        for dir_path in directories:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"ディレクトリを作成しました: {full_path}")
            
        self.logger.info("必要なディレクトリの作成が完了しました")
        
    def run_initial_tests(self):
        """初期テストの実行"""
        if not self.config.get('run_tests', True):
            return
            
        self.logger.info("初期テストを実行しています...")
        
        try:
            result = subprocess.run([
                self.get_venv_python(), '-m', 'pytest', 'tests/', '-v', '--tb=short'
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("すべてのテストが成功しました")
            else:
                self.logger.warning("一部のテストが失敗しました")
                self.logger.warning(result.stdout)
                self.logger.warning(result.stderr)
                
        except Exception as e:
            self.logger.warning(f"テストの実行に失敗しました: {e}")
            
    def generate_setup_summary(self):
        """セットアップサマリーの生成"""
        self.logger.info("=== セットアップ完了 ===")
        
        summary = f"""
開発環境のセットアップが完了しました！

プロジェクトディレクトリ: {self.project_root}
仮想環境: {self.venv_path}
Python: {self.get_venv_python()}

次のステップ:
1. 仮想環境をアクティベート:
   - Windows: {self.venv_path}\\Scripts\\activate
   - macOS/Linux: source {self.venv_path}/bin/activate

2. 環境変数を設定:
   - .envファイルを編集してAPIキーなどを設定

3. アプリケーションを起動:
   - python src/main.py

4. テストを実行:
   - pytest tests/

開発に必要なツール:
- Black (コードフォーマッター)
- Flake8 (リンター)
- MyPy (型チェッカー)
- pytest (テストフレームワーク)
- pre-commit (Gitフック)

問題が発生した場合は、ログファイルを確認してください:
{self.project_root}/logs/
"""
        
        print(summary)
        self.logger.info("セットアップサマリーを表示しました")
        
    def setup(self):
        """開発環境のセットアップ実行"""
        try:
            self.logger.info("開発環境のセットアップを開始します...")
            
            # システム要件チェック
            self.check_system_requirements()
            
            # 仮想環境の作成
            self.create_virtual_environment()
            
            # pipのアップグレード
            self.upgrade_pip()
            
            # 依存関係のインストール
            self.install_dependencies()
            
            # 開発ツールのインストール
            self.install_development_tools()
            
            # 必要なディレクトリの作成
            self.create_necessary_directories()
            
            # 環境変数ファイルの作成
            self.create_environment_file()
            
            # IDE設定のセットアップ
            self.setup_ide_configuration()
            
            # Gitフックのセットアップ
            self.setup_git_hooks()
            
            # 初期テストの実行
            self.run_initial_tests()
            
            # セットアップサマリーの表示
            self.generate_setup_summary()
            
        except SetupError as e:
            self.logger.error(f"セットアップエラー: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}")
            sys.exit(1)

def load_config(config_file: Optional[str] = None) -> Dict:
    """設定ファイルの読み込み"""
    if config_file and Path(config_file).exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # デフォルト設定
    return {
        'force_recreate': False,
        'skip_venv_prompt': False,
        'install_dev_tools': True,
        'setup_git_hooks': True,
        'setup_ide': True,
        'setup_vscode': True,
        'setup_pycharm': False,
        'overwrite_env': False,
        'run_tests': True
    }

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='LLM Code Assistant 開発環境セットアップ')
    parser.add_argument('--config', '-c', help='設定ファイルのパス')
    parser.add_argument('--force-recreate', action='store_true',
                       help='仮想環境を強制的に再作成')
    parser.add_argument('--skip-venv-prompt', action='store_true',
                       help='仮想環境の再作成プロンプトをスキップ')
    parser.add_argument('--no-dev-tools', action='store_true',
                       help='開発ツールをインストールしない')
    parser.add_argument('--no-git-hooks', action='store_true',
                       help='Gitフックをセットアップしない')
    parser.add_argument('--no-ide', action='store_true',
                       help='IDE設定をセットアップしない')
    parser.add_argument('--no-tests', action='store_true',
                       help='初期テストを実行しない')
    parser.add_argument('--overwrite-env', action='store_true',
                       help='既存の.envファイルを上書き')
    
    args = parser.parse_args()
    
    # 設定の読み込み
    config = load_config(args.config)
    
    # コマンドライン引数による設定の上書き
    if args.force_recreate:
        config['force_recreate'] = True
    if args.skip_venv_prompt:
        config['skip_venv_prompt'] = True
    if args.no_dev_tools:
        config['install_dev_tools'] = False
    if args.no_git_hooks:
        config['setup_git_hooks'] = False
    if args.no_ide:
        config['setup_ide'] = False
    if args.no_tests:
        config['run_tests'] = False
    if args.overwrite_env:
        config['overwrite_env'] = True
        
    # セットアップの実行
    setup = DevEnvironmentSetup(config)
    setup.setup()

if __name__ == '__main__':
    main()
