# config/__init__.py
"""
# config/__init__.py
# 設定パッケージ - LLM Code Assistant

このパッケージは設定管理機能を提供します：
- デフォルト設定の読み込み
- ログ設定の管理
- 設定ファイルのバリデーション
- 環境変数との統合
"""

import json
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

# パッケージ情報
__version__ = "1.0.0"
__author__ = "LLM Code Assistant Team"

# 設定ディレクトリのパス
CONFIG_DIR = Path(__file__).parent
PROJECT_ROOT = CONFIG_DIR.parent

# 設定ファイルのパス
DEFAULT_SETTINGS_FILE = CONFIG_DIR / "default_settings.json"
LOGGING_CONFIG_FILE = CONFIG_DIR / "logging_config.yaml"
USER_SETTINGS_FILE = CONFIG_DIR / "user_settings.json"

@dataclass
class ConfigPaths:
    """設定ファイルのパス情報"""
    config_dir: Path = CONFIG_DIR
    default_settings: Path = DEFAULT_SETTINGS_FILE
    logging_config: Path = LOGGING_CONFIG_FILE
    user_settings: Path = USER_SETTINGS_FILE
    project_root: Path = PROJECT_ROOT

def load_default_settings() -> Dict[str, Any]:
    """
    デフォルト設定を読み込み
    
    Returns:
        Dict[str, Any]: デフォルト設定辞書
        
    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
        json.JSONDecodeError: JSONの解析に失敗した場合
    """
    try:
        if not DEFAULT_SETTINGS_FILE.exists():
            raise FileNotFoundError(f"デフォルト設定ファイルが見つかりません: {DEFAULT_SETTINGS_FILE}")
        
        with open(DEFAULT_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        return settings
        
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"デフォルト設定ファイルの解析に失敗しました: {e}")
    except Exception as e:
        raise Exception(f"デフォルト設定の読み込みに失敗しました: {e}")

def load_logging_config() -> Dict[str, Any]:
    """
    ログ設定を読み込み
    
    Returns:
        Dict[str, Any]: ログ設定辞書
        
    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
        yaml.YAMLError: YAMLの解析に失敗した場合
    """
    try:
        if not LOGGING_CONFIG_FILE.exists():
            raise FileNotFoundError(f"ログ設定ファイルが見つかりません: {LOGGING_CONFIG_FILE}")
        
        with open(LOGGING_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
        
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"ログ設定ファイルの解析に失敗しました: {e}")
    except Exception as e:
        raise Exception(f"ログ設定の読み込みに失敗しました: {e}")

def load_user_settings() -> Dict[str, Any]:
    """
    ユーザー設定を読み込み（存在しない場合は空辞書を返す）
    
    Returns:
        Dict[str, Any]: ユーザー設定辞書
    """
    try:
        if not USER_SETTINGS_FILE.exists():
            return {}
        
        with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        return settings
        
    except (json.JSONDecodeError, Exception):
        # ユーザー設定の読み込みに失敗した場合は空辞書を返す
        return {}

def save_user_settings(settings: Dict[str, Any]) -> bool:
    """
    ユーザー設定を保存
    
    Args:
        settings: 保存する設定辞書
        
    Returns:
        bool: 保存成功フラグ
    """
    try:
        # ディレクトリが存在しない場合は作成
        USER_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        print(f"ユーザー設定の保存に失敗しました: {e}")
        return False

