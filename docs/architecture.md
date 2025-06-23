# docs/architecture.md

# LLM Code Assistant アーキテクチャ

## 概要

LLM Code Assistantは、ローカルLLMを活用したコード生成・編集支援システムです。プロジェクトの構造とコンテキストを理解し、一貫性のあるコード生成を行います。

## システム構成図

```mermaid
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
    
    K[プロジェクト管理] --> B
    L[ファイル管理] --> B
    M[プラグインシステム] --> B
    N[設定管理] --> B

アーキテクチャの主要コンポーネント
1. コアシステム (src/core/)
1.1 設定管理 (config_manager.py)
アプリケーション設定の一元管理
環境固有設定の処理
設定の永続化と読み込み

# 設定管理の基本構造
ConfigManager
├── load_config()      # 設定読み込み
├── save_config()      # 設定保存
├── get_setting()      # 設定値取得
├── set_setting()      # 設定値設定
└── validate_config()  # 設定検証

1.2 ログ管理 (logger.py)
構造化ログの出力
ログレベル管理
ファイル・コンソール出力

1.3 プロジェクト管理 (project_manager.py)
プロジェクト構造の解析
ファイル依存関係の追跡
メタデータ管理

1.4 ファイル管理 (file_manager.py)
ファイル操作の抽象化
バックアップ機能
ファイル監視

1.5 テンプレートエンジン (template_engine.py)
コードテンプレートの管理
動的コード生成
テンプレート継承

1.6 プラグインマネージャー (plugin_manager.py)
プラグインの動的読み込み
プラグインライフサイクル管理
プラグイン間通信

1.7 イベントシステム (event_system.py)
非同期イベント処理
コンポーネント間通信
イベントフィルタリング

2. LLMシステム (src/llm/)
2.1 LLM抽象化層
BaseLLM (base_llm.py)
├── OpenAIClient (openai_client.py)
├── ClaudeClient (claude_client.py)
└── LocalLLMClient (local_llm_client.py)

2.2 LLMファクトリー (llm_factory.py)
LLMインスタンスの生成
設定に基づくLLM選択
フォールバック機能

2.3 プロンプトテンプレート (prompt_templates.py)
用途別プロンプトテンプレート
コンテキスト挿入
多言語対応

2.4 レスポンス解析 (response_parser.py)
LLM出力の構造化
コード抽出
エラー処理

3. ユーザーインターフェース (src/ui/)
3.1 メインウィンドウ (main_window.py)
アプリケーションのメインUI
メニューバー・ツールバー
ドッキングシステム

3.2 コードエディタ (code_editor.py)
シンタックスハイライト
オートコンプリート
コード折りたたみ

3.3 プロジェクトツリー (project_tree.py)
ファイル階層表示
コンテキストメニュー
ドラッグ&ドロップ

3.4 チャットパネル (chat_panel.py)
LLMとの対話インターフェース
会話履歴管理
コード挿入機能

3.5 カスタムコンポーネント (components/)
再利用可能なUIコンポーネント
テーマシステム
カスタムウィジェット

4. ユーティリティ (src/utils/)
4.1 ファイルユーティリティ (file_utils.py)
ファイル操作ヘルパー
パス正規化
ファイル形式判定

4.2 テキストユーティリティ (text_utils.py)
テキスト処理
エンコーディング処理
文字列操作

4.3 バリデーションユーティリティ (validation_utils.py)
入力検証
データ形式チェック
セキュリティ検証

4.4 暗号化ユーティリティ (encryption_utils.py)
データ暗号化
API キー保護
セキュアストレージ

4.5 バックアップユーティリティ (backup_utils.py)
自動バックアップ
バージョン管理
復元機能

5. プラグインシステム (src/plugins/)
5.1 ベースプラグイン (base_plugin.py)
プラグインの基底クラス
ライフサイクル定義
イベントハンドリング

5.2 Git統合プラグイン (git_integration/)
バージョン管理統合
Git操作のGUI化
コミット支援

5.3 コードフォーマッタープラグイン (code_formatter/)
言語別コードフォーマット
スタイルガイド適用
自動整形

5.4 エクスポートツールプラグイン (export_tools/)
複数形式でのエクスポート
ドキュメント生成
レポート作成
データフロー

1. プロジェクト読み込みフロー
sequenceDiagram
    participant U as User
    participant PM as ProjectManager
    participant FM as FileManager
    participant VDB as VectorDB
    participant LLM as LocalLLM

    U->>PM: プロジェクト選択
    PM->>FM: ファイル構造解析
    FM->>PM: ファイルリスト返却
    PM->>VDB: コード情報保存
    PM->>LLM: プロジェクト情報登録
    PM->>U: 読み込み完了通知

2. コード生成フロー
sequenceDiagram
    participant U as User
    participant CP as ChatPanel
    participant VDB as VectorDB
    participant LLM as LocalLLM
    participant CE as CodeEditor

    U->>CP: 質問入力
    CP->>VDB: 関連コード検索
    VDB->>CP: 関連コード返却
    CP->>LLM: コンテキスト付きプロンプト送信
    LLM->>CP: コード生成結果返却
    CP->>CE: 生成コード挿入
    CE->>U: 結果表示

3. プラグイン実行フロー
sequenceDiagram
    participant U as User
    participant PM as PluginManager
    participant P as Plugin
    participant ES as EventSystem

    U->>PM: プラグイン実行要求
    PM->>P: プラグインアクティベート
    P->>ES: イベント登録
    P->>PM: 実行結果返却
    PM->>U: 結果通知

設計原則
1. 単一責任原則 (SRP)
各クラスは単一の責任を持ち、変更理由も単一であること。

2. 開放閉鎖原則 (OCP)
拡張に対して開放的で、修正に対して閉鎖的であること。

3. リスコフ置換原則 (LSP)
基底クラスは派生クラスで置換可能であること。

4. インターフェース分離原則 (ISP)
クライアントは使用しないインターフェースに依存すべきでない。

5. 依存性逆転原則 (DIP)
上位レベルのモジュールは下位レベルのモジュールに依存すべきでない。

セキュリティ考慮事項
1. APIキー管理
環境変数での管理
暗号化保存
アクセス制御

2. ファイルアクセス制御
サンドボックス化
パス検証
権限チェック

3. ネットワークセキュリティ
HTTPS通信
証明書検証
タイムアウト設定

4. データ保護
機密情報の暗号化
ログの匿名化
一時ファイルの安全な削除
パフォーマンス考慮事項

1. 非同期処理
LLM呼び出しの非同期化
ファイル操作の並列化
UI応答性の確保

2. キャッシュ戦略
LLMレスポンスキャッシュ
ファイル内容キャッシュ
設定値キャッシュ

3. メモリ管理
大容量ファイルの分割処理
不要オブジェクトの適切な解放
メモリリーク対策

4. データベース最適化
インデックス最適化
クエリ最適化
接続プール管理
拡張性

1. プラグインアーキテクチャ
動的プラグイン読み込み
プラグインAPI提供
プラグイン間通信

2. LLMプロバイダー拡張
新しいLLMプロバイダーの追加
カスタムプロンプトテンプレート
レスポンス形式の拡張

3. UI拡張
カスタムテーマ
ウィジェット拡張
レイアウトカスタマイズ

4. データ形式拡張
新しいファイル形式対応
カスタムパーサー
エクスポート形式追加
テスト戦略

1. 単体テスト
各コンポーネントの独立テスト
モック使用によるテスト
カバレッジ90%以上を目標

2. 統合テスト
コンポーネント間の連携テスト
エンドツーエンドテスト
パフォーマンステスト

3. UIテスト
自動UIテスト
ユーザビリティテスト
アクセシビリティテスト

4. セキュリティテスト
脆弱性スキャン
ペネトレーションテスト
セキュリティレビュー

運用・保守
1. ログ管理
構造化ログ出力
ログローテーション
監視・アラート

2. エラーハンドリング
例外の適切な処理
ユーザーフレンドリーなエラーメッセージ
自動復旧機能

3. 設定管理
環境別設定
設定の検証
設定変更の影響範囲管理

4. アップデート機能
自動アップデートチェック
段階的ロールアウト
ロールバック機能
今後の発展

1. AI機能強化
より高度なコード理解
自然言語でのコード操作
学習機能の追加

2. コラボレーション機能
リアルタイム共同編集
コードレビュー機能
チーム管理機能

3. クラウド統合
クラウドストレージ連携
リモートLLM利用
スケーラブルな処理

4. 多言語対応
プログラミング言語の拡張
自然言語の多言語化
地域固有の機能
参考資料
Clean Architecture
SOLID原則
PyQt6 Documentation
Python Best Practices