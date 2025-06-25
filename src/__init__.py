# src/__init__.py
"""
LLM Code Assistant パッケージ
AI支援コード生成・編集ツール
"""

import logging
import sys
from pathlib import Path

# バージョン情報
__version__ = "1.0.0"
__author__ = "LLM Code Assistant Team"
__description__ = "AI-powered code generation and assistance tool"

# パッケージルートパス
PACKAGE_ROOT = Path(__file__).parent
PROJECT_ROOT = PACKAGE_ROOT.parent

# ログ設定
logger = logging.getLogger(__name__)

def setup_package_logging():
    """パッケージログ設定"""
    try:
        # ログディレクトリ作成
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # 基本ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_dir / "llm_assistant.log", encoding='utf-8')
            ]
        )
        
        logger.info(f"LLM Code Assistant v{__version__} を初期化中...")
        
    except Exception as e:
        print(f"ログ設定エラー: {e}")

def initialize_package():
    """パッケージ初期化"""
    try:
        # ログ設定
        setup_package_logging()
        
        # 必要なディレクトリ作成
        directories = [
            PROJECT_ROOT / "logs",
            PROJECT_ROOT / "data",
            PROJECT_ROOT / "cache",
            PROJECT_ROOT / "temp",
            PROJECT_ROOT / "backups"
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True)
        
        # コンポーネント可用性チェック
        components_status = check_components_availability()
        
        logger.info("パッケージの初期化が完了しました")
        
        return components_status
        
    except Exception as e:
        logger.error(f"パッケージ初期化エラー: {e}")
        return {}

def check_components_availability():
    """コンポーネント可用性チェック"""
    status = {}
    
    try:
        # Core components
        try:
            from . import core
            status['core'] = True
            logger.info("coreコンポーネント: 利用可能")
        except ImportError as e:
            status['core'] = False
            logger.warning(f"coreコンポーネント: 利用不可 ({e})")
        
        # LLM components
        try:
            from . import llm_client_v2
            status['llm'] = True
            logger.info("llmコンポーネント: 利用可能")
        except ImportError as e:
            status['llm'] = False
            logger.warning(f"llmコンポーネント: 利用不可 ({e})")
        
        # UI components
        try:
            from . import ui
            status['ui'] = True
            logger.info("uiコンポーネント: 利用可能")
        except ImportError as e:
            status['ui'] = False
            logger.warning(f"uiコンポーネント: 利用不可 ({e})")
        
        # Utils components
        try:
            from . import utils
            status['utils'] = True
            logger.info("utilsコンポーネント: 利用可能")
        except ImportError as e:
            status['utils'] = False
            logger.warning(f"utilsコンポーネント: 利用不可 ({e})")
        
        # ⭐ LLM可用性チェック
        try:
            from .llm_client_v2 import EnhancedLLMClient
            client = EnhancedLLMClient()
            if client.is_available():
                models = client.list_available_models()
                status['llm_models'] = len(models)
                logger.info(f"LLMモデル: {len(models)}個利用可能")
            else:
                status['llm_models'] = 0
                logger.warning("利用可能なLLMプロバイダーが見つかりません")
        except Exception as e:
            status['llm_models'] = 0
            logger.warning(f"LLM可用性チェック失敗: {e}")
        
    except Exception as e:
        logger.error(f"コンポーネントチェックエラー: {e}")
    
    return status

# パッケージ情報
def get_package_info():
    """パッケージ情報取得"""
    return {
        'name': 'LLM Code Assistant',
        'version': __version__,
        'author': __author__,
        'description': __description__,
        'package_root': str(PACKAGE_ROOT),
        'project_root': str(PROJECT_ROOT),
        'components': check_components_availability()
    }

# 主要クラスのエクスポート
__all__ = [
    # バージョン情報
    '__version__',
    '__author__',
    '__description__',
    
    # パス情報
    'PACKAGE_ROOT',
    'PROJECT_ROOT',
    
    # 初期化関数
    'initialize_package',
    'check_components_availability',
    'get_package_info',
    
    # 主要クラス（遅延インポート）
    'EnhancedLLMClient',
    'LLMService',
    'MainWindow',
    'ConfigManager',
    'EventBus'
]

# 遅延インポート用の__getattr__
def __getattr__(name):
    """遅延インポート"""
    if name == 'EnhancedLLMClient':
        from .llm_client_v2 import EnhancedLLMClient
        return EnhancedLLMClient
    
    elif name == 'LLMService':
        from .services.llm_service import LLMService
        return LLMService
    
    elif name == 'MainWindow':
        from .ui.main_window import MainWindow
        return MainWindow
    
    elif name == 'ConfigManager':
        from .core.config_manager import ConfigManager
        return ConfigManager
    
    elif name == 'EventBus':
        from .core.event_system import EventBus
        return EventBus
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# パッケージ初期化実行
try:
    _package_status = initialize_package()
    
    # 初期化結果をログ出力
    if _package_status:
        available_components = [k for k, v in _package_status.items() if v]
        logger.info(f"利用可能コンポーネント: {', '.join(available_components)}")
    
except Exception as e:
    logger.error(f"パッケージ初期化に失敗しました: {e}")
    print(f"警告: LLM Code Assistant の初期化中にエラーが発生しました: {e}")

# デバッグ情報（開発時のみ）
if __name__ == "__main__":
    print("=== LLM Code Assistant パッケージ情報 ===")
    info = get_package_info()
    
    print(f"名前: {info['name']}")
    print(f"バージョン: {info['version']}")
    print(f"作成者: {info['author']}")
    print(f"説明: {info['description']}")
    print(f"パッケージルート: {info['package_root']}")
    print(f"プロジェクトルート: {info['project_root']}")
    
    print("\nコンポーネント状況:")
    for component, status in info['components'].items():
        status_text = "✓" if status else "✗"
        print(f"  {status_text} {component}: {status}")
