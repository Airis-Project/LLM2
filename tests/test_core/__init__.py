# tests/test_core/__init__.py
"""
coreモジュールのテストパッケージ
LLM Code Assistantのコア機能に関するテストを含む
"""

import sys
from pathlib import Path

# テスト用のパス設定
TEST_CORE_DIR = Path(__file__).parent
TESTS_DIR = TEST_CORE_DIR.parent
PROJECT_ROOT = TESTS_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

# srcディレクトリをPythonパスに追加
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# テスト対象のモジュールをインポート
try:
    from core.config_manager import ConfigManager
    from core.logger import Logger
    from core.project_manager import ProjectManager
    from core.file_manager import FileManager
    from core.template_engine import TemplateEngine
    from core.plugin_manager import PluginManager
    from core.event_system import EventSystem
except ImportError as e:
    print(f"Warning: Failed to import core modules: {e}")

# テスト用の共通設定
CORE_TEST_CONFIG = {
    'config_manager': {
        'test_config_file': 'test_config.json',
        'backup_enabled': False,
        'auto_save': False
    },
    'logger': {
        'level': 'DEBUG',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_enabled': False,
        'console_enabled': True
    },
    'project_manager': {
        'max_recent_projects': 5,
        'auto_backup': False,
        'scan_depth': 3,
        'ignored_directories': ['.git', '__pycache__', '.pytest_cache', 'node_modules']
    },
    'file_manager': {
        'max_file_size': 10 * 1024 * 1024,  # 10MB
        'supported_encodings': ['utf-8', 'utf-16', 'shift_jis', 'euc-jp'],
        'binary_extensions': ['.exe', '.dll', '.so', '.dylib', '.bin', '.dat'],
        'text_extensions': ['.py', '.js', '.html', '.css', '.md', '.txt', '.json', '.yaml', '.yml']
    },
    'template_engine': {
        'template_directory': 'templates',
        'cache_enabled': False,
        'auto_reload': True
    },
    'plugin_manager': {
        'plugin_directory': 'plugins',
        'auto_load': False,
        'sandbox_enabled': True
    },
    'event_system': {
        'max_listeners': 100,
        'async_enabled': True,
        'error_handling': 'log'
    }
}

def get_core_test_config():
    """コアテスト設定を取得"""
    return CORE_TEST_CONFIG.copy()

def get_test_config_for_module(module_name: str):
    """特定のモジュール用のテスト設定を取得"""
    return CORE_TEST_CONFIG.get(module_name, {}).copy()

# テスト用のモックデータ
MOCK_CONFIG_DATA = {
    'application': {
        'name': 'LLM Code Assistant Test',
        'version': '1.0.0-test',
        'debug': True
    },
    'database': {
        'type': 'sqlite',
        'path': ':memory:',
        'echo': False
    },
    'logging': {
        'level': 'DEBUG',
        'file_enabled': False
    },
    'ui': {
        'theme': 'test',
        'window_size': [800, 600],
        'auto_save': False
    },
    'llm': {
        'provider': 'mock',
        'model': 'test-model',
        'timeout': 5
    }
}

MOCK_PROJECT_STRUCTURE = {
    'name': 'test_project',
    'path': '/test/project/path',
    'language': 'python',
    'files': [
        {
            'name': 'main.py',
            'path': '/test/project/path/main.py',
            'relative_path': 'main.py',
            'size': 100,
            'modified_time': '2024-01-01T12:00:00'
        },
        {
            'name': 'utils.py',
            'path': '/test/project/path/utils.py',
            'relative_path': 'utils.py',
            'size': 200,
            'modified_time': '2024-01-01T11:00:00'
        }
    ],
    'directories': [
        {
            'name': 'src',
            'path': '/test/project/path/src',
            'relative_path': 'src'
        },
        {
            'name': 'tests',
            'path': '/test/project/path/tests',
            'relative_path': 'tests'
        }
    ]
}

