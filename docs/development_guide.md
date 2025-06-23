# docs/development_guide.md

# LLM Code Assistant 開発ガイド

## 概要

このドキュメントは、LLM Code Assistantの開発に参加する開発者向けのガイドです。プロジェクトの構造、開発環境のセットアップ、コーディング規約、テスト方法などについて説明します。

## 開発環境のセットアップ

### 1. 前提条件

- Python 3.11.9以上
- Git
- Visual Studio Code（推奨）

### 2. プロジェクトのクローン

```bash
git clone https://github.com/your-org/LLM-Code-Assistant.git
cd LLM-Code-Assistant

3. 仮想環境の作成
# Python仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

4. 依存関係のインストール
# 本番依存関係のインストール
pip install -r requirements.txt

# 開発依存関係のインストール（テスト、リント等）
pip install -r requirements-dev.txt

5. 環境設定
# 環境変数ファイルの作成
cp .env.example .env

# 必要な環境変数を設定
# OPENAI_API_KEY=your_openai_api_key
# CLAUDE_API_KEY=your_claude_api_key

6. 開発用セットアップスクリプトの実行
python scripts/setup_dev.py

プロジェクト構造
ディレクトリ構成の説明

LLM-Code-Assistant/
├── src/                    # メインソースコード
│   ├── core/              # コアシステム
│   ├── llm/               # LLM関連モジュール
│   ├── ui/                # ユーザーインターフェース
│   ├── utils/             # ユーティリティ
│   └── plugins/           # プラグインシステム
├── tests/                 # テストコード
├── docs/                  # ドキュメント
├── config/                # 設定ファイル
├── data/                  # データファイル（テンプレート等）
├── assets/                # リソースファイル
└── scripts/               # ビルド・デプロイスクリプト

モジュール依存関係
graph TD
    A[main.py] --> B[core/]
    A --> C[ui/]
    B --> D[llm/]
    B --> E[utils/]
    B --> F[plugins/]
    C --> B
    C --> G[ui/components/]
    F --> H[git_integration/]
    F --> I[code_formatter/]
    F --> J[export_tools/]

コーディング規約
1. Python スタイルガイド
PEP 8準拠
インデント: スペース4つ
行の長さ: 88文字以内（Black準拠）
インポート順序: 標準ライブラリ → サードパーティ → ローカル
命名規約

# クラス名: PascalCase
class ProjectManager:
    pass

# 関数・変数名: snake_case
def load_project_config():
    project_path = "/path/to/project"

# 定数: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 1024 * 1024

# プライベートメソッド: _で開始
def _internal_method(self):
    pass

型ヒント
from typing import List, Dict, Optional, Union

def process_files(
    file_paths: List[str], 
    config: Dict[str, Any]
) -> Optional[Dict[str, str]]:
    """ファイルを処理する
    
    Args:
        file_paths: 処理するファイルパスのリスト
        config: 設定辞書
        
    Returns:
        処理結果の辞書、失敗時はNone
    """
    pass

2. ドキュメント文字列
Google スタイル
def calculate_similarity(text1: str, text2: str) -> float:
    """2つのテキストの類似度を計算する
    
    Args:
        text1: 比較対象のテキスト1
        text2: 比較対象のテキスト2
        
    Returns:
        0.0から1.0の類似度スコア
        
    Raises:
        ValueError: 入力テキストが空の場合
        
    Example:
        >>> calculate_similarity("hello", "hello world")
        0.8
    """
    pass

3. エラーハンドリング
例外処理の基本パターン
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def safe_file_operation(file_path: str) -> Optional[str]:
    """安全なファイル操作の例"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"ファイル読み込み成功: {file_path}")
        return content
        
    except FileNotFoundError:
        logger.error(f"ファイルが見つかりません: {file_path}")
        return None
        
    except PermissionError:
        logger.error(f"ファイルアクセス権限がありません: {file_path}")
        return None
        
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        return None

カスタム例外
# src/core/exceptions.py
class LLMCodeAssistantError(Exception):
    """アプリケーション基底例外"""
    pass

class ConfigurationError(LLMCodeAssistantError):
    """設定エラー"""
    pass

class LLMConnectionError(LLMCodeAssistantError):
    """LLM接続エラー"""
    pass

開発ワークフロー
1. 機能開発の流れ
graph LR
    A[Issue作成] --> B[ブランチ作成]
    B --> C[実装]
    C --> D[テスト作成]
    D --> E[テスト実行]
    E --> F[コードレビュー]
    F --> G[マージ]

2. ブランチ戦略
Git Flow
# 機能開発
git checkout -b feature/add-new-llm-provider
git commit -m "feat: OpenAI GPT-4対応を追加"

# バグ修正
git checkout -b hotfix/fix-file-encoding
git commit -m "fix: ファイルエンコーディング問題を修正"

# リリース準備
git checkout -b release/v1.2.0
git commit -m "chore: v1.2.0リリース準備"

コミットメッセージ規約
type(scope): subject

body

footer

Type:

feat: 新機能
fix: バグ修正
docs: ドキュメント
style: コードスタイル
refactor: リファクタリング
test: テスト
chore: その他
例:
feat(llm): Claude 3対応を追加

- Claude 3 APIクライアントを実装
- プロンプトテンプレートを最適化
- レスポンス解析機能を追加

Closes #123
3. プルリクエスト
PRテンプレート
## 概要
この変更の概要を説明してください。

## 変更内容
- [ ] 新機能の追加
- [ ] バグ修正
- [ ] ドキュメント更新
- [ ] リファクタリング

## テスト
- [ ] 単体テストを追加/更新
- [ ] 統合テストを実行
- [ ] 手動テストを実行

## チェックリスト
- [ ] コードレビューを受けた
- [ ] テストが通る
- [ ] ドキュメントを更新した
- [ ] 破壊的変更がある場合、マイグレーションガイドを作成した

テスト
1. テスト構成
tests/
├── conftest.py              # pytest設定
├── test_core/               # コアモジュールテスト
├── test_llm/                # LLMモジュールテスト
├── test_ui/                 # UIテスト
└── test_utils/              # ユーティリティテスト

2. テスト実行
# 全テスト実行
python -m pytest

# 特定のテストファイル実行
python -m pytest tests/test_core/test_config_manager.py

# カバレッジ付きテスト実行
python -m pytest --cov=src --cov-report=html

# 並列テスト実行
python -m pytest -n auto

3. テスト作成例
単体テスト
# tests/test_core/test_config_manager.py
import pytest
from unittest.mock import patch, mock_open
from src.core.config_manager import ConfigManager

class TestConfigManager:
    """ConfigManagerのテストクラス"""
    
    def setup_method(self):
        """各テストメソッド実行前の準備"""
        self.config_manager = ConfigManager()
    
    def test_load_config_success(self):
        """設定読み込み成功のテスト"""
        mock_config = '{"test_key": "test_value"}'
        
        with patch("builtins.open", mock_open(read_data=mock_config)):
            config = self.config_manager.load_config("test_config.json")
            
        assert config["test_key"] == "test_value"
    
    def test_load_config_file_not_found(self):
        """設定ファイルが見つからない場合のテスト"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            config = self.config_manager.load_config("nonexistent.json")
            
        assert config == {}
    
    @pytest.mark.parametrize("invalid_json", [
        '{"invalid": json}',
        '{"unclosed": "string}',
        ''
    ])
    def test_load_config_invalid_json(self, invalid_json):
        """無効なJSON形式のテスト"""
        with patch("builtins.open", mock_open(read_data=invalid_json)):
            config = self.config_manager.load_config("invalid.json")
            
        assert config == {}

統合テスト
# tests/test_integration/test_llm_integration.py
import pytest
from src.llm.llm_factory import LLMFactory
from src.core.config_manager import ConfigManager

class TestLLMIntegration:
    """LLM統合テスト"""
    
    @pytest.fixture
    def config_manager(self):
        """設定マネージャーのフィクスチャ"""
        return ConfigManager()
    
    @pytest.fixture
    def llm_factory(self, config_manager):
        """LLMファクトリーのフィクスチャ"""
        return LLMFactory(config_manager)
    
    def test_create_openai_client(self, llm_factory):
        """OpenAIクライアント作成のテスト"""
        client = llm_factory.create_llm("openai")
        assert client is not None
        assert hasattr(client, 'generate_response')
    
    @pytest.mark.asyncio
    async def test_llm_response_generation(self, llm_factory):
        """LLMレスポンス生成のテスト"""
        client = llm_factory.create_llm("mock")  # モッククライアント使用
        response = await client.generate_response("Hello, world!")
        
        assert response is not None
        assert len(response) > 0

4. UIテスト
# tests/test_ui/test_main_window.py
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from src.ui.main_window import MainWindow

@pytest.fixture(scope="session")
def qapp():
    """QApplicationのフィクスチャ"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()

class TestMainWindow:
    """メインウィンドウのテスト"""
    
    @pytest.fixture
    def main_window(self, qapp):
        """メインウィンドウのフィクスチャ"""
        window = MainWindow()
        window.show()
        yield window
        window.close()
    
    def test_window_title(self, main_window):
        """ウィンドウタイトルのテスト"""
        assert "LLM Code Assistant" in main_window.windowTitle()
    
    def test_menu_bar_exists(self, main_window):
        """メニューバーの存在確認"""
        menu_bar = main_window.menuBar()
        assert menu_bar is not None
        
        # ファイルメニューの確認
        file_menu = None
        for action in menu_bar.actions():
            if action.text() == "ファイル":
                file_menu = action.menu()
                break
        
        assert file_menu is not None
    
    def test_open_project_action(self, main_window, qtbot):
        """プロジェクト開くアクションのテスト"""
        # メニューアクションの実行をシミュレート
        main_window.open_project_action.trigger()
        
        # ダイアログが開かれることを確認
        # （実際の実装では適切なモックを使用）
        assert True  # 簡略化

デバッグ
1. ログ設定
# 開発時のログ設定
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.debug("デバッグメッセージ")

2. デバッガー使用
VSCode設定 (.vscode/launch.json)
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Main",
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
            "name": "Python: Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        }
    ]
}

3. プロファイリング
import cProfile
import pstats

def profile_function():
    """プロファイリング対象の関数"""
    # 重い処理
    pass

# プロファイリング実行
cProfile.run('profile_function()', 'profile_stats')

# 結果分析
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative')
stats.print_stats(10)

プラグイン開発
1. プラグインの基本構造
# src/plugins/example_plugin/example_plugin.py
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QObject, pyqtSignal
from src.plugins.base_plugin import BasePlugin

class ExamplePlugin(BasePlugin):
    """サンプルプラグイン"""
    
    # プラグイン情報
    name = "Example Plugin"
    version = "1.0.0"
    description = "プラグイン開発のサンプル"
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """UIの初期化"""
        layout = QVBoxLayout()
        label = QLabel("サンプルプラグイン")
        layout.addWidget(label)
        self.setLayout(layout)
    
    def activate(self) -> bool:
        """プラグインの有効化"""
        try:
            # 初期化処理
            self.logger.info(f"{self.name} activated")
            return True
        except Exception as e:
            self.logger.error(f"Failed to activate {self.name}: {e}")
            return False
    
    def deactivate(self) -> None:
        """プラグインの無効化"""
        try:
            # クリーンアップ処理
            self.logger.info(f"{self.name} deactivated")
        except Exception as e:
            self.logger.error(f"Failed to deactivate {self.name}: {e}")
    
    def get_settings(self) -> Dict[str, Any]:
        """プラグイン設定の取得"""
        return {
            "enabled": True,
            "sample_setting": "default_value"
        }
    
    def set_settings(self, settings: Dict[str, Any]) -> None:
        """プラグイン設定の適用"""
        # 設定の適用処理
        pass

# プラグインエクスポート関数
def create_plugin(parent: Optional[QWidget] = None) -> ExamplePlugin:
    return ExamplePlugin(parent)

def get_plugin_info() -> Dict[str, Any]:
    return {
        'name': 'Example Plugin',
        'version': '1.0.0',
        'description': 'プラグイン開発のサンプル',
        'author': 'Developer',
        'category': 'Example'
    }

2. プラグイン登録
# src/plugins/__init__.py に追加
from .example_plugin.example_plugin import create_plugin as create_example_plugin

AVAILABLE_PLUGINS = {
    'example': create_example_plugin,
    # 他のプラグイン...
}

ビルドとデプロイ
1. 開発ビルド
# 開発用ビルド
python scripts/build.py --dev

# 本番用ビルド
python scripts/build.py --prod

2. パッケージング
# PyInstaller使用
pip install pyinstaller
pyinstaller --onefile --windowed src/main.py

# setuptools使用
python setup.py sdist bdist_wheel

3. CI/CD設定
GitHub Actions (.github/workflows/ci.yml)

name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        python -m pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1

トラブルシューティング
1. よくある問題
インポートエラー
# PYTHONPATHの設定
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# または
python -m src.main

Qt関連エラー
# 必要なシステムライブラリのインストール
# Ubuntu/Debian
sudo apt-get install python3-pyqt6

# macOS
brew install pyqt6

LLM API接続エラー
# APIキーの確認
import os
print(os.getenv('OPENAI_API_KEY'))

# プロキシ設定の確認
import requests
response = requests.get('https://api.openai.com/v1/models')
print(response.status_code)

2. パフォーマンス問題
メモリ使用量の監視
import psutil
import os

def monitor_memory():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    print(f"RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB")

プロファイリング
# line_profilerを使用
pip install line_profiler
kernprof -l -v script.py

# memory_profilerを使用
pip install memory_profiler
python -m memory_profiler script.py

貢献ガイドライン

1. Issue報告
バグ報告時は再現手順を明記
機能要求時は具体的なユースケースを説明
適切なラベルを付与

2. プルリクエスト
小さな変更に分割
適切なテストを追加
ドキュメントの更新
コードレビューへの対応

3. コードレビュー
建設的なフィードバック
セキュリティ観点でのチェック
パフォーマンス影響の確認
可読性・保守性の評価

参考資料
Python公式ドキュメント
PyQt6ドキュメント
pytest公式ドキュメント
PEP 8 -- Style Guide for Python Code
Google Python Style Guide