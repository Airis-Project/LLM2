# tests/__init__.py
"""
テストパッケージ
LLM Code Assistantのテストスイート
"""

import os
import sys
from pathlib import Path

# テストディレクトリのパスを取得
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

# srcディレクトリをPythonパスに追加
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# テスト環境の設定
TEST_CONFIG = {
    'test_data_dir': TEST_DIR / 'test_data',
    'temp_dir': TEST_DIR / 'temp',
    'fixtures_dir': TEST_DIR / 'fixtures',
    'mock_projects_dir': TEST_DIR / 'mock_projects'
}

# テスト用の環境変数設定
os.environ.setdefault('TESTING', 'true')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')

# テスト用のデータディレクトリを作成
for dir_path in TEST_CONFIG.values():
    dir_path.mkdir(exist_ok=True)

def get_test_config():
    """テスト設定を取得"""
    return TEST_CONFIG.copy()

def get_test_data_path(filename: str) -> Path:
    """テストデータファイルのパスを取得"""
    return TEST_CONFIG['test_data_dir'] / filename

def get_temp_path(filename: str) -> Path:
    """一時ファイルのパスを取得"""
    return TEST_CONFIG['temp_dir'] / filename

def get_fixture_path(filename: str) -> Path:
    """フィクスチャファイルのパスを取得"""
    return TEST_CONFIG['fixtures_dir'] / filename

def get_mock_project_path(project_name: str) -> Path:
    """モックプロジェクトのパスを取得"""
    return TEST_CONFIG['mock_projects_dir'] / project_name

# テスト用の共通設定
COMMON_TEST_SETTINGS = {
    'database': {
        'type': 'sqlite',
        'path': ':memory:',  # インメモリデータベース
        'echo': False
    },
    'logging': {
        'level': 'DEBUG',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    },
    'llm': {
        'provider': 'mock',
        'timeout': 5,
        'max_retries': 1
    },
    'ui': {
        'theme': 'test',
        'auto_save': False
    }
}

def get_common_test_settings():
    """共通テスト設定を取得"""
    return COMMON_TEST_SETTINGS.copy()

# テスト用のモックデータ
MOCK_PROJECT_DATA = {
    'name': 'test_project',
    'path': '/path/to/test/project',
    'language': 'python',
    'files': [
        {
            'name': 'main.py',
            'path': '/path/to/test/project/main.py',
            'content': 'print("Hello, World!")',
            'language': 'python',
            'size': 22
        },
        {
            'name': 'utils.py',
            'path': '/path/to/test/project/utils.py',
            'content': 'def helper_function():\n    pass',
            'language': 'python',
            'size': 32
        }
    ],
    'metadata': {
        'created_at': '2024-01-01T00:00:00',
        'updated_at': '2024-01-01T12:00:00',
        'total_files': 2,
        'total_size': 54
    }
}

MOCK_FILE_DATA = {
    'name': 'test_file.py',
    'path': '/path/to/test_file.py',
    'content': 'def test_function():\n    return "test"',
    'language': 'python',
    'size': 35,
    'encoding': 'utf-8',
    'line_count': 2
}

MOCK_CODE_DATA = {
    'content': 'def example():\n    return "example"',
    'language': 'python',
    'timestamp': '2024-01-01T12:00:00',
    'metadata': {
        'author': 'test_user',
        'description': 'Test code snippet'
    }
}

def get_mock_project_data():
    """モックプロジェクトデータを取得"""
    return MOCK_PROJECT_DATA.copy()

def get_mock_file_data():
    """モックファイルデータを取得"""
    return MOCK_FILE_DATA.copy()

def get_mock_code_data():
    """モックコードデータを取得"""
    return MOCK_CODE_DATA.copy()

# テスト用のユーティリティ関数
def cleanup_temp_files():
    """一時ファイルをクリーンアップ"""
    import shutil
    temp_dir = TEST_CONFIG['temp_dir']
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        temp_dir.mkdir()

def create_test_file(filename: str, content: str = "", directory: str = "temp") -> Path:
    """テスト用ファイルを作成"""
    if directory == "temp":
        file_path = get_temp_path(filename)
    elif directory == "test_data":
        file_path = get_test_data_path(filename)
    elif directory == "fixtures":
        file_path = get_fixture_path(filename)
    else:
        raise ValueError(f"Unknown directory: {directory}")
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')
    return file_path

