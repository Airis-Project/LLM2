# config/__init__.py
"""
設定管理パッケージ

アプリケーションの設定ファイルと設定管理機能を提供します：
- default_settings.json: デフォルト設定
- logging_config.yaml: ログ設定
- 設定の読み込み・保存・検証機能
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# パッケージレベルの設定
CONFIG_DIR = Path(__file__).parent
DEFAULT_SETTINGS_FILE = CONFIG_DIR / "default_settings.json"
LOGGING_CONFIG_FILE = CONFIG_DIR / "logging_config.yaml"

# バージョン情報
__version__ = "1.0.0"

def load_default_settings() -> Dict[str, Any]:
    """
    デフォルト設定の読み込み
    
    Returns:
        Dict[str, Any]: デフォルト設定辞書
        
    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
        json.JSONDecodeError: JSON形式が不正な場合
    """
    try:
        with open(DEFAULT_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"デフォルト設定ファイルが見つかりません: {DEFAULT_SETTINGS_FILE}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"デフォルト設定ファイルのJSON形式が不正です: {e}")
        raise

def load_logging_config() -> Dict[str, Any]:
    """
    ログ設定の読み込み
    
    Returns:
        Dict[str, Any]: ログ設定辞書
        
    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
        yaml.YAMLError: YAML形式が不正な場合
    """
    try:
        with open(LOGGING_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"ログ設定ファイルが見つかりません: {LOGGING_CONFIG_FILE}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"ログ設定ファイルのYAML形式が不正です: {e}")
        raise

def validate_settings(settings: Dict[str, Any]) -> bool:
    """
    設定の妥当性検証
    
    Args:
        settings: 検証する設定辞書
        
    Returns:
        bool: 設定が有効な場合True
    """
    required_keys = [
        "app_name",
        "version", 
        "ui",
        "llm",
        "logging"
    ]
    
    # 必須キーの存在確認
    for key in required_keys:
        if key not in settings:
            logging.error(f"必須設定キー '{key}' が見つかりません")
            return False
    
    # UI設定の検証
    ui_config = settings.get("ui", {})
    if not isinstance(ui_config, dict):
        logging.error("UI設定が辞書形式ではありません")
        return False
    
    # LLM設定の検証
    llm_config = settings.get("llm", {})
    if not isinstance(llm_config, dict):
        logging.error("LLM設定が辞書形式ではありません")
        return False
    
    return True

def get_config_file_paths() -> Dict[str, Path]:
    """
    設定ファイルのパス一覧を取得
    
    Returns:
        Dict[str, Path]: 設定ファイルパス辞書
    """
    return {
        "default_settings": DEFAULT_SETTINGS_FILE,
        "logging_config": LOGGING_CONFIG_FILE,
        "config_dir": CONFIG_DIR
    }

# エクスポートする関数
__all__ = [
    "load_default_settings",
    "load_logging_config", 
    "validate_settings",
    "get_config_file_paths",
    "CONFIG_DIR",
    "DEFAULT_SETTINGS_FILE",
    "LOGGING_CONFIG_FILE",
    "__version__"
]

# パッケージ初期化
def _initialize_config_package():
    """設定パッケージの初期化"""
    logger = logging.getLogger(__name__)
    
    # 設定ファイルの存在確認
    if not DEFAULT_SETTINGS_FILE.exists():
        logger.warning(f"デフォルト設定ファイルが存在しません: {DEFAULT_SETTINGS_FILE}")
    
    if not LOGGING_CONFIG_FILE.exists():
        logger.warning(f"ログ設定ファイルが存在しません: {LOGGING_CONFIG_FILE}")
    
    logger.info("設定パッケージが初期化されました")

# パッケージ読み込み時に初期化実行
_initialize_config_package()
