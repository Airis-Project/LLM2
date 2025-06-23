# tests/test_core/test_file_manager.py
"""
FileManagerのテストモジュール
ファイル管理機能の単体テストと統合テストを実装
"""

import pytest
import tempfile
import shutil
import os
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from typing import Dict, Any, List, Optional

# テスト対象のインポート
from core.file_manager import FileManager
from core.config_manager import ConfigManager
from core.logger import Logger

# テスト用のインポート
from tests.test_core import (
    get_mock_file_content,
    get_mock_file_structure,
    assert_file_structure_valid,
    MockFileContext,
    requires_file,
    create_test_config_manager,
    create_test_logger
)


class TestFileManager:
    """FileManagerのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="file_test_"))
        self.test_files_dir = self.temp_dir / "test_files"
        self.test_files_dir.mkdir(exist_ok=True)
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_file_manager")
        
        # テスト用のファイルデータ
        self.test_file_data = get_mock_file_structure()
        
        # FileManagerのインスタンスを作成
        self.file_manager = FileManager(self.config_manager, self.logger)
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_test_file(self, filename: str, content: str = None) -> Path:
        """テスト用のファイルを作成"""
        file_path = self.test_files_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if content is None:
            content = get_mock_file_content('python')
        
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    def _create_test_directory_structure(self) -> Path:
        """テスト用のディレクトリ構造を作成"""
        base_dir = self.test_files_dir / "test_project"
        base_dir.mkdir(exist_ok=True)
        
        # ファイル構造を作成
        for file_info in self.test_file_data['files']:
            file_path = base_dir / file_info['path']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_info['content'], encoding='utf-8')
        
        # ディレクトリ構造を作成
        for dir_info in self.test_file_data['directories']:
            dir_path = base_dir / dir_info['path']
            dir_path.mkdir(parents=True, exist_ok=True)
        
        return base_dir
    
    def test_init(self):
        """FileManagerの初期化テスト"""
        # 初期化の確認
        assert self.file_manager.config_manager is not None
        assert self.file_manager.logger is not None
        assert isinstance(self.file_manager._file_cache, dict)
        assert isinstance(self.file_manager._watched_files, set)
        assert isinstance(self.file_manager._file_locks, dict)
    
    def test_read_file(self):
        """ファイル読み込みテスト"""
        test_content = "Hello, World!\nThis is a test file."
        file_path = self._create_test_file("test_read.txt", test_content)
        
        # ファイルを読み込み
        content = self.file_manager.read_file(str(file_path))
        
        assert content == test_content
    
    def test_read_file_with_encoding(self):
        """エンコーディング指定でのファイル読み込みテスト"""
        test_content = "こんにちは、世界！\nこれはテストファイルです。"
        file_path = self._create_test_file("test_read_utf8.txt", test_content)
        
        # UTF-8エンコーディングで読み込み
        content = self.file_manager.read_file(str(file_path), encoding='utf-8')
        
        assert content == test_content
    
    def test_read_nonexistent_file(self):
        """存在しないファイルの読み込みテスト"""
        nonexistent_path = self.test_files_dir / "nonexistent.txt"
        
        # 存在しないファイルを読み込もうとする
        content = self.file_manager.read_file(str(nonexistent_path))
        
        assert content is None
    
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_read_file_permission_error(self, mock_open):
        """ファイル読み込み時の権限エラーテスト"""
        file_path = self._create_test_file("test_permission.txt")
        
        # 権限エラーで読み込み失敗
        content = self.file_manager.read_file(str(file_path))
        
        assert content is None
    
    def test_write_file(self):
        """ファイル書き込みテスト"""
        test_content = "This is new content for the file."
        file_path = self.test_files_dir / "test_write.txt"
        
        # ファイルに書き込み
        result = self.file_manager.write_file(str(file_path), test_content)
        
        assert result is True
        assert file_path.exists()
        
        # 書き込まれた内容を確認
        written_content = file_path.read_text(encoding='utf-8')
        assert written_content == test_content
    
    def test_write_file_create_directory(self):
        """ディレクトリ作成を伴うファイル書き込みテスト"""
        test_content = "Content in nested directory."
        file_path = self.test_files_dir / "nested" / "deep" / "test.txt"
        
        # ネストしたディレクトリにファイルを書き込み
        result = self.file_manager.write_file(str(file_path), test_content)
        
        assert result is True
        assert file_path.exists()
        assert file_path.parent.exists()
        
        # 内容を確認
        written_content = file_path.read_text(encoding='utf-8')
        assert written_content == test_content
    
    def test_write_file_backup(self):
        """バックアップ付きファイル書き込みテスト"""
        original_content = "Original content"
        new_content = "New content"
        file_path = self._create_test_file("test_backup.txt", original_content)
        
        # バックアップ付きで書き込み
        result = self.file_manager.write_file(
            str(file_path), 
            new_content, 
            create_backup=True
        )
        
        assert result is True
        
        # バックアップファイルが作成されていることを確認
        backup_files = list(file_path.parent.glob(f"{file_path.stem}_backup_*.txt"))
        assert len(backup_files) > 0
        
        # バックアップファイルの内容確認
        backup_content = backup_files[0].read_text(encoding='utf-8')
        assert backup_content == original_content
        
        # 元ファイルの内容確認
        current_content = file_path.read_text(encoding='utf-8')
        assert current_content == new_content
    
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_write_file_permission_error(self, mock_open):
        """ファイル書き込み時の権限エラーテスト"""
        file_path = self.test_files_dir / "test_permission.txt"
        test_content = "Test content"
        
        # 権限エラーで書き込み失敗
        result = self.file_manager.write_file(str(file_path), test_content)
        
        assert result is False
    
    def test_copy_file(self):
        """ファイルコピーテスト"""
        test_content = "Content to be copied"
        source_path = self._create_test_file("source.txt", test_content)
        dest_path = self.test_files_dir / "destination.txt"
        
        # ファイルをコピー
        result = self.file_manager.copy_file(str(source_path), str(dest_path))
        
        assert result is True
        assert dest_path.exists()
        
        # コピーされた内容を確認
        copied_content = dest_path.read_text(encoding='utf-8')
        assert copied_content == test_content
    
    def test_copy_file_to_directory(self):
        """ディレクトリへのファイルコピーテスト"""
        test_content = "Content to be copied to directory"
        source_path = self._create_test_file("source_dir.txt", test_content)
        dest_dir = self.test_files_dir / "destination_dir"
        dest_dir.mkdir()
        
        # ディレクトリにファイルをコピー
        result = self.file_manager.copy_file(str(source_path), str(dest_dir))
        
        assert result is True
        
        # コピーされたファイルを確認
        copied_file = dest_dir / source_path.name
        assert copied_file.exists()
        
        copied_content = copied_file.read_text(encoding='utf-8')
        assert copied_content == test_content
    
    def test_move_file(self):
        """ファイル移動テスト"""
        test_content = "Content to be moved"
        source_path = self._create_test_file("move_source.txt", test_content)
        dest_path = self.test_files_dir / "move_destination.txt"
        
        # ファイルを移動
        result = self.file_manager.move_file(str(source_path), str(dest_path))
        
        assert result is True
        assert not source_path.exists()
        assert dest_path.exists()
        
        # 移動された内容を確認
        moved_content = dest_path.read_text(encoding='utf-8')
        assert moved_content == test_content
    
    def test_delete_file(self):
        """ファイル削除テスト"""
        file_path = self._create_test_file("delete_test.txt")
        
        # ファイルが存在することを確認
        assert file_path.exists()
        
        # ファイルを削除
        result = self.file_manager.delete_file(str(file_path))
        
        assert result is True
        assert not file_path.exists()
    
    def test_delete_nonexistent_file(self):
        """存在しないファイルの削除テスト"""
        nonexistent_path = self.test_files_dir / "nonexistent_delete.txt"
        
        # 存在しないファイルを削除しようとする
        result = self.file_manager.delete_file(str(nonexistent_path))
        
        assert result is False
    
    def test_file_exists(self):
        """ファイル存在確認テスト"""
        existing_file = self._create_test_file("exists_test.txt")
        nonexistent_file = self.test_files_dir / "nonexistent.txt"
        
        # 存在するファイル
        assert self.file_manager.file_exists(str(existing_file)) is True
        
        # 存在しないファイル
        assert self.file_manager.file_exists(str(nonexistent_file)) is False
    
    def test_get_file_info(self):
        """ファイル情報取得テスト"""
        test_content = "Test content for file info"
        file_path = self._create_test_file("info_test.txt", test_content)
        
        # ファイル情報を取得
        file_info = self.file_manager.get_file_info(str(file_path))
        
        assert file_info is not None
        assert 'name' in file_info
        assert 'path' in file_info
        assert 'size' in file_info
        assert 'modified_time' in file_info
        assert 'created_time' in file_info
        assert 'extension' in file_info
        assert 'mime_type' in file_info
        
        # 値の確認
        assert file_info['name'] == file_path.name
        assert file_info['path'] == str(file_path)
        assert file_info['size'] == len(test_content.encode('utf-8'))
        assert file_info['extension'] == '.txt'
    
    def test_get_file_info_nonexistent(self):
        """存在しないファイルの情報取得テスト"""
        nonexistent_path = self.test_files_dir / "nonexistent_info.txt"
        
        # 存在しないファイルの情報取得
        file_info = self.file_manager.get_file_info(str(nonexistent_path))
        
        assert file_info is None
    
    def test_list_files(self):
        """ファイル一覧取得テスト"""
        # テスト用のファイルを複数作成
        test_files = []
        for i in range(3):
            file_path = self._create_test_file(f"list_test_{i}.txt")
            test_files.append(file_path)
        
        # ファイル一覧を取得
        file_list = self.file_manager.list_files(str(self.test_files_dir))
        
        assert isinstance(file_list, list)
        assert len(file_list) >= 3
        
        # 作成したファイルが含まれていることを確認
        file_names = [f['name'] for f in file_list]
        for test_file in test_files:
            assert test_file.name in file_names
    
    def test_list_files_with_pattern(self):
        """パターン指定でのファイル一覧取得テスト"""
        # 異なる拡張子のファイルを作成
        self._create_test_file("pattern_test.txt")
        self._create_test_file("pattern_test.py")
        self._create_test_file("pattern_test.md")
        
        # .txtファイルのみを取得
        txt_files = self.file_manager.list_files(
            str(self.test_files_dir), 
            pattern="*.txt"
        )
        
        assert isinstance(txt_files, list)
        assert len(txt_files) >= 1
        
        # 全てのファイルが.txtファイルであることを確認
        for file_info in txt_files:
            assert file_info['name'].endswith('.txt')
    
    def test_list_files_recursive(self):
        """再帰的ファイル一覧取得テスト"""
        # ネストしたディレクトリ構造を作成
        nested_dir = self.test_files_dir / "nested"
        nested_dir.mkdir()
        
        self._create_test_file("top_level.txt")
        nested_file = nested_dir / "nested_file.txt"
        nested_file.write_text("nested content", encoding='utf-8')
        
        # 再帰的にファイル一覧を取得
        all_files = self.file_manager.list_files(
            str(self.test_files_dir), 
            recursive=True
        )
        
        assert isinstance(all_files, list)
        assert len(all_files) >= 2
        
        # ネストしたファイルが含まれていることを確認
        file_paths = [f['path'] for f in all_files]
        assert str(nested_file) in file_paths
    
    def test_search_in_files(self):
        """ファイル内検索テスト"""
        # 検索対象のファイルを作成
        search_content = "This is a search target text."
        self._create_test_file("search_test_1.txt", f"Some content\n{search_content}\nMore content")
        self._create_test_file("search_test_2.txt", f"Different content\n{search_content}\nEnd")
        self._create_test_file("search_test_3.txt", "No match here")
        
        # ファイル内検索を実行
        search_results = self.file_manager.search_in_files(
            str(self.test_files_dir),
            "search target"
        )
        
        assert isinstance(search_results, list)
        assert len(search_results) >= 2
        
        # 検索結果の構造確認
        for result in search_results:
            assert 'file' in result
            assert 'line_number' in result
            assert 'line_content' in result
            assert 'match_start' in result
            assert 'match_end' in result
            assert 'search target' in result['line_content']
    
    def test_search_in_files_regex(self):
        """正規表現によるファイル内検索テスト"""
        # 正規表現検索対象のファイルを作成
        self._create_test_file("regex_test.py", "def test_function():\n    pass\n\ndef another_function():\n    return True")
        
        # 正規表現でファンクション定義を検索
        search_results = self.file_manager.search_in_files(
            str(self.test_files_dir),
            r"def\s+\w+\(",
            use_regex=True
        )
        
        assert isinstance(search_results, list)
        assert len(search_results) >= 2
    
    def test_replace_in_files(self):
        """ファイル内置換テスト"""
        original_content = "Hello World\nHello Python\nGoodbye World"
        file_path = self._create_test_file("replace_test.txt", original_content)
        
        # ファイル内の文字列を置換
        result = self.file_manager.replace_in_files(
            str(self.test_files_dir),
            "Hello",
            "Hi",
            file_patterns=["*.txt"]
        )
        
        assert result > 0  # 置換された数
        
        # 置換後の内容を確認
        replaced_content = file_path.read_text(encoding='utf-8')
        assert "Hi World" in replaced_content
        assert "Hi Python" in replaced_content
        assert "Hello" not in replaced_content
    
    def test_get_file_hash(self):
        """ファイルハッシュ取得テスト"""
        test_content = "Content for hash calculation"
        file_path = self._create_test_file("hash_test.txt", test_content)
        
        # ファイルハッシュを取得
        file_hash = self.file_manager.get_file_hash(str(file_path))
        
        assert file_hash is not None
        assert isinstance(file_hash, str)
        assert len(file_hash) == 64  # SHA256ハッシュの長さ
        
        # 期待されるハッシュ値と比較
        expected_hash = hashlib.sha256(test_content.encode('utf-8')).hexdigest()
        assert file_hash == expected_hash
    
    def test_get_file_hash_different_algorithm(self):
        """異なるアルゴリズムでのファイルハッシュ取得テスト"""
        test_content = "Content for MD5 hash"
        file_path = self._create_test_file("md5_test.txt", test_content)
        
        # MD5ハッシュを取得
        file_hash = self.file_manager.get_file_hash(str(file_path), algorithm='md5')
        
        assert file_hash is not None
        assert isinstance(file_hash, str)
        assert len(file_hash) == 32  # MD5ハッシュの長さ
        
        # 期待されるハッシュ値と比較
        expected_hash = hashlib.md5(test_content.encode('utf-8')).hexdigest()
        assert file_hash == expected_hash
    
    def test_watch_file(self):
        """ファイル監視テスト"""
        file_path = self._create_test_file("watch_test.txt", "Initial content")
        
        # ファイル監視を開始
        result = self.file_manager.watch_file(str(file_path))
        
        assert result is True
        assert str(file_path) in self.file_manager._watched_files
    
    def test_unwatch_file(self):
        """ファイル監視停止テスト"""
        file_path = self._create_test_file("unwatch_test.txt")
        
        # ファイル監視を開始してから停止
        self.file_manager.watch_file(str(file_path))
        result = self.file_manager.unwatch_file(str(file_path))
        
        assert result is True
        assert str(file_path) not in self.file_manager._watched_files
    
    def test_create_directory(self):
        """ディレクトリ作成テスト"""
        dir_path = self.test_files_dir / "new_directory"
        
        # ディレクトリを作成
        result = self.file_manager.create_directory(str(dir_path))
        
        assert result is True
        assert dir_path.exists()
        assert dir_path.is_dir()
    
    def test_create_nested_directory(self):
        """ネストしたディレクトリ作成テスト"""
        nested_path = self.test_files_dir / "level1" / "level2" / "level3"
        
        # ネストしたディレクトリを作成
        result = self.file_manager.create_directory(str(nested_path))
        
        assert result is True
        assert nested_path.exists()
        assert nested_path.is_dir()
    
    def test_delete_directory(self):
        """ディレクトリ削除テスト"""
        dir_path = self.test_files_dir / "delete_dir"
        dir_path.mkdir()
        
        # ディレクトリを削除
        result = self.file_manager.delete_directory(str(dir_path))
        
        assert result is True
        assert not dir_path.exists()
    
    def test_delete_directory_with_contents(self):
        """内容があるディレクトリの削除テスト"""
        dir_path = self.test_files_dir / "delete_dir_with_contents"
        dir_path.mkdir()
        
        # ディレクトリ内にファイルを作成
        test_file = dir_path / "test.txt"
        test_file.write_text("test content", encoding='utf-8')
        
        # ディレクトリを削除
        result = self.file_manager.delete_directory(str(dir_path))
        
        assert result is True
        assert not dir_path.exists()
    
    def test_file_locking(self):
        """ファイルロックテスト"""
        file_path = self._create_test_file("lock_test.txt")
        
        # ファイルをロック
        result = self.file_manager.lock_file(str(file_path))
        assert result is True
        assert str(file_path) in self.file_manager._file_locks
        
        # ファイルのロック解除
        result = self.file_manager.unlock_file(str(file_path))
        assert result is True
        assert str(file_path) not in self.file_manager._file_locks
    
    def test_file_cache(self):
        """ファイルキャッシュテスト"""
        test_content = "Content for caching test"
        file_path = self._create_test_file("cache_test.txt", test_content)
        
        # ファイルを読み込み（キャッシュに保存される）
        content1 = self.file_manager.read_file(str(file_path), use_cache=True)
        assert content1 == test_content
        
        # キャッシュから読み込み
        content2 = self.file_manager.read_file(str(file_path), use_cache=True)
        assert content2 == test_content
        assert content1 == content2
    
    def test_clear_cache(self):
        """キャッシュクリアテスト"""
        file_path = self._create_test_file("clear_cache_test.txt")
        
        # ファイルをキャッシュに読み込み
        self.file_manager.read_file(str(file_path), use_cache=True)
        assert len(self.file_manager._file_cache) > 0
        
        # キャッシュをクリア
        self.file_manager.clear_cache()
        assert len(self.file_manager._file_cache) == 0
    
    @requires_file
    def test_with_file_context(self):
        """ファイルコンテキストテスト"""
        test_content = "Context test content"
        
        with MockFileContext(self.test_files_dir, "context_test.txt", test_content) as file_path:
            # ファイルが存在することを確認
            assert self.file_manager.file_exists(str(file_path))
            
            # ファイル内容を確認
            content = self.file_manager.read_file(str(file_path))
            assert content == test_content
    
    def test_concurrent_file_operations(self):
        """並行ファイル操作テスト"""
        import threading
        import time
        
        results = []
        
        def worker(worker_id):
            file_path = self.test_files_dir / f"concurrent_{worker_id}.txt"
            content = f"Worker {worker_id} content"
            
            # ファイルを書き込み
            result = self.file_manager.write_file(str(file_path), content)
            results.append(('write', worker_id, result))
            
            time.sleep(0.1)
            
            # ファイルを読み込み
            read_content = self.file_manager.read_file(str(file_path))
            results.append(('read', worker_id, read_content == content))
        
        # 複数スレッドで同時実行
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 結果の確認
        assert len(results) == 6  # 3 workers × 2 operations
        
        # 全ての操作が成功していることを確認
        for operation, worker_id, success in results:
            assert success is True
    
    def test_large_file_handling(self):
        """大きなファイルの処理テスト"""
        # 大きなコンテンツを生成（1MB程度）
        large_content = "Large file content line.\n" * 50000
        file_path = self.test_files_dir / "large_file.txt"
        
        # 大きなファイルを書き込み
        result = self.file_manager.write_file(str(file_path), large_content)
        assert result is True
        
        # 大きなファイルを読み込み
        read_content = self.file_manager.read_file(str(file_path))
        assert read_content == large_content
        
        # ファイル情報を取得
        file_info = self.file_manager.get_file_info(str(file_path))
        assert file_info['size'] > 1000000  # 1MB以上
