# src/ui/code_editor.py

"""
コードエディタウィジェット
シンタックスハイライト、自動補完、行番号表示などの機能を提供
"""

import sys
import os
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import (
    Qt, QRect, QSize, QTimer, QPoint, QThread, pyqtSignal,
    QMimeData, QUrl, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QFont, QFontMetrics, QPainter, QColor, QPalette, QTextCursor,
    QTextDocument, QTextFormat, QTextCharFormat, QKeySequence,
    QAction, QIcon, QPixmap, QDragEnterEvent, QDropEvent,
    QContextMenuEvent, QKeyEvent, QMouseEvent, QWheelEvent,
    QResizeEvent, QPaintEvent, QFocusEvent
)
from PyQt6.QtWidgets import (
    QPlainTextEdit, QWidget, QTextEdit, QScrollBar, QMenu,
    QApplication, QToolTip, QMessageBox, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QSplitter, QCompleter, QListView
)

from ..core.logger import get_logger
from ..core.event_system import EventSystem, EventType
from ..utils.text_utils import TextUtils
from ..utils.validation_utils import ValidationUtils
from .components.syntax_highlighter import SyntaxHighlighter
from .components.auto_complete import AutoCompleter
from .components.theme_manager import ThemeManager


# エディタ設定のデータクラス
@dataclass
class EditorSettings:
    """エディタ設定"""
    font_family: str = "Consolas"
    font_size: int = 12
    tab_width: int = 4
    use_spaces: bool = True
    show_line_numbers: bool = True
    show_whitespace: bool = False
    word_wrap: bool = False
    highlight_current_line: bool = True
    auto_indent: bool = True
    auto_complete: bool = True
    bracket_matching: bool = True
    code_folding: bool = True
    minimap: bool = False


