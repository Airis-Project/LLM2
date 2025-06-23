# docs/user_guide.md

# LLM Code Assistant ユーザーガイド

## 目次

1. [概要](#概要)
2. [インストール](#インストール)
3. [初期設定](#初期設定)
4. [基本的な使い方](#基本的な使い方)
5. [高度な機能](#高度な機能)
6. [プラグイン](#プラグイン)
7. [設定とカスタマイズ](#設定とカスタマイズ)
8. [トラブルシューティング](#トラブルシューティング)
9. [FAQ](#faq)

## 概要

LLM Code Assistantは、ローカルLLM（大規模言語モデル）を活用したコード生成・編集支援ツールです。プロジェクトの構造とコンテキストを理解し、一貫性のあるコード生成を行います。

### 主な機能

- **インテリジェントなコード生成**: プロジェクトコンテキストを理解したコード生成
- **対話型アシスタント**: 自然言語でのコード相談・修正依頼
- **プロジェクト管理**: ファイル構造の解析と管理
- **複数LLMサポート**: OpenAI、Claude、ローカルLLMに対応
- **プラグインシステム**: Git統合、コードフォーマッター等の拡張機能
- **カスタマイズ可能なUI**: テーマ、レイアウトの変更

## インストール

### システム要件

- **OS**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **Python**: 3.11.9以上
- **メモリ**: 8GB以上推奨
- **ストレージ**: 2GB以上の空き容量

### インストール手順

#### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/LLM-Code-Assistant.git
cd LLM-Code-Assistant

2. 仮想環境の作成
# Python仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

3. 依存関係のインストール
pip install -r requirements.txt

4. アプリケーションの起動
python src/main.py

初期設定
1. 初回起動
アプリケーションを初回起動すると、設定ウィザードが表示されます。

2. LLMプロバイダーの設定
OpenAI設定
設定 → LLM設定 → OpenAIを選択
APIキーを入力
使用するモデル（GPT-4, GPT-3.5-turbo等）を選択

APIキー: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
モデル: gpt-4
最大トークン数: 4096
温度: 0.7

Claude設定
設定 → LLM設定 → Claudeを選択
APIキーを入力
使用するモデルを選択

APIキー: sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
モデル: claude-3-opus-20240229
最大トークン数: 4096
温度: 0.7

ローカルLLM設定
設定 → LLM設定 → ローカルLLMを選択
モデルファイルのパスを指定
推論エンジンを選択（Ollama、LlamaCpp等）
モデルパス: /path/to/model.gguf
推論エンジン: Ollama
ホスト: localhost
ポート: 11434

3. 環境変数の設定
.envファイルを作成し、必要な環境変数を設定します：
# .env
OPENAI_API_KEY=your_openai_api_key
CLAUDE_API_KEY=your_claude_api_key
DEFAULT_LLM_PROVIDER=openai
LOG_LEVEL=INFO

基本的な使い方
1. プロジェクトの開始
・新規プロジェクト作成
・ファイル → 新規プロジェクトを選択
・プロジェクト名とディレクトリを指定
・プロジェクトテンプレートを選択（Python、JavaScript、HTML等）

既存プロジェクトを開く
・ファイル → プロジェクトを開くを選択
・プロジェクトのルートディレクトリを選択
・プロジェクト構造の解析を待つ

2. コード生成
・チャットパネルでの対話
・右側のチャットパネルにコード生成の依頼を入力
・「Enterキー」または「送信」ボタンでリクエスト送信
・生成されたコードを確認・編集

例：
ユーザー: "Pythonでファイル読み込み関数を作って"

アシスタント: 以下のファイル読み込み関数を作成しました：

```python
def read_file(file_path: str, encoding: str = 'utf-8') -> str:
    """
    ファイルを読み込んで内容を返す
    
    Args:
        file_path: 読み込むファイルのパス
        encoding: ファイルのエンコーディング
        
    Returns:
        ファイルの内容
        
    Raises:
        FileNotFoundError: ファイルが見つからない場合
        UnicodeDecodeError: エンコーディングエラーの場合
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(f"エンコーディングエラー: {e}")

この関数をプロジェクトに追加しますか？

#### コードエディタでの直接生成
1. コードエディタでコメントを記述
2. `Ctrl+Shift+G`（Windows/Linux）または`Cmd+Shift+G`（macOS）でコード生成
3. 生成されたコードを確認・採用

**例：**
```python
# TODO: データベース接続クラスを作成
# - PostgreSQL対応
# - 接続プール機能
# - エラーハンドリング

3. コード編集・修正
・既存コードの修正依頼
・修正したいコードを選択
・右クリック → LLMで修正を選択
・修正内容をチャットで指示
例：
選択されたコード:
def calculate(a, b):
    return a + b

修正依頼: "この関数に型ヒントとドキュメント文字列を追加して"

リファクタリング
・リファクタリング対象のコードを選択
・編集 → リファクタリング → LLMリファクタリング
・リファクタリング方針を指示

4. プロジェクト解析
ファイル構造の確認
・左側のプロジェクトツリーでファイル構造を確認
・ファイルアイコンで種類を識別
・右クリックメニューで各種操作
・依存関係の可視化
・表示 → 依存関係グラフを選択
・モジュール間の依存関係を確認
・循環依存等の問題を特定

高度な機能
1. コンテキスト管理
・プロジェクトコンテキスト
・プロジェクト全体の構造を自動解析
・関連ファイルの自動検出
・依存関係の追跡
会話履歴の活用
・過去の対話内容を参照
・一貫したコード生成
・コンテキストの継続

2. テンプレートシステム
カスタムテンプレート作成
・ツール → テンプレート管理を選択
・新規テンプレートをクリック
・テンプレート内容を作成
例：Pythonクラステンプレート
class {{class_name}}:
    """{{class_description}}"""
    
    def __init__(self{{init_params}}):
        """初期化メソッド"""
        {{init_body}}
    
    {{methods}}

テンプレート変数
・{{variable_name}}: 置換される変数
・{{#if condition}}...{{/if}}: 条件分岐
・{{#each items}}...{{/each}}: 繰り返し

3. バッチ処理
複数ファイルの一括処理
・ツール → バッチ処理を選択
・処理対象ファイルを選択
・実行する処理を指定

処理例：
コメント追加
型ヒント追加
リファクタリング
フォーマット統一

4. コード品質チェック
自動レビュー
・ツール → コード品質チェックを選択
・チェック項目を選択
・レポートを確認

チェック項目：
・コーディング規約準拠
・セキュリティ脆弱性
・パフォーマンス問題
・保守性評価

プラグイン
1. Git統合プラグイン
機能
・Git操作のGUI化
・コミット支援
・ブランチ管理
・マージ競合解決支援

使用方法
・プラグイン → Git統合を有効化
・プロジェクトでGitリポジトリを初期化
・Git操作パネルを使用

2. コードフォーマッタープラグイン
対応言語
Python（Black、autopep8）
JavaScript（Prettier）
TypeScript（Prettier）
HTML/CSS（Prettier）

使用方法
・プラグイン → コードフォーマッターを有効化
・フォーマッター設定を選択
・自動フォーマットを有効化

3. エクスポートツールプラグイン
エクスポート形式
PDF
HTML
Markdown
Word文書

使用方法
・プラグイン → エクスポートツールを有効化
・ファイル → エクスポートを選択
・出力形式と設定を選択

設定とカスタマイズ
1. 一般設定
基本設定
{
  "language": "ja",
  "auto_save": true,
  "auto_save_interval": 30,
  "backup_enabled": true,
  "max_backup_files": 10
}

エディタ設定
{
  "font_family": "Consolas",
  "font_size": 12,
  "tab_size": 4,
  "word_wrap": true,
  "show_line_numbers": true,
  "highlight_current_line": true
}

2. テーマ設定
組み込みテーマ
・Light: 明るいテーマ
・Dark: 暗いテーマ
・High Contrast: 高コントラストテーマ

カスタムテーマ作成
・設定 → テーマ → カスタムテーマを選択
・色設定を調整
・テーマファイルとして保存

3. キーボードショートカット
デフォルトショートカット
機能            Windows/Linux	macOS
新規ファイル    Ctrl+N	        Cmd+N
ファイルを開く  Ctrl+O	        Cmd+O
保存            Ctrl+S	        Cmd+S
コード生成      Ctrl+Shift+G	Cmd+Shift+G
検索            Ctrl+F	        Cmd+F
置換	        Ctrl+H	        Cmd+Option+F
LLM呼び出し	    Ctrl+L	        Cmd+L

カスタムショートカット
・設定 → キーボードショートカットを選択
・変更したい機能を選択
・新しいキー組み合わせを設定

4. LLM設定の詳細
プロンプトテンプレート
{
  "code_generation": {
    "system_prompt": "あなたは優秀なプログラマーです。",
    "user_prompt_template": "以下の要求に基づいてコードを生成してください：\n{request}\n\nプロジェクトコンテキスト：\n{context}"
  },
  "code_review": {
    "system_prompt": "あなたはコードレビューの専門家です。",
    "user_prompt_template": "以下のコードをレビューしてください：\n{code}\n\n改善点があれば指摘してください。"
  }
}

レスポンス設定
{
  "max_tokens": 4096,
  "temperature": 0.7,
  "top_p": 0.9,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "timeout": 30
}

トラブルシューティング
1. よくある問題
アプリケーションが起動しない
症状: ダブルクリックしても起動しない

解決方法:

1.コマンドラインから起動してエラーメッセージを確認
python src/main.py

2.依存関係を再インストール
pip install -r requirements.txt --force-reinstall

3.Python環境を確認
python --version

LLMに接続できない
症状: "LLM接続エラー"が表示される

解決方法:

1.APIキーを確認
2.ネットワーク接続を確認
3.プロキシ設定を確認
4.APIクォータを確認

プロジェクトが正しく読み込まれない
症状: ファイル構造が表示されない

解決方法:

1.プロジェクトディレクトリの権限を確認
2.隠しファイル・フォルダの表示設定を確認
3.プロジェクト設定ファイルを削除して再作成

. ログの確認
ログファイルの場所
Windows: %APPDATA%\LLMCodeAssistant\logs\
macOS: ~/Library/Application Support/LLMCodeAssistant/logs/
Linux: ~/.local/share/LLMCodeAssistant/logs/

ログレベル設定
# config/logging_config.yaml
version: 1
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: default
  file:
    class: logging.FileHandler
    level: DEBUG
    formatter: default
    filename: logs/app.log
loggers:
  '':
    level: DEBUG
    handlers: [console, file]

パフォーマンス問題
動作が重い場合
・メモリ使用量を確認
・大容量ファイルを除外
・インデックス再構築
・キャッシュクリア

LLMレスポンスが遅い場合
・モデルサイズを確認
・ローカルLLMの設定を最適化
・バッチサイズを調整
・並列処理設定を確認

FAQ
Q1: 複数のLLMプロバイダーを同時に使用できますか？
A: はい、設定で複数のプロバイダーを設定し、用途に応じて切り替えることができます。チャットパネルの上部でプロバイダーを選択できます。

Q2: オフラインで使用できますか？
A: ローカルLLMを設定すれば、インターネット接続なしで使用できます。ただし、初回セットアップ時はモデルファイルのダウンロードが必要です。

Q3: 生成されたコードの品質はどの程度ですか？
A: プロジェクトコンテキストを理解した高品質なコードを生成しますが、必ずレビューと テストを行ってください。複雑な要求の場合は段階的に指示することをお勧めします。

Q4: 商用プロジェクトで使用できますか？
A: はい、ライセンス条項に従って商用利用可能です。ただし、使用するLLMプロバイダーの利用規約も確認してください。

Q5: カスタムプラグインを作成できますか？
A: はい、プラグインAPIを使用してカスタムプラグインを作成できます。詳細は開発ガイドを参照してください。

Q6: データのプライバシーは保護されますか？
A: ローカルLLMを使用する場合、データは外部に送信されません。クラウドLLMを使用する場合は、各プロバイダーのプライバシーポリシーを確認してください。

Q7: 大規模プロジェクトでも使用できますか？
A: はい、インデックス機能により大規模プロジェクトにも対応しています。ただし、初回解析には時間がかかる場合があります。

Q8: バックアップ機能はありますか？
A: はい、自動バックアップ機能があります。設定で有効化し、バックアップ間隔を調整できます。

Q9: 多言語プロジェクトに対応していますか？
A: はい、Python、JavaScript、TypeScript、HTML、CSS、Java、C++等の主要言語に対応しています。

Q10: アップデート方法を教えてください
A: Gitプルで最新版を取得し、依存関係を更新してください：
git pull origin main
pip install -r requirements.txt --upgrade

サポート
ヘルプとサポート
公式ドキュメント: https://docs.llm-code-assistant.com
GitHub Issues: https://github.com/your-org/LLM-Code-Assistant/issues
コミュニティフォーラム: https://community.llm-code-assistant.com
メールサポート: support@llm-code-assistant.com
貢献方法
プロジェクトへの貢献を歓迎します：

GitHubでIssueを報告
機能改善の提案
プルリクエストの送信
ドキュメントの改善
翻訳の協力
ライセンス
このソフトウェアはMITライセンスの下で配布されています。詳細はLICENSEファイルを参照してください。

最終更新: 2024年12月
バージョン: 1.0.0