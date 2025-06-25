# LLM Code Assistant

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-development-yellow.svg)

**LLM Code Assistant** は、複数のLLMプロバイダー（OpenAI、Claude、ローカルLLM）を統合したインテリジェントなコード開発支援ツールです。プロジェクト管理、コード生成、リファクタリング、レビューなどの機能を提供し、開発者の生産性を大幅に向上させます。

## 🌟 主な機能

### 🤖 マルチLLM対応
- **OpenAI GPT-4/GPT-3.5** - 高品質なコード生成とレビュー
- **Claude (Anthropic)** - 詳細な分析と説明
- **ローカルLLM** - プライバシーを重視した開発環境

### 📁 プロジェクト管理
- プロジェクトの作成、管理、バックアップ
- ファイル構造の自動認識と整理
- Git統合による版数管理
- テンプレートベースの迅速な開発

### 💻 コード支援機能
- **インテリジェントなコード生成** - 自然言語からコードを生成
- **自動リファクタリング** - コード品質の向上
- **コードレビュー** - AIによる詳細な分析とフィードバック
- **バグ検出と修正提案** - 潜在的な問題の早期発見

### 🎨 ユーザーインターフェース
- **モダンなGUI** - tkinter/customtkinterベースの直感的なUI
- **シンタックスハイライト** - 複数言語対応
- **テーマシステム** - ライト/ダーク/カスタムテーマ
- **分割パネル** - 効率的なワークスペース

### 🔌 プラグインシステム
- **拡張可能なアーキテクチャ** - カスタムプラグインの開発
- **Git統合プラグイン** - 版数管理の自動化
- **コードフォーマッタープラグイン** - 複数言語の自動整形
- **エクスポートツールプラグイン** - 多様な形式での出力

## 🚀 クイックスタート

### 前提条件

- Python 3.8以上
- pip（Pythonパッケージマネージャー）
- Git（オプション、版数管理用）

### インストール

1. **リポジトリのクローン**
```bash
git clone https://github.com/yourusername/LLM-Code-Assistant.git
cd LLM-Code-Assistant

2.仮想環境の作成（推奨）
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

3.依存関係のインストール
pip install -r requirements.txt

4.環境変数の設定
# .env.example を .env にコピー
cp .env.example .env

# .env ファイルを編集してAPIキーを設定
# 最低限必要な設定：
# - OPENAI_API_KEY（OpenAI使用時）
# - CLAUDE_API_KEY（Claude使用時）

5.アプリケーションの起動
python src/main.py

開発環境のセットアップ
開発者向けの詳細なセットアップ：
# 開発用依存関係のインストール
pip install -r requirements-dev.txt

# 開発環境の初期化
python scripts/setup_dev.py

# テストの実行
python scripts/test_runner.py

# コード品質チェック
flake8 src/
black src/

📖 使用方法
基本的な使用フロー
プロジェクトの作成

新規プロジェクトを作成または既存プロジェクトを開く
プロジェクト設定（言語、フレームワーク等）を選択
LLMプロバイダーの選択

設定画面でLLMプロバイダーを選択
APIキーの設定と接続テスト
コード開発

チャットパネルで自然言語による指示
コードエディターでの直接編集
AIによるコード生成とレビュー
プロジェクト管理

ファイルの整理と構造化
版数管理とバックアップ
エクスポートと共有

主要な機能の使用例

コード生成
ユーザー: "Pythonでファイルを読み込んでCSVデータを処理するクラスを作成してください"
AI: [詳細なコード生成と説明]

コードレビュー
ユーザー: "このコードの問題点を教えてください"
AI: [コードの分析、問題点の指摘、改善提案]

リファクタリング
ユーザー: "この関数をより効率的にリファクタリングしてください"
AI: [最適化されたコードと変更理由の説明]

⚙️ 設定
環境変数
主要な環境変数の説明：
# LLMプロバイダー設定
DEFAULT_LLM_PROVIDER=openai          # デフォルトプロバイダー
OPENAI_API_KEY=your_api_key          # OpenAI APIキー
CLAUDE_API_KEY=your_api_key          # Claude APIキー

# アプリケーション設定
LOG_LEVEL=INFO                       # ログレベル
DEFAULT_THEME=light                  # デフォルトテーマ
DEFAULT_LANGUAGE=ja                  # デフォルト言語

# データベース設定
VECTOR_DB_PATH=./data/vector_db      # ベクトルDBパス
SQLITE_DB_PATH=./data/history.db     # 履歴DBパス

設定ファイル
config/default_settings.json - デフォルト設定
config/logging_config.yaml - ログ設定
.env - 環境変数（機密情報含む）

🔌 プラグイン開発
カスタムプラグインの作成
from src.plugins.base_plugin import BasePlugin

class MyCustomPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "My Custom Plugin"
        self.version = "1.0.0"
    
    def activate(self):
        # プラグインの初期化処理
        pass
    
    def execute(self, context):
        # プラグインのメイン処理
        pass

詳細な開発ガイドは docs/development_guide.md を参照してください。

🏗️ アーキテクチャ
LLM-Code-Assistant/
├── src/
│   ├── core/           # コア機能
│   ├── llm/            # LLM統合
│   ├── ui/             # ユーザーインターフェース
│   ├── plugins/        # プラグインシステム
│   └── utils/          # ユーティリティ
├── config/             # 設定ファイル
├── data/               # データとテンプレート
├── tests/              # テストスイート
└── docs/               # ドキュメント

詳細なアーキテクチャ設計は docs/architecture.md を参照してください。

🧪 テスト
テストの実行
# 全テストの実行
python -m pytest tests/

# 特定のテストモジュール
python -m pytest tests/test_core/

# カバレッジレポート付き
python -m pytest tests/ --cov=src --cov-report=html

テストの種類
単体テスト - 個別コンポーネントのテスト
統合テスト - モジュール間の連携テスト
UIテスト - ユーザーインターフェースのテスト
E2Eテスト - エンドツーエンドのシナリオテスト
📚 ドキュメント
ユーザーガイド - 詳細な使用方法
API リファレンス - 開発者向けAPI
開発ガイド - 開発者向け情報
アーキテクチャ - システム設計
🤝 コントリビューション
プロジェクトへの貢献を歓迎します！

貢献方法
Issue の報告

バグレポート
機能要望
改善提案
プルリクエスト

フォークしてブランチを作成
変更を実装
テストを追加/更新
プルリクエストを送信
開発ガイドライン

PEP 8に準拠したコードスタイル
適切なテストカバレッジ
明確なコミットメッセージ
ドキュメントの更新
開発者向けセットアップ

# 開発用ブランチの作成
git checkout -b feature/your-feature-name

# 開発環境の準備
python scripts/setup_dev.py

# コード品質チェック
pre-commit install

📄 ライセンス
このプロジェクトは MIT License の下で公開されています。

🙏 謝辞
OpenAI - GPT APIの提供
Anthropic - Claude APIの提供
Hugging Face - ローカルLLMサポート
オープンソースコミュニティの皆様
📞 サポート
問題が発生した場合
FAQ の確認 - よくある質問と解決方法
Issue の検索 - 既存の問題と解決策
新しい Issue の作成 - 詳細な情報と再現手順
連絡先
GitHub Issues: プロジェクトのIssue
Email: support@example.com
Discord: 開発者コミュニティ

LLM Code Assistant - AIの力で開発を加速する 🚀

最終更新: 2024年12月