def create_test_project(project_name: str, files: dict = None) -> Path:
    """テスト用プロジェクトを作成"""
    project_path = get_mock_project_path(project_name)
    project_path.mkdir(parents=True, exist_ok=True)
    
    if files:
        for filename, content in files.items():
            file_path = project_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
    
    return project_path

# テスト用のアサーション関数
def assert_file_exists(file_path: Path, message: str = ""):
    """ファイルの存在をアサート"""
    assert file_path.exists(), f"File does not exist: {file_path}. {message}"

def assert_file_content(file_path: Path, expected_content: str, message: str = ""):
    """ファイル内容をアサート"""
    assert_file_exists(file_path, message)
    actual_content = file_path.read_text(encoding='utf-8')
    assert actual_content == expected_content, f"File content mismatch in {file_path}. {message}"

def assert_directory_exists(dir_path: Path, message: str = ""):
    """ディレクトリの存在をアサート"""
    assert dir_path.exists() and dir_path.is_dir(), f"Directory does not exist: {dir_path}. {message}"

def assert_json_equal(actual: dict, expected: dict, message: str = ""):
    """JSON形式のデータをアサート"""
    import json
    actual_str = json.dumps(actual, sort_keys=True, ensure_ascii=False)
    expected_str = json.dumps(expected, sort_keys=True, ensure_ascii=False)
    assert actual_str == expected_str, f"JSON data mismatch. {message}"

# テスト用のデコレータ
def requires_database(func):
    """データベースが必要なテスト用デコレータ"""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # データベース接続のセットアップ
        # 実際の実装では適切なデータベースセットアップを行う
        return func(*args, **kwargs)
    
    return wrapper

def requires_llm(func):
    """LLMが必要なテスト用デコレータ"""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # LLMモックのセットアップ
        # 実際の実装では適切なLLMモックセットアップを行う
        return func(*args, **kwargs)
    
    return wrapper

def slow_test(func):
    """時間のかかるテスト用デコレータ"""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 遅いテストのマーキング
        return func(*args, **kwargs)
    
    wrapper._slow_test = True
    return wrapper

# テスト用のコンテキストマネージャー
class TempDirectory:
    """一時ディレクトリのコンテキストマネージャー"""
    
    def __init__(self, prefix: str = "test_"):
        self.prefix = prefix
        self.path = None
    
    def __enter__(self):
        import tempfile
        self.path = Path(tempfile.mkdtemp(prefix=self.prefix))
        return self.path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.path and self.path.exists():
            import shutil
            shutil.rmtree(self.path)

class MockLLMResponse:
    """モックLLMレスポンスのコンテキストマネージャー"""
    
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.original_method = None
    
    def __enter__(self):
        # LLMクライアントのモック化
        # 実際の実装では適切なモック化を行う
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # モックの復元
        pass

# テスト実行時の初期化
def setup_test_environment():
    """テスト環境のセットアップ"""
    # ログレベルの設定
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # テストディレクトリの作成
    for dir_path in TEST_CONFIG.values():
        dir_path.mkdir(exist_ok=True)
    
    # 環境変数の設定
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'DEBUG'

def teardown_test_environment():
    """テスト環境のクリーンアップ"""
    cleanup_temp_files()
    
    # 環境変数のクリーンアップ
    test_env_vars = ['TESTING', 'LOG_LEVEL']
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]

# テスト実行時の自動セットアップ
if os.environ.get('TESTING') == 'true':
    setup_test_environment()

# テストスイートの情報
__version__ = '1.0.0'
__author__ = 'LLM Code Assistant Team'
__description__ = 'Test suite for LLM Code Assistant'

# エクスポートする関数とクラス
__all__ = [
    'get_test_config',
    'get_test_data_path',
    'get_temp_path',
    'get_fixture_path',
    'get_mock_project_path',
    'get_common_test_settings',
    'get_mock_project_data',
    'get_mock_file_data',
    'get_mock_code_data',
    'cleanup_temp_files',
    'create_test_file',
    'create_test_project',
    'assert_file_exists',
    'assert_file_content',
    'assert_directory_exists',
    'assert_json_equal',
    'requires_database',
    'requires_llm',
    'slow_test',
    'TempDirectory',
    'MockLLMResponse',
    'setup_test_environment',
    'teardown_test_environment'
]