# 言語タイプの列挙
class LanguageType(Enum):
    """サポートする言語タイプ"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    HTML = "html"
    CSS = "css"
    JSON = "json"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


# 行番号表示ウィジェット
class LineNumberArea(QWidget):
    """行番号表示エリア"""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor
        self.logger = get_logger(__name__)
    
    def sizeHint(self) -> QSize:
        """推奨サイズを返す"""
        return QSize(self.code_editor.line_number_area_width(), 0)
    
    def paintEvent(self, event: QPaintEvent):
        """描画イベント"""
        try:
            self.code_editor.line_number_area_paint_event(event)
        except Exception as e:
            self.logger.error(f"行番号描画エラー: {e}")


# メインのコードエディタクラス
class CodeEditor(QPlainTextEdit):
    """
    高機能コードエディタ
    シンタックスハイライト、自動補完、行番号表示などをサポート
    """
    
    # シグナル定義
    text_changed_signal = pyqtSignal(str)  # テキスト変更
    cursor_position_changed_signal = pyqtSignal(int, int)  # カーソル位置変更
    language_changed_signal = pyqtSignal(str)  # 言語変更
    file_dropped_signal = pyqtSignal(str)  # ファイルドロップ
    completion_requested_signal = pyqtSignal(str, int)  # 補完要求
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ロガーとイベントシステム
        self.logger = get_logger(__name__)
        self.event_system = EventSystem()
        
        # 設定
        self.settings = EditorSettings()
        
        # ファイル情報
        self.file_path: Optional[str] = None
        self.language_type: LanguageType = LanguageType.PLAIN_TEXT
        self.encoding: str = "utf-8"
        
        # UI コンポーネント
        self.line_number_area = LineNumberArea(self)
        self.syntax_highlighter: Optional[SyntaxHighlighter] = None
        self.auto_completer: Optional[AutoCompleter] = None
        self.theme_manager = ThemeManager()
        
        # 内部状態
        self.is_modified = False
        self.last_cursor_position = (0, 0)
        self.bracket_pairs = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
        self.indent_stack = []
        
        # タイマー
        self.completion_timer = QTimer()
        self.completion_timer.setSingleShot(True)
        self.completion_timer.timeout.connect(self._trigger_completion)
        
        # アニメーション
        self.animations = {}
        
        # 初期化
        self._init_ui()
        self._init_connections()
        self._init_shortcuts()
        self._apply_settings()
        
        self.logger.info("CodeEditorを初期化しました")
    
    def _init_ui(self):
        """UI初期化"""
        try:
            # 基本設定
            self.setAcceptDrops(True)
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            
            # フォント設定
            font = QFont(self.settings.font_family, self.settings.font_size)
            font.setFixedPitch(True)
            self.setFont(font)
            
            # 行番号エリアの設定
            self._update_line_number_area_width()
            
            # カーソル設定
            self.setCursorWidth(2)
            
            # コンテキストメニュー
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            
        except Exception as e:
            self.logger.error(f"UI初期化エラー: {e}")
            raise
    
    def _init_connections(self):
        """シグナル・スロット接続"""
        try:
            # テキスト変更
            self.textChanged.connect(self._on_text_changed)
            self.document().modificationChanged.connect(self._on_modification_changed)
            
            # カーソル位置変更
            self.cursorPositionChanged.connect(self._on_cursor_position_changed)
            
            # スクロール
            self.verticalScrollBar().valueChanged.connect(self._update_line_numbers)
            
            # 行番号エリア
            self.blockCountChanged.connect(self._update_line_number_area_width)
            self.updateRequest.connect(self._update_line_number_area)
            
            # コンテキストメニュー
            self.customContextMenuRequested.connect(self._show_context_menu)
            
            # 補完タイマー
            self.completion_timer.timeout.connect(self._trigger_completion)
            
        except Exception as e:
            self.logger.error(f"シグナル接続エラー: {e}")
            raise
    
    def _init_shortcuts(self):
        """ショートカット初期化"""
        try:
            shortcuts = [
                # 基本操作
                (QKeySequence.StandardKey.Save, self._save_file),
                (QKeySequence.StandardKey.Find, self._show_find_dialog),
                (QKeySequence.StandardKey.Replace, self._show_replace_dialog),
                (QKeySequence("Ctrl+D"), self._duplicate_line),
                (QKeySequence("Ctrl+L"), self._delete_line),
                (QKeySequence("Ctrl+/"), self._toggle_comment),
                (QKeySequence("Tab"), self._handle_tab),
                (QKeySequence("Shift+Tab"), self._handle_shift_tab),
                (QKeySequence("Ctrl+Space"), self._trigger_completion),
                (QKeySequence("Ctrl+Shift+F"), self._format_code),
                (QKeySequence("F3"), self._goto_line),
                (QKeySequence("Ctrl+G"), self._goto_definition),
                (QKeySequence("Ctrl+Shift+Up"), self._move_line_up),
                (QKeySequence("Ctrl+Shift+Down"), self._move_line_down),
            ]
            
            for key_sequence, slot in shortcuts:
                action = QAction(self)
                action.setShortcut(key_sequence)
                action.triggered.connect(slot)
                self.addAction(action)
            
        except Exception as e:
            self.logger.error(f"ショートカット初期化エラー: {e}")
    
    def _apply_settings(self):
        """設定を適用"""
        try:
            # フォント
            font = QFont(self.settings.font_family, self.settings.font_size)
            font.setFixedPitch(True)
            self.setFont(font)
            
            # タブ幅
            metrics = QFontMetrics(font)
            tab_width = metrics.horizontalAdvance(' ') * self.settings.tab_width
            self.setTabStopDistance(tab_width)
            
            # 行の折り返し
            if self.settings.word_wrap:
                self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
            else:
                self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            
            # 行番号表示
            self.line_number_area.setVisible(self.settings.show_line_numbers)
            self._update_line_number_area_width()
            
            # 現在行のハイライト
            if self.settings.highlight_current_line:
                self._highlight_current_line()
            
            # テーマを適用
            self._apply_theme()
            
        except Exception as e:
            self.logger.error(f"設定適用エラー: {e}")
    
    def _apply_theme(self):
        """テーマを適用"""
        try:
            current_theme = self.theme_manager.get_current_theme()
            theme_data = self.theme_manager.get_theme_data(current_theme)
            
            if theme_data:
                editor_colors = theme_data.get('editor', {})
                
                # 背景色
                bg_color = QColor(editor_colors.get('background', '#ffffff'))
                palette = self.palette()
                palette.setColor(QPalette.ColorRole.Base, bg_color)
                self.setPalette(palette)
                
                # テキスト色
                text_color = QColor(editor_colors.get('text', '#000000'))
                palette.setColor(QPalette.ColorRole.Text, text_color)
                self.setPalette(palette)
                
                # 選択色
                selection_color = QColor(editor_colors.get('selection', '#3399ff'))
                palette.setColor(QPalette.ColorRole.Highlight, selection_color)
                self.setPalette(palette)
                
                # 行番号エリアの更新
                self.line_number_area.update()
            
        except Exception as e:
            self.logger.error(f"テーマ適用エラー: {e}")
    
    # プロパティ
    @property
    def current_line_number(self) -> int:
        """現在の行番号を取得"""
        return self.textCursor().blockNumber() + 1
    
    @property
    def current_column_number(self) -> int:
        """現在の列番号を取得"""
        return self.textCursor().columnNumber() + 1
    
    @property
    def total_lines(self) -> int:
        """総行数を取得"""
        return self.blockCount()
    
    @property
    def selected_text(self) -> str:
        """選択されたテキストを取得"""
        return self.textCursor().selectedText()
    
    # ファイル操作
    def load_file(self, file_path: str) -> bool:
        """ファイルを読み込み"""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"ファイルが存在しません: {file_path}")
                return False
            
            # エンコーディング検出
            encoding = self._detect_encoding(file_path)
            
            # ファイル読み込み
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # テキストを設定
            self.setPlainText(content)
            self.document().setModified(False)
            
            # ファイル情報を設定
            self.file_path = file_path
            self.encoding = encoding
            self.language_type = self._detect_language(file_path)
            
            # シンタックスハイライトを設定
            self._setup_syntax_highlighter()
            
            # 自動補完を設定
            self._setup_auto_completer()
            
            # イベント発行
            self.event_system.emit(EventType.FILE_OPENED, {
                'file_path': file_path,
                'language': self.language_type.value
            })
            
            self.logger.info(f"ファイルを読み込みました: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー: {e}")
            return False
    
    def save_file(self, file_path: str = None) -> bool:
        """ファイルを保存"""
        try:
            target_path = file_path or self.file_path
            
            if not target_path:
                self.logger.error("保存先パスが指定されていません")
                return False
            
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # ファイル保存
            content = self.toPlainText()
            with open(target_path, 'w', encoding=self.encoding) as f:
                f.write(content)
            
            # 変更フラグをクリア
            self.document().setModified(False)
            
            # ファイルパスを更新
            if file_path:
                self.file_path = file_path
                self.language_type = self._detect_language(file_path)
                self._setup_syntax_highlighter()
            
            # イベント発行
            self.event_system.emit(EventType.FILE_SAVED, {
                'file_path': target_path,
                'language': self.language_type.value
            })
            
            self.logger.info(f"ファイルを保存しました: {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル保存エラー: {e}")
            return False
    
    def _detect_encoding(self, file_path: str) -> str:
        """ファイルのエンコーディングを検出"""
        try:
            import chardet
            
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # 最初の10KB
                result = chardet.detect(raw_data)
                return result.get('encoding', 'utf-8')
                
        except ImportError:
            # chardetが利用できない場合はutf-8を使用
            return 'utf-8'
        except Exception as e:
            self.logger.warning(f"エンコーディング検出エラー: {e}")
            return 'utf-8'
    
    def _detect_language(self, file_path: str) -> LanguageType:
        """ファイル拡張子から言語を検出"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            language_map = {
                '.py': LanguageType.PYTHON,
                '.js': LanguageType.JAVASCRIPT,
                '.html': LanguageType.HTML,
                '.htm': LanguageType.HTML,
                '.css': LanguageType.CSS,
                '.json': LanguageType.JSON,
                '.md': LanguageType.MARKDOWN,
                '.markdown': LanguageType.MARKDOWN,
            }
            
            return language_map.get(ext, LanguageType.PLAIN_TEXT)
            
        except Exception as e:
            self.logger.error(f"言語検出エラー: {e}")
            return LanguageType.PLAIN_TEXT
    
    # シンタックスハイライト
    def _setup_syntax_highlighter(self):
        """シンタックスハイライトを設定"""
        try:
            if self.syntax_highlighter:
                self.syntax_highlighter.setDocument(None)
            
            if self.language_type != LanguageType.PLAIN_TEXT:
                self.syntax_highlighter = SyntaxHighlighter(
                    self.document(),
                    self.language_type
                )
            
        except Exception as e:
            self.logger.error(f"シンタックスハイライト設定エラー: {e}")
    
    # 自動補完
    def _setup_auto_completer(self):
        """自動補完を設定"""
        try:
            if not self.settings.auto_complete:
                return
            
            if self.auto_completer:
                self.auto_completer.setWidget(None)
            
            self.auto_completer = AutoCompleter(self, self.language_type)
            
        except Exception as e:
            self.logger.error(f"自動補完設定エラー: {e}")
    
    # 行番号関連
    def line_number_area_width(self) -> int:
        """行番号エリアの幅を計算"""
        try:
            if not self.settings.show_line_numbers:
                return 0
            
            digits = len(str(max(1, self.blockCount())))
            space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
            return space
            
        except Exception as e:
            self.logger.error(f"行番号エリア幅計算エラー: {e}")
            return 50
    
    def _update_line_number_area_width(self):
        """行番号エリアの幅を更新"""
        try:
            self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
            
        except Exception as e:
            self.logger.error(f"行番号エリア幅更新エラー: {e}")
    
    def _update_line_number_area(self, rect: QRect, dy: int):
        """行番号エリアを更新"""
        try:
            if dy:
                self.line_number_area.scroll(0, dy)
            else:
                self.line_number_area.update(0, rect.y(), 
                                           self.line_number_area.width(), 
                                           rect.height())
            
            if rect.contains(self.viewport().rect()):
                self._update_line_number_area_width()
                
        except Exception as e:
            self.logger.error(f"行番号エリア更新エラー: {e}")
    
    def _update_line_numbers(self):
        """行番号を更新"""
        try:
            self.line_number_area.update()
            
        except Exception as e:
            self.logger.error(f"行番号更新エラー: {e}")
    
    def line_number_area_paint_event(self, event: QPaintEvent):
        """行番号エリアの描画"""
        try:
            painter = QPainter(self.line_number_area)
            
            # 背景色
            theme_data = self.theme_manager.get_theme_data(
                self.theme_manager.get_current_theme()
            )
            bg_color = QColor('#f0f0f0')
            text_color = QColor('#666666')
            
            if theme_data:
                editor_colors = theme_data.get('editor', {})
                bg_color = QColor(editor_colors.get('line_number_bg', '#f0f0f0'))
                text_color = QColor(editor_colors.get('line_number_text', '#666666'))
            
            painter.fillRect(event.rect(), bg_color)
            
            # 行番号を描画
            block = self.firstVisibleBlock()
            block_number = block.blockNumber()
            top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            bottom = top + self.blockBoundingRect(block).height()
            
            font = self.font()
            font.setPointSize(font.pointSize() - 1)
            painter.setFont(font)
            painter.setPen(text_color)
            
            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    number = str(block_number + 1)
                    painter.drawText(0, int(top), 
                                   self.line_number_area.width() - 3, 
                                   self.fontMetrics().height(),
                                   Qt.AlignmentFlag.AlignRight, number)
                
                block = block.next()
                top = bottom
                bottom = top + self.blockBoundingRect(block).height()
                block_number += 1
            
        except Exception as e:
            self.logger.error(f"行番号描画エラー: {e}")
    
    # 現在行のハイライト
    def _highlight_current_line(self):
        """現在行をハイライト"""
        try:
            if not self.settings.highlight_current_line:
                return
            
            extra_selections = []
            
            if not self.isReadOnly():
                selection = QTextEdit.ExtraSelection()
                
                # ハイライト色
                theme_data = self.theme_manager.get_theme_data(
                    self.theme_manager.get_current_theme()
                )
                line_color = QColor('#ffffcc')
                
                if theme_data:
                    editor_colors = theme_data.get('editor', {})
                    line_color = QColor(editor_colors.get('current_line', '#ffffcc'))
                
                selection.format.setBackground(line_color)
                selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                selection.cursor = self.textCursor()
                selection.cursor.clearSelection()
                extra_selections.append(selection)
            
            self.setExtraSelections(extra_selections)
            
        except Exception as e:
            self.logger.error(f"現在行ハイライトエラー: {e}")
    
    # イベントハンドラ
    def _on_text_changed(self):
        """テキスト変更ハンドラ"""
        try:
            # 補完タイマーを開始
            if self.settings.auto_complete:
                self.completion_timer.start(500)  # 500ms後に補完をトリガー
            
            # シグナル発行
            self.text_changed_signal.emit(self.toPlainText())
            
        except Exception as e:
            self.logger.error(f"テキスト変更ハンドラエラー: {e}")
    
    def _on_modification_changed(self, modified: bool):
        """変更状態変更ハンドラ"""
        try:
            self.is_modified = modified
            
        except Exception as e:
            self.logger.error(f"変更状態ハンドラエラー: {e}")
    
    def _on_cursor_position_changed(self):
        """カーソル位置変更ハンドラ"""
        try:
            line = self.current_line_number
            column = self.current_column_number
            
            # 現在行をハイライト
            self._highlight_current_line()
            
            # 対応する括弧をハイライト
            if self.settings.bracket_matching:
                self._highlight_matching_brackets()
            
            # シグナル発行
            if (line, column) != self.last_cursor_position:
                self.cursor_position_changed_signal.emit(line, column)
                self.last_cursor_position = (line, column)
            
        except Exception as e:
            self.logger.error(f"カーソル位置変更ハンドラエラー: {e}")
    
    def _highlight_matching_brackets(self):
        """対応する括弧をハイライト"""
        try:
            cursor = self.textCursor()
            pos = cursor.position()
            text = self.toPlainText()
            
            if pos >= len(text):
                return
            
            char = text[pos]
            
            # 開き括弧の場合
            if char in self.bracket_pairs:
                matching_pos = self._find_matching_bracket(text, pos, char, self.bracket_pairs[char], 1)
                if matching_pos >= 0:
                    self._highlight_bracket_pair(pos, matching_pos)
            
            # 閉じ括弧の場合
            elif char in self.bracket_pairs.values():
                opening_char = None
                for k, v in self.bracket_pairs.items():
                    if v == char:
                        opening_char = k
                        break
                
                if opening_char:
                    matching_pos = self._find_matching_bracket(text, pos, char, opening_char, -1)
                    if matching_pos >= 0:
                        self._highlight_bracket_pair(matching_pos, pos)
            
        except Exception as e:
            self.logger.error(f"括弧ハイライトエラー: {e}")
    
    def _find_matching_bracket(self, text: str, start_pos: int, open_char: str, close_char: str, direction: int) -> int:
        """対応する括弧を検索"""
        try:
            count = 1
            pos = start_pos + direction
            
            while 0 <= pos < len(text) and count > 0:
                char = text[pos]
                
                if char == open_char:
                    count += direction
                elif char == close_char:
                    count -= direction
                
                if count == 0:
                    return pos
                
                pos += direction
            
            return -1
            
        except Exception as e:
            self.logger.error(f"括弧検索エラー: {e}")
            return -1
    
    def _highlight_bracket_pair(self, pos1: int, pos2: int):
        """括弧ペアをハイライト"""
        try:
            extra_selections = self.extraSelections()
            
            # 括弧ハイライト用の選択を追加
            for pos in [pos1, pos2]:
                selection = QTextEdit.ExtraSelection()
                
                # ハイライト色
                theme_data = self.theme_manager.get_theme_data(
                    self.theme_manager.get_current_theme()
                )
                bracket_color = QColor('#ffff00')
                
                if theme_data:
                    editor_colors = theme_data.get('editor', {})
                    bracket_color = QColor(editor_colors.get('bracket_match', '#ffff00'))
                
                selection.format.setBackground(bracket_color)
                cursor = self.textCursor()
                cursor.setPosition(pos)
                cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, 
                                  QTextCursor.MoveMode.KeepAnchor)
                selection.cursor = cursor
                extra_selections.append(selection)
            
            self.setExtraSelections(extra_selections)
            
        except Exception as e:
            self.logger.error(f"括弧ペアハイライトエラー: {e}")

    # キーボードイベント処理
    def keyPressEvent(self, event: QKeyEvent):
        """キーボードイベント処理"""
        try:
            # 自動補完が表示されている場合の処理
            if self.auto_completer and self.auto_completer.popup().isVisible():
                if event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab]:
                    self.auto_completer.insertCompletion()
                    event.accept()
                    return
                elif event.key() == Qt.Key.Key_Escape:
                    self.auto_completer.popup().hide()
                    event.accept()
                    return
            
            # 特殊キーの処理
            if event.key() == Qt.Key.Key_Tab:
                self._handle_tab()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Backtab:
                self._handle_shift_tab()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self._handle_enter()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Backspace:
                self._handle_backspace()
                event.accept()
                return
            
            # 自動括弧補完
            if event.text() in self.bracket_pairs and self.settings.auto_complete:
                self._handle_bracket_completion(event.text())
                event.accept()
                return
            
            # デフォルト処理
            super().keyPressEvent(event)
            
        except Exception as e:
            self.logger.error(f"キーボードイベント処理エラー: {e}")
            super().keyPressEvent(event)
    
    def _handle_tab(self):
        """タブキー処理"""
        try:
            cursor = self.textCursor()
            
            if cursor.hasSelection():
                # 選択範囲がある場合はインデント
                self._indent_selection()
            else:
                # 通常のタブ挿入
                if self.settings.use_spaces:
                    spaces = ' ' * self.settings.tab_width
                    cursor.insertText(spaces)
                else:
                    cursor.insertText('\t')
            
        except Exception as e:
            self.logger.error(f"タブ処理エラー: {e}")
    
    def _handle_shift_tab(self):
        """Shift+タブキー処理"""
        try:
            cursor = self.textCursor()
            
            if cursor.hasSelection():
                # 選択範囲がある場合はアンインデント
                self._unindent_selection()
            else:
                # 現在行をアンインデント
                self._unindent_current_line()
            
        except Exception as e:
            self.logger.error(f"Shift+タブ処理エラー: {e}")
    
    def _handle_enter(self):
        """エンターキー処理"""
        try:
            cursor = self.textCursor()
            
            # 自動インデント
            if self.settings.auto_indent:
                current_line = cursor.block().text()
                indent = self._get_line_indent(current_line)
                
                # 特定の文字で終わる場合は追加インデント
                if current_line.rstrip().endswith((':',)):
                    if self.settings.use_spaces:
                        indent += ' ' * self.settings.tab_width
                    else:
                        indent += '\t'
                
                cursor.insertText('\n' + indent)
            else:
                cursor.insertText('\n')
            
        except Exception as e:
            self.logger.error(f"エンター処理エラー: {e}")
    
    def _handle_backspace(self):
        """バックスペースキー処理"""
        try:
            cursor = self.textCursor()
            
            # 自動括弧削除
            if not cursor.hasSelection():
                pos = cursor.position()
                text = self.toPlainText()
                
                if pos > 0 and pos < len(text):
                    prev_char = text[pos - 1]
                    next_char = text[pos]
                    
                    if (prev_char in self.bracket_pairs and 
                        self.bracket_pairs[prev_char] == next_char):
                        # 対応する括弧も削除
                        cursor.deletePreviousChar()
                        cursor.deleteChar()
                        return
            
            # デフォルトのバックスペース処理
            cursor.deletePreviousChar()
            
        except Exception as e:
            self.logger.error(f"バックスペース処理エラー: {e}")
    
    def _handle_bracket_completion(self, open_bracket: str):
        """括弧補完処理"""
        try:
            cursor = self.textCursor()
            close_bracket = self.bracket_pairs[open_bracket]
            
            if cursor.hasSelection():
                # 選択範囲を括弧で囲む
                selected_text = cursor.selectedText()
                cursor.insertText(open_bracket + selected_text + close_bracket)
            else:
                # 括弧ペアを挿入
                cursor.insertText(open_bracket + close_bracket)
                cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
                self.setTextCursor(cursor)
            
        except Exception as e:
            self.logger.error(f"括弧補完処理エラー: {e}")
    
    # インデント関連
    def _get_line_indent(self, line: str) -> str:
        """行のインデントを取得"""
        try:
            indent = ''
            for char in line:
                if char in [' ', '\t']:
                    indent += char
                else:
                    break
            return indent
            
        except Exception as e:
            self.logger.error(f"インデント取得エラー: {e}")
            return ''
    
    def _indent_selection(self):
        """選択範囲をインデント"""
        try:
            cursor = self.textCursor()
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            
            # 選択範囲の開始・終了ブロックを取得
            cursor.setPosition(start)
            start_block = cursor.block()
            cursor.setPosition(end)
            end_block = cursor.block()
            
            # 各行にインデントを追加
            cursor.setPosition(start_block.position())
            
            while cursor.block() <= end_block:
                if self.settings.use_spaces:
                    cursor.insertText(' ' * self.settings.tab_width)
                else:
                    cursor.insertText('\t')
                
                if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                    break
            
        except Exception as e:
            self.logger.error(f"選択範囲インデントエラー: {e}")
    
    def _unindent_selection(self):
        """選択範囲をアンインデント"""
        try:
            cursor = self.textCursor()
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            
            # 選択範囲の開始・終了ブロックを取得
            cursor.setPosition(start)
            start_block = cursor.block()
            cursor.setPosition(end)
            end_block = cursor.block()
            
            # 各行からインデントを削除
            cursor.setPosition(start_block.position())
            
            while cursor.block() <= end_block:
                line_text = cursor.block().text()
                
                if self.settings.use_spaces:
                    # スペースを削除
                    spaces_to_remove = min(self.settings.tab_width, 
                                         len(line_text) - len(line_text.lstrip(' ')))
                    for _ in range(spaces_to_remove):
                        if cursor.block().text().startswith(' '):
                            cursor.deleteChar()
                else:
                    # タブを削除
                    if cursor.block().text().startswith('\t'):
                        cursor.deleteChar()
                
                if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                    break
            
        except Exception as e:
            self.logger.error(f"選択範囲アンインデントエラー: {e}")
    
    def _unindent_current_line(self):
        """現在行をアンインデント"""
        try:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            
            line_text = cursor.block().text()
            
            if self.settings.use_spaces:
                # スペースを削除
                spaces_to_remove = min(self.settings.tab_width, 
                                     len(line_text) - len(line_text.lstrip(' ')))
                for _ in range(spaces_to_remove):
                    if cursor.block().text().startswith(' '):
                        cursor.deleteChar()
            else:
                # タブを削除
                if cursor.block().text().startswith('\t'):
                    cursor.deleteChar()
            
        except Exception as e:
            self.logger.error(f"現在行アンインデントエラー: {e}")
    
    # マウスイベント処理
    def mousePressEvent(self, event: QMouseEvent):
        """マウスプレスイベント"""
        try:
            # 自動補完を非表示
            if self.auto_completer and self.auto_completer.popup().isVisible():
                self.auto_completer.popup().hide()
            
            super().mousePressEvent(event)
            
        except Exception as e:
            self.logger.error(f"マウスプレスイベントエラー: {e}")
            super().mousePressEvent(event)
    
    def wheelEvent(self, event: QWheelEvent):
        """ホイールイベント"""
        try:
            # Ctrl+ホイールでフォントサイズ変更
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                if delta > 0:
                    self._zoom_in()
                else:
                    self._zoom_out()
                event.accept()
                return
            
            super().wheelEvent(event)
            
        except Exception as e:
            self.logger.error(f"ホイールイベントエラー: {e}")
            super().wheelEvent(event)
    
    # ドラッグ&ドロップ
    def dragEnterEvent(self, event: QDragEnterEvent):
        """ドラッグエンターイベント"""
        try:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            else:
                super().dragEnterEvent(event)
                
        except Exception as e:
            self.logger.error(f"ドラッグエンターイベントエラー: {e}")
    
    def dropEvent(self, event: QDropEvent):
        """ドロップイベント"""
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                for url in urls:
                    file_path = url.toLocalFile()
                    if os.path.isfile(file_path):
                        self.file_dropped_signal.emit(file_path)
                event.acceptProposedAction()
            else:
                super().dropEvent(event)
                
        except Exception as e:
            self.logger.error(f"ドロップイベントエラー: {e}")
    
    # リサイズイベント
    def resizeEvent(self, event: QResizeEvent):
        """リサイズイベント"""
        try:
            super().resizeEvent(event)
            
            # 行番号エリアのサイズを調整
            cr = self.contentsRect()
            self.line_number_area.setGeometry(
                QRect(cr.left(), cr.top(), 
                      self.line_number_area_width(), cr.height())
            )
            
        except Exception as e:
            self.logger.error(f"リサイズイベントエラー: {e}")
    
    # フォーカスイベント
    def focusInEvent(self, event: QFocusEvent):
        """フォーカスインイベント"""
        try:
            super().focusInEvent(event)
            
            # 現在行をハイライト
            self._highlight_current_line()
            
        except Exception as e:
            self.logger.error(f"フォーカスインイベントエラー: {e}")
    
    def focusOutEvent(self, event: QFocusEvent):
        """フォーカスアウトイベント"""
        try:
            super().focusOutEvent(event)
            
            # 自動補完を非表示
            if self.auto_completer and self.auto_completer.popup().isVisible():
                self.auto_completer.popup().hide()
            
        except Exception as e:
            self.logger.error(f"フォーカスアウトイベントエラー: {e}")
    
    # ショートカットハンドラ
    def _save_file(self):
        """ファイル保存"""
        try:
            if self.file_path:
                self.save_file()
            else:
                # 名前を付けて保存ダイアログを表示
                # この機能は親ウィンドウで実装される
                pass
                
        except Exception as e:
            self.logger.error(f"ファイル保存エラー: {e}")
    
    def _show_find_dialog(self):
        """検索ダイアログ表示"""
        try:
            # 検索ダイアログは親ウィンドウで実装される
            pass
            
        except Exception as e:
            self.logger.error(f"検索ダイアログ表示エラー: {e}")
    
    def _show_replace_dialog(self):
        """置換ダイアログ表示"""
        try:
            # 置換ダイアログは親ウィンドウで実装される
            pass
            
        except Exception as e:
            self.logger.error(f"置換ダイアログ表示エラー: {e}")
    
    def _duplicate_line(self):
        """行を複製"""
        try:
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            selected_text = cursor.selectedText()
            
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
            cursor.insertText('\n' + selected_text)
            
        except Exception as e:
            self.logger.error(f"行複製エラー: {e}")
    
    def _delete_line(self):
        """行を削除"""
        try:
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # 改行文字も削除
            
        except Exception as e:
            self.logger.error(f"行削除エラー: {e}")
    
    def _toggle_comment(self):
        """コメントの切り替え"""
        try:
            cursor = self.textCursor()
            
            # 言語に応じたコメント文字を取得
            comment_char = self._get_comment_char()
            if not comment_char:
                return
            
            if cursor.hasSelection():
                # 選択範囲の各行をコメント切り替え
                self._toggle_comment_selection(comment_char)
            else:
                # 現在行をコメント切り替え
                self._toggle_comment_line(comment_char)
            
        except Exception as e:
            self.logger.error(f"コメント切り替えエラー: {e}")
    
    def _get_comment_char(self) -> str:
        """言語に応じたコメント文字を取得"""
        try:
            comment_map = {
                LanguageType.PYTHON: '#',
                LanguageType.JAVASCRIPT: '//',
                LanguageType.HTML: '<!-- -->',
                LanguageType.CSS: '/* */',
            }
            
            return comment_map.get(self.language_type, '#')
            
        except Exception as e:
            self.logger.error(f"コメント文字取得エラー: {e}")
            return '#'
    
    def _toggle_comment_line(self, comment_char: str):
        """現在行のコメントを切り替え"""
        try:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            
            line_text = cursor.block().text()
            stripped_text = line_text.lstrip()
            
            if stripped_text.startswith(comment_char):
                # コメントを削除
                indent = len(line_text) - len(stripped_text)
                cursor.movePosition(QTextCursor.MoveOperation.Right, 
                                  QTextCursor.MoveMode.MoveAnchor, indent)
                for _ in range(len(comment_char)):
                    cursor.deleteChar()
                # コメント文字の後のスペースも削除
                if cursor.block().text()[cursor.position():cursor.position()+1] == ' ':
                    cursor.deleteChar()
            else:
                # コメントを追加
                indent = len(line_text) - len(stripped_text)
                cursor.movePosition(QTextCursor.MoveOperation.Right, 
                                  QTextCursor.MoveMode.MoveAnchor, indent)
                cursor.insertText(comment_char + ' ')
            
        except Exception as e:
            self.logger.error(f"行コメント切り替えエラー: {e}")
    
    def _toggle_comment_selection(self, comment_char: str):
        """選択範囲のコメントを切り替え"""
        try:
            cursor = self.textCursor()
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            
            # 選択範囲の開始・終了ブロックを取得
            cursor.setPosition(start)
            start_block = cursor.block()
            cursor.setPosition(end)
            end_block = cursor.block()
            
            # 各行のコメントを切り替え
            cursor.setPosition(start_block.position())
            
            while cursor.block() <= end_block:
                self._toggle_comment_line(comment_char)
                
                if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                    break
            
        except Exception as e:
            self.logger.error(f"選択範囲コメント切り替えエラー: {e}")
    
    def _trigger_completion(self):
        """自動補完をトリガー"""
        try:
            if not self.settings.auto_complete or not self.auto_completer:
                return
            
            cursor = self.textCursor()
            text_under_cursor = self._get_text_under_cursor()
            
            if len(text_under_cursor) >= 2:  # 2文字以上で補完を開始
                self.completion_requested_signal.emit(text_under_cursor, cursor.position())
                self.auto_completer.show_completions(text_under_cursor)
            
        except Exception as e:
            self.logger.error(f"自動補完トリガーエラー: {e}")
    
    def _get_text_under_cursor(self) -> str:
        """カーソル下のテキストを取得"""
        try:
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            return cursor.selectedText()
            
        except Exception as e:
            self.logger.error(f"カーソル下テキスト取得エラー: {e}")
            return ''
    
    def _format_code(self):
        """コードフォーマット"""
        try:
            # コードフォーマット機能は別途実装
            # ここでは基本的なインデント整理のみ
            self._fix_indentation()
            
        except Exception as e:
            self.logger.error(f"コードフォーマットエラー: {e}")
    
    def _fix_indentation(self):
        """インデントを修正"""
        try:
            cursor = self.textCursor()
            cursor.beginEditBlock()
            
            # 全文を取得
            text = self.toPlainText()
            lines = text.split('\n')
            
            # インデントレベルを追跡
            indent_level = 0
            fixed_lines = []
            
            for line in lines:
                stripped = line.strip()
                
                if not stripped:
                    fixed_lines.append('')
                    continue
                
                # インデントレベルを調整
                if stripped.endswith(':'):
                    # インデントを増やす行
                    if self.settings.use_spaces:
                        indent = ' ' * (indent_level * self.settings.tab_width)
                    else:
                        indent = '\t' * indent_level
                    
                    fixed_lines.append(indent + stripped)
                    indent_level += 1
                elif stripped in ['else:', 'elif', 'except:', 'finally:']:
                    # 同じレベルを維持する行
                    if indent_level > 0:
                        indent_level -= 1
                    
                    if self.settings.use_spaces:
                        indent = ' ' * (indent_level * self.settings.tab_width)
                    else:
                        indent = '\t' * indent_level
                    
                    fixed_lines.append(indent + stripped)
                    indent_level += 1
                else:
                    # 通常の行
                    if self.settings.use_spaces:
                        indent = ' ' * (indent_level * self.settings.tab_width)
                    else:
                        indent = '\t' * indent_level
                    
                    fixed_lines.append(indent + stripped)
            
            # テキストを置換
            self.setPlainText('\n'.join(fixed_lines))
            cursor.endEditBlock()
            
        except Exception as e:
            self.logger.error(f"インデント修正エラー: {e}")
    
    def _goto_line(self):
        """指定行に移動"""
        try:
            # 行番号入力ダイアログは親ウィンドウで実装される
            pass
            
        except Exception as e:
            self.logger.error(f"行移動エラー: {e}")
    
    def _goto_definition(self):
        """定義に移動"""
        try:
            # 定義移動機能は将来実装
            pass
            
        except Exception as e:
            self.logger.error(f"定義移動エラー: {e}")
    
    def _move_line_up(self):
        """行を上に移動"""
        try:
            cursor = self.textCursor()
            cursor.beginEditBlock()
            
            # 現在行を取得
            current_block = cursor.block()
            if current_block.blockNumber() == 0:
                cursor.endEditBlock()
                return
            
            # 現在行のテキストを取得
            current_text = current_block.text()
            
            # 前の行を取得
            previous_block = current_block.previous()
            previous_text = previous_block.text()
            
            # 行を入れ替え
            cursor.setPosition(previous_block.position())
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.insertText(current_text)
            
            cursor.setPosition(current_block.position())
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.insertText(previous_text)
            
            cursor.endEditBlock()
            
        except Exception as e:
            self.logger.error(f"行上移動エラー: {e}")
    
    def _move_line_down(self):
        """行を下に移動"""
        try:
            cursor = self.textCursor()
            cursor.beginEditBlock()
            
            # 現在行を取得
            current_block = cursor.block()
            if current_block.blockNumber() >= self.blockCount() - 1:
                cursor.endEditBlock()
                return
            
            # 現在行のテキストを取得
            current_text = current_block.text()
            
            # 次の行を取得
            next_block = current_block.next()
            next_text = next_block.text()
            
            # 行を入れ替え
            cursor.setPosition(current_block.position())
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.insertText(next_text)
            
            cursor.setPosition(next_block.position())
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.insertText(current_text)
            
            cursor.endEditBlock()
            
        except Exception as e:
            self.logger.error(f"行下移動エラー: {e}")
    
    # ズーム機能
    def _zoom_in(self):
        """ズームイン"""
        try:
            current_font = self.font()
            new_size = min(current_font.pointSize() + 1, 72)  # 最大72pt
            current_font.setPointSize(new_size)
            self.setFont(current_font)
            
            # 設定を更新
            self.settings.font_size = new_size
            
        except Exception as e:
            self.logger.error(f"ズームインエラー: {e}")
    
    def _zoom_out(self):
        """ズームアウト"""
        try:
            current_font = self.font()
            new_size = max(current_font.pointSize() - 1, 8)  # 最小8pt
            current_font.setPointSize(new_size)
            self.setFont(current_font)
            
            # 設定を更新
            self.settings.font_size = new_size
            
        except Exception as e:
            self.logger.error(f"ズームアウトエラー: {e}")
    
    # コンテキストメニュー
    def _show_context_menu(self, position: QPoint):
        """コンテキストメニューを表示"""
        try:
            menu = QMenu(self)
            
            # 基本操作
            cut_action = menu.addAction("切り取り")
            cut_action.triggered.connect(self.cut)
            cut_action.setEnabled(self.textCursor().hasSelection())
            
            copy_action = menu.addAction("コピー")
            copy_action.triggered.connect(self.copy)
            copy_action.setEnabled(self.textCursor().hasSelection())
            
            paste_action = menu.addAction("貼り付け")
            paste_action.triggered.connect(self.paste)
            paste_action.setEnabled(QApplication.clipboard().text() != "")
            
            menu.addSeparator()
            
            # 全選択
            select_all_action = menu.addAction("すべて選択")
            select_all_action.triggered.connect(self.selectAll)
            
            menu.addSeparator()
            
            # 行操作
            duplicate_line_action = menu.addAction("行を複製")
            duplicate_line_action.triggered.connect(self._duplicate_line)
            
            delete_line_action = menu.addAction("行を削除")
            delete_line_action.triggered.connect(self._delete_line)
            
            menu.addSeparator()
            
            # コメント
            comment_action = menu.addAction("コメント切り替え")
            comment_action.triggered.connect(self._toggle_comment)
            
            # メニューを表示
            menu.exec(self.mapToGlobal(position))
            
        except Exception as e:
            self.logger.error(f"コンテキストメニュー表示エラー: {e}")
    
    # パブリックメソッド
    def set_language(self, language: LanguageType):
        """言語を設定"""
        try:
            if self.language_type != language:
                self.language_type = language
                self._setup_syntax_highlighter()
                self._setup_auto_completer()
                self.language_changed_signal.emit(language.value)
            
        except Exception as e:
            self.logger.error(f"言語設定エラー: {e}")
    
    def set_settings(self, settings: EditorSettings):
        """設定を更新"""
        try:
            self.settings = settings
            self._apply_settings()
            
        except Exception as e:
            self.logger.error(f"設定更新エラー: {e}")
    
    def get_settings(self) -> EditorSettings:
        """現在の設定を取得"""
        return self.settings
    
    def insert_text(self, text: str):
        """テキストを挿入"""
        try:
            cursor = self.textCursor()
            cursor.insertText(text)
            
        except Exception as e:
            self.logger.error(f"テキスト挿入エラー: {e}")
    
    def replace_text(self, old_text: str, new_text: str, case_sensitive: bool = False):
        """テキストを置換"""
        try:
            flags = QTextDocument.FindFlag(0)
            if case_sensitive:
                flags |= QTextDocument.FindFlag.FindCaseSensitively
            
            cursor = self.textCursor()
            cursor.beginEditBlock()
            
            # 最初から検索
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            
            while True:
                cursor = self.document().find(old_text, cursor, flags)
                if cursor.isNull():
                    break
                
                cursor.insertText(new_text)
            
            cursor.endEditBlock()
            
        except Exception as e:
            self.logger.error(f"テキスト置換エラー: {e}")
    
    def find_text(self, text: str, case_sensitive: bool = False, 
                  whole_words: bool = False, backwards: bool = False) -> bool:
        """テキストを検索"""
        try:
            flags = QTextDocument.FindFlag(0)
            
            if case_sensitive:
                flags |= QTextDocument.FindFlag.FindCaseSensitively
            if whole_words:
                flags |= QTextDocument.FindFlag.FindWholeWords
            if backwards:
                flags |= QTextDocument.FindFlag.FindBackward
            
            cursor = self.document().find(text, self.textCursor(), flags)
            
            if not cursor.isNull():
                self.setTextCursor(cursor)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"テキスト検索エラー: {e}")
            return False
    
    def goto_line(self, line_number: int):
        """指定行に移動"""
        try:
            if 1 <= line_number <= self.blockCount():
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                cursor.movePosition(QTextCursor.MoveOperation.Down, 
                                  QTextCursor.MoveMode.MoveAnchor, line_number - 1)
                self.setTextCursor(cursor)
                self.centerCursor()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"行移動エラー: {e}")
            return False
    
    def get_word_under_cursor(self) -> str:
        """カーソル下の単語を取得"""
        try:
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            return cursor.selectedText()
            
        except Exception as e:
            self.logger.error(f"カーソル下単語取得エラー: {e}")
            return ''
    
    def get_line_text(self, line_number: int = None) -> str:
        """指定行のテキストを取得"""
        try:
            if line_number is None:
                # 現在行
                cursor = self.textCursor()
                return cursor.block().text()
            else:
                # 指定行
                if 1 <= line_number <= self.blockCount():
                    block = self.document().findBlockByLineNumber(line_number - 1)
                    return block.text()
            
            return ''
            
        except Exception as e:
            self.logger.error(f"行テキスト取得エラー: {e}")
            return ''
    
    def set_line_text(self, line_number: int, text: str):
        """指定行のテキストを設定"""
        try:
            if 1 <= line_number <= self.blockCount():
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                cursor.movePosition(QTextCursor.MoveOperation.Down, 
                                  QTextCursor.MoveMode.MoveAnchor, line_number - 1)
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                cursor.insertText(text)
            
        except Exception as e:
            self.logger.error(f"行テキスト設定エラー: {e}")
    
    def insert_snippet(self, snippet: str):
        """スニペットを挿入"""
        try:
            cursor = self.textCursor()
            
            # タブストップを処理
            processed_snippet = self._process_snippet(snippet)
            cursor.insertText(processed_snippet)
            
        except Exception as e:
            self.logger.error(f"スニペット挿入エラー: {e}")
    
    def _process_snippet(self, snippet: str) -> str:
        """スニペットを処理"""
        try:
            # 基本的なプレースホルダー置換
            import re
            
            # ${1:default} 形式のプレースホルダーを処理
            def replace_placeholder(match):
                return match.group(2) if match.group(2) else ''
            
            pattern = r'\$\{(\d+):?([^}]*)\}'
            processed = re.sub(pattern, replace_placeholder, snippet)
            
            # インデントを調整
            cursor = self.textCursor()
            current_line = cursor.block().text()
            indent = self._get_line_indent(current_line)
            
            lines = processed.split('\n')
            if len(lines) > 1:
                indented_lines = [lines[0]]  # 最初の行はそのまま
                for line in lines[1:]:
                    if line.strip():  # 空行でない場合
                        indented_lines.append(indent + line)
                    else:
                        indented_lines.append(line)
                processed = '\n'.join(indented_lines)
            
            return processed
            
        except Exception as e:
            self.logger.error(f"スニペット処理エラー: {e}")
            return snippet
    
    def toggle_bookmark(self, line_number: int = None):
        """ブックマークを切り替え"""
        try:
            if line_number is None:
                line_number = self.current_line_number
            
            # ブックマーク機能は将来実装
            # 現在は基本的な実装のみ
            self.logger.info(f"ブックマーク切り替え: 行 {line_number}")
            
        except Exception as e:
            self.logger.error(f"ブックマーク切り替えエラー: {e}")
    
    def get_selection_info(self) -> Dict[str, Any]:
        """選択範囲の情報を取得"""
        try:
            cursor = self.textCursor()
            
            if not cursor.hasSelection():
                return {
                    'has_selection': False,
                    'start_line': 0,
                    'start_column': 0,
                    'end_line': 0,
                    'end_column': 0,
                    'selected_text': '',
                    'selection_length': 0
                }
            
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            selected_text = cursor.selectedText()
            
            # 開始位置
            cursor.setPosition(start)
            start_line = cursor.blockNumber() + 1
            start_column = cursor.columnNumber() + 1
            
            # 終了位置
            cursor.setPosition(end)
            end_line = cursor.blockNumber() + 1
            end_column = cursor.columnNumber() + 1
            
            return {
                'has_selection': True,
                'start_line': start_line,
                'start_column': start_column,
                'end_line': end_line,
                'end_column': end_column,
                'selected_text': selected_text,
                'selection_length': len(selected_text)
            }
            
        except Exception as e:
            self.logger.error(f"選択範囲情報取得エラー: {e}")
            return {
                'has_selection': False,
                'start_line': 0,
                'start_column': 0,
                'end_line': 0,
                'end_column': 0,
                'selected_text': '',
                'selection_length': 0
            }
    
    def get_editor_info(self) -> Dict[str, Any]:
        """エディタの情報を取得"""
        try:
            return {
                'file_path': self.file_path,
                'language': self.language_type.value,
                'encoding': self.encoding,
                'is_modified': self.is_modified,
                'current_line': self.current_line_number,
                'current_column': self.current_column_number,
                'total_lines': self.total_lines,
                'total_characters': len(self.toPlainText()),
                'selection_info': self.get_selection_info(),
                'font_family': self.settings.font_family,
                'font_size': self.settings.font_size,
                'tab_width': self.settings.tab_width,
                'use_spaces': self.settings.use_spaces
            }
            
        except Exception as e:
            self.logger.error(f"エディタ情報取得エラー: {e}")
            return {}
    
    def apply_theme(self, theme_name: str):
        """テーマを適用"""
        try:
            self.theme_manager.set_current_theme(theme_name)
            self._apply_theme()
            
            # シンタックスハイライトも更新
            if self.syntax_highlighter:
                self.syntax_highlighter.apply_theme(theme_name)
            
        except Exception as e:
            self.logger.error(f"テーマ適用エラー: {e}")
    
    def export_as_html(self) -> str:
        """HTMLとしてエクスポート"""
        try:
            # シンタックスハイライト付きHTMLを生成
            html = self.document().toHtml()
            
            # 基本的なスタイルを追加
            styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{os.path.basename(self.file_path) if self.file_path else 'Code'}</title>
    <style>
        body {{
            font-family: '{self.settings.font_family}', monospace;
            font-size: {self.settings.font_size}px;
            line-height: 1.4;
            margin: 20px;
            background-color: #ffffff;
            color: #000000;
        }}
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
    </style>
