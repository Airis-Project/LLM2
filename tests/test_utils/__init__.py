# tests/test_utils/__init__.py
"""
ユーティリティテストパッケージ
ユーティリティ関数のテストモジュールを提供
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from unittest.mock import Mock, patch, MagicMock

# 共通テストユーティリティ
from tests.test_core import (
    create_test_config_manager,
    create_test_logger,
    MockFileContext,
    requires_file
)


class UtilsTestBase:
    """ユーティリティテストの基底クラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        # テスト用の一時ディレクトリ
        self.temp_dir = Path(tempfile.mkdtemp(prefix="utils_test_"))
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_utils")
        
        # テスト用ファイルの作成
        self._create_test_files()
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_test_files(self):
        """テスト用ファイルの作成"""
        # テキストファイル
        self.test_text_file = self.temp_dir / "test.txt"
        self.test_text_content = "Hello, World!\nThis is a test file.\n日本語のテストです。"
        self.test_text_file.write_text(self.test_text_content, encoding='utf-8')
        
        # JSONファイル
        self.test_json_file = self.temp_dir / "test.json"
        self.test_json_data = {
            "name": "Test Project",
            "version": "1.0.0",
            "description": "テストプロジェクト",
            "settings": {
                "debug": True,
                "max_items": 100
            }
        }
        import json
        self.test_json_file.write_text(
            json.dumps(self.test_json_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        # バイナリファイル
        self.test_binary_file = self.temp_dir / "test.bin"
        self.test_binary_data = b'\x00\x01\x02\x03\xFF\xFE\xFD'
        self.test_binary_file.write_bytes(self.test_binary_data)
        
        # 大きなファイル
        self.test_large_file = self.temp_dir / "large.txt"
        large_content = "Large file content.\n" * 10000
        self.test_large_file.write_text(large_content, encoding='utf-8')
        
        # サブディレクトリとファイル
        self.test_subdir = self.temp_dir / "subdir"
        self.test_subdir.mkdir()
        
        self.test_subfile = self.test_subdir / "subfile.txt"
        self.test_subfile.write_text("Subfile content", encoding='utf-8')
        
        # 空のディレクトリ
        self.test_empty_dir = self.temp_dir / "empty_dir"
        self.test_empty_dir.mkdir()
        
        # 複数レベルのディレクトリ
        self.test_deep_dir = self.temp_dir / "level1" / "level2" / "level3"
        self.test_deep_dir.mkdir(parents=True)
        
        self.test_deep_file = self.test_deep_dir / "deep_file.txt"
        self.test_deep_file.write_text("Deep file content", encoding='utf-8')


class MockFileSystem:
    """テスト用のファイルシステムモック"""
    
    def __init__(self):
        self.files = {}
        self.directories = set()
        self.permissions = {}
        self.access_times = {}
        self.modification_times = {}
        self.file_sizes = {}
    
    def create_file(self, path: str, content: Union[str, bytes] = "", 
                   permissions: int = 0o644):
        """ファイル作成"""
        self.files[path] = content
        self.permissions[path] = permissions
        self.file_sizes[path] = len(content) if isinstance(content, (str, bytes)) else 0
        
        # ディレクトリも作成
        parent_dir = str(Path(path).parent)
        if parent_dir != path:
            self.directories.add(parent_dir)
    
    def create_directory(self, path: str, permissions: int = 0o755):
        """ディレクトリ作成"""
        self.directories.add(path)
        self.permissions[path] = permissions
    
    def exists(self, path: str) -> bool:
        """パス存在確認"""
        return path in self.files or path in self.directories
    
    def is_file(self, path: str) -> bool:
        """ファイル確認"""
        return path in self.files
    
    def is_directory(self, path: str) -> bool:
        """ディレクトリ確認"""
        return path in self.directories
    
    def get_content(self, path: str) -> Union[str, bytes, None]:
        """ファイル内容取得"""
        return self.files.get(path)
    
    def set_content(self, path: str, content: Union[str, bytes]):
        """ファイル内容設定"""
        if path in self.files:
            self.files[path] = content
            self.file_sizes[path] = len(content) if isinstance(content, (str, bytes)) else 0
    
    def delete_file(self, path: str):
        """ファイル削除"""
        if path in self.files:
            del self.files[path]
            if path in self.permissions:
                del self.permissions[path]
            if path in self.file_sizes:
                del self.file_sizes[path]
    
    def delete_directory(self, path: str):
        """ディレクトリ削除"""
        if path in self.directories:
            self.directories.remove(path)
            if path in self.permissions:
                del self.permissions[path]
    
    def list_directory(self, path: str) -> List[str]:
        """ディレクトリ内容一覧"""
        if path not in self.directories:
            return []
        
        items = []
        for file_path in self.files:
            if str(Path(file_path).parent) == path:
                items.append(Path(file_path).name)
        
        for dir_path in self.directories:
            if str(Path(dir_path).parent) == path:
                items.append(Path(dir_path).name)
        
        return sorted(items)
    
    def get_permissions(self, path: str) -> int:
        """パーミッション取得"""
        return self.permissions.get(path, 0o644)
    
    def set_permissions(self, path: str, permissions: int):
        """パーミッション設定"""
        if self.exists(path):
            self.permissions[path] = permissions
    
    def get_size(self, path: str) -> int:
        """ファイルサイズ取得"""
        return self.file_sizes.get(path, 0)


class TextTestHelper:
    """テキスト処理テスト用ヘルパー"""
    
    @staticmethod
    def create_test_text_samples() -> Dict[str, str]:
        """テスト用テキストサンプル作成"""
        return {
            "simple": "Hello, World!",
            "multiline": "Line 1\nLine 2\nLine 3",
            "unicode": "こんにちは、世界！🌍",
            "mixed": "Hello, こんにちは! 123 🎉",
            "empty": "",
            "whitespace": "   \t\n   ",
            "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
            "long_line": "A" * 1000,
            "code_sample": '''def hello_world():
    """Hello World関数"""
    print("Hello, World!")
    return "success"
''',
            "json_sample": '''{"name": "test", "value": 123}''',
            "xml_sample": '''<?xml version="1.0"?>
<root>
    <item>value</item>
</root>''',
            "csv_sample": '''name,age,city
Alice,25,Tokyo
Bob,30,Osaka''',
            "markdown_sample": '''# Title
## Subtitle
- Item 1
- Item 2
**Bold text** and *italic text*'''
        }
    
    @staticmethod
    def create_encoding_test_data() -> Dict[str, bytes]:
        """エンコーディングテスト用データ作成"""
        test_text = "Hello, こんにちは! 123"
        return {
            "utf-8": test_text.encode('utf-8'),
            "utf-16": test_text.encode('utf-16'),
            "shift_jis": test_text.encode('shift_jis'),
            "euc-jp": test_text.encode('euc-jp'),
            "ascii": "Hello, World!".encode('ascii'),
            "latin-1": "Café".encode('latin-1')
        }


class ValidationTestHelper:
    """バリデーションテスト用ヘルパー"""
    
    @staticmethod
    def create_email_test_cases() -> Dict[str, bool]:
        """メールアドレステストケース作成"""
        return {
            "valid@example.com": True,
            "user.name@domain.co.jp": True,
            "test+tag@example.org": True,
            "123@example.com": True,
            "invalid.email": False,
            "@example.com": False,
            "user@": False,
            "user@.com": False,
            "user name@example.com": False,
            "": False,
            "user@example": True,  # ローカルドメインは有効とする
        }
    
    @staticmethod
    def create_url_test_cases() -> Dict[str, bool]:
        """URLテストケース作成"""
        return {
            "https://example.com": True,
            "http://example.com": True,
            "https://www.example.com/path?query=value": True,
            "ftp://ftp.example.com": True,
            "file:///path/to/file": True,
            "invalid-url": False,
            "http://": False,
            "https://": False,
            "://example.com": False,
            "": False,
        }
    
    @staticmethod
    def create_path_test_cases() -> Dict[str, bool]:
        """パステストケース作成"""
        return {
            "/valid/unix/path": True,
            "C:\\valid\\windows\\path": True,
            "relative/path": True,
            "./current/dir": True,
            "../parent/dir": True,
            "~": True,
            "~/home/path": True,
            "": False,
            "path\x00with\x00null": False,
            "path/with/../../traversal": True,  # パストラバーサルは構文的には有効
        }
    
    @staticmethod
    def create_json_test_cases() -> Dict[str, bool]:
        """JSONテストケース作成"""
        return {
            '{"valid": "json"}': True,
            '{"number": 123}': True,
            '{"array": [1, 2, 3]}': True,
            '{"nested": {"object": true}}': True,
            '[]': True,
            '""': True,
            '123': True,
            'true': True,
            'null': True,
            '{invalid: json}': False,
            '{"unclosed": "object"': False,
            '{"trailing": "comma",}': False,
            '': False,
        }


class EncryptionTestHelper:
    """暗号化テスト用ヘルパー"""
    
    @staticmethod
    def create_test_data() -> Dict[str, Union[str, bytes]]:
        """暗号化テスト用データ作成"""
        return {
            "simple_text": "Hello, World!",
            "unicode_text": "こんにちは、世界！",
            "long_text": "A" * 1000,
            "binary_data": b'\x00\x01\x02\x03\xFF\xFE\xFD',
            "json_data": '{"key": "value", "number": 123}',
            "empty_string": "",
            "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
        }
    
    @staticmethod
    def create_password_test_cases() -> Dict[str, bool]:
        """パスワードテストケース作成"""
        return {
            "StrongP@ssw0rd": True,
            "weak": False,
            "12345678": False,
            "password": False,
            "P@ssw0rd": True,
            "VeryLongButWeakPassword": False,
            "Sh0rt!": False,  # 短すぎる
            "": False,
            "NoNumbers!": False,
            "nonumbers123": False,
            "NOLOWERCASE123!": False,
            "nouppercase123!": False,
        }


class BackupTestHelper:
    """バックアップテスト用ヘルパー"""
    
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.source_dir = temp_dir / "source"
        self.backup_dir = temp_dir / "backup"
        self.source_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_test_structure(self):
        """テスト用ディレクトリ構造作成"""
        # ファイル作成
        (self.source_dir / "file1.txt").write_text("Content 1")
        (self.source_dir / "file2.txt").write_text("Content 2")
        
        # サブディレクトリ作成
        subdir = self.source_dir / "subdir"
        subdir.mkdir()
        (subdir / "subfile.txt").write_text("Sub content")
        
        # 深いディレクトリ構造
        deep_dir = self.source_dir / "level1" / "level2"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep_file.txt").write_text("Deep content")
        
        return {
            "files": [
                self.source_dir / "file1.txt",
                self.source_dir / "file2.txt",
                subdir / "subfile.txt",
                deep_dir / "deep_file.txt"
            ],
            "directories": [
                subdir,
                self.source_dir / "level1",
                deep_dir
            ]
        }
    
    def verify_backup(self, backup_path: Path) -> bool:
        """バックアップ検証"""
        if not backup_path.exists():
            return False
        
        # 元のファイル構造と比較
        for source_file in self.source_dir.rglob("*"):
            if source_file.is_file():
                relative_path = source_file.relative_to(self.source_dir)
                backup_file = backup_path / relative_path
                
                if not backup_file.exists():
                    return False
                
                if source_file.read_text() != backup_file.read_text():
                    return False
        
        return True


# テスト用デコレータ
def requires_temp_file(func):
    """一時ファイルが必要なテスト用デコレータ"""
    def wrapper(self, *args, **kwargs):
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                return func(self, temp_path, *args, **kwargs)
            finally:
                if temp_path.exists():
                    temp_path.unlink()
    return wrapper


def requires_temp_dir(func):
    """一時ディレクトリが必要なテスト用デコレータ"""
    def wrapper(self, *args, **kwargs):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            return func(self, temp_path, *args, **kwargs)
    return wrapper


# 共通テストフィクスチャ
class UtilsTestFixtures:
    """ユーティリティテスト用フィクスチャ"""
    
    @staticmethod
    def create_mock_file_system() -> MockFileSystem:
        """モックファイルシステム作成"""
        mock_fs = MockFileSystem()
        
        # 基本的なファイル構造を作成
        mock_fs.create_directory("/")
        mock_fs.create_directory("/home")
        mock_fs.create_directory("/home/user")
        mock_fs.create_file("/home/user/test.txt", "Test content")
        mock_fs.create_file("/home/user/data.json", '{"key": "value"}')
        
        return mock_fs
    
    @staticmethod
    def create_test_config() -> Dict[str, Any]:
        """テスト用設定作成"""
        return {
            "file_utils": {
                "default_encoding": "utf-8",
                "backup_enabled": True,
                "max_file_size": 10 * 1024 * 1024,  # 10MB
                "allowed_extensions": [".txt", ".py", ".json", ".md"]
            },
            "text_utils": {
                "default_encoding": "utf-8",
                "line_ending": "auto",
                "tab_size": 4,
                "max_line_length": 120
            },
            "validation": {
                "strict_mode": False,
                "allow_unicode": True,
                "max_string_length": 1000
            },
            "encryption": {
                "algorithm": "AES-256-GCM",
                "key_derivation": "PBKDF2",
                "iterations": 100000
            },
            "backup": {
                "compression": True,
                "retention_days": 30,
                "max_backup_size": 100 * 1024 * 1024  # 100MB
            }
        }


# エクスポート
__all__ = [
    'UtilsTestBase',
    'MockFileSystem',
    'TextTestHelper',
    'ValidationTestHelper',
    'EncryptionTestHelper',
    'BackupTestHelper',
    'UtilsTestFixtures',
    'requires_temp_file',
    'requires_temp_dir'
]
