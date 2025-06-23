# src/__init__.py
# LLM Code Assistant - メインソースパッケージ初期化

"""
LLM Code Assistant - メインソースパッケージ

このパッケージには、LLM Code Assistantのメイン機能が含まれています。

パッケージ構成:
- core: コア機能（設定管理、ログ、プロジェクト管理など）
- llm: LLM関連機能（クライアント、プロンプト、レスポンス処理）
- ui: ユーザーインターフェース（GUI、ダイアログ、コンポーネント）
- utils: ユーティリティ機能（ファイル操作、テキスト処理など）
- plugins: プラグインシステム（拡張機能）

作成者: LLM Code Assistant Team
バージョン: 1.0.0
作成日: 2024-01-01
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import importlib.util
from importlib import import_module

# ロガーの設定
logger = logging.getLogger(__name__)

# パッケージディレクトリのパス
SRC_DIR = Path(__file__).parent
PROJECT_ROOT = SRC_DIR.parent

# バージョン情報
__version__ = '1.0.0'
__author__ = 'LLM Code Assistant Team'
__email__ = 'team@llm-code-assistant.com'
__description__ = 'LLM Code Assistant - AI-powered code generation and assistance tool'

# サブパッケージの定義
SUBPACKAGES = {
    'core': 'コア機能パッケージ',
    'llm': 'LLM機能パッケージ',
    'ui': 'ユーザーインターフェースパッケージ',
    'utils': 'ユーティリティパッケージ',
    'plugins': 'プラグインパッケージ'
}

# 必須モジュールの定義
REQUIRED_MODULES = {
    'core': [
        'config_manager',
        'logger',
        'project_manager',
        'file_manager',
        'template_engine',
        'plugin_manager',
        'event_system'
    ],
    'llm': [
        'base_llm',
        'openai_client',
        'claude_client',
        'local_llm_client',
        'llm_factory',
        'prompt_templates',
        'response_parser'
    ],
    'ui': [
        'main_window',
        'code_editor',
        'project_tree',
        'chat_panel',
        'settings_dialog',
        'about_dialog',
        'progress_dialog',
        'find_replace_dialog'
    ],
    'utils': [
        'file_utils',
        'text_utils',
        'validation_utils',
        'encryption_utils',
        'backup_utils'
    ],
    'plugins': [
        'base_plugin'
    ]
}

class PackageManager:
    """
    パッケージ管理クラス
    
    サブパッケージとモジュールの動的読み込み、検証、管理を行います。
    """
    
    def __init__(self):
        """初期化"""
        self.loaded_modules = {}
        self.failed_imports = {}
        self._validate_package_structure()
    
    def _validate_package_structure(self) -> None:
        """パッケージ構造の妥当性を検証"""
        try:
            for package_name, description in SUBPACKAGES.items():
                package_path = SRC_DIR / package_name
                
                if not package_path.exists():
                    logger.error(f"サブパッケージが見つかりません: {package_name} ({package_path})")
                    continue
                
                if not (package_path / '__init__.py').exists():
                    logger.error(f"__init__.pyが見つかりません: {package_name}")
                    continue
                
                logger.debug(f"サブパッケージを確認: {package_name} - {description}")
                
                # 必須モジュールの確認
                if package_name in REQUIRED_MODULES:
                    self._validate_required_modules(package_name)
                    
        except Exception as e:
            logger.error(f"パッケージ構造の検証エラー: {e}")
    
    def _validate_required_modules(self, package_name: str) -> None:
        """必須モジュールの存在を確認"""
        package_path = SRC_DIR / package_name
        required_modules = REQUIRED_MODULES.get(package_name, [])
        
        for module_name in required_modules:
            module_file = package_path / f"{module_name}.py"
            if not module_file.exists():
                logger.warning(f"必須モジュールが見つかりません: {package_name}.{module_name}")
            else:
                logger.debug(f"必須モジュールを確認: {package_name}.{module_name}")
    
    def load_module(self, package_name: str, module_name: str) -> Optional[Any]:
        """
        指定されたモジュールを動的に読み込み
        
        Args:
            package_name: パッケージ名
            module_name: モジュール名
            
        Returns:
            読み込まれたモジュール（失敗時はNone）
        """
        module_key = f"{package_name}.{module_name}"
        
        # 既に読み込み済みの場合はキャッシュから返す
        if module_key in self.loaded_modules:
            return self.loaded_modules[module_key]
        
        try:
            full_module_name = f"src.{package_name}.{module_name}"
            module = import_module(full_module_name)
            self.loaded_modules[module_key] = module
            logger.debug(f"モジュールを読み込み: {module_key}")
            return module
            
        except ImportError as e:
            self.failed_imports[module_key] = str(e)
            logger.error(f"モジュール読み込みエラー: {module_key} - {e}")
            return None
        except Exception as e:
            self.failed_imports[module_key] = str(e)
            logger.error(f"予期しないエラー: {module_key} - {e}")
            return None
    
    def load_package(self, package_name: str) -> Optional[Any]:
        """
        指定されたパッケージを読み込み
        
        Args:
            package_name: パッケージ名
            
        Returns:
            読み込まれたパッケージ（失敗時はNone）
        """
        if package_name in self.loaded_modules:
            return self.loaded_modules[package_name]
        
        try:
            full_package_name = f"src.{package_name}"
            package = import_module(full_package_name)
            self.loaded_modules[package_name] = package
            logger.debug(f"パッケージを読み込み: {package_name}")
            return package
            
        except ImportError as e:
            self.failed_imports[package_name] = str(e)
            logger.error(f"パッケージ読み込みエラー: {package_name} - {e}")
            return None
        except Exception as e:
            self.failed_imports[package_name] = str(e)
            logger.error(f"予期しないエラー: {package_name} - {e}")
            return None
    
    def get_loaded_modules(self) -> Dict[str, Any]:
        """
        読み込み済みモジュールの一覧を取得
        
        Returns:
            読み込み済みモジュールの辞書
        """
        return self.loaded_modules.copy()
    
    def get_failed_imports(self) -> Dict[str, str]:
        """
        読み込み失敗したモジュールの一覧を取得
        
        Returns:
            失敗したモジュールとエラーメッセージの辞書
        """
        return self.failed_imports.copy()
    
    def reload_module(self, package_name: str, module_name: str) -> Optional[Any]:
        """
        指定されたモジュールを再読み込み
        
        Args:
            package_name: パッケージ名
            module_name: モジュール名
            
        Returns:
            再読み込みされたモジュール（失敗時はNone）
        """
        module_key = f"{package_name}.{module_name}"
        
        # キャッシュから削除
        if module_key in self.loaded_modules:
            del self.loaded_modules[module_key]
        
        if module_key in self.failed_imports:
            del self.failed_imports[module_key]
        
        # 再読み込み
        return self.load_module(package_name, module_name)
    
    def get_package_info(self) -> Dict[str, Any]:
        """
        パッケージ情報を取得
        
        Returns:
            パッケージ情報の辞書
        """
        return {
            'version': __version__,
            'author': __author__,
            'email': __email__,
            'description': __description__,
            'src_dir': str(SRC_DIR),
            'project_root': str(PROJECT_ROOT),
            'subpackages': SUBPACKAGES,
            'required_modules': REQUIRED_MODULES,
            'loaded_modules': list(self.loaded_modules.keys()),
            'failed_imports': list(self.failed_imports.keys())
        }

# パッケージマネージャーのシングルトンインスタンス
_package_manager = None

def get_package_manager() -> PackageManager:
    """
    パッケージマネージャーのシングルトンインスタンスを取得
    
    Returns:
        PackageManager インスタンス
    """
    global _package_manager
    if _package_manager is None:
        _package_manager = PackageManager()
    return _package_manager

def load_core_modules() -> Tuple[bool, List[str]]:
    """
    コアモジュールを読み込み
    
    Returns:
        (成功フラグ, エラーメッセージのリスト)
    """
    manager = get_package_manager()
    errors = []
    
    core_modules = REQUIRED_MODULES.get('core', [])
    for module_name in core_modules:
        module = manager.load_module('core', module_name)
        if module is None:
            errors.append(f"core.{module_name}")
    
    success = len(errors) == 0
    if success:
        logger.info("コアモジュールの読み込みが完了しました")
    else:
        logger.error(f"コアモジュールの読み込みに失敗: {', '.join(errors)}")
    
    return success, errors

def initialize_package() -> bool:
    """
    パッケージの初期化
    
    Returns:
        初期化成功フラグ
    """
    try:
        logger.info(f"LLM Code Assistant v{__version__} を初期化中...")
        
        # パッケージマネージャーの初期化
        manager = get_package_manager()
        
        # コアモジュールの読み込み
        success, errors = load_core_modules()
        
        if success:
            logger.info("パッケージの初期化が完了しました")
            return True
        else:
            logger.error(f"パッケージの初期化に失敗しました: {errors}")
            return False
            
    except Exception as e:
        logger.error(f"パッケージ初期化エラー: {e}")
        return False

def get_version_info() -> Dict[str, str]:
    """
    バージョン情報を取得
    
    Returns:
        バージョン情報の辞書
    """
    return {
        'version': __version__,
        'author': __author__,
        'email': __email__,
        'description': __description__
    }

def check_dependencies() -> Dict[str, bool]:
    """
    依存関係をチェック
    
    Returns:
        依存関係の状態
    """
    dependencies = {}
    
    # 必須パッケージのチェック
    required_packages = [
        'pathlib',
        'logging',
        'typing',
        'importlib'
    ]
    
    for package in required_packages:
        try:
            importlib.util.find_spec(package)
            dependencies[package] = True
        except ImportError:
            dependencies[package] = False
    
    return dependencies

# パッケージレベルでエクスポートする要素
__all__ = [
    'PackageManager',
    'get_package_manager',
    'load_core_modules',
    'initialize_package',
    'get_version_info',
    'check_dependencies',
    'SRC_DIR',
    'PROJECT_ROOT',
    'SUBPACKAGES',
    'REQUIRED_MODULES',
    '__version__',
    '__author__',
    '__email__',
    '__description__'
]

# パッケージ初期化時の処理
try:
    # 依存関係のチェック
    deps = check_dependencies()
    missing_deps = [pkg for pkg, available in deps.items() if not available]
    
    if missing_deps:
        logger.warning(f"不足している依存関係: {', '.join(missing_deps)}")
    
    # パッケージの初期化
    if not initialize_package():
        logger.error("パッケージの初期化に失敗しました")
    
except Exception as e:
    logger.error(f"パッケージ初期化時のエラー: {e}")

# デバッグ情報の出力
if __name__ == "__main__":
    print(f"LLM Code Assistant v{__version__}")
    print(f"作成者: {__author__}")
    print(f"説明: {__description__}")
    print(f"ソースディレクトリ: {SRC_DIR}")
    print(f"プロジェクトルート: {PROJECT_ROOT}")
    
    print("\nサブパッケージ:")
    for package, description in SUBPACKAGES.items():
        print(f"  - {package}: {description}")
    
    print("\n依存関係チェック:")
    deps = check_dependencies()
    for package, available in deps.items():
        status = "✓" if available else "✗"
        print(f"  {status} {package}")
    
    print("\nパッケージマネージャー情報:")
    manager = get_package_manager()
    info = manager.get_package_info()
    print(f"  読み込み済みモジュール: {len(info['loaded_modules'])}")
    print(f"  読み込み失敗モジュール: {len(info['failed_imports'])}")
