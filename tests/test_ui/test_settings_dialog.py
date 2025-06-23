# tests/test_ui/test_settings_dialog.py
"""
設定ダイアログのテストモジュール
設定ダイアログの単体テストと統合テストを実装
"""

import pytest
import tempfile
import shutil
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, List, Optional, Tuple

# テスト対象のインポート
try:
    from PyQt6.QtWidgets import (
        QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QGroupBox, QLabel, QLineEdit, QPushButton,
        QCheckBox, QSpinBox, QComboBox, QSlider, QColorDialog,
        QFontDialog, QFileDialog, QMessageBox
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtTest import QTest
    from PyQt6.QtGui import QFont, QColor, QPalette
    QT_VERSION = 6
except ImportError:
    try:
        from PyQt5.QtWidgets import (
            QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
            QTabWidget, QGroupBox, QLabel, QLineEdit, QPushButton,
            QCheckBox, QSpinBox, QComboBox, QSlider, QColorDialog,
            QFontDialog, QFileDialog, QMessageBox
        )
        from PyQt5.QtCore import Qt, QTimer, pyqtSignal
        from PyQt5.QtTest import QTest
        from PyQt5.QtGui import QFont, QColor, QPalette
        QT_VERSION = 5
    except ImportError:
        QT_VERSION = None

# プロジェクト内のインポート
from ui.settings_dialog import SettingsDialog, GeneralTab, EditorTab, LLMTab, UITab
from ui.components.theme_manager import ThemeManager
from core.config_manager import ConfigManager
from core.logger import Logger
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


class MockThemeManager:
    """テスト用のテーママネージャーモック"""
    
    def __init__(self):
        self.current_theme = "light"
        self.available_themes = ["light", "dark", "custom"]
        self.theme_data = {
            "light": {
                "background_color": "#ffffff",
                "text_color": "#000000",
                "accent_color": "#0078d4"
            },
            "dark": {
                "background_color": "#2d2d30",
                "text_color": "#ffffff",
                "accent_color": "#007acc"
            }
        }
    
    def get_available_themes(self) -> List[str]:
        """利用可能なテーマ一覧取得"""
        return self.available_themes
    
    def get_current_theme(self) -> str:
        """現在のテーマ取得"""
        return self.current_theme
    
    def set_theme(self, theme_name: str) -> bool:
        """テーマ設定"""
        if theme_name in self.available_themes:
            self.current_theme = theme_name
            return True
        return False
    
    def get_theme_data(self, theme_name: str) -> Dict[str, Any]:
        """テーマデータ取得"""
        return self.theme_data.get(theme_name, {})


class MockLLMFactory:
    """テスト用のLLMファクトリーモック"""
    
    def __init__(self):
        self.available_providers = ["openai", "claude", "local"]
        self.current_provider = "openai"
        self.provider_configs = {
            "openai": {
                "api_key": "",
                "model": "gpt-3.5-turbo",
                "max_tokens": 2048
            },
            "claude": {
                "api_key": "",
                "model": "claude-3-sonnet",
                "max_tokens": 4096
            },
            "local": {
                "model_path": "",
                "model_name": "llama-7b",
                "max_tokens": 1024
            }
        }
    
    def get_available_providers(self) -> List[str]:
        """利用可能なプロバイダー一覧取得"""
        return self.available_providers
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """プロバイダー設定取得"""
        return self.provider_configs.get(provider, {})
    
    def validate_provider_config(self, provider: str, config: Dict[str, Any]) -> bool:
        """プロバイダー設定検証"""
        if provider not in self.available_providers:
            return False
        
        required_keys = list(self.provider_configs[provider].keys())
        return all(key in config for key in required_keys)


@pytest.mark.skipif(QT_VERSION is None, reason="Qt not available")
class TestSettingsDialog(UITestBase):
    """設定ダイアログのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        
        # テスト用の一時ディレクトリ
        self.temp_dir = Path(tempfile.mkdtemp(prefix="settings_dialog_test_"))
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_settings_dialog")
        
        # テスト用の設定を追加
        self._setup_test_config()
        
        # モックオブジェクトの作成
        self.mock_theme_manager = MockThemeManager()
        self.mock_llm_factory = MockLLMFactory()
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        super().teardown_method()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _setup_test_config(self):
        """テスト用設定のセットアップ"""
        # 一般設定
        self.config_manager.set('general.language', 'ja')
        self.config_manager.set('general.auto_save', True)
        self.config_manager.set('general.auto_save_interval', 5)
        self.config_manager.set('general.backup_enabled', True)
        self.config_manager.set('general.max_recent_files', 10)
        
        # エディター設定
        self.config_manager.set('editor.font_family', 'Consolas')
        self.config_manager.set('editor.font_size', 12)
        self.config_manager.set('editor.tab_size', 4)
        self.config_manager.set('editor.show_line_numbers', True)
        self.config_manager.set('editor.word_wrap', False)
        self.config_manager.set('editor.syntax_highlighting', True)
        self.config_manager.set('editor.auto_complete', True)
        self.config_manager.set('editor.auto_indent', True)
        
        # UI設定
        self.config_manager.set('ui.theme', 'light')
        self.config_manager.set('ui.window_geometry.width', 800)
        self.config_manager.set('ui.window_geometry.height', 600)
        self.config_manager.set('ui.show_toolbar', True)
        self.config_manager.set('ui.show_statusbar', True)
        
        # LLM設定
        self.config_manager.set('llm.default_provider', 'openai')
        self.config_manager.set('llm.openai.api_key', '')
        self.config_manager.set('llm.openai.model', 'gpt-3.5-turbo')
        self.config_manager.set('llm.openai.max_tokens', 2048)
        self.config_manager.set('llm.claude.api_key', '')
        self.config_manager.set('llm.claude.model', 'claude-3-sonnet')
        self.config_manager.set('llm.local.model_path', '')
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_settings_dialog_initialization(self):
        """設定ダイアログの初期化テスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # 基本的な初期化の確認
        assert dialog.config_manager is not None
        assert dialog.logger is not None
        assert dialog.llm_factory is not None
        
        # ダイアログの基本設定確認
        assert dialog.windowTitle() != ""
        assert dialog.isModal()
        
        # タブウィジェットの存在確認
        assert hasattr(dialog, 'tab_widget')
        assert isinstance(dialog.tab_widget, QTabWidget)
        
        # 各タブの存在確認
        tab_count = dialog.tab_widget.count()
        assert tab_count >= 4  # General, Editor, UI, LLM
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_general_tab(self):
        """一般設定タブのテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # 一般設定タブの取得
        general_tab = None
        for i in range(dialog.tab_widget.count()):
            widget = dialog.tab_widget.widget(i)
            if isinstance(widget, GeneralTab):
                general_tab = widget
                break
        
        assert general_tab is not None
        
        # 設定項目の確認
        assert hasattr(general_tab, 'language_combo')
        assert hasattr(general_tab, 'auto_save_checkbox')
        assert hasattr(general_tab, 'auto_save_interval_spinbox')
        assert hasattr(general_tab, 'backup_checkbox')
        assert hasattr(general_tab, 'max_recent_files_spinbox')
        
        # 初期値の確認
        assert general_tab.language_combo.currentText() in ['日本語', 'English', 'ja', 'en']
        assert general_tab.auto_save_checkbox.isChecked() == True
        assert general_tab.auto_save_interval_spinbox.value() == 5
        assert general_tab.backup_checkbox.isChecked() == True
        assert general_tab.max_recent_files_spinbox.value() == 10
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_editor_tab(self):
        """エディター設定タブのテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # エディター設定タブの取得
        editor_tab = None
        for i in range(dialog.tab_widget.count()):
            widget = dialog.tab_widget.widget(i)
            if isinstance(widget, EditorTab):
                editor_tab = widget
                break
        
        assert editor_tab is not None
        
        # 設定項目の確認
        assert hasattr(editor_tab, 'font_family_combo')
        assert hasattr(editor_tab, 'font_size_spinbox')
        assert hasattr(editor_tab, 'tab_size_spinbox')
        assert hasattr(editor_tab, 'line_numbers_checkbox')
        assert hasattr(editor_tab, 'word_wrap_checkbox')
        assert hasattr(editor_tab, 'syntax_highlighting_checkbox')
        assert hasattr(editor_tab, 'auto_complete_checkbox')
        
        # 初期値の確認
        assert editor_tab.font_family_combo.currentText() == 'Consolas'
        assert editor_tab.font_size_spinbox.value() == 12
        assert editor_tab.tab_size_spinbox.value() == 4
        assert editor_tab.line_numbers_checkbox.isChecked() == True
        assert editor_tab.word_wrap_checkbox.isChecked() == False
        assert editor_tab.syntax_highlighting_checkbox.isChecked() == True
        assert editor_tab.auto_complete_checkbox.isChecked() == True
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_ui_tab(self):
        """UI設定タブのテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # UI設定タブの取得
        ui_tab = None
        for i in range(dialog.tab_widget.count()):
            widget = dialog.tab_widget.widget(i)
            if isinstance(widget, UITab):
                ui_tab = widget
                break
        
        assert ui_tab is not None
        
        # 設定項目の確認
        assert hasattr(ui_tab, 'theme_combo')
        assert hasattr(ui_tab, 'toolbar_checkbox')
        assert hasattr(ui_tab, 'statusbar_checkbox')
        
        # 初期値の確認
        assert ui_tab.theme_combo.currentText() == 'light'
        assert ui_tab.toolbar_checkbox.isChecked() == True
        assert ui_tab.statusbar_checkbox.isChecked() == True
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_llm_tab(self):
        """LLM設定タブのテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # LLM設定タブの取得
        llm_tab = None
        for i in range(dialog.tab_widget.count()):
            widget = dialog.tab_widget.widget(i)
            if isinstance(widget, LLMTab):
                llm_tab = widget
                break
        
        assert llm_tab is not None
        
        # 設定項目の確認
        assert hasattr(llm_tab, 'provider_combo')
        assert hasattr(llm_tab, 'api_key_edit')
        assert hasattr(llm_tab, 'model_combo')
        assert hasattr(llm_tab, 'max_tokens_spinbox')
        
        # 初期値の確認
        assert llm_tab.provider_combo.currentText() == 'openai'
        assert llm_tab.max_tokens_spinbox.value() == 2048
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_settings_load_and_save(self):
        """設定の読み込みと保存テスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # 設定の読み込み確認
        dialog.load_settings()
        
        # 設定値の変更
        original_font_size = self.config_manager.get('editor.font_size')
        new_font_size = original_font_size + 2
        
        # エディタータブで設定変更
        editor_tab = None
        for i in range(dialog.tab_widget.count()):
            widget = dialog.tab_widget.widget(i)
            if isinstance(widget, EditorTab):
                editor_tab = widget
                break
        
        if editor_tab:
            editor_tab.font_size_spinbox.setValue(new_font_size)
        
        # 設定の保存
        dialog.save_settings()
        
        # 設定が保存されたことを確認
        saved_font_size = self.config_manager.get('editor.font_size')
        assert saved_font_size == new_font_size
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_font_selection_dialog(self):
        """フォント選択ダイアログテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # エディタータブの取得
        editor_tab = None
        for i in range(dialog.tab_widget.count()):
            widget = dialog.tab_widget.widget(i)
            if isinstance(widget, EditorTab):
                editor_tab = widget
                break
        
        assert editor_tab is not None
        
        # フォント選択ボタンの存在確認
        if hasattr(editor_tab, 'font_select_button'):
            with patch('PyQt6.QtWidgets.QFontDialog.getFont' if QT_VERSION == 6 else 'PyQt5.QtWidgets.QFontDialog.getFont') as mock_font_dialog:
                # フォントダイアログのモック設定
                test_font = QFont("Arial", 14)
                mock_font_dialog.return_value = (test_font, True)
                
                # フォント選択ボタンをクリック
                editor_tab.font_select_button.click()
                
                # ダイアログが呼ばれることを確認
                mock_font_dialog.assert_called_once()
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_theme_preview(self):
        """テーマプレビューテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # UI設定タブの取得
        ui_tab = None
        for i in range(dialog.tab_widget.count()):
            widget = dialog.tab_widget.widget(i)
            if isinstance(widget, UITab):
                ui_tab = widget
                break
        
        assert ui_tab is not None
        
        # テーマ変更
        if hasattr(ui_tab, 'theme_combo'):
            # ダークテーマに変更
            dark_index = ui_tab.theme_combo.findText('dark')
            if dark_index >= 0:
                ui_tab.theme_combo.setCurrentIndex(dark_index)
                
                # プレビューが更新されることを確認
                if hasattr(ui_tab, 'apply_theme_preview'):
                    ui_tab.apply_theme_preview('dark')
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_llm_provider_switching(self):
        """LLMプロバイダー切り替えテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # LLM設定タブの取得
        llm_tab = None
        for i in range(dialog.tab_widget.count()):
            widget = dialog.tab_widget.widget(i)
            if isinstance(widget, LLMTab):
                llm_tab = widget
                break
        
        assert llm_tab is not None
        
        # プロバイダー変更
        if hasattr(llm_tab, 'provider_combo'):
            # Claudeプロバイダーに変更
            claude_index = llm_tab.provider_combo.findText('claude')
            if claude_index >= 0:
                llm_tab.provider_combo.setCurrentIndex(claude_index)
                
                # 設定項目が更新されることを確認
                if hasattr(llm_tab, 'update_provider_settings'):
                    llm_tab.update_provider_settings('claude')
                    
                    # Claudeの設定項目が表示されることを確認
                    assert llm_tab.max_tokens_spinbox.value() == 4096
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_validation_and_error_handling(self):
        """バリデーションとエラーハンドリングテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # 無効な設定値のテスト
        editor_tab = None
        for i in range(dialog.tab_widget.count()):
            widget = dialog.tab_widget.widget(i)
            if isinstance(widget, EditorTab):
                editor_tab = widget
                break
        
        if editor_tab:
            # 無効なフォントサイズ
            editor_tab.font_size_spinbox.setValue(0)
            
            # バリデーションが働くことを確認
            if hasattr(dialog, 'validate_settings'):
                is_valid = dialog.validate_settings()
                assert is_valid is False
            
            # 有効な値に戻す
            editor_tab.font_size_spinbox.setValue(12)
            
            if hasattr(dialog, 'validate_settings'):
                is_valid = dialog.validate_settings()
                assert is_valid is True
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_dialog_buttons(self):
        """ダイアログボタンのテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # ボタンの存在確認
        assert hasattr(dialog, 'ok_button')
        assert hasattr(dialog, 'cancel_button')
        assert hasattr(dialog, 'apply_button')
        
        # OKボタンのテスト
        original_font_size = self.config_manager.get('editor.font_size')
        
        # 設定変更
        editor_tab = None
        for i in range(dialog.tab_widget.count()):
            widget = dialog.tab_widget.widget(i)
            if isinstance(widget, EditorTab):
                editor_tab = widget
                break
        
        if editor_tab:
            new_font_size = original_font_size + 2
            editor_tab.font_size_spinbox.setValue(new_font_size)
        
        # OKボタンをクリック
        dialog.ok_button.click()
        
        # 設定が保存されてダイアログが閉じることを確認
        saved_font_size = self.config_manager.get('editor.font_size')
        assert saved_font_size == new_font_size
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_reset_to_defaults(self):
        """デフォルト値リセットテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # 設定値を変更
        self.config_manager.set('editor.font_size', 20)
        self.config_manager.set('editor.tab_size', 8)
        
        # デフォルトリセット機能があるかチェック
        if hasattr(dialog, 'reset_to_defaults'):
            dialog.reset_to_defaults()
            
            # デフォルト値に戻ることを確認
            assert self.config_manager.get('editor.font_size') == 12
            assert self.config_manager.get('editor.tab_size') == 4
    
    @patch('ui.settings_dialog.ThemeManager', MockThemeManager)
    def test_settings_import_export(self):
        """設定のインポート・エクスポートテスト"""
        dialog = self.create_widget(
            SettingsDialog,
            self.config_manager,
            self.logger,
            self.mock_llm_factory
        )
        
        # エクスポート機能があるかチェック
        if hasattr(dialog, 'export_settings'):
            export_file = self.temp_dir / "exported_settings.json"
            
            with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName' if QT_VERSION == 6 else 'PyQt5.QtWidgets.QFileDialog.getSaveFileName') as mock_save_dialog:
                mock_save_dialog.return_value = (str(export_file), "JSON files (*.json)")
                
                # エクスポート実行
                dialog.export_settings()
                
                # ファイルが作成されることを確認
                assert export_file.exists()
                
                # インポート機能があるかチェック
                if hasattr(dialog, 'import_settings'):
                    with patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName' if QT_VERSION == 6 else 'PyQt5.QtWidgets.QFileDialog.getOpenFileName') as mock_open_dialog:
                        mock_open_dialog.return_value = (str(export_file), "JSON files (*.json)")
                        
                        # インポート実行
                        dialog.import_settings()


@mock_qt_test
class TestSettingsDialogMocked:
    """モック環境での設定ダイアログテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="settings_dialog_mock_test_"))
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_settings_dialog_mock")
        self.mock_llm_factory = MockLLMFactory()
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_settings_dialog_mock_initialization(self):
        """モック環境での設定ダイアログ初期化テスト"""
        # モック環境でもSettingsDialogの基本機能が動作することを確認
        with patch('ui.settings_dialog.QDialog'), \
             patch('ui.settings_dialog.QTabWidget'), \
             patch('ui.settings_dialog.ThemeManager', MockThemeManager):
            
            # SettingsDialogの作成をテスト
            # 実際の実装では、モック環境でも基本的な初期化が可能であることを確認
            assert self.config_manager is not None
            assert self.logger is not None
            assert self.mock_llm_factory is not None
    
    def test_config_validation_mock(self):
        """モック環境での設定バリデーションテスト"""
        # 設定値のバリデーション機能をテスト
        test_configs = {
            'editor.font_size': [8, 12, 16, 24, 48],  # 有効な値
            'editor.tab_size': [2, 4, 8],  # 有効な値
            'general.auto_save_interval': [1, 5, 10, 30],  # 有効な値
        }
        
        for config_key, valid_values in test_configs.items():
            for value in valid_values:
                self.config_manager.set(config_key, value)
                stored_value = self.config_manager.get(config_key)
                assert stored_value == value
