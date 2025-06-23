# tests/test_core/test_project_manager.py
"""
ProjectManagerのテストモジュール
プロジェクト管理機能の単体テストと統合テストを実装
"""

import pytest
import json
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# テスト対象のインポート
from core.project_manager import ProjectManager
from core.config_manager import ConfigManager
from core.logger import Logger

# テスト用のインポート
from tests.test_core import (
    get_mock_project_structure,
    get_mock_file_content,
    assert_project_structure_valid,
    MockProjectContext,
    requires_project,
    create_test_config_manager,
    create_test_logger
)


class TestProjectManager:
    """ProjectManagerのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="project_test_"))
        self.projects_dir = self.temp_dir / "projects"
        self.projects_dir.mkdir(exist_ok=True)
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_project_manager")
        
        # テスト用のプロジェクトデータ
        self.test_project_data = get_mock_project_structure()
        self.test_project_path = self.projects_dir / self.test_project_data['name']
        
        # ProjectManagerのインスタンスを作成
        self.project_manager = ProjectManager(self.config_manager, self.logger)
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_test_project(self, project_name: str = None) -> Path:
        """テスト用のプロジェクトを作成"""
        if project_name is None:
            project_name = self.test_project_data['name']
        
        project_path = self.projects_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        
        # プロジェクトファイルを作成
        for file_info in self.test_project_data['files']:
            file_path = project_path / file_info['relative_path']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイル内容を作成
            content = get_mock_file_content('python')
            file_path.write_text(content, encoding='utf-8')
        
        # ディレクトリを作成
        for dir_info in self.test_project_data['directories']:
            dir_path = project_path / dir_info['relative_path']
            dir_path.mkdir(parents=True, exist_ok=True)
        
        return project_path
    
    def test_init(self):
        """ProjectManagerの初期化テスト"""
        # 初期化の確認
        assert self.project_manager.config_manager is not None
        assert self.project_manager.logger is not None
        assert isinstance(self.project_manager._projects, dict)
        assert isinstance(self.project_manager._current_project, type(None))
        assert isinstance(self.project_manager._recent_projects, list)
    
    def test_create_project(self):
        """プロジェクト作成テスト"""
        project_name = "new_test_project"
        project_path = self.projects_dir / project_name
        
        # プロジェクトを作成
        result = self.project_manager.create_project(
            name=project_name,
            path=str(project_path),
            language="python",
            template="basic"
        )
        
        assert result is True
        assert project_path.exists()
        assert project_path.is_dir()
        
        # プロジェクトがマネージャーに登録されていることを確認
        assert project_name in self.project_manager._projects
        
        # プロジェクト情報の確認
        project_info = self.project_manager._projects[project_name]
        assert project_info['name'] == project_name
        assert project_info['path'] == str(project_path)
        assert project_info['language'] == "python"
    
    def test_create_project_existing_path(self):
        """既存パスでのプロジェクト作成テスト"""
        project_path = self._create_test_project()
        
        # 既存のパスでプロジェクト作成を試行
        result = self.project_manager.create_project(
            name="duplicate_project",
            path=str(project_path),
            language="python"
        )
        
        # 作成は失敗するはず
        assert result is False
    
    def test_open_project(self):
        """プロジェクトオープンテスト"""
        project_path = self._create_test_project()
        
        # プロジェクトを開く
        result = self.project_manager.open_project(str(project_path))
        
        assert result is True
        assert self.project_manager._current_project is not None
        assert self.project_manager._current_project['path'] == str(project_path)
        
        # 最近のプロジェクトリストに追加されていることを確認
        assert str(project_path) in self.project_manager._recent_projects
    
    def test_open_nonexistent_project(self):
        """存在しないプロジェクトのオープンテスト"""
        nonexistent_path = self.projects_dir / "nonexistent_project"
        
        # 存在しないプロジェクトを開こうとする
        result = self.project_manager.open_project(str(nonexistent_path))
        
        assert result is False
        assert self.project_manager._current_project is None
    
    def test_close_project(self):
        """プロジェクトクローズテスト"""
        project_path = self._create_test_project()
        
        # プロジェクトを開いてから閉じる
        self.project_manager.open_project(str(project_path))
        assert self.project_manager._current_project is not None
        
        result = self.project_manager.close_project()
        
        assert result is True
        assert self.project_manager._current_project is None
    
    def test_close_no_project(self):
        """プロジェクトが開かれていない状態でのクローズテスト"""
        # プロジェクトが開かれていない状態でクローズを試行
        result = self.project_manager.close_project()
        
        assert result is False
    
    def test_scan_project(self):
        """プロジェクトスキャンテスト"""
        project_path = self._create_test_project()
        
        # プロジェクトをスキャン
        scan_result = self.project_manager.scan_project(str(project_path))
        
        assert scan_result is not None
        assert 'files' in scan_result
        assert 'directories' in scan_result
        assert 'statistics' in scan_result
        
        # ファイルが検出されていることを確認
        assert len(scan_result['files']) > 0
        
        # 統計情報の確認
        stats = scan_result['statistics']
        assert 'total_files' in stats
        assert 'total_directories' in stats
        assert 'total_size' in stats
        assert stats['total_files'] > 0
    
    def test_scan_project_with_filters(self):
        """フィルタ付きプロジェクトスキャンテスト"""
        project_path = self._create_test_project()
        
        # .pyファイルのみをスキャン
        scan_result = self.project_manager.scan_project(
            str(project_path),
            file_patterns=['*.py']
        )
        
        assert scan_result is not None
        
        # 全てのファイルが.pyファイルであることを確認
        for file_info in scan_result['files']:
            assert file_info['name'].endswith('.py')
    
    def test_scan_project_with_ignore_patterns(self):
        """無視パターン付きプロジェクトスキャンテスト"""
        project_path = self._create_test_project()
        
        # __pycache__ディレクトリを作成
        pycache_dir = project_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "test.pyc").write_text("compiled")
        
        # __pycache__を無視してスキャン
        scan_result = self.project_manager.scan_project(
            str(project_path),
            ignore_patterns=['__pycache__']
        )
        
        assert scan_result is not None
        
        # __pycache__ディレクトリが結果に含まれていないことを確認
        for dir_info in scan_result['directories']:
            assert '__pycache__' not in dir_info['name']
    
    def test_get_project_info(self):
        """プロジェクト情報取得テスト"""
        project_path = self._create_test_project()
        self.project_manager.open_project(str(project_path))
        
        # プロジェクト情報を取得
        project_info = self.project_manager.get_project_info()
        
        assert project_info is not None
        assert 'name' in project_info
        assert 'path' in project_info
        assert 'language' in project_info
        assert 'created_at' in project_info
        assert 'last_modified' in project_info
    
    def test_get_project_info_no_project(self):
        """プロジェクトが開かれていない状態での情報取得テスト"""
        # プロジェクトが開かれていない状態で情報取得を試行
        project_info = self.project_manager.get_project_info()
        
        assert project_info is None
    
    def test_get_project_files(self):
        """プロジェクトファイル一覧取得テスト"""
        project_path = self._create_test_project()
        self.project_manager.open_project(str(project_path))
        
        # ファイル一覧を取得
        files = self.project_manager.get_project_files()
        
        assert isinstance(files, list)
        assert len(files) > 0
        
        # ファイル情報の構造確認
        for file_info in files:
            assert 'name' in file_info
            assert 'path' in file_info
            assert 'relative_path' in file_info
            assert 'size' in file_info
            assert 'modified_time' in file_info
    
    def test_get_project_files_by_extension(self):
        """拡張子によるファイル一覧取得テスト"""
        project_path = self._create_test_project()
        self.project_manager.open_project(str(project_path))
        
        # .pyファイルのみを取得
        py_files = self.project_manager.get_project_files(extensions=['.py'])
        
        assert isinstance(py_files, list)
        
        # 全てのファイルが.pyファイルであることを確認
        for file_info in py_files:
            assert file_info['name'].endswith('.py')
    
    def test_get_recent_projects(self):
        """最近のプロジェクト一覧取得テスト"""
        # 複数のプロジェクトを作成して開く
        project_paths = []
        for i in range(3):
            project_name = f"recent_project_{i}"
            project_path = self._create_test_project(project_name)
            project_paths.append(project_path)
            self.project_manager.open_project(str(project_path))
            self.project_manager.close_project()
        
        # 最近のプロジェクト一覧を取得
        recent_projects = self.project_manager.get_recent_projects()
        
        assert isinstance(recent_projects, list)
        assert len(recent_projects) == 3
        
        # 最新のプロジェクトが先頭にあることを確認
        assert str(project_paths[-1]) == recent_projects[0]
    
    def test_get_recent_projects_limit(self):
        """最近のプロジェクト一覧の制限テスト"""
        # 制限数を設定
        max_recent = 2
        self.project_manager._max_recent_projects = max_recent
        
        # 制限数を超えるプロジェクトを作成
        for i in range(5):
            project_name = f"limited_project_{i}"
            project_path = self._create_test_project(project_name)
            self.project_manager.open_project(str(project_path))
            self.project_manager.close_project()
        
        # 最近のプロジェクト一覧を取得
        recent_projects = self.project_manager.get_recent_projects()
        
        # 制限数以下であることを確認
        assert len(recent_projects) <= max_recent
    
    def test_save_project_state(self):
        """プロジェクト状態保存テスト"""
        project_path = self._create_test_project()
        self.project_manager.open_project(str(project_path))
        
        # プロジェクト状態を保存
        result = self.project_manager.save_project_state()
        
        assert result is True
        
        # 状態ファイルが作成されていることを確認
        state_file = project_path / ".llm_assistant_state.json"
        assert state_file.exists()
        
        # 状態ファイルの内容確認
        with open(state_file, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        
        assert 'project_info' in state_data
        assert 'last_saved' in state_data
    
    def test_load_project_state(self):
        """プロジェクト状態読み込みテスト"""
        project_path = self._create_test_project()
        self.project_manager.open_project(str(project_path))
        
        # 状態を保存してから読み込み
        self.project_manager.save_project_state()
        
        # 新しいProjectManagerインスタンスで状態を読み込み
        new_manager = ProjectManager(self.config_manager, self.logger)
        result = new_manager.load_project_state(str(project_path))
        
        assert result is True
        assert new_manager._current_project is not None
    
    def test_delete_project(self):
        """プロジェクト削除テスト"""
        project_path = self._create_test_project()
        project_name = self.test_project_data['name']
        
        # プロジェクトを登録
        self.project_manager.open_project(str(project_path))
        
        # プロジェクトを削除
        result = self.project_manager.delete_project(project_name, delete_files=True)
        
        assert result is True
        assert not project_path.exists()
        assert project_name not in self.project_manager._projects
    
    def test_delete_project_keep_files(self):
        """ファイルを保持してプロジェクト削除テスト"""
        project_path = self._create_test_project()
        project_name = self.test_project_data['name']
        
        # プロジェクトを登録
        self.project_manager.open_project(str(project_path))
        
        # ファイルを保持してプロジェクトを削除
        result = self.project_manager.delete_project(project_name, delete_files=False)
        
        assert result is True
        assert project_path.exists()  # ファイルは残っている
        assert project_name not in self.project_manager._projects
    
    def test_rename_project(self):
        """プロジェクト名変更テスト"""
        project_path = self._create_test_project()
        old_name = self.test_project_data['name']
        new_name = "renamed_project"
        
        # プロジェクトを登録
        self.project_manager.open_project(str(project_path))
        
        # プロジェクト名を変更
        result = self.project_manager.rename_project(old_name, new_name)
        
        assert result is True
        assert old_name not in self.project_manager._projects
        assert new_name in self.project_manager._projects
        
        # 現在のプロジェクト情報も更新されていることを確認
        if self.project_manager._current_project:
            assert self.project_manager._current_project['name'] == new_name
    
    def test_export_project_info(self):
        """プロジェクト情報エクスポートテスト"""
        project_path = self._create_test_project()
        self.project_manager.open_project(str(project_path))
        
        # プロジェクト情報をエクスポート
        export_data = self.project_manager.export_project_info()
        
        assert export_data is not None
        assert isinstance(export_data, dict)
        assert 'project_info' in export_data
        assert 'files' in export_data
        assert 'directories' in export_data
        assert 'statistics' in export_data
        
        # プロジェクト情報の妥当性確認
        assert_project_structure_valid(export_data)
    
    def test_import_project_info(self):
        """プロジェクト情報インポートテスト"""
        # エクスポートデータを作成
        export_data = {
            'project_info': {
                'name': 'imported_project',
                'path': str(self.projects_dir / 'imported_project'),
                'language': 'python'
            },
            'files': [],
            'directories': [],
            'statistics': {'total_files': 0, 'total_directories': 0, 'total_size': 0}
        }
        
        # プロジェクト情報をインポート
        result = self.project_manager.import_project_info(export_data)
        
        assert result is True
        assert 'imported_project' in self.project_manager._projects
    
    def test_search_in_project(self):
        """プロジェクト内検索テスト"""
        project_path = self._create_test_project()
        self.project_manager.open_project(str(project_path))
        
        # プロジェクト内で検索
        search_results = self.project_manager.search_in_project("test")
        
        assert isinstance(search_results, list)
        
        # 検索結果の構造確認
        for result in search_results:
            assert 'file' in result
            assert 'line_number' in result
            assert 'line_content' in result
            assert 'match_start' in result
            assert 'match_end' in result
    
    def test_search_in_project_regex(self):
        """正規表現によるプロジェクト内検索テスト"""
        project_path = self._create_test_project()
        self.project_manager.open_project(str(project_path))
        
        # 正規表現で検索
        search_results = self.project_manager.search_in_project(
            r"def\s+\w+",
            use_regex=True
        )
        
        assert isinstance(search_results, list)
    
    def test_get_project_statistics(self):
        """プロジェクト統計情報取得テスト"""
        project_path = self._create_test_project()
        self.project_manager.open_project(str(project_path))
        
        # 統計情報を取得
        stats = self.project_manager.get_project_statistics()
        
        assert stats is not None
        assert 'total_files' in stats
        assert 'total_directories' in stats
        assert 'total_size' in stats
        assert 'file_types' in stats
        assert 'language_distribution' in stats
        
        # 統計値が正の値であることを確認
        assert stats['total_files'] >= 0
        assert stats['total_directories'] >= 0
        assert stats['total_size'] >= 0
    
    @requires_project
    def test_with_project_context(self):
        """プロジェクトコンテキストテスト"""
        with MockProjectContext(self.test_project_path, self.test_project_data) as project_path:
            # プロジェクトを開く
            result = self.project_manager.open_project(str(project_path))
            assert result is True
            
            # プロジェクト情報を確認
            project_info = self.project_manager.get_project_info()
            assert project_info is not None
    
    def test_concurrent_project_operations(self):
        """並行プロジェクト操作テスト"""
        import threading
        import time
        
        results = []
        
        def worker(worker_id):
            project_name = f"concurrent_project_{worker_id}"
            project_path = self._create_test_project(project_name)
            
            # プロジェクトを開く
            result = self.project_manager.open_project(str(project_path))
            results.append(('open', worker_id, result))
            
            time.sleep(0.1)
            
            # プロジェクトを閉じる
            result = self.project_manager.close_project()
            results.append(('close', worker_id, result))
        
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
    
    def test_project_backup_and_restore(self):
        """プロジェクトバックアップと復元テスト"""
        project_path = self._create_test_project()
        self.project_manager.open_project(str(project_path))
        
        # バックアップを作成
        backup_path = self.project_manager.create_project_backup()
        
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.suffix == '.zip'
        
        # プロジェクトを削除
        shutil.rmtree(project_path)
        assert not project_path.exists()
        
        # バックアップから復元
        result = self.project_manager.restore_project_from_backup(backup_path, str(project_path))
        
        assert result is True
        assert project_path.exists()
        
        # 復元されたプロジェクトの内容確認
        restored_files = list(project_path.rglob("*.py"))
        assert len(restored_files) > 0