MOCK_FILE_CONTENT = {
    'python': '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト用Pythonファイル
"""

def test_function():
    """テスト関数"""
    return "test"

class TestClass:
    """テストクラス"""
    
    def __init__(self):
        self.value = "test"
    
    def get_value(self):
        return self.value

if __name__ == "__main__":
    test = TestClass()
    print(test.get_value())
''',
    'javascript': '''/**
 * テスト用JavaScriptファイル
 */

function testFunction() {
    return "test";
}

class TestClass {
    constructor() {
        this.value = "test";
    }
    
    getValue() {
        return this.value;
    }
}

// メイン処理
const test = new TestClass();
console.log(test.getValue());
''',
    'html': '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>テストページ</title>
</head>
<body>
    <h1>テストページ</h1>
    <p>これはテスト用のHTMLファイルです。</p>
</body>
</html>
'''
}

def get_mock_config_data():
    """モック設定データを取得"""
    return MOCK_CONFIG_DATA.copy()

def get_mock_project_structure():
    """モックプロジェクト構造を取得"""
    return MOCK_PROJECT_STRUCTURE.copy()

def get_mock_file_content(language: str = 'python'):
    """モックファイル内容を取得"""
    return MOCK_FILE_CONTENT.get(language, MOCK_FILE_CONTENT['python'])

# テスト用のユーティリティ関数
def create_test_config_manager(temp_dir: Path):
    """テスト用ConfigManagerを作成"""
    config_file = temp_dir / "test_config.json"
    manager = ConfigManager(config_file)
    manager._config = get_mock_config_data()
    return manager

def create_test_logger(name: str = "test_logger"):
    """テスト用Loggerを作成"""
    return Logger(name, level="DEBUG", file_enabled=False)

def create_test_project_manager(config_manager, logger):
    """テスト用ProjectManagerを作成"""
    return ProjectManager(config_manager, logger)

def create_test_file_manager(config_manager, logger):
    """テスト用FileManagerを作成"""
    return FileManager(config_manager, logger)

def create_test_template_engine(config_manager, logger, template_dir: Path):
    """テスト用TemplateEngineを作成"""
    return TemplateEngine(config_manager, logger, template_dir)

def create_test_plugin_manager(config_manager, logger, plugin_dir: Path):
    """テスト用PluginManagerを作成"""
    return PluginManager(config_manager, logger, plugin_dir)

def create_test_event_system(config_manager, logger):
    """テスト用EventSystemを作成"""
    return EventSystem(config_manager, logger)

# テスト用のアサーション関数
def assert_config_valid(config_data: dict):
    """設定データの妥当性をアサート"""
    assert isinstance(config_data, dict), "Config must be a dictionary"
    assert 'application' in config_data, "Config must contain 'application' section"
    assert 'name' in config_data['application'], "Application section must contain 'name'"

def assert_project_structure_valid(project_data: dict):
    """プロジェクト構造の妥当性をアサート"""
    assert isinstance(project_data, dict), "Project data must be a dictionary"
    assert 'name' in project_data, "Project must have a name"
    assert 'path' in project_data, "Project must have a path"
    assert 'files' in project_data, "Project must contain files list"
    assert isinstance(project_data['files'], list), "Files must be a list"

def assert_file_data_valid(file_data: dict):
    """ファイルデータの妥当性をアサート"""
    assert isinstance(file_data, dict), "File data must be a dictionary"
    assert 'name' in file_data, "File must have a name"
    assert 'path' in file_data, "File must have a path"
    assert 'size' in file_data, "File must have a size"

def assert_logger_configured(logger):
    """ロガーの設定をアサート"""
    assert logger is not None, "Logger must not be None"
    assert hasattr(logger, 'debug'), "Logger must have debug method"
    assert hasattr(logger, 'info'), "Logger must have info method"
    assert hasattr(logger, 'warning'), "Logger must have warning method"
    assert hasattr(logger, 'error'), "Logger must have error method"

# テスト用のコンテキストマネージャー
class MockConfigContext:
    """モック設定のコンテキストマネージャー"""
    
    def __init__(self, config_data: dict):
        self.config_data = config_data
        self.original_config = None
    
    def __enter__(self):
        return self.config_data
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockProjectContext:
    """モックプロジェクトのコンテキストマネージャー"""
    
    def __init__(self, project_path: Path, project_data: dict):
        self.project_path = project_path
        self.project_data = project_data
    
    def __enter__(self):
        # プロジェクトディレクトリとファイルを作成
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        for file_info in self.project_data.get('files', []):
            file_path = self.project_path / file_info['relative_path']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイル内容を決定
            language = file_info.get('language', 'python')
            content = get_mock_file_content(language)
            file_path.write_text(content, encoding='utf-8')
        
        return self.project_path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # クリーンアップ
        import shutil
        if self.project_path.exists():
            shutil.rmtree(self.project_path)

# テスト用のデコレータ
def requires_config(func):
    """設定が必要なテスト用デコレータ"""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 設定の前提条件チェック
        return func(*args, **kwargs)
    
    return wrapper

def requires_project(func):
    """プロジェクトが必要なテスト用デコレータ"""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # プロジェクトの前提条件チェック
        return func(*args, **kwargs)
    
    return wrapper

def slow_core_test(func):
    """時間のかかるコアテスト用デコレータ"""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 遅いテストのマーキング
        return func(*args, **kwargs)
    
    wrapper._slow_core_test = True
    return wrapper

# テストスイートの情報
__test_suite__ = 'core'
__test_version__ = '1.0.0'
__test_description__ = 'Core functionality tests for LLM Code Assistant'

# エクスポートする関数とクラス
__all__ = [
    'get_core_test_config',
    'get_test_config_for_module',
    'get_mock_config_data',
    'get_mock_project_structure',
    'get_mock_file_content',
    'create_test_config_manager',
    'create_test_logger',
    'create_test_project_manager',
    'create_test_file_manager',
    'create_test_template_engine',
    'create_test_plugin_manager',
    'create_test_event_system',
    'assert_config_valid',
    'assert_project_structure_valid',
    'assert_file_data_valid',
    'assert_logger_configured',
    'MockConfigContext',
    'MockProjectContext',
    'requires_config',
    'requires_project',
    'slow_core_test'
]
