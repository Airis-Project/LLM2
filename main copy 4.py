# main.py
"""
LLM Chat Assistant - メインエントリーポイント
多機能LLMチャットアプリケーションのメイン実行ファイル
"""

import sys
import os
import argparse
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from typing import Optional, Dict, Any

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# グローバル変数（遅延初期化用）
logger = None
config_manager = None
event_system = None
llm_factory = None
llm_service = None
app = None

# 次に設定管理を初期化（遅延インポートを使用）
def _initialize_config():
    """設定管理を遅延初期化"""
    try:
        from src.core.config_manager import get_config, initialize_config
        initialize_config()
        return get_config()
    except Exception as e:
        print(f"設定管理初期化エラー: {e}")
        return None

def _initialize_event_system():
    """イベントシステムを遅延初期化"""
    try:
        from src.core.event_system import get_event_system, initialize_event_system
        initialize_event_system()
        return get_event_system()
    except Exception as e:
        print(f"イベントシステム初期化エラー: {e}")
        return None

def _initialize_llm_services():
    """LLMサービスを遅延初期化"""
    try:
        from src.llm.llm_service import get_llm_service, initialize_llm_service
        from src.llm.llm_factory import get_llm_factory, initialize_llm_factory
        
        initialize_llm_factory()
        initialize_llm_service()
        
        return get_llm_factory(), get_llm_service()
    except Exception as e:
        print(f"LLMサービス初期化エラー: {e}")
        return None, None

def _initialize_ui():
    """UIを遅延初期化"""
    try:
        from src.ui.gui import create_gui
        return create_gui
    except Exception as e:
        print(f"UI初期化エラー: {e}")
        return None

def setup_logging():
    """ログシステムをセットアップ"""
    global logger
    try:
        from src.core.logger import configure_logging, LogConfig, get_logger
        
        log_config = LogConfig(
            level='INFO',
            format_type='detailed',
            console_enabled=True,
            file_enabled=True
        )
        configure_logging(log_config)
        logger = get_logger(__name__)
        logger.info("ログシステムを初期化しました")
        return True
    except Exception as e:
        print(f"ログシステム初期化エラー: {e}")
        return False

def setup_config():
    """設定管理をセットアップ"""
    global config_manager
    try:
        from src.core.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        config_manager.initialize()
        
        if logger:
            logger.info("設定管理を初期化しました")
        return True
    except Exception as e:
        if logger:
            logger.error(f"設定管理初期化エラー: {e}")
        else:
            print(f"設定管理初期化エラー: {e}")
        return False

def setup_event_system():
    """イベントシステムをセットアップ"""
    global event_system
    try:
        from src.core.event_system import EventSystem
        
        event_system = EventSystem()
        
        if logger:
            logger.info("イベントシステムを初期化しました")
        return True
    except Exception as e:
        if logger:
            logger.error(f"イベントシステム初期化エラー: {e}")
        else:
            print(f"イベントシステム初期化エラー: {e}")
        return False
    
def setup_llm_services():
    """LLMサービスをセットアップ"""
    global llm_factory, llm_service
    try:
        from src.llm.llm_factory import LLMFactory
        from src.llm.llm_service import LLMServiceCore
        
        llm_factory = LLMFactory()
        llm_service = LLMServiceCore()
        
        if logger:
            logger.info("LLMサービスを初期化しました")
        return True
    except Exception as e:
        if logger:
            logger.error(f"LLMサービス初期化エラー: {e}")
        else:
            print(f"LLMサービス初期化エラー: {e}")
        return False

def setup_application():
    """
    アプリケーションの初期設定を行う
    Returns:
        bool: 初期化が成功した場合True
    """
    global logger
    
    try:
        """アプリケーションの初期設定を行う"""
        # 1. ログシステムの初期化
        if not setup_logging():
            return False
        
        # 2. 設定管理の初期化
        if not setup_config():
            return False
        
        # 3. イベントシステムの初期化
        if not setup_event_system():
            return False
        
        # 4. LLMサービスの初期化
        if not setup_llm_services():
            return False
        
        # 必要なディレクトリの作成
        create_required_directories()
        
        logger.info("アプリケーション初期化が完了しました")
        return True
        
    except Exception as e:
        error_msg = f"アプリケーション初期化エラー: {e}"
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        
        messagebox.showerror("初期化エラー", error_msg)
        return False

