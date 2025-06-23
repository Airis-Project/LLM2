# tests/test_utils/test_file_utils.py
"""
ファイルユーティリティのテストモジュール
ファイル操作関連の機能をテスト
"""

import pytest
import tempfile
import shutil
import os
import stat
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from unittest.mock import Mock, patch, MagicMock, mock_open

# テスト対象のインポート
from utils.file_utils import (
    FileUtils,
    FileInfo,
    DirectoryScanner,
    FileWatcher,
    SafeFileWriter,
    FileBackup,
    FileCompressor,
    FileEncryption
)

# テスト用のインポート
from tests.test_core import (
    create_test_config_manager,
    create_test_logger,
    MockFileContext,
    requires_file
)
from tests.test_utils import (
    UtilsTestBase,
    MockFileSystem,
    requires_temp_file,
    requires_temp_dir,
    UtilsTestFixtures
)


class TestFileUtils(UtilsTestBase):
    """FileUtilsクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.file_utils = FileUtils(self.config_manager, self.logger)
    
    def test_file_exists(self):
        """ファイル存在確認テスト"""
        # 存在するファイル
        assert self.file_utils.exists(self.test_text_file) is True
        
        # 存在しないファイル
        non_existent = self.temp_dir / "non_existent.txt"
        assert self.file_utils.exists(non_existent) is False
        
        # ディレクトリ
        assert self.file_utils.exists(self.test_subdir) is True
    
    def test_file_is_file(self):
        """ファイル判定テスト"""
        # ファイル
        assert self.file_utils.is_file(self.test_text_file) is True
        
        # ディレクトリ
        assert self.file_utils.is_file(self.test_subdir) is False
        
        # 存在しないパス
        non_existent = self.temp_dir / "non_existent.txt"
        assert self.file_utils.is_file(non_existent) is False
    
    def test_file_is_directory(self):
        """ディレクトリ判定テスト"""
        # ディレクトリ
        assert self.file_utils.is_directory(self.test_subdir) is True
        
        # ファイル
        assert self.file_utils.is_directory(self.test_text_file) is False
        
        # 存在しないパス
        non_existent = self.temp_dir / "non_existent"
        assert self.file_utils.is_directory(non_existent) is False
    
    def test_read_text_file(self):
        """テキストファイル読み込みテスト"""
        # 正常なファイル読み込み
        content = self.file_utils.read_text(self.test_text_file)
        assert content == self.test_text_content
        
        # エンコーディング指定
        content_utf8 = self.file_utils.read_text(self.test_text_file, encoding='utf-8')
        assert content_utf8 == self.test_text_content
        
        # 存在しないファイル
        non_existent = self.temp_dir / "non_existent.txt"
        with pytest.raises(FileNotFoundError):
            self.file_utils.read_text(non_existent)
    
    def test_write_text_file(self):
        """テキストファイル書き込みテスト"""
        test_file = self.temp_dir / "write_test.txt"
        test_content = "Test write content\n日本語テスト"
        
        # ファイル書き込み
        self.file_utils.write_text(test_file, test_content)
        
        # 書き込み内容確認
        written_content = test_file.read_text(encoding='utf-8')
        assert written_content == test_content
        
        # 上書き
        new_content = "New content"
        self.file_utils.write_text(test_file, new_content)
        written_content = test_file.read_text(encoding='utf-8')
        assert written_content == new_content
    
    def test_read_binary_file(self):
        """バイナリファイル読み込みテスト"""
        # バイナリファイル読み込み
        content = self.file_utils.read_binary(self.test_binary_file)
        assert content == self.test_binary_data
        
        # 存在しないファイル
        non_existent = self.temp_dir / "non_existent.bin"
        with pytest.raises(FileNotFoundError):
            self.file_utils.read_binary(non_existent)
    
    def test_write_binary_file(self):
        """バイナリファイル書き込みテスト"""
        test_file = self.temp_dir / "write_binary_test.bin"
        test_data = b'\x00\x01\x02\x03\xFF\xFE\xFD'
        
        # バイナリ書き込み
        self.file_utils.write_binary(test_file, test_data)
        
        # 書き込み内容確認
        written_data = test_file.read_bytes()
        assert written_data == test_data
    
    def test_read_json_file(self):
        """JSONファイル読み込みテスト"""
        # JSON読み込み
        data = self.file_utils.read_json(self.test_json_file)
        assert data == self.test_json_data
        
        # 無効なJSONファイル
        invalid_json_file = self.temp_dir / "invalid.json"
        invalid_json_file.write_text("invalid json content")
        
        with pytest.raises(json.JSONDecodeError):
            self.file_utils.read_json(invalid_json_file)
    
    def test_write_json_file(self):
        """JSONファイル書き込みテスト"""
        test_file = self.temp_dir / "write_json_test.json"
        test_data = {
            "name": "Test",
            "value": 123,
            "items": ["a", "b", "c"],
            "nested": {"key": "value"}
        }
        
        # JSON書き込み
        self.file_utils.write_json(test_file, test_data)
        
        # 書き込み内容確認
        written_data = self.file_utils.read_json(test_file)
        assert written_data == test_data
    
    def test_copy_file(self):
        """ファイルコピーテスト"""
        dest_file = self.temp_dir / "copied_file.txt"
        
        # ファイルコピー
        self.file_utils.copy_file(self.test_text_file, dest_file)
        
        # コピー確認
        assert dest_file.exists()
        assert dest_file.read_text(encoding='utf-8') == self.test_text_content
        
        # 上書きコピー
        new_content = "New content for copy test"
        self.test_text_file.write_text(new_content, encoding='utf-8')
        
        self.file_utils.copy_file(self.test_text_file, dest_file, overwrite=True)
        assert dest_file.read_text(encoding='utf-8') == new_content
    
    def test_move_file(self):
        """ファイル移動テスト"""
        # 移動用のファイル作成
        source_file = self.temp_dir / "move_source.txt"
        source_content = "Content to move"
        source_file.write_text(source_content, encoding='utf-8')
        
        dest_file = self.temp_dir / "move_dest.txt"
        
        # ファイル移動
        self.file_utils.move_file(source_file, dest_file)
        
        # 移動確認
        assert not source_file.exists()
        assert dest_file.exists()
        assert dest_file.read_text(encoding='utf-8') == source_content
    
    def test_delete_file(self):
        """ファイル削除テスト"""
        # 削除用のファイル作成
        delete_file = self.temp_dir / "delete_test.txt"
        delete_file.write_text("Content to delete")
        
        assert delete_file.exists()
        
        # ファイル削除
        self.file_utils.delete_file(delete_file)
        
        # 削除確認
        assert not delete_file.exists()
        
        # 存在しないファイルの削除（エラーにならない）
        self.file_utils.delete_file(delete_file)
    
    def test_create_directory(self):
        """ディレクトリ作成テスト"""
        new_dir = self.temp_dir / "new_directory"
        
        # ディレクトリ作成
        self.file_utils.create_directory(new_dir)
        
        # 作成確認
        assert new_dir.exists()
        assert new_dir.is_dir()
        
        # 既存ディレクトリの作成（エラーにならない）
        self.file_utils.create_directory(new_dir)
        
        # 深いディレクトリ構造の作成
        deep_dir = self.temp_dir / "level1" / "level2" / "level3"
        self.file_utils.create_directory(deep_dir, parents=True)
        
        assert deep_dir.exists()
        assert deep_dir.is_dir()
    
    def test_delete_directory(self):
        """ディレクトリ削除テスト"""
        # 削除用のディレクトリ作成
        delete_dir = self.temp_dir / "delete_directory"
        delete_dir.mkdir()
        
        # ディレクトリ内にファイル作成
        (delete_dir / "file.txt").write_text("content")
        
        assert delete_dir.exists()
        
        # ディレクトリ削除
        self.file_utils.delete_directory(delete_dir)
        
        # 削除確認
        assert not delete_dir.exists()
    
    def test_list_directory(self):
        """ディレクトリ一覧テスト"""
        # ディレクトリ一覧取得
        items = self.file_utils.list_directory(self.temp_dir)
        
        # 作成したファイル・ディレクトリが含まれることを確認
        item_names = [item.name for item in items]
        assert self.test_text_file.name in item_names
        assert self.test_json_file.name in item_names
        assert self.test_subdir.name in item_names
        
        # ファイルのみ取得
        files_only = self.file_utils.list_directory(self.temp_dir, files_only=True)
        for item in files_only:
            assert item.is_file()
        
        # ディレクトリのみ取得
        dirs_only = self.file_utils.list_directory(self.temp_dir, directories_only=True)
        for item in dirs_only:
            assert item.is_dir()
    
    def test_get_file_size(self):
        """ファイルサイズ取得テスト"""
        # テキストファイルのサイズ
        size = self.file_utils.get_file_size(self.test_text_file)
        expected_size = len(self.test_text_content.encode('utf-8'))
        assert size == expected_size
        
        # バイナリファイルのサイズ
        binary_size = self.file_utils.get_file_size(self.test_binary_file)
        assert binary_size == len(self.test_binary_data)
        
        # 存在しないファイル
        non_existent = self.temp_dir / "non_existent.txt"
        assert self.file_utils.get_file_size(non_existent) == 0
    
    def test_get_file_info(self):
        """ファイル情報取得テスト"""
        file_info = self.file_utils.get_file_info(self.test_text_file)
        
        assert isinstance(file_info, FileInfo)
        assert file_info.path == self.test_text_file
        assert file_info.size == len(self.test_text_content.encode('utf-8'))
        assert file_info.is_file is True
        assert file_info.is_directory is False
        assert file_info.created_time is not None
        assert file_info.modified_time is not None
        assert file_info.permissions is not None
    
    def test_find_files(self):
        """ファイル検索テスト"""
        # パターンでファイル検索
        txt_files = self.file_utils.find_files(self.temp_dir, "*.txt")
        txt_file_names = [f.name for f in txt_files]
        assert self.test_text_file.name in txt_file_names
        
        # 再帰検索
        all_txt_files = self.file_utils.find_files(self.temp_dir, "*.txt", recursive=True)
        assert len(all_txt_files) >= len(txt_files)
        
        # 拡張子で検索
        json_files = self.file_utils.find_files_by_extension(self.temp_dir, ".json")
        json_file_names = [f.name for f in json_files]
        assert self.test_json_file.name in json_file_names
    
    def test_calculate_checksum(self):
        """チェックサム計算テスト"""
        # MD5チェックサム
        md5_hash = self.file_utils.calculate_checksum(self.test_text_file, "md5")
        assert len(md5_hash) == 32  # MD5は32文字
        
        # SHA256チェックサム
        sha256_hash = self.file_utils.calculate_checksum(self.test_text_file, "sha256")
        assert len(sha256_hash) == 64  # SHA256は64文字
        
        # 同じファイルは同じハッシュ
        md5_hash2 = self.file_utils.calculate_checksum(self.test_text_file, "md5")
        assert md5_hash == md5_hash2
    
    def test_safe_file_operations(self):
        """安全なファイル操作テスト"""
        test_file = self.temp_dir / "safe_operation_test.txt"
        test_content = "Safe operation test content"
        
        # 安全な書き込み
        success = self.file_utils.safe_write_text(test_file, test_content)
        assert success is True
        assert test_file.exists()
        assert test_file.read_text(encoding='utf-8') == test_content
        
        # 読み取り専用ファイルへの書き込み（失敗）
        test_file.chmod(stat.S_IRUSR)  # 読み取り専用
        success = self.file_utils.safe_write_text(test_file, "new content")
        assert success is False
        
        # パーミッションを戻す
        test_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
    
    def test_backup_and_restore(self):
        """バックアップと復元テスト"""
        # バックアップ作成
        backup_path = self.file_utils.create_backup(self.test_text_file)
        
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.read_text(encoding='utf-8') == self.test_text_content
        
        # 元ファイルを変更
        new_content = "Modified content"
        self.test_text_file.write_text(new_content, encoding='utf-8')
        
        # バックアップから復元
        success = self.file_utils.restore_from_backup(backup_path, self.test_text_file)
        assert success is True
        assert self.test_text_file.read_text(encoding='utf-8') == self.test_text_content
    
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        # 存在しないディレクトリのファイル操作
        non_existent_dir = self.temp_dir / "non_existent_dir"
        test_file = non_existent_dir / "test.txt"
        
        # ディレクトリが存在しない場合の書き込み
        success = self.file_utils.safe_write_text(test_file, "content")
        assert success is False
        
        # 権限のないディレクトリでの操作
        if os.name != 'nt':  # Windows以外でのみテスト
            restricted_dir = self.temp_dir / "restricted"
            restricted_dir.mkdir()
            restricted_dir.chmod(0o000)  # 権限なし
            
            try:
                restricted_file = restricted_dir / "test.txt"
                success = self.file_utils.safe_write_text(restricted_file, "content")
                assert success is False
            finally:
                # パーミッションを戻してクリーンアップ
                restricted_dir.chmod(0o755)


class TestDirectoryScanner(UtilsTestBase):
    """DirectoryScannerクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.scanner = DirectoryScanner(self.config_manager, self.logger)
    
    def test_scan_directory(self):
        """ディレクトリスキャンテスト"""
        results = self.scanner.scan(self.temp_dir)
        
        assert results is not None
        assert len(results.files) > 0
        assert len(results.directories) > 0
        
        # 作成したファイルが含まれることを確認
        file_paths = [f.path for f in results.files]
        assert self.test_text_file in file_paths
        assert self.test_json_file in file_paths
    
    def test_scan_with_filters(self):
        """フィルタ付きスキャンテスト"""
        # 拡張子フィルタ
        txt_results = self.scanner.scan(self.temp_dir, include_patterns=["*.txt"])
        txt_files = [f.path.name for f in txt_results.files]
        assert all(name.endswith('.txt') for name in txt_files)
        
        # 除外フィルタ
        no_json_results = self.scanner.scan(self.temp_dir, exclude_patterns=["*.json"])
        json_files = [f for f in no_json_results.files if f.path.name.endswith('.json')]
        assert len(json_files) == 0
    
    def test_scan_recursive(self):
        """再帰スキャンテスト"""
        # 非再帰スキャン
        non_recursive = self.scanner.scan(self.temp_dir, recursive=False)
        
        # 再帰スキャン
        recursive = self.scanner.scan(self.temp_dir, recursive=True)
        
        # 再帰スキャンの方が多くのファイルを検出
        assert len(recursive.files) >= len(non_recursive.files)
        
        # サブディレクトリのファイルが含まれることを確認
        file_paths = [f.path for f in recursive.files]
        assert self.test_subfile in file_paths


