# src/main.py
"""
メインエントリーポイント
アプリケーションの起動と初期化を管理
"""

import sys
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import ConfigManager
from src.core.event_system import EventBus
from src.core.plugin_manager import PluginManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def initialize_application():
    """アプリケーションの初期化"""
    try:
        logger.info("アプリケーションを初期化しています...")
        
        # 設定マネージャーの初期化
        config_manager = ConfigManager()
        logger.info("ConfigManagerが初期化されました")
        
        # イベントシステムの初期化
        event_bus = EventBus()
        logger.info("EventBusが初期化されました")
        
        # プラグインマネージャーの初期化
        plugin_manager = PluginManager()
        logger.info("PluginManagerが初期化されました")
        
        logger.info("アプリケーションの初期化が完了しました")
        
        return {
            'config_manager': config_manager,
            'event_bus': event_bus,
            'plugin_manager': plugin_manager
        }
        
    except Exception as e:
        logger.error(f"アプリケーションの初期化中にエラーが発生しました: {e}")
        raise

def main():
    """メイン関数"""
    try:
        # アプリケーション初期化
        app_components = initialize_application()
        
        # PyQt6アプリケーションの起動
        from PyQt6.QtWidgets import QApplication
        from src.ui.main_window import MainWindow
        
        app = QApplication(sys.argv)
        
        # アプリケーション情報設定
        config = app_components['config_manager'].config
        app_config = config.get('app', {})
        
        app.setApplicationName(app_config.get('name', 'LLM Application'))
        app.setApplicationVersion(app_config.get('version', '1.0.0'))
        app.setOrganizationName('LLM Development Team')
        
        # メインウィンドウ作成（コンポーネントを渡す）
        window = MainWindow(app_components)
        window.show()
        
        logger.info("アプリケーションを開始しました")
        
        # アプリケーション実行
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"アプリケーション実行中にエラーが発生しました: {e}")
        
        # エラーダイアログを表示
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if not QApplication.instance():
                app = QApplication(sys.argv)
            
            QMessageBox.critical(
                None,
                "エラー",
                f"アプリケーションの初期化中にエラーが発生しました:\n{str(e)}"
            )
        except:
            pass
        
        sys.exit(1)

if __name__ == '__main__':
    main()
