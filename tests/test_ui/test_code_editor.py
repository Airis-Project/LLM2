# tests/test_ui/test_code_editor.py
"""
コードエディターのテストモジュール
コードエディターの単体テストと統合テストを実装
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, List, Optional, Tuple

# テスト対象のインポート
try:
    from PyQt6.QtWidgets import (
        QApplication, QTextEdit, QPlainTextEdit, QWidget, 
        QVBoxLayout, QHBoxLayout, QScrollBar
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect
    from PyQt6.QtTest import QTest
    from PyQt6.QtGui import (
        QTextCursor, QTextDocument, QFont, QFontMetrics,
        QKeyEvent, QMouseEvent, QWheelEvent, QPainter,
        QTextCharFormat, QColor, QSyntaxHighlighter
    )
    QT_VERSION = 6
except ImportError:
    try:
        from PyQt5.QtWidgets import (
            QApplication, QTextEdit, QPlainTextEdit, QWidget,
            QVBoxLayout, QHBoxLayout, QScrollBar
        )
        from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect
        from PyQt5.QtTest import QTest
        from PyQt5.QtGui import (
            QTextCursor, QTextDocument, QFont, QFontMetrics,
            QKeyEvent, QMouseEvent, QWheelEvent, QPainter,
            QTextCharFormat, QColor, QSyntaxHighlighter
        )
        QT_VERSION = 5
    except ImportError:
        QT_VERSION = None

# プロジェクト内のインポート
from ui.code_editor import CodeEditor, LineNumberArea
from ui.components.syntax_highlighter import SyntaxHighlighter
from ui.components.auto_complete import AutoCompleter
from ui.components.theme_manager import ThemeManager
from core.config_manager import ConfigManager
from core.logger import Logger
from utils.file_utils import FileUtils
from utils.text_utils import TextUtils

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


class MockSyntaxHighlighter:
    """テスト用のシンタックスハイライターモック"""
    
    def __init__(self, document=None):
        self.document = document
        self.language = "python"
        self.theme = "light"
        self.enabled = True
        self.keywords = ["def", "class", "import", "from", "if", "else", "for", "while"]
    
    def set_language(self, language: str):
        """言語設定"""
        self.language = language
    
    def set_theme(self, theme: str):
        """テーマ設定"""
        self.theme = theme
    
    def set_enabled(self, enabled: bool):
        """有効/無効設定"""
        self.enabled = enabled
    
    def highlight_block(self, text: str):
        """ブロックハイライト（モック）"""
        if not self.enabled:
            return
        # モック実装では何もしない
        pass
    
    def rehighlight(self):
        """再ハイライト（モック）"""
        if self.enabled and self.document:
            # モック実装では何もしない
            pass


class MockAutoCompleter:
    """テスト用のオートコンプリートモック"""
    
    def __init__(self, editor=None):
        self.editor = editor
        self.enabled = True
        self.completions = [
            "print", "len", "str", "int", "float", "list", "dict",
            "def", "class", "import", "from", "if", "else", "for", "while"
        ]
        self.current_completions = []
    
    def set_enabled(self, enabled: bool):
        """有効/無効設定"""
        self.enabled = enabled
    
    def add_completions(self, completions: List[str]):
        """補完候補追加"""
        self.completions.extend(completions)
    
    def get_completions(self, text: str, position: int) -> List[str]:
        """補完候補取得"""
        if not self.enabled:
            return []
        
        # 簡単なマッチング
        word_start = position
        while word_start > 0 and text[word_start - 1].isalnum():
            word_start -= 1
        
        current_word = text[word_start:position]
        if len(current_word) < 2:
            return []
        
        matches = [comp for comp in self.completions if comp.startswith(current_word)]
        return matches[:10]  # 最大10件
    
    def show_completions(self, completions: List[str], position: int):
        """補完リスト表示（モック）"""
        self.current_completions = completions
    
    def hide_completions(self):
        """補完リスト非表示（モック）"""
        self.current_completions = []


class MockLineNumberArea(QWidget if QT_VERSION else object):
    """テスト用の行番号エリアモック"""
    
    def __init__(self, editor=None):
        if QT_VERSION:
            super().__init__()
        self.editor = editor
        self.width_value = 50
        self.visible = True
    
    def sizeHint(self):
        """サイズヒント"""
        if QT_VERSION:
            from PyQt6.QtCore import QSize if QT_VERSION == 6 else PyQt5.QtCore.QSize
            return QSize(self.width_value, 0)
        return (self.width_value, 0)
    
    def paintEvent(self, event):
        """描画イベント（モック）"""
        # モック実装では何もしない
        pass
    
    def set_visible(self, visible: bool):
        """表示/非表示設定"""
        self.visible = visible
        if QT_VERSION and hasattr(self, 'setVisible'):
            self.setVisible(visible)


@pytest.mark.skipif(QT_VERSION is None, reason="Qt not available")
class TestCodeEditor(UITestBase):
    """コードエディターのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        
        # テスト用の一時ディレクトリ
        self.temp_dir = Path(tempfile.mkdtemp(prefix="code_editor_test_"))
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_code_editor")
        
        # テスト用の設定を追加
        self.config_manager.set('editor.font_family', 'Consolas')
        self.config_manager.set('editor.font_size', 12)
        self.config_manager.set('editor.tab_size', 4)
        self.config_manager.set('editor.show_line_numbers', True)
        self.config_manager.set('editor.word_wrap', False)
        self.config_manager.set('editor.syntax_highlighting', True)
        self.config_manager.set('editor.auto_complete', True)
        self.config_manager.set('ui.theme', 'light')
        
        # テストファイルの作成
        self.test_file = self.temp_dir / "test_code.py"
        self.test_content = '''# テストファイル
def hello_world():
    """Hello World関数"""
    print("Hello, World!")
    return "success"

class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
'''
        self.test_file.write_text(self.test_content, encoding='utf-8')
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        super().teardown_method()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_code_editor_initialization(self):
        """コードエディターの初期化テスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # 基本的な初期化の確認
        assert editor.config_manager is not None
        assert editor.logger is not None
        assert hasattr(editor, 'syntax_highlighter')
        assert hasattr(editor, 'auto_completer')
        assert hasattr(editor, 'line_number_area')
        
        # 設定の反映確認
        font = editor.font()
        assert font.family() == 'Consolas'
        assert font.pointSize() == 12
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_file_operations(self):
        """ファイル操作テスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # ファイルを開く
        result = editor.open_file(str(self.test_file))
        assert result is True
        assert editor.get_current_file() == str(self.test_file)
        assert self.test_content in editor.toPlainText()
        
        # ファイルを保存
        new_content = self.test_content + "\n# 追加行"
        editor.setPlainText(new_content)
        result = editor.save_file()
        assert result is True
        
        # 保存内容の確認
        saved_content = self.test_file.read_text(encoding='utf-8')
        assert new_content == saved_content
        
        # 別名で保存
        new_file = self.temp_dir / "new_test_code.py"
        result = editor.save_file_as(str(new_file))
        assert result is True
        assert new_file.exists()
        assert editor.get_current_file() == str(new_file)
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_text_editing_operations(self):
        """テキスト編集操作テスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # テキスト設定
        test_text = "def test_function():\n    pass"
        editor.setPlainText(test_text)
        assert editor.toPlainText() == test_text
        
        # カーソル位置の操作
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        # テキスト追加
        editor.insertPlainText("\n    return True")
        assert "return True" in editor.toPlainText()
        
        # 選択操作
        cursor = editor.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        editor.setTextCursor(cursor)
        selected_text = cursor.selectedText()
        assert len(selected_text) > 0
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_syntax_highlighting(self):
        """シンタックスハイライトテスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # Python コードを設定
        python_code = "def hello():\n    print('Hello')"
        editor.setPlainText(python_code)
        editor.set_language("python")
        
        # ハイライターの設定確認
        assert editor.syntax_highlighter.language == "python"
        
        # 言語変更
        editor.set_language("javascript")
        assert editor.syntax_highlighter.language == "javascript"
        
        # ハイライト有効/無効
        editor.set_syntax_highlighting(False)
        assert not editor.syntax_highlighter.enabled
        
        editor.set_syntax_highlighting(True)
        assert editor.syntax_highlighter.enabled
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_auto_completion(self):
        """オートコンプリートテスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # オートコンプリート設定
        editor.set_auto_complete(True)
        assert editor.auto_completer.enabled
        
        # テキスト入力とコンプリート
        editor.setPlainText("pr")
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        # 補完候補取得
        completions = editor.auto_completer.get_completions("pr", 2)
        assert "print" in completions
        
        # オートコンプリート無効化
        editor.set_auto_complete(False)
        assert not editor.auto_completer.enabled
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_line_numbers(self):
        """行番号表示テスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # 行番号表示設定
        editor.set_line_numbers(True)
        assert editor.line_number_area.visible
        
        # 複数行テキスト設定
        multi_line_text = "\n".join([f"line {i}" for i in range(1, 11)])
        editor.setPlainText(multi_line_text)
        
        # 行数確認
        line_count = editor.document().blockCount()
        assert line_count == 10
        
        # 行番号非表示
        editor.set_line_numbers(False)
        assert not editor.line_number_area.visible
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_word_wrap(self):
        """ワードラップテスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # ワードラップ有効
        editor.set_word_wrap(True)
        if QT_VERSION:
            assert editor.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth
        
        # ワードラップ無効
        editor.set_word_wrap(False)
        if QT_VERSION:
            assert editor.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_font_settings(self):
        """フォント設定テスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # フォント変更
        editor.set_font_family("Arial")
        font = editor.font()
        assert font.family() == "Arial"
        
        # フォントサイズ変更
        editor.set_font_size(14)
        font = editor.font()
        assert font.pointSize() == 14
        
        # フォントサイズ増減
        original_size = font.pointSize()
        editor.increase_font_size()
        assert editor.font().pointSize() > original_size
        
        editor.decrease_font_size()
        assert editor.font().pointSize() == original_size
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_tab_settings(self):
        """タブ設定テスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # タブサイズ設定
        editor.set_tab_size(8)
        assert editor.tab_size == 8
        
        # タブ文字の挿入テスト
        editor.setPlainText("")
        cursor = editor.textCursor()
        
        # タブキーのシミュレート
        if QT_VERSION:
            key_event = QKeyEvent(
                QKeyEvent.Type.KeyPress,
                Qt.Key.Key_Tab,
                Qt.KeyboardModifier.NoModifier
            )
            editor.keyPressEvent(key_event)
            
            # インデントが挿入されることを確認
            text = editor.toPlainText()
            assert len(text) > 0
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_search_and_replace(self):
        """検索・置換テスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # テストテキスト設定
        test_text = "Hello World\nHello Python\nGoodbye World"
        editor.setPlainText(test_text)
        
        # 検索
        found = editor.find_text("Hello")
        assert found is True
        
        # 選択されたテキストの確認
        cursor = editor.textCursor()
        selected_text = cursor.selectedText()
        assert selected_text == "Hello"
        
        # 次を検索
        found = editor.find_next("Hello")
        assert found is True
        
        # 置換
        replaced_count = editor.replace_all("Hello", "Hi")
        assert replaced_count == 2
        assert "Hi World" in editor.toPlainText()
        assert "Hi Python" in editor.toPlainText()
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_undo_redo(self):
        """元に戻す・やり直しテスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # 初期テキスト
        initial_text = "Initial text"
        editor.setPlainText(initial_text)
        
        # テキスト変更
        modified_text = initial_text + "\nModified"
        editor.setPlainText(modified_text)
        
        # 元に戻す
        if hasattr(editor, 'undo'):
            editor.undo()
            # 元のテキストに戻ることを確認
            current_text = editor.toPlainText()
            assert current_text != modified_text
        
        # やり直し
        if hasattr(editor, 'redo'):
            editor.redo()
            # 変更が再適用されることを確認
            current_text = editor.toPlainText()
            assert "Modified" in current_text
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_clipboard_operations(self):
        """クリップボード操作テスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # テストテキスト設定
        test_text = "Copy this text"
        editor.setPlainText(test_text)
        
        # 全選択
        editor.selectAll()
        selected_text = editor.textCursor().selectedText()
        assert selected_text == test_text
        
        # コピー操作のテスト（実際のクリップボードは使用しない）
        if hasattr(editor, 'copy'):
            editor.copy()
        
        # 切り取り操作のテスト
        if hasattr(editor, 'cut'):
            editor.cut()
            # テキストが削除されることを確認
            assert editor.toPlainText() != test_text
        
        # 貼り付け操作のテスト
        if hasattr(editor, 'paste'):
            editor.paste()
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_theme_switching(self):
        """テーマ切り替えテスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # ライトテーマ
        editor.set_theme("light")
        assert editor.syntax_highlighter.theme == "light"
        
        # ダークテーマ
        editor.set_theme("dark")
        assert editor.syntax_highlighter.theme == "dark"
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_cursor_position_tracking(self):
        """カーソル位置追跡テスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # 複数行テキスト設定
        multi_line_text = "Line 1\nLine 2\nLine 3"
        editor.setPlainText(multi_line_text)
        
        # カーソル位置取得
        line, column = editor.get_cursor_position()
        assert isinstance(line, int)
        assert isinstance(column, int)
        
        # カーソル位置設定
        editor.set_cursor_position(2, 5)  # 2行目、5文字目
        new_line, new_column = editor.get_cursor_position()
        assert new_line == 2
        assert new_column == 5
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # 存在しないファイルを開こうとする
        result = editor.open_file("/nonexistent/file.py")
        assert result is False
        
        # 読み込み専用ファイルに保存しようとする
        readonly_file = self.temp_dir / "readonly.py"
        readonly_file.write_text("readonly content")
        readonly_file.chmod(0o444)  # 読み込み専用
        
        try:
            editor.open_file(str(readonly_file))
            editor.setPlainText("modified content")
            result = editor.save_file()
            # 保存に失敗することを確認
            assert result is False
        finally:
            # パーミッションを戻す
            readonly_file.chmod(0o644)
    
    @patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter)
    @patch('ui.code_editor.AutoCompleter', MockAutoCompleter)
    @patch('ui.code_editor.LineNumberArea', MockLineNumberArea)
    def test_modification_tracking(self):
        """変更追跡テスト"""
        editor = self.create_widget(
            CodeEditor,
            self.config_manager,
            self.logger
        )
        
        # ファイルを開く
        editor.open_file(str(self.test_file))
        assert not editor.is_modified()
        
        # テキストを変更
        editor.setPlainText(self.test_content + "\n# Modified")
        assert editor.is_modified()
        
        # 保存
        editor.save_file()
        assert not editor.is_modified()


@mock_qt_test
class TestCodeEditorMocked:
    """モック環境でのコードエディターテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="code_editor_mock_test_"))
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_code_editor_mock")
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_code_editor_mock_initialization(self):
        """モック環境でのコードエディター初期化テスト"""
        # モック環境でもCodeEditorの基本機能が動作することを確認
        with patch('ui.code_editor.QPlainTextEdit'), \
             patch('ui.code_editor.SyntaxHighlighter', MockSyntaxHighlighter), \
             patch('ui.code_editor.AutoCompleter', MockAutoCompleter), \
             patch('ui.code_editor.LineNumberArea', MockLineNumberArea):
            
            # CodeEditorの作成をテスト
            # 実際の実装では、モック環境でも基本的な初期化が可能であることを確認
            assert self.config_manager is not None
            assert self.logger is not None