</head>
<body>
{html}
</body>
</html>
"""
            return styled_html
            
        except Exception as e:
            self.logger.error(f"HTML エクスポートエラー: {e}")
            return ''
    
    def get_statistics(self) -> Dict[str, int]:
        """統計情報を取得"""
        try:
            text = self.toPlainText()
            
            # 基本統計
            total_chars = len(text)
            total_chars_no_spaces = len(text.replace(' ', '').replace('\t', '').replace('\n', ''))
            total_lines = self.total_lines
            total_words = len(text.split())
            
            # 空行数
            empty_lines = sum(1 for line in text.split('\n') if not line.strip())
            
            # コメント行数（Python の場合）
            comment_lines = 0
            if self.language_type == LanguageType.PYTHON:
                comment_lines = sum(1 for line in text.split('\n') 
                                  if line.strip().startswith('#'))
            
            return {
                'total_characters': total_chars,
                'total_characters_no_spaces': total_chars_no_spaces,
                'total_lines': total_lines,
                'total_words': total_words,
                'empty_lines': empty_lines,
                'comment_lines': comment_lines,
                'code_lines': total_lines - empty_lines - comment_lines
            }
            
        except Exception as e:
            self.logger.error(f"統計情報取得エラー: {e}")
            return {}
    
    def cleanup(self):
        """クリーンアップ"""
        try:
            # タイマーを停止
            if self.completion_timer.isActive():
                self.completion_timer.stop()
            
            # アニメーションを停止
            for animation in self.animations.values():
                if animation.state() == QPropertyAnimation.State.Running:
                    animation.stop()
            
            # シンタックスハイライトをクリア
            if self.syntax_highlighter:
                self.syntax_highlighter.setDocument(None)
                self.syntax_highlighter = None
            
            # 自動補完をクリア
            if self.auto_completer:
                self.auto_completer.setWidget(None)
                self.auto_completer = None
            
            self.logger.info("CodeEditor をクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")


# エディタ設定ダイアログ
class EditorSettingsDialog(QWidget):
    """エディタ設定ダイアログ"""
    
    settings_changed = pyqtSignal(EditorSettings)
    
    def __init__(self, current_settings: EditorSettings, parent=None):
        super().__init__(parent)
        self.current_settings = current_settings
        self.logger = get_logger(__name__)
        
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """UI初期化"""
        try:
            self.setWindowTitle("エディタ設定")
            self.setFixedSize(400, 500)
            
            layout = QVBoxLayout(self)
            
            # フォント設定
            font_group = self._create_font_group()
            layout.addWidget(font_group)
            
            # インデント設定
            indent_group = self._create_indent_group()
            layout.addWidget(indent_group)
            
            # 表示設定
            display_group = self._create_display_group()
            layout.addWidget(display_group)
            
            # 機能設定
            feature_group = self._create_feature_group()
            layout.addWidget(feature_group)
            
            # ボタン
            button_layout = QHBoxLayout()
            
            self.ok_button = QPushButton("OK")
            self.ok_button.clicked.connect(self._apply_settings)
            
            self.cancel_button = QPushButton("キャンセル")
            self.cancel_button.clicked.connect(self.close)
            
            self.reset_button = QPushButton("リセット")
            self.reset_button.clicked.connect(self._reset_settings)
            
            button_layout.addWidget(self.reset_button)
            button_layout.addStretch()
            button_layout.addWidget(self.cancel_button)
            button_layout.addWidget(self.ok_button)
            
            layout.addLayout(button_layout)
            
        except Exception as e:
            self.logger.error(f"UI初期化エラー: {e}")
    
    def _create_font_group(self) -> QFrame:
        """フォント設定グループを作成"""
        # 実装は省略（基本的なフォント選択UI）
        pass
    
    def _create_indent_group(self) -> QFrame:
        """インデント設定グループを作成"""
        # 実装は省略（タブ幅、スペース/タブ選択UI）
        pass
    
    def _create_display_group(self) -> QFrame:
        """表示設定グループを作成"""
        # 実装は省略（行番号、現在行ハイライトなどのUI）
        pass
    
    def _create_feature_group(self) -> QFrame:
        """機能設定グループを作成"""
        # 実装は省略（自動補完、括弧マッチングなどのUI）
        pass
    
    def _load_settings(self):
        """設定を読み込み"""
        # 実装は省略
        pass
    
    def _apply_settings(self):
        """設定を適用"""
        # 実装は省略
        pass
    
    def _reset_settings(self):
        """設定をリセット"""
        # 実装は省略
        pass

