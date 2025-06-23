# tests/conftest.py
"""
pytest設定ファイル
テスト全体で使用される共通のフィクスチャとセットアップを定義
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, Generator

# プロジェクトルートをPythonパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# テスト用のインポート
from core.config_manager import ConfigManager
from core.logger import Logger
from core.project_manager import ProjectManager
from core.file_manager import FileManager
from llm.llm_factory import LLMFactory


# pytest設定
def pytest_configure(config):
    """pytest設定の初期化"""
    # テスト環境変数の設定
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    # カスタムマーカーの登録
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_llm: marks tests that require LLM connection"
    )
    config.addinivalue_line(
        "markers", "requires_database: marks tests that require database"
    )


def pytest_unconfigure(config):
    """pytest終了時のクリーンアップ"""
    # 環境変数のクリーンアップ
    test_env_vars = ['TESTING', 'LOG_LEVEL']
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]


# 基本的なフィクスチャ
@pytest.fixture(scope="session")
def project_root() -> Path:
    """プロジェクトルートディレクトリのパス"""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def src_dir() -> Path:
    """srcディレクトリのパス"""
    return SRC_DIR


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """テストデータディレクトリのパス"""
    test_data_path = Path(__file__).parent / "test_data"
    test_data_path.mkdir(exist_ok=True)
    return test_data_path


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """一時ディレクトリ"""
    temp_path = Path(tempfile.mkdtemp(prefix="llm_test_"))
    try:
        yield temp_path
    finally:
        if temp_path.exists():
            shutil.rmtree(temp_path)


@pytest.fixture
def temp_file() -> Generator[Path, None, None]:
    """一時ファイル"""
    with tempfile.NamedTemporaryFile(delete=False, prefix="llm_test_", suffix=".py") as f:
        temp_path = Path(f.name)
    try:
        yield temp_path
    finally:
        if temp_path.exists():
            temp_path.unlink()


# 設定関連のフィクスチャ
@pytest.fixture
def test_config() -> Dict[str, Any]:
    """テスト用設定"""
    return {
        'database': {
            'type': 'sqlite',
            'path': ':memory:',
            'echo': False
        },
        'logging': {
            'level': 'DEBUG',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file_enabled': False
        },
        'llm': {
            'provider': 'mock',
            'timeout': 5,
            'max_retries': 1,
            'model': 'test-model'
        },
        'ui': {
            'theme': 'test',
            'auto_save': False,
            'window_size': [800, 600]
        },
        'project': {
            'auto_backup': False,
            'max_recent_projects': 5
        }
    }


@pytest.fixture
def config_manager(temp_dir: Path, test_config: Dict[str, Any]) -> ConfigManager:
    """テスト用ConfigManager"""
    config_file = temp_dir / "test_config.json"
    manager = ConfigManager(config_file)
    manager._config = test_config.copy()
    return manager


@pytest.fixture
def logger() -> Logger:
    """テスト用Logger"""
    return Logger("test_logger", level="DEBUG")


# プロジェクト関連のフィクスチャ
@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    """サンプルプロジェクトデータ"""
    return {
        'name': 'test_project',
        'path': '/path/to/test/project',
        'language': 'python',
        'files': [
            {
                'name': 'main.py',
                'path': '/path/to/test/project/main.py',
                'relative_path': 'main.py',
                'content': 'print("Hello, World!")',
                'language': 'python',
                'size': 22,
                'extension': '.py',
                'modified_time': '2024-01-01T12:00:00',
                'created_time': '2024-01-01T10:00:00'
            },
            {
                'name': 'utils.py',
                'path': '/path/to/test/project/utils.py',
                'relative_path': 'utils.py',
                'content': 'def helper_function():\n    pass',
                'language': 'python',
                'size': 32,
                'extension': '.py',
                'modified_time': '2024-01-01T11:00:00',
                'created_time': '2024-01-01T10:30:00'
            }
        ],
        'metadata': {
            'created_at': '2024-01-01T10:00:00',
            'updated_at': '2024-01-01T12:00:00',
            'total_files': 2,
            'total_size': 54,
            'description': 'Test project for unit testing'
        },
        'structure': {
            'directories': ['src', 'tests'],
            'files': ['main.py', 'utils.py'],
            'depth': 2
        }
    }


@pytest.fixture
def mock_project_dir(temp_dir: Path, sample_project_data: Dict[str, Any]) -> Path:
    """モックプロジェクトディレクトリ"""
    project_path = temp_dir / sample_project_data['name']
    project_path.mkdir(parents=True, exist_ok=True)
    
    # ファイルを作成
    for file_info in sample_project_data['files']:
        file_path = project_path / file_info['relative_path']
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file_info['content'], encoding='utf-8')
    
    return project_path


@pytest.fixture
def project_manager(config_manager: ConfigManager, logger: Logger) -> ProjectManager:
    """テスト用ProjectManager"""
    return ProjectManager(config_manager, logger)


@pytest.fixture
def file_manager(config_manager: ConfigManager, logger: Logger) -> FileManager:
    """テスト用FileManager"""
    return FileManager(config_manager, logger)


# LLM関連のフィクスチャ
@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """モックLLMレスポンス"""
    return {
        'content': 'This is a test response from the mock LLM.',
        'model': 'test-model',
        'usage': {
            'prompt_tokens': 10,
            'completion_tokens': 15,
            'total_tokens': 25
        },
        'finish_reason': 'stop'
    }


@pytest.fixture
def mock_llm_client(mock_llm_response: Dict[str, Any]) -> Mock:
    """モックLLMクライアント"""
    mock_client = Mock()
    mock_client.generate.return_value = mock_llm_response
    mock_client.is_available.return_value = True
    mock_client.get_model_info.return_value = {
        'name': 'test-model',
        'provider': 'mock',
        'max_tokens': 4096
    }
    return mock_client


@pytest.fixture
def llm_factory(config_manager: ConfigManager, logger: Logger) -> LLMFactory:
    """テスト用LLMFactory"""
    return LLMFactory(config_manager, logger)


# ファイル関連のフィクスチャ
@pytest.fixture
def sample_python_file(temp_dir: Path) -> Path:
    """サンプルPythonファイル"""
    content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サンプルPythonファイル
テスト用のコードファイル
"""

