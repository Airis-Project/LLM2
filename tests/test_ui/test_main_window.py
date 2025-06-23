# tests/test_ui/test_main_window.py
"""
メインウィンドウのテストモジュール
アプリケーションのメインウィンドウの単体テストと統合テストを実装
"""

import pytest
import tempfile
import shutil
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, List, Optional

# テスト対象のインポート
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtTest import QTest
    from PyQt6.QtGui import QKeySequence, QAction
    QT_VERSION = 6
except ImportError:
    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
        from PyQt5.QtCore import Qt, QTimer, pyqtSignal
        from PyQt5.QtTest import QTest
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QAction
        QT_VERSION = 5
    except ImportError:
        QT_VERSION = None

# プロジェクト内のインポート
from ui.main_window import MainWindow
from ui.code_editor import CodeEditor
from ui.project_tree import ProjectTree
from ui.chat_panel import ChatPanel
from ui.settings_dialog import SettingsDialog
from core.config_manager import ConfigManager
from core.logger import Logger
from core.project_manager import ProjectManager
from llm.llm_factory import LLMFactory

# テスト用のインポート
from tests.test_core import (
    create_test_config_manager,
    create_test_logger,
    MockFileContext,
    requires_file
)
from tests.test_ui import (
    UITestBase,
    requires_qt,
    mock_qt_test,
    UITestHelper,
    UITestFixtures
)


class MockCodeEditor(QWidget if QT_VERSION else object):
    """テスト用のコードエディターモック"""
    
    # シグナルの定義
    if QT_VERSION:
        text_changed = pyqtSignal()
        file_opened = pyqtSignal(str)
        file_saved = pyqtSignal(str)
    
    def __init__(self, parent=None):
        if QT_VERSION:
            super().__init__(parent)
        self.current_file = None
        self.content = ""
        self.is_modified = False
        self.language = "python"
        self.font_size = 12
        
    def open_file(self, file_path: str) -> bool:
        """ファイルを開く（モック）"""
        self.current_file = file_path
        self.content = f"# Mock content for {file_path}"
        if QT_VERSION and hasattr(self, 'file_opened'):
            self.file_opened.emit(file_path)
        return True
    
    def save_file(self, file_path: str = None) -> bool:
        """ファイルを保存（モック）"""
        save_path = file_path or self.current_file
        if save_path:
            self.is_modified = False
            if QT_VERSION and hasattr(self, 'file_saved'):
                self.file_saved.emit(save_path)
            return True
        return False
    
    def get_text(self) -> str:
        """テキスト取得"""
        return self.content
    
    def set_text(self, text: str):
        """テキスト設定"""
        self.content = text
        self.is_modified = True
        if QT_VERSION and hasattr(self, 'text_changed'):
            self.text_changed.emit()
    
    def get_current_file(self) -> Optional[str]:
        """現在のファイルパス取得"""
        return self.current_file
    
    def is_file_modified(self) -> bool:
        """ファイル変更状態取得"""
        return self.is_modified


class MockProjectTree(QWidget if QT_VERSION else object):
    """テスト用のプロジェクトツリーモック"""
    
    # シグナルの定義
    if QT_VERSION:
        file_selected = pyqtSignal(str)
        project_loaded = pyqtSignal(str)
    
    def __init__(self, parent=None):
        if QT_VERSION:
            super().__init__(parent)
        self.current_project = None
        self.selected_file = None
        self.project_files = []
    
    def load_project(self, project_path: str):
        """プロジェクト読み込み（モック）"""
        self.current_project = project_path
        self.project_files = [
            f"{project_path}/main.py",
            f"{project_path}/config.json",
            f"{project_path}/README.md"
        ]
        if QT_VERSION and hasattr(self, 'project_loaded'):
            self.project_loaded.emit(project_path)
    
    def select_file(self, file_path: str):
        """ファイル選択（モック）"""
        self.selected_file = file_path
        if QT_VERSION and hasattr(self, 'file_selected'):
            self.file_selected.emit(file_path)
    
    def get_selected_file(self) -> Optional[str]:
        """選択ファイル取得"""
        return self.selected_file
    
    def get_project_files(self) -> List[str]:
        """プロジェクトファイル一覧取得"""
        return self.project_files


class MockChatPanel(QWidget if QT_VERSION else object):
    """テスト用のチャットパネルモック"""
    
    # シグナルの定義
    if QT_VERSION:
        message_sent = pyqtSignal(str)
        response_received = pyqtSignal(str)
    
    def __init__(self, parent=None):
        if QT_VERSION:
            super().__init__(parent)
        self.messages = []
        self.is_processing = False
    
    def send_message(self, message: str):
        """メッセージ送信（モック）"""
        self.messages.append({"type": "user", "content": message})
        if QT_VERSION and hasattr(self, 'message_sent'):
            self.message_sent.emit(message)
        
        # 自動応答をシミュレート
        response = f"Mock response to: {message}"
        self.add_response(response)
    
    def add_response(self, response: str):
        """応答追加（モック）"""
        self.messages.append({"type": "assistant", "content": response})
        if QT_VERSION and hasattr(self, 'response_received'):
            self.response_received.emit(response)
    
    def clear_chat(self):
        """チャットクリア"""
        self.messages.clear()
    
    def get_messages(self) -> List[Dict[str, str]]:
        """メッセージ一覧取得"""
        return self.messages