class TestFileWatcher(UtilsTestBase):
    """FileWatcherクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.watcher = FileWatcher(self.config_manager, self.logger)
        self.events = []
        
        # イベントハンドラー
        def on_file_event(event):
            self.events.append(event)
        
        self.watcher.on_file_changed = on_file_event
        self.watcher.on_file_created = on_file_event
        self.watcher.on_file_deleted = on_file_event
    
    def test_watch_file_changes(self):
        """ファイル変更監視テスト"""
        # 監視開始
        self.watcher.start_watching(self.temp_dir)
        
        try:
            # ファイル作成
            new_file = self.temp_dir / "watched_file.txt"
            new_file.write_text("Initial content")
            
            # 少し待つ
            time.sleep(0.1)
            
            # ファイル変更
            new_file.write_text("Modified content")
            
            # 少し待つ
            time.sleep(0.1)
            
            # ファイル削除
            new_file.unlink()
            
            # 少し待つ
            time.sleep(0.1)
            
            # イベントが発生したことを確認
            assert len(self.events) > 0
            
        finally:
            # 監視停止
            self.watcher.stop_watching()


class TestSafeFileWriter(UtilsTestBase):
    """SafeFileWriterクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.writer = SafeFileWriter(self.config_manager, self.logger)
    
    def test_atomic_write(self):
        """アトミック書き込みテスト"""
        test_file = self.temp_dir / "atomic_write_test.txt"
        test_content = "Atomic write test content"
        
        # アトミック書き込み
        success = self.writer.write_atomic(test_file, test_content)
        
        assert success is True
        assert test_file.exists()
        assert test_file.read_text(encoding='utf-8') == test_content
    
    def test_write_with_backup(self):
        """バックアップ付き書き込みテスト"""
        # 既存ファイルを使用
        original_content = self.test_text_file.read_text(encoding='utf-8')
        new_content = "New content with backup"
        
        # バックアップ付き書き込み
        backup_path = self.writer.write_with_backup(self.test_text_file, new_content)
        
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.read_text(encoding='utf-8') == original_content
        assert self.test_text_file.read_text(encoding='utf-8') == new_content
    
    def test_transactional_write(self):
        """トランザクション書き込みテスト"""
        files_to_write = [
            (self.temp_dir / "trans1.txt", "Content 1"),
            (self.temp_dir / "trans2.txt", "Content 2"),
            (self.temp_dir / "trans3.txt", "Content 3")
        ]
        
        # トランザクション書き込み
        success = self.writer.write_transactional(files_to_write)
        
        assert success is True
        for file_path, content in files_to_write:
            assert file_path.exists()
            assert file_path.read_text(encoding='utf-8') == content