def create_required_directories():
    """必要なディレクトリを作成"""
    try:
        directories = [
            "config",
            "logs",
            "data",
            "cache",
            "exports",
            "templates"
        ]
        
        for directory in directories:
            dir_path = Path(directory)
            dir_path.mkdir(exist_ok=True)
            if logger:
                logger.debug(f"ディレクトリを作成/確認: {directory}")
        
    except Exception as e:
        if logger:
            logger.error(f"ディレクトリ作成エラー: {e}")
        else:
            print(f"ディレクトリ作成エラー: {e}")
        raise

def create_gui_app():
    """GUIアプリケーションを作成"""
    global app
    try:
        from src.ui.gui import create_gui
        
        root = tk.Tk()
        app = create_gui(root)
        
        # 終了処理の設定
        def on_closing():
            cleanup_resources()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        logger.info("GUIアプリケーションを作成しました")
        return root
    except Exception as e:
        logger.error(f"GUI作成エラー: {e}")
        raise

def check_dependencies():
    """
    必要な依存関係をチェック
    
    Returns:
        bool: すべての依存関係が満たされている場合True
    """
    try:
        # モジュール名とインポート名のマッピング
        required_modules = {
            'tkinter': 'tkinter',
            'requests': 'requests', 
            'openai': 'openai',
            'anthropic': 'anthropic',
            'aiohttp': 'aiohttp',
            'yaml': 'PyYAML',
            'markdown': 'markdown',
            'bs4': 'beautifulsoup4'
        }
        
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            error_msg = f"不足しているモジュール: {', '.join(missing_modules)}"
            if logger:
                logger.error(error_msg)
            else:
                print(error_msg)
            messagebox.showerror(
                "依存関係エラー",
                f"{error_msg}\n\npip install -r requirements.txt を実行してください。"
            )
            return False
        
        if logger:
            logger.info("すべての依存関係が満たされています")
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"依存関係チェックエラー: {e}")
        else:
            print(f"依存関係チェックエラー: {e}")
        return False

def setup_exception_handler():
    """グローバル例外ハンドラーを設定"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Ctrl+C による中断は通常の終了として扱う
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        error_msg = f"予期しないエラーが発生しました: {exc_value}"
        
        if logger:
            logger.error(error_msg, exc_info=(exc_type, exc_value, exc_traceback))
        else:
            print(error_msg)
        
        # GUIが利用可能な場合はメッセージボックスを表示
        try:
            messagebox.showerror("予期しないエラー", error_msg)
        except:
            pass
    
    sys.excepthook = handle_exception

def create_main_window():
    """
    メインウィンドウを作成
    
    Returns:
        tk.Tk: Tkinterルートウィンドウ
    """
    try:
        # Tkinterルートウィンドウを作成
        root = tk.Tk()
        
        # ウィンドウの基本設定
        root.title("LLM Chat Assistant")
        root.geometry("1200x800")
        
        # アイコンの設定（存在する場合）
        icon_path = Path("assets/icon.ico")
        if icon_path.exists():
            try:
                root.iconbitmap(str(icon_path))
            except Exception as e:
                if logger:
                    logger.warning(f"アイコン設定エラー: {e}")
        
        # ウィンドウを中央に配置
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        if logger:
            logger.info("メインウィンドウを作成しました")
        return root
        
    except Exception as e:
        if logger:
            logger.error(f"メインウィンドウ作成エラー: {e}")
        else:
            print(f"メインウィンドウ作成エラー: {e}")
        raise

def run_gui():
    """GUIアプリケーションを実行"""
    try:
        if logger:
            logger.info("GUIアプリケーションを開始します")
        
        # メインウィンドウを作成
        root = create_main_window()
        
        # GUIを作成
        create_gui_func = _initialize_ui()
        if create_gui_func:
            gui = create_gui_func(root)
        else:
            messagebox.showerror("エラー", "GUIの初期化に失敗しました")
            return
        
        # アプリケーション情報を表示
        show_startup_info()
        
        # メインループを開始
        if logger:
            logger.info("GUIメインループを開始します")
        root.mainloop()
        
        if logger:
            logger.info("GUIアプリケーションが終了しました")
        
    except Exception as e:
        error_msg = f"GUIアプリケーション実行エラー: {e}"
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        messagebox.showerror("実行エラー", f"アプリケーションの実行に失敗しました: {e}")
        raise

def show_startup_info():
    """起動時の情報を表示"""
    try:
        config = _initialize_config()
        llm_factory, _ = _initialize_llm_services()
        
        # 利用可能なプロバイダー情報
        providers = []
        if llm_factory:
            providers = llm_factory.get_available_providers()
        
        startup_info = f"""