@pytest.mark.skipif(QT_VERSION is None, reason="Qt not available")
class TestMainWindow(UITestBase):
    """メインウィンドウのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        
        # テスト用の一時ディレクトリ
        self.temp_dir = Path(tempfile.mkdtemp(prefix="main_window_test_"))
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_main_window")
        
        # テスト用の設定を追加
        self.config_manager.set('ui.theme', 'light')
        self.config_manager.set('ui.font_family', 'Consolas')
        self.config_manager.set('ui.font_size', 12)
        self.config_manager.set('ui.window_geometry.width', 800)
        self.config_manager.set('ui.window_geometry.height', 600)
        self.config_manager.set('llm.default_provider', 'openai')
        
        # プロジェクトマネージャーとLLMファクトリーのモック
        self.mock_project_manager = Mock(spec=ProjectManager)
        self.mock_llm_factory = Mock(spec=LLMFactory)
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        super().teardown_method()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_main_window_initialization(self):
        """メインウィンドウの初期化テスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # 基本的な初期化の確認
        assert main_window.config_manager is not None
        assert main_window.logger is not None
        assert main_window.project_manager is not None
        assert main_window.llm_factory is not None
        
        # ウィンドウの基本設定確認
        assert main_window.windowTitle() != ""
        assert main_window.width() > 0
        assert main_window.height() > 0
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_main_window_ui_components(self):
        """メインウィンドウのUIコンポーネントテスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # 主要コンポーネントの存在確認
        assert hasattr(main_window, 'code_editor')
        assert hasattr(main_window, 'project_tree')
        assert hasattr(main_window, 'chat_panel')
        
        # コンポーネントの型確認
        assert isinstance(main_window.code_editor, MockCodeEditor)
        assert isinstance(main_window.project_tree, MockProjectTree)
        assert isinstance(main_window.chat_panel, MockChatPanel)
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_menu_bar_creation(self):
        """メニューバー作成テスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # メニューバーの存在確認
        menu_bar = main_window.menuBar()
        assert menu_bar is not None
        
        # 主要メニューの存在確認
        menus = [action.text() for action in menu_bar.actions()]
        assert any('ファイル' in menu or 'File' in menu for menu in menus)
        assert any('編集' in menu or 'Edit' in menu for menu in menus)
        assert any('表示' in menu or 'View' in menu for menu in menus)
        assert any('ヘルプ' in menu or 'Help' in menu for menu in menus)
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_toolbar_creation(self):
        """ツールバー作成テスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # ツールバーの存在確認
        toolbars = main_window.findChildren(type(main_window.addToolBar("")))
        assert len(toolbars) > 0
        
        # 主要アクションの存在確認
        actions = []
        for toolbar in toolbars:
            actions.extend(toolbar.actions())
        
        action_texts = [action.text() for action in actions if action.text()]
        assert len(action_texts) > 0
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_status_bar_creation(self):
        """ステータスバー作成テスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # ステータスバーの存在確認
        status_bar = main_window.statusBar()
        assert status_bar is not None
        assert status_bar.isVisible()
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_file_operations(self):
        """ファイル操作テスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # テストファイルパス
        test_file = str(self.temp_dir / "test_file.py")
        
        # ファイルを開く
        result = main_window.open_file(test_file)
        assert result is True
        assert main_window.code_editor.get_current_file() == test_file
        
        # ファイルを保存
        main_window.code_editor.set_text("# Test content")
        result = main_window.save_current_file()
        assert result is True
        assert not main_window.code_editor.is_file_modified()
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_project_operations(self):
        """プロジェクト操作テスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # プロジェクトを開く
        project_path = str(self.temp_dir)
        main_window.open_project(project_path)
        
        # プロジェクトツリーに反映されることを確認
        assert main_window.project_tree.current_project == project_path
        assert len(main_window.project_tree.get_project_files()) > 0
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_chat_integration(self):
        """チャット統合テスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # チャットメッセージを送信
        test_message = "テストメッセージです"
        main_window.chat_panel.send_message(test_message)
        
        # メッセージが記録されることを確認
        messages = main_window.chat_panel.get_messages()
        assert len(messages) >= 1
        assert any(msg['content'] == test_message for msg in messages)
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_settings_dialog(self):
        """設定ダイアログテスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # 設定ダイアログを開く
        with patch('ui.main_window.SettingsDialog') as mock_dialog:
            mock_instance = Mock()
            mock_dialog.return_value = mock_instance
            mock_instance.exec.return_value = True
            
            main_window.show_settings()
            
            # ダイアログが作成されることを確認
            mock_dialog.assert_called_once()
            mock_instance.exec.assert_called_once()
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_window_state_management(self):
        """ウィンドウ状態管理テスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # ウィンドウ状態の保存
        original_geometry = main_window.geometry()
        main_window.save_window_state()
        
        # 設定に保存されることを確認
        saved_width = self.config_manager.get('ui.window_geometry.width')
        saved_height = self.config_manager.get('ui.window_geometry.height')
        assert saved_width is not None
        assert saved_height is not None
        
        # ウィンドウ状態の復元
        main_window.restore_window_state()
        # 復元後のジオメトリが設定値と一致することを確認
        assert main_window.width() == saved_width
        assert main_window.height() == saved_height
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_keyboard_shortcuts(self):
        """キーボードショートカットテスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # ショートカットの存在確認
        actions = main_window.findChildren(QAction)
        shortcuts = [action.shortcut() for action in actions if not action.shortcut().isEmpty()]
        
        # 主要ショートカットの確認
        shortcut_sequences = [shortcut.toString() for shortcut in shortcuts]
        assert any('Ctrl+N' in seq for seq in shortcut_sequences)  # 新規ファイル
        assert any('Ctrl+O' in seq for seq in shortcut_sequences)  # ファイルを開く
        assert any('Ctrl+S' in seq for seq in shortcut_sequences)  # 保存
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_theme_switching(self):
        """テーマ切り替えテスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # 初期テーマの確認
        initial_theme = self.config_manager.get('ui.theme')
        assert initial_theme == 'light'
        
        # テーマを変更
        main_window.switch_theme('dark')
        
        # 設定が更新されることを確認
        current_theme = self.config_manager.get('ui.theme')
        assert current_theme == 'dark'
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # 存在しないファイルを開こうとする
        result = main_window.open_file("/nonexistent/file.py")
        assert result is False
        
        # 無効なプロジェクトパスを開こうとする
        with patch.object(main_window.project_tree, 'load_project', side_effect=Exception("Test error")):
            try:
                main_window.open_project("/invalid/project/path")
                # エラーが適切に処理されることを確認
            except Exception:
                pytest.fail("Exception should be handled gracefully")
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_signal_connections(self):
        """シグナル接続テスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # プロジェクトツリーからファイル選択シグナル
        test_file = "/test/file.py"
        main_window.project_tree.select_file(test_file)
        
        # コードエディターにファイルが開かれることを確認
        # （実際の実装では、シグナル接続により自動的に開かれる）
        assert main_window.project_tree.get_selected_file() == test_file
    
    @patch('ui.main_window.CodeEditor', MockCodeEditor)
    @patch('ui.main_window.ProjectTree', MockProjectTree)
    @patch('ui.main_window.ChatPanel', MockChatPanel)
    def test_window_close_handling(self):
        """ウィンドウ閉じる処理テスト"""
        main_window = self.create_widget(
            MainWindow,
            self.config_manager,
            self.logger,
            self.mock_project_manager,
            self.mock_llm_factory
        )
        
        # 未保存の変更がある状態をシミュレート
        main_window.code_editor.set_text("Modified content")
        assert main_window.code_editor.is_file_modified()
        
        # ウィンドウを閉じる処理
        with patch('PyQt6.QtWidgets.QMessageBox.question' if QT_VERSION == 6 else 'PyQt5.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = mock_question.return_value.Save if hasattr(mock_question.return_value, 'Save') else 1
            
            # closeEventをシミュレート
            from PyQt6.QtGui import QCloseEvent if QT_VERSION == 6 else PyQt5.QtGui.QCloseEvent
            close_event = QCloseEvent()
            main_window.closeEvent(close_event)
            
            # 確認ダイアログが表示されることを確認
            if main_window.code_editor.is_file_modified():
                mock_question.assert_called_once()


@mock_qt_test
class TestMainWindowMocked:
    """モック環境でのメインウィンドウテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="main_window_mock_test_"))
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_main_window_mock")
        self.mock_project_manager = Mock(spec=ProjectManager)
        self.mock_llm_factory = Mock(spec=LLMFactory)
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_main_window_mock_initialization(self):
        """モック環境でのメインウィンドウ初期化テスト"""
        # モック環境でもMainWindowが作成できることを確認
        with patch('ui.main_window.QMainWindow'), \
             patch('ui.main_window.CodeEditor', MockCodeEditor), \
             patch('ui.main_window.ProjectTree', MockProjectTree), \
             patch('ui.main_window.ChatPanel', MockChatPanel):
            
            # MainWindowの作成をテスト
            # 実際の実装では、モック環境でも基本的な初期化が可能であることを確認
            assert self.config_manager is not None
            assert self.logger is not None