import os
import sys
from typing import List, Dict, Any


class SampleClass:
    """サンプルクラス"""
    
    def __init__(self, name: str):
        self.name = name
        self.data = {}
    
    def add_data(self, key: str, value: Any) -> None:
        """データを追加"""
        self.data[key] = value
    
    def get_data(self, key: str) -> Any:
        """データを取得"""
        return self.data.get(key)


def sample_function(items: List[str]) -> Dict[str, int]:
    """サンプル関数"""
    result = {}
    for item in items:
        result[item] = len(item)
    return result


if __name__ == "__main__":
    # メイン処理
    sample = SampleClass("test")
    sample.add_data("key1", "value1")
    print(f"Data: {sample.get_data('key1')}")
    
    items = ["apple", "banana", "cherry"]
    lengths = sample_function(items)
    print(f"Lengths: {lengths}")
'''
    
    file_path = temp_dir / "sample.py"
    file_path.write_text(content, encoding='utf-8')
    return file_path


@pytest.fixture
def sample_javascript_file(temp_dir: Path) -> Path:
    """サンプルJavaScriptファイル"""
    content = '''/**
 * サンプルJavaScriptファイル
 * テスト用のJSコード
 */

class SampleClass {
    constructor(name) {
        this.name = name;
        this.data = {};
    }
    
    addData(key, value) {
        this.data[key] = value;
    }
    
    getData(key) {
        return this.data[key];
    }
}

function sampleFunction(items) {
    const result = {};
    items.forEach(item => {
        result[item] = item.length;
    });
    return result;
}

// メイン処理
const sample = new SampleClass("test");
sample.addData("key1", "value1");
console.log(`Data: ${sample.getData("key1")}`);

