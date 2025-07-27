# LLM Code Assistant

![LLM Code Assistant Logo](assets/icons/app_icon.png)

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/llm-code-assistant/llm-code-assistant)
[![Coverage](https://img.shields.io/badge/coverage-85%25-yellow.svg)](https://github.com/llm-code-assistant/llm-code-assistant)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://llm-code-assistant.readthedocs.io/)

**LLM Code Assistant** は、AI を活用したコード生成・支援ツールです。OpenAI GPT、Claude、ローカル LLM など複数の AI プロバイダーをサポートし、開発者の生産性向上を支援します。

## 【ルール】
- ## 1　過去のチャット履歴と現在認識しているディレクトリ一覧、ファイル一覧、ファイル内容を参照し一貫した実装をすること。(ファイルの先頭にコメントでディレクトリ名、ファイル名を記述すること)
- ## 2　pipでインストールが必要なライブラリはpython 3.11.9に適合するバージョンをrequirements.txtファイルにまとめること。
- ## 3　実用的で動作するコードにすること。
- ## 4　コードにはコメントを含めてください
- ## 5　エラーハンドリングを考慮してください
- ## 6　ベストプラクティスに従ってください
- ## 7　既存のプロジェクト構造に合わせてください
- ## 8　日本語に対応してください
- ## 9　複数のファイルを記述する際は1つ記述し、記述が終わるごとに指示を待つこと。
- ## 10　指示を待ち、「続き」と入力されたら続きを記述する。
- ## 11　既存のコードに追記をするときはコード内にコメントを記載し一貫した実装をすること。
- ## 12　エラー内容から既存のコードが存在する可能性がある場合は、ファイル内容を先に催促すること。


## 開発目的
- ## 1: 高品質なローカルLLMを構築する。(GUIで操作する)
- ## 2:このシステムは開発者のみが使用する。
- ## 3:アップロードされたプロジェクトを解析しフォルダ構成、ファイル構成、ファイル内容をDBに履歴として保存する。
- ## 4:対話形式で行いDBに履歴として保存したプロジェクト構成(フォルダ、ファイル、ファイル内容)を参照しコード生成、修正、デバッグなど一貫し、矛盾な く実装する。
- ## 5:対話形式で行うモデルはOllamaのモデルを主に使用する。
- ## 6:Ollamaモデルは変更できるものとする。
- ## 7:OpenAIに変更できるようにするものとする。
- ## 8:既存のシステムに追記、変更、削除する場合は、プロジェクト全体を同じディレクトリにコピーしプロジェクト名_testとしてテスト環境を構築すること。
- ## 9:テスト環境を使用し問題がなければユーザが手動でプロジェクトを置き換えること。
- ## 10:システム内の位置づけは下記のとおりである。

graph TD
    A[ユーザーの質問] --> B[LocalCodeAssistant]
    B --> C[VectorDB検索]
    C --> D[関連コード取得]
    D --> E[LocalLLM] 
    E --> F[コンテキスト構築]
    F --> G[プロンプト生成]
    G --> H[LLM推論]
    H --> I[回答生成]
    I --> J[ユーザーに返答]

## 開発PCスペック
- ## OS：Windows11
- ## GPU：NVIDIA GeForce RTX 4060 8GB
- ## CPU：13th Gen Intel Core(TM)i5-13400F
- ## メモリ：64GB
- ## ストレージ：SSD1TB

## 開発ツール
- ## Python 3.11.3
- ## MongoDB4.4
- ## Redis6
- ## Docker Desktop
- ## vscode
- ## github
- ## Kubernetes
- ## FastAPI
- ## TensorFlow
- ## Prometheus
- ## Ollama

## Ollamaモデル
- ## llama3.3:70b
- ## llama3.1:405b
- ## wizardcoder:33b
- ## codellama:70b
- ## phi4:14b
- ## starcoder:7b
- ## nomic-embed-text:latest
- ## codellama:7b

## ✨ 主な機能

### 🤖 マルチ LLM サポート
- **OpenAI GPT シリーズ**: GPT-4, GPT-3.5-turbo
- **Anthropic Claude**: Claude-3, Claude-2
- **ローカル LLM**: Llama, CodeLlama, その他 Hugging Face モデル
- **カスタム API**: 独自の LLM エンドポイント対応

### 💻 高機能コードエディター
- シンタックスハイライト（100+ 言語対応）
- インテリジェントなコード補完
- リアルタイムエラー検出
- Git 統合
- プロジェクト管理

### 🎯 AI アシスタント機能
- **コード生成**: 自然言語からのコード生成
- **コードレビュー**: AI による品質チェック
- **リファクタリング**: コード改善提案
- **ドキュメント生成**: 自動コメント・ドキュメント作成
- **バグ修正**: エラー解析と修正提案

### 🔧 開発支援ツール
- **テンプレート管理**: カスタマイズ可能なコードテンプレート
- **スニペット管理**: 再利用可能なコード片
- **プラグインシステム**: 機能拡張対応
- **バックアップ・同期**: クラウド連携

## 🚀 クイックスタート

### システム要件
- **Python**: 3.11 以上
- **OS**: Windows 10+, macOS 10.15+, Linux (Ubuntu 20.04+)
- **RAM**: 8GB 以上推奨（ローカル LLM 使用時は 16GB+）
- **ストレージ**: 2GB 以上の空き容量

### インストール

#### 方法 1: pip でインストール（推奨）
```bash
# 基本インストール
pip install llm-code-assistant

# 全機能付きインストール
pip install llm-code-assistant[full]

# GPU サポート付きインストール
pip install llm-code-assistant[gpu]

方法 2: ソースからインストール
# リポジトリをクローン
git clone https://github.com/llm-code-assistant/llm-code-assistant.git
cd llm-code-assistant

# 仮想環境作成・有効化
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# 開発モードでインストール
pip install -e .

方法 3: Conda でインストール
# Conda 環境作成
conda env create -f conda-environment.yml
conda activate llm-code-assistant

# アプリケーション実行
python -m src.main

初回セットアップ
1.アプリケーション起動
    llm-code-assistant

2.API キー設定
    設定 → LLM プロバイダー → API キー入力
    OpenAI: sk-...
    Anthropic: sk-ant-...

3.初期設定完了
    テーマ選択
    エディター設定
    プロジェクトフォルダー指定

📖 使用方法
基本的な使い方
1. コード生成
プロンプト例:
"Python でファイルを読み込んで CSV として保存する関数を作成してください"

生成されるコード:
```python
import csv
import pandas as pd

def save_to_csv(data, filename):
    """データを CSV ファイルとして保存する関数"""
    try:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"データが {filename} に保存されました")
        return True
    except Exception as e:
        print(f"エラー: {e}")
        return False


#### 2. コードレビュー
- コードを選択
- 右クリック → "AI レビュー"
- 品質・セキュリティ・パフォーマンスの観点から分析

#### 3. リファクタリング
- 改善したいコードを選択
- Ctrl+Shift+R (Cmd+Shift+R)
- AI が最適化案を提示

### 高度な機能

#### カスタムテンプレート作成
```yaml
# templates/python_class.yaml
name: "Python クラステンプレート"
language: "python"
description: "基本的な Python クラス構造"
template: |
  class {{class_name}}:
      """{{description}}"""
      
      def __init__(self{{init_params}}):
          {{init_body}}
      
      def __str__(self):
          return f"{{class_name}}({{str_format}})"
      
      {{methods}}

variables:
  - name: "class_name"
    type: "string"
    required: true
  - name: "description"
    type: "string"
    default: "クラスの説明"
  - name: "init_params"
    type: "string"
    default: ""

プラグイン開発
# plugins/my_plugin.py
from src.core.plugin_system import PluginBase

class MyPlugin(PluginBase):
    name = "My Custom Plugin"
    version = "1.0.0"
    
    def initialize(self):
        """プラグイン初期化処理"""
        self.add_menu_item("Tools", "My Tool", self.run_tool)
    
    def run_tool(self):
        """カスタムツール実行"""
        # ツールの処理を実装
        pass

⚙️ 設定
設定ファイル
設定は以下のファイルで管理されます：
    config/default_config.json: デフォルト設定
    config/user_settings.json: ユーザー設定
    config/logging_config.yaml: ログ設定
    .env: 環境変数（API キーなど）

主要設定項目
LLM プロバイダー設定
{
  "llm": {
    "providers": {
      "openai": {
        "api_key": "your-api-key",
        "model": "gpt-4",
        "max_tokens": 2048,
        "temperature": 0.7
      },
      "claude": {
        "api_key": "your-api-key",
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 4096
      },
      "local": {
        "model_path": "models/codellama-7b-instruct.gguf",
        "context_length": 4096,
        "gpu_layers": 32
      }
    }
  }
}

UI テーマ設定
{
  "ui": {
    "theme": {
      "current": "dark",
      "custom_themes": {
        "my_theme": {
          "background": "#1e1e1e",
          "foreground": "#d4d4d4",
          "accent": "#007acc"
        }
      }
    }
  }
}

🔌 API リファレンス
REST API エンドポイント
コード生成
POST /api/v1/generate
Content-Type: application/json

{
  "prompt": "Create a Python function to calculate fibonacci",
  "language": "python",
  "provider": "openai",
  "model": "gpt-4"
}

コードレビュー
POST /api/v1/review
Content-Type: application/json

{
  "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
  "language": "python",
  "review_type": "quality"
}

Python API
from llm_assistant import LLMAssistant

# インスタンス作成
assistant = LLMAssistant()

# コード生成
result = assistant.generate_code(
    prompt="Create a REST API with FastAPI",
    language="python",
    provider="openai"
)

# コードレビュー
review = assistant.review_code(
    code=my_code,
    language="python",
    focus=["security", "performance"]
)

🧪 テスト
テスト実行
# 全テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=src --cov-report=html

# 特定のテストのみ
pytest tests/test_llm_providers.py

# マーカー指定
pytest -m "not slow"  # 重いテストを除外
pytest -m "integration"  # 統合テストのみ

テストカテゴリ
    Unit Tests: 単体テスト
    Integration Tests: 統合テスト
    UI Tests: GUI テスト
    LLM Tests: AI 機能テスト
    Performance Tests: パフォーマンステスト

📚 ドキュメント
ドキュメント生成
# Sphinx ドキュメント生成
cd docs
make html

# ドキュメントサーバー起動
python -m http.server 8000 -d _build/html

ドキュメント構成
    ユーザーガイド: 基本的な使用方法
    開発者ガイド: プラグイン・カスタマイズ
    API リファレンス: 詳細な API 仕様
    FAQ: よくある質問と回答
🤝 コントリビューション
開発環境セットアップ
# リポジトリフォーク・クローン
git clone https://github.com/yourusername/llm-code-assistant.git
cd llm-code-assistant

# 開発環境セットアップ
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# pre-commit フック設定
pre-commit install

コントリビューションガイドライン
    Issue 作成: バグ報告・機能要望
    フォーク: リポジトリをフォーク
    ブランチ作成: git checkout -b feature/your-feature
    開発: コード作成・テスト追加
    テスト: pytest でテスト実行
    コミット: git commit -m "Add: your feature"
    プッシュ: git push origin feature/your-feature
    プルリクエスト: GitHub で PR 作成

コーディング規約
    Python: PEP 8 準拠
    フォーマッター: Black
    リンター: Flake8, Pylint
    型チェック: MyPy
    ドキュメント: Google スタイル

🐛 トラブルシューティング
よくある問題
1. API キーエラー
Error: Invalid API key for OpenAI

解決方法:

設定画面で API キーを確認
    .env ファイルの OPENAI_API_KEY を確認
    API キーの権限を確認

2.ローカル LLM が動作しない
Error: Failed to load local model

解決方法:

    モデルファイルのパスを確認
    十分なメモリがあるか確認
    GPU ドライバーを更新（GPU 使用時）

3. UI が表示されない
Error: Qt platform plugin could not be initialized

解決方法:
# Linux の場合
sudo apt-get install python3-pyqt6

# macOS の場合
brew install pyqt6

# Windows の場合
pip uninstall PyQt6
pip install PyQt6

ログファイル確認
# ログディレクトリ
ls logs/

# エラーログ確認
tail -f logs/error.log

# デバッグログ確認
tail -f logs/debug.log

📄 ライセンス
このプロジェクトは MIT License の下で公開されています。

🙏 謝辞
    OpenAI: GPT API の提供
    Anthropic: Claude API の提供
    Hugging Face: Transformers ライブラリ
    Qt: GUI フレームワーク
    コントリビューター: 全ての貢献者に感謝

LLM Code Assistant - AI と共に、より良いコードを。
