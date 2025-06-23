# tests/test_core/test_config_manager.py
"""
ConfigManagerのテストモジュール
設定管理機能の単体テストと統合テストを実装
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from typing import Dict, Any

# テスト対象のインポート
from core.config_manager import ConfigManager
from core.logger import Logger

# テスト用のインポート
from tests.test_core import (
    get_mock_config_data,
    assert_config_valid,
    MockConfigContext,
    requires_config
)


class TestConfigManager:
    """ConfigManagerのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="config_test_"))
        self.config_file = self.temp_dir / "test_config.json"
        self.backup_dir = self.temp_dir / "backups"
        self.test_config_data = get_mock_config_data()
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_init_with_new_config_file(self):
        """新しい設定ファイルでの初期化テスト"""
        # 存在しない設定ファイルで初期化
        config_manager = ConfigManager(self.config_file)
        
        # 初期化の確認
        assert config_manager.config_file == self.config_file
        assert isinstance(config_manager._config, dict)
        assert config_manager._logger is not None
        
        # デフォルト設定の確認
        assert 'application' in config_manager._config
        assert 'logging' in config_manager._config
        assert 'database' in config_manager._config
    
    def test_init_with_existing_config_file(self):
        """既存の設定ファイルでの初期化テスト"""
        # 設定ファイルを事前に作成
        self.config_file.write_text(
            json.dumps(self.test_config_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        # 既存ファイルで初期化
        config_manager = ConfigManager(self.config_file)
        
        # 設定の読み込み確認
        assert config_manager.get('application.name') == self.test_config_data['application']['name']
        assert config_manager.get('database.type') == self.test_config_data['database']['type']
    
    def test_init_with_invalid_config_file(self):
        """不正な設定ファイルでの初期化テスト"""
        # 不正なJSONファイルを作成
        self.config_file.write_text("invalid json content", encoding='utf-8')
        
        # 初期化時にデフォルト設定が使用されることを確認
        config_manager = ConfigManager(self.config_file)
        
        # デフォルト設定が適用されていることを確認
        assert 'application' in config_manager._config
        assert config_manager.get('application.name') is not None
    
    def test_get_existing_key(self):
        """既存キーの取得テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 単純なキーの取得
        assert config_manager.get('application.name') == self.test_config_data['application']['name']
        
        # ネストしたキーの取得
        assert config_manager.get('database.type') == self.test_config_data['database']['type']
        
        # 辞書全体の取得
        app_config = config_manager.get('application')
        assert isinstance(app_config, dict)
        assert app_config['name'] == self.test_config_data['application']['name']
    
    def test_get_nonexistent_key(self):
        """存在しないキーの取得テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 存在しないキーはNoneを返す
        assert config_manager.get('nonexistent.key') is None
        
        # デフォルト値の指定
        default_value = "default"
        assert config_manager.get('nonexistent.key', default_value) == default_value
    
    def test_set_new_key(self):
        """新しいキーの設定テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 新しいキーを設定
        new_value = "new_value"
        config_manager.set('new.key', new_value)
        
        # 設定値の確認
        assert config_manager.get('new.key') == new_value
        
        # ネストした新しいキーの設定
        config_manager.set('nested.deep.key', 'deep_value')
        assert config_manager.get('nested.deep.key') == 'deep_value'
    
    def test_set_existing_key(self):
        """既存キーの更新テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 既存キーの更新
        original_name = config_manager.get('application.name')
        new_name = "Updated Test App"
        config_manager.set('application.name', new_name)
        
        # 更新の確認
        assert config_manager.get('application.name') == new_name
        assert config_manager.get('application.name') != original_name
    
    def test_remove_existing_key(self):
        """既存キーの削除テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # キーが存在することを確認
        assert config_manager.get('application.debug') is not None
        
        # キーを削除
        result = config_manager.remove('application.debug')
        assert result is True
        
        # 削除の確認
        assert config_manager.get('application.debug') is None
    
    def test_remove_nonexistent_key(self):
        """存在しないキーの削除テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 存在しないキーの削除
        result = config_manager.remove('nonexistent.key')
        assert result is False
    
    def test_save_config(self):
        """設定の保存テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 設定を保存
        result = config_manager.save()
        assert result is True
        
        # ファイルが作成されていることを確認
        assert self.config_file.exists()
        
        # 保存された内容の確認
        with open(self.config_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data['application']['name'] == self.test_config_data['application']['name']
    
    def test_save_config_with_backup(self):
        """バックアップ付き設定保存テスト"""
        # 既存の設定ファイルを作成
        self.config_file.write_text(
            json.dumps(self.test_config_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        config_manager = ConfigManager(self.config_file, backup_enabled=True)
        
        # 設定を変更
        config_manager.set('application.name', 'Modified App')
        
        # バックアップ付きで保存
        result = config_manager.save()
        assert result is True
        
        # バックアップファイルが作成されていることを確認
        backup_files = list(self.config_file.parent.glob(f"{self.config_file.stem}_backup_*.json"))
        assert len(backup_files) > 0
    
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_save_config_permission_error(self, mock_open):
        """設定保存時の権限エラーテスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 権限エラーで保存失敗
        result = config_manager.save()
        assert result is False
    
    def test_load_config(self):
        """設定の読み込みテスト"""
        # 設定ファイルを作成
        self.config_file.write_text(
            json.dumps(self.test_config_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        config_manager = ConfigManager(self.config_file)
        
        # 設定を変更してから再読み込み
        config_manager.set('application.name', 'Changed')
        result = config_manager.load()
        
        assert result is True
        # 元の設定に戻っていることを確認
        assert config_manager.get('application.name') == self.test_config_data['application']['name']
    
    def test_load_nonexistent_config(self):
        """存在しない設定ファイルの読み込みテスト"""
        config_manager = ConfigManager(self.config_file)
        
        # 存在しないファイルの読み込み
        result = config_manager.load()
        assert result is False
    
    def test_reset_to_defaults(self):
        """デフォルト設定へのリセットテスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 設定を変更
        config_manager.set('application.name', 'Modified')
        modified_name = config_manager.get('application.name')
        
        # デフォルトにリセット
        config_manager.reset_to_defaults()
        
        # デフォルト設定に戻っていることを確認
        reset_name = config_manager.get('application.name')
        assert reset_name != modified_name
        assert 'application' in config_manager._config
    
    def test_get_all_config(self):
        """全設定の取得テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 全設定を取得
        all_config = config_manager.get_all()
        
        assert isinstance(all_config, dict)
        assert 'application' in all_config
        assert 'database' in all_config
        assert all_config['application']['name'] == self.test_config_data['application']['name']
    
    def test_update_config(self):
        """設定の一括更新テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 更新データ
        update_data = {
            'application': {
                'name': 'Updated App',
                'version': '2.0.0'
            },
            'new_section': {
                'key': 'value'
            }
        }
        
        # 設定を更新
        config_manager.update(update_data)
        
        # 更新の確認
        assert config_manager.get('application.name') == 'Updated App'
        assert config_manager.get('application.version') == '2.0.0'
        assert config_manager.get('new_section.key') == 'value'
        
        # 既存の他の設定が保持されていることを確認
        assert config_manager.get('database.type') == self.test_config_data['database']['type']
    
    def test_validate_config(self):
        """設定の検証テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 有効な設定の検証
        is_valid, errors = config_manager.validate()
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_invalid_config(self):
        """不正な設定の検証テスト"""
        config_manager = ConfigManager(self.config_file)
        
        # 不正な設定を作成
        invalid_config = {
            'application': {
                # nameが欠けている
                'version': '1.0.0'
            }
        }
        config_manager._config = invalid_config
        
        # 検証で失敗することを確認
        is_valid, errors = config_manager.validate()
        assert is_valid is False
        assert len(errors) > 0
    
    def test_get_section(self):
        """セクション取得テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # アプリケーションセクションを取得
        app_section = config_manager.get_section('application')
        assert isinstance(app_section, dict)
        assert app_section['name'] == self.test_config_data['application']['name']
        
        # 存在しないセクション
        nonexistent = config_manager.get_section('nonexistent')
        assert nonexistent == {}
    
    def test_has_key(self):
        """キー存在確認テスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # 存在するキー
        assert config_manager.has('application.name') is True
        assert config_manager.has('database.type') is True
        
        # 存在しないキー
        assert config_manager.has('nonexistent.key') is False
    
    def test_create_backup(self):
        """バックアップ作成テスト"""
        # 設定ファイルを作成
        self.config_file.write_text(
            json.dumps(self.test_config_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        config_manager = ConfigManager(self.config_file, backup_enabled=True)
        
        # バックアップを作成
        backup_path = config_manager.create_backup()
        
        assert backup_path is not None
        assert backup_path.exists()
        
        # バックアップ内容の確認
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        assert backup_data['application']['name'] == self.test_config_data['application']['name']
    
    def test_restore_from_backup(self):
        """バックアップからの復元テスト"""
        config_manager = ConfigManager(self.config_file, backup_enabled=True)
        config_manager._config = self.test_config_data.copy()
        
        # バックアップを作成
        backup_path = config_manager.create_backup()
        
        # 設定を変更
        config_manager.set('application.name', 'Modified')
        
        # バックアップから復元
        result = config_manager.restore_from_backup(backup_path)
        assert result is True
        
        # 復元の確認
        assert config_manager.get('application.name') == self.test_config_data['application']['name']
    
    def test_auto_save(self):
        """自動保存テスト"""
        config_manager = ConfigManager(self.config_file, auto_save=True)
        config_manager._config = self.test_config_data.copy()
        
        # 設定を変更（自動保存が有効）
        config_manager.set('application.name', 'Auto Saved')
        
        # ファイルが自動的に保存されていることを確認
        assert self.config_file.exists()
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data['application']['name'] == 'Auto Saved'
    
    def test_config_change_event(self):
        """設定変更イベントテスト"""
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        # イベントハンドラーをモック
        event_handler = Mock()
        config_manager.on_config_changed = event_handler
        
        # 設定を変更
        config_manager.set('application.name', 'Event Test')
        
        # イベントが発火されたことを確認
        event_handler.assert_called_once()
    
    @requires_config
    def test_with_config_context(self):
        """設定コンテキストテスト"""
        with MockConfigContext(self.test_config_data) as config_data:
            config_manager = ConfigManager(self.config_file)
            config_manager._config = config_data
            
            # コンテキスト内での設定確認
            assert config_manager.get('application.name') == config_data['application']['name']
    
    def test_thread_safety(self):
        """スレッドセーフティテスト"""
        import threading
        import time
        
        config_manager = ConfigManager(self.config_file)
        config_manager._config = self.test_config_data.copy()
        
        results = []
        
        def worker(worker_id):
            for i in range(10):
                key = f'thread_{worker_id}.value_{i}'
                value = f'worker_{worker_id}_value_{i}'
                config_manager.set(key, value)
                retrieved = config_manager.get(key)
                results.append(retrieved == value)
                time.sleep(0.001)
        
        # 複数スレッドで同時実行
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 全ての操作が成功していることを確認
        assert all(results)
    
    def test_memory_usage(self):
        """メモリ使用量テスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 大量の設定データを作成
        config_manager = ConfigManager(self.config_file)
        
        for i in range(1000):
            config_manager.set(f'test.key_{i}', f'value_{i}' * 100)
        
        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory
        
        # メモリ使用量が合理的な範囲内であることを確認（10MB以下）
        assert memory_increase < 10 * 1024 * 1024