const items = ["apple", "banana", "cherry"];
const lengths = sampleFunction(items);
console.log(`Lengths:`, lengths);
'''
    
    file_path = temp_dir / "sample.js"
    file_path.write_text(content, encoding='utf-8')
    return file_path


# データベース関連のフィクスチャ
@pytest.fixture
def mock_database() -> Mock:
    """モックデータベース"""
    mock_db = Mock()
    mock_db.connect.return_value = True
    mock_db.disconnect.return_value = True
    mock_db.execute.return_value = {'rows_affected': 1}
    mock_db.fetch_all.return_value = []
    mock_db.fetch_one.return_value = None
    return mock_db


# UI関連のフィクスチャ
@pytest.fixture
def mock_qt_application():
    """モックQtアプリケーション"""
    try:
        from PyQt6.QtWidgets import QApplication
        import sys
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        yield app
        
        # テスト後のクリーンアップ
        app.processEvents()
    except ImportError:
        # PyQt6がインストールされていない場合はモックを返す
        yield Mock()


# エラーハンドリング用のフィクスチャ
@pytest.fixture
def mock_error_handler() -> Mock:
    """モックエラーハンドラー"""
    mock_handler = Mock()
    mock_handler.handle_error.return_value = None
    mock_handler.log_error.return_value = None
    mock_handler.show_error_dialog.return_value = None
    return mock_handler


# パフォーマンステスト用のフィクスチャ
@pytest.fixture
def performance_monitor():
    """パフォーマンス監視"""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        def elapsed_time(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return PerformanceMonitor()


# テストデータ生成用のヘルパー関数
def create_test_file_data(name: str = "test.py", content: str = "", language: str = "python") -> Dict[str, Any]:
    """テスト用ファイルデータを生成"""
    return {
        'name': name,
        'path': f'/test/path/{name}',
        'content': content or f'# Test file: {name}\nprint("Hello from {name}")',
        'language': language,
        'size': len(content) if content else 50,
        'extension': Path(name).suffix,
        'modified_time': '2024-01-01T12:00:00',
        'created_time': '2024-01-01T10:00:00'
    }


def create_test_project_data(name: str = "test_project", file_count: int = 3) -> Dict[str, Any]:
    """テスト用プロジェクトデータを生成"""
    files = []
    for i in range(file_count):
        files.append(create_test_file_data(f"file_{i}.py"))
    
    return {
        'name': name,
        'path': f'/test/projects/{name}',
        'language': 'python',
        'files': files,
        'metadata': {
            'created_at': '2024-01-01T10:00:00',
            'updated_at': '2024-01-01T12:00:00',
            'total_files': file_count,
            'total_size': sum(f['size'] for f in files)
        }
    }


# テスト用のマーカー関数
def pytest_runtest_setup(item):
    """テスト実行前のセットアップ"""
    # slowマーカーがついたテストをスキップする条件
    if "slow" in item.keywords and item.config.getoption("-m") == "not slow":
        pytest.skip("slow test skipped")


# カスタムアサーション関数
def assert_file_structure_equal(actual: Dict[str, Any], expected: Dict[str, Any]):
    """ファイル構造の比較"""
    assert actual.get('name') == expected.get('name'), "File names do not match"
    assert actual.get('language') == expected.get('language'), "Languages do not match"
    assert len(actual.get('files', [])) == len(expected.get('files', [])), "File counts do not match"


def assert_llm_response_valid(response: Dict[str, Any]):
    """LLMレスポンスの検証"""
    assert 'content' in response, "Response must contain 'content'"
    assert isinstance(response['content'], str), "Content must be a string"
    assert len(response['content']) > 0, "Content must not be empty"


# テストユーティリティクラス
class TestHelper:
    """テスト用ヘルパークラス"""
    
    @staticmethod
    def create_mock_file(path: Path, content: str = ""):
        """モックファイルを作成"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content or f"# Mock file: {path.name}", encoding='utf-8')
        return path
    
    @staticmethod
    def cleanup_files(*paths: Path):
        """ファイルをクリーンアップ"""
        for path in paths:
            if path.exists():
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)


@pytest.fixture
def test_helper() -> TestHelper:
    """テストヘルパー"""
    return TestHelper()