LLM Chat Assistant が起動しました

利用可能なプロバイダー: {len(providers)}個
- {', '.join(providers) if providers else 'なし'}

設定ファイル: {config.config_file if config and hasattr(config, 'config_file') else '不明'}
ログレベル: {logger.level if logger and hasattr(logger, 'level') else '不明'}
        """
        
        if logger:
            logger.info(startup_info.strip())
        
        # 初回起動時のヘルプ表示（オプション）
        if not providers:
            show_first_time_help()
        
    except Exception as e:
        if logger:
            logger.error(f"起動情報表示エラー: {e}")
        else:
            print(f"起動情報表示エラー: {e}")

def show_first_time_help():
    """初回起動時のヘルプを表示"""
    try:
        help_msg = """
LLM Chat Assistant へようこそ！

現在、利用可能なLLMプロバイダーがありません。
以下の手順で設定してください：

1. OpenAI を使用する場合:
   - OpenAI API キーを取得
   - 環境変数 OPENAI_API_KEY に設定

2. Anthropic Claude を使用する場合:
   - Anthropic API キーを取得
   - 環境変数 ANTHROPIC_API_KEY に設定

3. ローカルLLM (Ollama) を使用する場合:
   - Ollama をインストール
   - モデルをダウンロード

設定後、アプリケーションを再起動してください。
        """
        
        messagebox.showinfo("初回起動ヘルプ", help_msg)
        
    except Exception as e:
        if logger:
            logger.error(f"初回起動ヘルプ表示エラー: {e}")
        else:
            print(f"初回起動ヘルプ表示エラー: {e}")

def run_cli():
    """CLIモードで実行（将来の実装用）"""
    try:
        if logger:
            logger.info("CLIモードは現在開発中です")
        print("CLIモードは現在開発中です。GUIモードを使用してください。")
        print("python main.py --gui")
        
    except Exception as e:
        if logger:
            logger.error(f"CLIモード実行エラー: {e}")
        else:
            print(f"CLIモード実行エラー: {e}")
            
def generate_text(prompt: str, provider: Optional[str] = None, model: Optional[str] = None):
    """テキストを生成"""
    try:
        from src.llm.llm_service import TaskType
        
        task = llm_service.create_task(
            task_type=TaskType.GENERAL,
            prompt=prompt,
            provider=provider,
            model=model
        )
        
        result = llm_service.execute_task(task)
        
        if result.success:
            logger.info("生成結果:")
            print(result.content)
        else:
            logger.error(f"生成失敗: {result.error}")
            
    except Exception as e:
        logger.error(f"テキスト生成エラー: {e}")

def signal_handler(signum, frame):
    """シグナルハンドラー"""
    logger.info(f"シグナル {signum} を受信しました。終了処理を開始...")
    cleanup_resources()
    sys.exit(0)

def cleanup_resources():
    """リソースをクリーンアップ"""
    try:
        logger.info("リソースのクリーンアップを開始...")
        
        # LLMサービスのクリーンアップ
        if llm_service:
            llm_service.cleanup()
        
        # LLMファクトリーのクリーンアップ
        if llm_factory:
            llm_factory.cleanup_all_clients()
        
        # イベントシステムのクリーンアップ
        if event_system:
            event_system.cleanup()
        
        # 設定の保存
        if config_manager:
            config_manager.save_all()
        
        logger.info("リソースのクリーンアップが完了しました")
        
    except Exception as e:
        if logger:
            logger.error(f"クリーンアップエラー: {e}")
        else:
            print(f"クリーンアップエラー: {e}")

def cleanup_application():
    """アプリケーション終了時のクリーンアップ"""
    try:
        if logger:
            logger.info("アプリケーションのクリーンアップを開始します")
        
        # LLMサービスのクリーンアップ
        try:
            _, llm_service = _initialize_llm_services()
            if llm_service:
                llm_service.cleanup()
                if logger:
                    logger.info("LLMサービスをクリーンアップしました")
        except Exception as e:
            if logger:
                logger.error(f"LLMサービスクリーンアップエラー: {e}")
        
        # イベントシステムのクリーンアップ
        try:
            event_system = _initialize_event_system()
            if event_system:
                event_system.cleanup()
                if logger:
                    logger.info("イベントシステムをクリーンアップしました")
        except Exception as e:
            if logger:
                logger.error(f"イベントシステムクリーンアップエラー: {e}")
        
        if logger:
            logger.info("アプリケーションのクリーンアップが完了しました")
        
    except Exception as e:
        if logger:
            logger.error(f"クリーンアップエラー: {e}")
        else:
            print(f"クリーンアップエラー: {e}")

def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(description='LLMシステム')
    parser.add_argument('--mode', choices=['gui', 'cli'], default='gui',
                       help='実行モード (default: gui)')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                       help='設定ファイルのパス')
    
    # CLIモード用のサブコマンド
    subparsers = parser.add_subparsers(dest='command', help='CLIコマンド')
    
    # テストコマンド
    test_parser = subparsers.add_parser('test', help='LLM接続をテスト')
    
    # 生成コマンド
    generate_parser = subparsers.add_parser('generate', help='テキストを生成')
    generate_parser.add_argument('prompt', type=str, help='プロンプト')
    generate_parser.add_argument('--provider', type=str, help='プロバイダー')
    generate_parser.add_argument('--model', type=str, help='モデル')
    
    return parser.parse_args()

def main():
    """メイン関数"""
    global logger
    logger = None
    
    try:
        # コマンドライン引数の解析
        import argparse
        
        parser = argparse.ArgumentParser(description="LLM Chat Assistant")
        parser.add_argument("--gui", action="store_true", default=True, help="GUIモードで起動（デフォルト）")
        parser.add_argument("--cli", action="store_true", help="CLIモードで起動")
        parser.add_argument("--debug", action="store_true", help="デバッグモードで起動")
        parser.add_argument("--config", type=str, help="設定ファイルのパス")
        
        args = parser.parse_args()
        
        # グローバル例外ハンドラーを設定
        setup_exception_handler()
        
        # アプリケーションの初期化
        if not setup_application():
            sys.exit(1)
        
        # 依存関係のチェック
        if not check_dependencies():
            sys.exit(1)
        
        try:
            # 実行モードに応じて処理を分岐
            if args.cli:
                run_cli()
            else:
                run_gui()
                
        finally:
            # クリーンアップ
            cleanup_application()
    
    except KeyboardInterrupt:
        print("\nアプリケーションが中断されました")
        if logger:
            logger.info("アプリケーションが中断されました")
        sys.exit(0)
    
    except Exception as e:
        error_msg = f"アプリケーション実行エラー: {e}"
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        
        try:
            messagebox.showerror("実行エラー", error_msg)
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