def merge_settings(*settings_dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    複数の設定辞書をマージ（後の辞書が優先）
    
    Args:
        *settings_dicts: マージする設定辞書
        
    Returns:
        Dict[str, Any]: マージされた設定辞書
    """
    def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深い階層まで辞書をマージ"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    if not settings_dicts:
        return {}
    
    result = settings_dicts[0].copy()
    for settings in settings_dicts[1:]:
        result = deep_merge(result, settings)
    
    return result

def validate_settings(settings: Dict[str, Any]) -> bool:
    """
    設定の基本的なバリデーション
    
    Args:
        settings: 検証する設定辞書
        
    Returns:
        bool: 設定が有効な場合True
    """
    try:
        # 必須セクションの確認
        required_sections = ['application', 'ui', 'llm', 'logging']
        for section in required_sections:
            if section not in settings:
                return False
        
        # アプリケーション設定の確認
        app_config = settings.get('application', {})
        if not app_config.get('name') or not app_config.get('version'):
            return False
        
        # LLM設定の確認
        llm_config = settings.get('llm', {})
        if 'providers' not in llm_config:
            return False
        
        return True
        
    except Exception:
        return False

def get_config_info() -> Dict[str, Any]:
    """
    設定パッケージの情報を取得
    
    Returns:
        Dict[str, Any]: パッケージ情報
    """
    return {
        'version': __version__,
        'author': __author__,
        'config_dir': str(CONFIG_DIR),
        'files': {
            'default_settings': str(DEFAULT_SETTINGS_FILE),
            'logging_config': str(LOGGING_CONFIG_FILE),
            'user_settings': str(USER_SETTINGS_FILE)
        },
        'file_exists': {
            'default_settings': DEFAULT_SETTINGS_FILE.exists(),
            'logging_config': LOGGING_CONFIG_FILE.exists(),
            'user_settings': USER_SETTINGS_FILE.exists()
        }
    }

def create_default_user_settings() -> Dict[str, Any]:
    """
    デフォルトのユーザー設定を作成
    
    Returns:
        Dict[str, Any]: デフォルトユーザー設定
    """
    return {
        'ui': {
            'theme': {
                'current': 'dark'
            },
            'window': {
                'width': 1200,
                'height': 800,
                'maximized': False,
                'position': {
                    'x': 100,
                    'y': 100
                }
            },
            'editor': {
                'font_size': 12,
                'tab_width': 4,
                'show_line_numbers': True
            }
        },
        'llm': {
            'default_provider': 'openai',
            'last_used_model': 'gpt-4'
        },
        'project': {
            'recent_projects': [],
            'last_opened_project': None
        },
        'preferences': {
            'auto_save': True,
            'auto_backup': True,
            'check_updates': True
        }
    }

def ensure_config_directories():
    """必要な設定ディレクトリを作成"""
    try:
        # 基本ディレクトリ
        directories = [
            CONFIG_DIR,
            PROJECT_ROOT / 'logs',
            PROJECT_ROOT / 'data',
            PROJECT_ROOT / 'cache',
            PROJECT_ROOT / 'temp',
            PROJECT_ROOT / 'backups',
            PROJECT_ROOT / 'user_data'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        return True
        
    except Exception as e:
        print(f"設定ディレクトリの作成に失敗しました: {e}")
        return False

# エクスポートする要素
__all__ = [
    # パス情報
    'CONFIG_DIR',
    'PROJECT_ROOT',
    'DEFAULT_SETTINGS_FILE',
    'LOGGING_CONFIG_FILE',
    'USER_SETTINGS_FILE',
    'ConfigPaths',
    
    # 設定読み込み関数
    'load_default_settings',
    'load_logging_config',
    'load_user_settings',
    'save_user_settings',
    
    # ユーティリティ関数
    'merge_settings',
    'validate_settings',
    'get_config_info',
    'create_default_user_settings',
    'ensure_config_directories',
    
    # バージョン情報
    '__version__',
    '__author__'
]

# パッケージ初期化処理
def _initialize_config_package():
    """設定パッケージの初期化"""
    try:
        # 必要なディレクトリを作成
        ensure_config_directories()
        
        # ユーザー設定ファイルが存在しない場合は作成
        if not USER_SETTINGS_FILE.exists():
            default_user_settings = create_default_user_settings()
            save_user_settings(default_user_settings)
        
        return True
        
    except Exception as e:
        print(f"設定パッケージの初期化に失敗しました: {e}")
        return False

# パッケージ読み込み時に初期化実行
_initialize_config_package()

# デバッグ情報の出力（スクリプト実行時のみ）
if __name__ == "__main__":
    print("=== LLM Code Assistant 設定パッケージ ===")
    print(f"バージョン: {__version__}")
    print(f"作成者: {__author__}")
    
    # 設定情報の表示
    info = get_config_info()
    print(f"\n設定ディレクトリ: {info['config_dir']}")
    
    print("\n設定ファイル:")
    for name, path in info['files'].items():
        exists = "✓" if info['file_exists'][name] else "✗"
        print(f"  {exists} {name}: {path}")
    
    # 設定の読み込みテスト
    try:
        default_settings = load_default_settings()
        print(f"\nデフォルト設定読み込み: ✓ ({len(default_settings)} セクション)")
    except Exception as e:
        print(f"\nデフォルト設定読み込み: ✗ ({e})")
    
    try:
        logging_config = load_logging_config()
        print(f"ログ設定読み込み: ✓ (バージョン {logging_config.get('version', 'N/A')})")
    except Exception as e:
        print(f"ログ設定読み込み: ✗ ({e})")
    
    try:
        user_settings = load_user_settings()
        print(f"ユーザー設定読み込み: ✓ ({len(user_settings)} 項目)")
    except Exception as e:
        print(f"ユーザー設定読み込み: ✗ ({e})")
