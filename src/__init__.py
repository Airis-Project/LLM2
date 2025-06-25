# src/__init__.py
"""
LLM Code Assistant - メインソースパッケージ

このパッケージは、LLM Code Assistantのメイン機能を提供します。

パッケージ構成:
- core: コア機能（設定管理、ログ、例外処理）
- llm: LLM関連機能（クライアント、ファクトリー）
- utils: ユーティリティ機能（ファイル操作、バリデーション）

作成者: LLM Code Assistant Team
バージョン: 1.0.0
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# パッケージディレクトリのパス
SRC_DIR = Path(__file__).parent
PROJECT_ROOT = SRC_DIR.parent

# バージョン情報
__version__ = '1.0.0'
__author__ = 'LLM Code Assistant Team'
__description__ = 'LLM Code Assistant - AI-powered code generation and assistance tool'

# コア機能のインポート
try:
    from .core import get_logger, get_config, ConfigManager
    from .core.exceptions import LLMError, LLMConfigurationError
except ImportError as e:
    print(f"コア機能のインポートエラー: {e}")
    # フォールバック用の基本ログ設定
    logging.basicConfig(level=logging.INFO)
    get_logger = logging.getLogger
    get_config = lambda: {}

# LLM機能のインポート
try:
    from .llm import (
        create_llm_client,
        create_llm_client_async,
        get_llm_factory,
        LLMConfig,
        LLMRole,
        get_available_providers
    )
    _llm_available = True
except ImportError as e:
    print(f"LLM機能のインポートエラー: {e}")
    _llm_available = False
    # フォールバック関数
    def create_llm_client(*args, **kwargs):
        raise ImportError("LLM機能が利用できません")
    def create_llm_client_async(*args, **kwargs):
        raise ImportError("LLM機能が利用できません")
    def get_llm_factory():
        raise ImportError("LLM機能が利用できません")
    def get_available_providers():
        return []

# ユーティリティ機能のインポート
try:
    from .utils import FileUtils, ValidationUtils
    _utils_available = True
except ImportError as e:
    print(f"ユーティリティ機能のインポートエラー: {e}")
    _utils_available = False

# エクスポートする要素
__all__ = [
    # コア機能
    'get_logger',
    'get_config',
    'ConfigManager',
    
    # LLM機能
    'create_llm_client',
    'create_llm_client_async',
    'get_llm_factory',
    'get_available_providers',
    
    # ユーティリティ
    'FileUtils',
    'ValidationUtils',
    
    # パッケージ情報
    'get_version_info',
    'get_package_status',
    'initialize_package',
    
    # パス情報
    'SRC_DIR',
    'PROJECT_ROOT',
    
    # バージョン情報
    '__version__',
    '__author__',
    '__description__'
]

def get_version_info() -> Dict[str, str]:
    """
    バージョン情報を取得
    
    Returns:
        バージョン情報の辞書
    """
    return {
        'version': __version__,
        'author': __author__,
        'description': __description__
    }

def get_package_status() -> Dict[str, Any]:
    """
    パッケージの状態を取得
    
    Returns:
        パッケージ状態の辞書
    """
    return {
        'version': __version__,
        'src_dir': str(SRC_DIR),
        'project_root': str(PROJECT_ROOT),
        'components': {
            'core': True,  # 常に利用可能（フォールバックあり）
            'llm': _llm_available,
            'utils': _utils_available
        },
        'available_providers': get_available_providers() if _llm_available else []
    }

def initialize_package() -> bool:
    """
    パッケージの初期化
    
    Returns:
        初期化成功フラグ
    """
    try:
        logger = get_logger(__name__)
        logger.info(f"LLM Code Assistant v{__version__} を初期化中...")
        
        # パッケージ状態の確認
        status = get_package_status()
        
        # 各コンポーネントの状態をログ出力
        for component, available in status['components'].items():
            status_text = "利用可能" if available else "利用不可"
            logger.info(f"{component}コンポーネント: {status_text}")
        
        # LLMプロバイダーの状態
        if _llm_available:
            providers = get_available_providers()
            if providers:
                logger.info(f"利用可能なLLMプロバイダー: {', '.join(providers)}")
            else:
                logger.warning("利用可能なLLMプロバイダーが見つかりません")
        
        logger.info("パッケージの初期化が完了しました")
        return True
        
    except Exception as e:
        print(f"パッケージ初期化エラー: {e}")
        return False

def check_dependencies() -> Dict[str, bool]:
    """
    依存関係をチェック
    
    Returns:
        依存関係の状態
    """
    dependencies = {}
    
    # 基本パッケージ
    basic_packages = ['pathlib', 'logging', 'typing']
    for package in basic_packages:
        try:
            __import__(package)
            dependencies[package] = True
        except ImportError:
            dependencies[package] = False
    
    # オプショナルパッケージ
    optional_packages = {
        'openai': 'OpenAI GPT支援',
        'anthropic': 'Claude支援', 
        'requests': 'HTTP通信',
        'pydantic': 'データ検証',
        'pyyaml': 'YAML設定ファイル'
    }
    
    for package, description in optional_packages.items():
        try:
            __import__(package)
            dependencies[f"{package} ({description})"] = True
        except ImportError:
            dependencies[f"{package} ({description})"] = False
    
    return dependencies

# パッケージ初期化処理
try:
    initialize_package()
except Exception as e:
    print(f"パッケージ初期化時のエラー: {e}")

# デバッグ情報の出力（スクリプト実行時のみ）
if __name__ == "__main__":
    print(f"LLM Code Assistant v{__version__}")
    print(f"作成者: {__author__}")
    print(f"説明: {__description__}")
    print(f"ソースディレクトリ: {SRC_DIR}")
    print(f"プロジェクトルート: {PROJECT_ROOT}")
    
    print("\nパッケージ状態:")
    status = get_package_status()
    for component, available in status['components'].items():
        status_symbol = "✓" if available else "✗"
        print(f"  {status_symbol} {component}")
    
    print("\n依存関係チェック:")
    deps = check_dependencies()
    for package, available in deps.items():
        status_symbol = "✓" if available else "✗"
        print(f"  {status_symbol} {package}")
    
    if status['available_providers']:
        print(f"\n利用可能なLLMプロバイダー: {', '.join(status['available_providers'])}")
