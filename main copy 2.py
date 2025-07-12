# main.py
"""
LLM Chat Assistant - メインエントリーポイント
多機能LLMチャットアプリケーションのメイン実行ファイル
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox
import asyncio
import threading
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 循環インポートを避けるため、インポート順序を調整
# まずコアモジュールを初期化
from src.core.logger import _setup_logging, get_logger

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

# コア例外処理
from src.core.exceptions import LLMSystemError, LLMError, ConfigError

# LLMサービスのインポート
from src.llm.llm_service import get_llm_service, initialize_llm_service
from src.llm.llm_factory import get_llm_factory, initialize_llm_factory

# UIのインポート
from src.ui.gui import create_gui

# ユーティリティのインポート
from src.utils.file_utils import FileUtils
from src.utils.text_utils import TextUtils


def setup_application():
    """
    アプリケーションの初期設定を行う
    
    Returns:
        bool: 初期化が成功した場合True
    """
    global logger
    
    try:
        # ログシステムの初期化
        _setup_logging()
        logger = get_logger(__name__)
        logger.info("アプリケーション初期化を開始します")
        
        # 設定管理の初期化
        config = _initialize_config()
        if config:
            logger.info("設定管理を初期化しました")
        else:
            logger.warning("設定管理の初期化に失敗しました")
        
        # イベントシステムの初期化
        event_system = _initialize_event_system()
        if event_system:
            logger.info("イベントシステムを初期化しました")
        else:
            logger.warning("イベントシステムの初期化に失敗しました")
        
        # LLMファクトリーの初期化
        initialize_llm_factory()
        llm_factory = get_llm_factory()
        logger.info("LLMファクトリーを初期化しました")
        
        # LLMサービスの初期化
        initialize_llm_service()
        llm_service = get_llm_service()
        logger.info("LLMサービスを初期化しました")
        
        # 必要なディレクトリの作成
        create_required_directories()
        
        # プロバイダーの初期化確認
        available_providers = llm_factory.get_available_providers()
        if not available_providers:
            logger.warning("利用可能なLLMプロバイダーがありません")
            messagebox.showwarning(
                "警告", 
                "利用可能なLLMプロバイダーがありません。\n"
                "API キーを設定してください。"
            )
        else:
            logger.info(f"利用可能なプロバイダー: {available_providers}")
        
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
            logger.debug(f"ディレクトリを作成/確認: {directory}")
        
    except Exception as e:
        logger.error(f"ディレクトリ作成エラー: {e}")
        raise

def check_dependencies():
    """
    必要な依存関係をチェック
    
    Returns:
        bool: すべての依存関係が満たされている場合True
    """
    try:
        required_modules = [
            'tkinter',
            'requests',
            'openai',
            'anthropic',
            'aiohttp',
            'pyyaml',
            'markdown',
            'beautifulsoup4'
        ]
        
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            error_msg = f"不足しているモジュール: {', '.join(missing_modules)}"
            logger.error(error_msg)
            messagebox.showerror(
                "依存関係エラー",
                f"{error_msg}\n\npip install -r requirements.txt を実行してください。"
            )
            return False
        
        logger.info("すべての依存関係が満たされています")
        return True
        
    except Exception as e:
        logger.error(f"依存関係チェックエラー: {e}")
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
                logger.warning(f"アイコン設定エラー: {e}")
        
        # ウィンドウを中央に配置
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        logger.info("メインウィンドウを作成しました")
        return root
        
    except Exception as e:
        logger.error(f"メインウィンドウ作成エラー: {e}")
        raise

def run_gui():
    """GUIアプリケーションを実行"""
    try:
        logger.info("GUIアプリケーションを開始します")
        
        # メインウィンドウを作成
        root = create_main_window()
        
        # GUIを作成
        gui = create_gui(root)
        
        # アプリケーション情報を表示
        show_startup_info()
        
        # メインループを開始
        logger.info("GUIメインループを開始します")
        root.mainloop()
        
        logger.info("GUIアプリケーションが終了しました")
        
    except Exception as e:
        logger.error(f"GUIアプリケーション実行エラー: {e}")
        messagebox.showerror("実行エラー", f"アプリケーションの実行に失敗しました: {e}")
        raise

def show_startup_info():
    """起動時の情報を表示"""
    try:
        config = _initialize_config()
        llm_factory, _ = _initialize_llm_services()
        
        # 利用可能なプロバイダー情報
        providers = llm_factory.get_available_providers()
        
        startup_info = f"""
LLM Chat Assistant が起動しました

利用可能なプロバイダー: {len(providers)}個
- {', '.join(providers) if providers else 'なし'}

設定ファイル: {config.config_file if hasattr(config, 'config_file') else '不明'}
ログレベル: {logger.level if hasattr(logger, 'level') else '不明'}
        """
        
        logger.info(startup_info.strip())
        
        # 初回起動時のヘルプ表示（オプション）
        if not providers:
            show_first_time_help()
        
    except Exception as e:
        logger.error(f"起動情報表示エラー: {e}")

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
        logger.error(f"初回起動ヘルプ表示エラー: {e}")

def run_cli():
    """CLIモードで実行（将来の実装用）"""
    try:
        logger.info("CLIモードは現在開発中です")
        print("CLIモードは現在開発中です。GUIモードを使用してください。")
        print("python main.py --gui")
        
    except Exception as e:
        logger.error(f"CLIモード実行エラー: {e}")

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

def main():
    """メイン関数"""
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
        
        messagebox.showerror("実行エラー", error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
