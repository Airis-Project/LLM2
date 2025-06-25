# Scripts Directory

このディレクトリには、LLM Chat Systemの初期化と起動に関するスクリプトが含まれています。

## スクリプト一覧

### 初期化スクリプト
- `init.py` - システムの初期化とセットアップ
- `init.bat` - Windows用初期化スクリプト（オプション）

### 起動スクリプト
- `start.py` - システムの起動とヘルスチェック
- `start.bat` - Windows用起動スクリプト
- `start.sh` - Unix/Linux用起動スクリプト

## 使用方法

### 初回セットアップ
```bash
# システムの初期化
python scripts/init.py

# 強制初期化（既存ファイルを上書き）
python scripts/init.py --force

# システム状態チェック
python scripts/init.py --check

# 基本起動
python scripts/start.py

# GUIで起動
python scripts/start.py --interface gui

# デバッグモードで起動
python scripts/start.py --debug

# カスタム設定ファイルで起動
python scripts/start.py --config config/my_config.json

# ヘルスチェックのみ
python scripts/start.py --health-check

プラットフォーム固有の起動
Windows

scripts\start.bat

Unix/Linux/macOS
chmod +x scripts/start.sh
./scripts/start.sh

機能
初期化機能
・ディレクトリ構造の作成
・設定ファイルの生成
・環境ファイルの作成
・権限の設定
・システム状態チェック

起動機能
・プリフライトチェック
・設定検証
・依存関係チェック
・ヘルスチェック
・システム起動

トラブルシューティング
よくある問題
1.Python not found
・Python 3.8以上がインストールされているか確認
・PATHにPythonが含まれているか確認

2.Permission denied
・スクリプトに実行権限を付与: chmod +x scripts/start.sh

3.Missing dependencies
・依存関係をインストール: pip install -r requirements.txt

4.Configuration errors
・設定ファイルを再初期化: python scripts/init.py --force