@pytest.mark.skipif(os.name == 'nt', reason="Unix permissions test")
class TestFilePermissions(UtilsTestBase):
    """ファイルパーミッションテスト（Unix系のみ）"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.file_utils = FileUtils(self.config_manager, self.logger)
    
    def test_file_permissions(self):
        """ファイルパーミッションテスト"""
        test_file = self.temp_dir / "permission_test.txt"
        test_file.write_text("Permission test")
        
        # パーミッション設定
        self.file_utils.set_permissions(test_file, 0o644)
        
        # パーミッション確認
        permissions = self.file_utils.get_permissions(test_file)
        assert permissions & 0o777 == 0o644
        
        # 読み取り専用に変更
        self.file_utils.set_permissions(test_file, 0o444)
        permissions = self.file_utils.get_permissions(test_file)
        assert permissions & 0o777 == 0o444


class TestFileUtilsIntegration(UtilsTestBase):
    """FileUtils統合テスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.file_utils = FileUtils(self.config_manager, self.logger)
    
    def test_project_backup_scenario(self):
        """プロジェクトバックアップシナリオテスト"""
        # プロジェクト構造作成
        project_dir = self.temp_dir / "test_project"
        project_dir.mkdir()
        
        # ファイル作成
        (project_dir / "main.py").write_text("print('Hello, World!')")
        (project_dir / "config.json").write_text('{"debug": true}')
        
        src_dir = project_dir / "src"
        src_dir.mkdir()
        (src_dir / "utils.py").write_text("def helper(): pass")
        
        # バックアップ作成
        backup_dir = self.temp_dir / "backup"
        backup_dir.mkdir()
        
        # プロジェクト全体をバックアップ
        success = self.file_utils.backup_directory(project_dir, backup_dir)
        assert success is True
        
        # バックアップ内容確認
        backup_project = backup_dir / "test_project"
        assert backup_project.exists()
        assert (backup_project / "main.py").exists()
        assert (backup_project / "config.json").exists()
        assert (backup_project / "src" / "utils.py").exists()
    
    def test_large_file_handling(self):
        """大きなファイル処理テスト"""
        # 大きなファイルの読み書き
        large_content = "Large file content line.\n" * 100000
        large_file = self.temp_dir / "large_file.txt"
        
        # 書き込み
        start_time = time.time()
        self.file_utils.write_text(large_file, large_content)
        write_time = time.time() - start_time
        
        # 読み込み
        start_time = time.time()
        read_content = self.file_utils.read_text(large_file)
        read_time = time.time() - start_time
        
        assert read_content == large_content
        assert write_time < 5.0  # 5秒以内
        assert read_time < 5.0   # 5秒以内
        
        # チャンク読み込み
        chunks = list(self.file_utils.read_text_chunks(large_file, chunk_size=1024))
        assert len(chunks) > 1
        assert ''.join(chunks) == large_content
