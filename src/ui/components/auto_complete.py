# src/ui/components/auto_complete.py
"""
オートコンプリート機能
コードエディタでの自動補完を提供
"""

import re
import os
import ast
import keyword
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import (
    Qt, QObject, pyqtSignal, QTimer, QThread, 
    QAbstractListModel, QModelIndex, QRect, QPoint
)
from PyQt6.QtGui import (
    QTextCursor, QKeyEvent, QFont, QFontMetrics,
    QPixmap, QIcon, QPainter, QColor
)
from PyQt6.QtWidgets import (
    QListView, QWidget, QVBoxLayout, QLabel,
    QFrame, QApplication, QTextEdit
)

from ...core.logger import get_logger


class CompletionType(Enum):
    """補完タイプ"""
    KEYWORD = "keyword"
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    METHOD = "method"
    PROPERTY = "property"
    MODULE = "module"
    BUILTIN = "builtin"
    SNIPPET = "snippet"


@dataclass
class CompletionItem:
    """補完アイテム"""
    text: str
    completion_type: CompletionType
    description: str = ""
    detail: str = ""
    insert_text: str = ""
    documentation: str = ""
    sort_text: str = ""
    filter_text: str = ""
    
    def __post_init__(self):
        if not self.insert_text:
            self.insert_text = self.text
        if not self.sort_text:
            self.sort_text = self.text
        if not self.filter_text:
            self.filter_text = self.text


class CompletionModel(QAbstractListModel):
    """補完リストモデル"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.items: List[CompletionItem] = []
        self._icons = self._create_icons()
    
    def _create_icons(self) -> Dict[CompletionType, QIcon]:
        """補完タイプ用のアイコンを作成"""
        try:
            icons = {}
            colors = {
                CompletionType.KEYWORD: QColor(0, 0, 255),
                CompletionType.FUNCTION: QColor(128, 0, 128),
                CompletionType.CLASS: QColor(0, 128, 0),
                CompletionType.VARIABLE: QColor(255, 140, 0),
                CompletionType.METHOD: QColor(128, 0, 128),
                CompletionType.PROPERTY: QColor(255, 140, 0),
                CompletionType.MODULE: QColor(0, 128, 128),
                CompletionType.BUILTIN: QColor(128, 128, 0),
                CompletionType.SNIPPET: QColor(255, 0, 0)
            }
            
            for comp_type, color in colors.items():
                pixmap = QPixmap(16, 16)
                pixmap.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(color)
                painter.setPen(color)
                
                # タイプに応じた形状を描画
                if comp_type == CompletionType.KEYWORD:
                    painter.drawRect(2, 2, 12, 12)
                elif comp_type == CompletionType.FUNCTION:
                    painter.drawEllipse(2, 2, 12, 12)
                elif comp_type == CompletionType.CLASS:
                    painter.drawPolygon([
                        QPoint(8, 2), QPoint(14, 8), QPoint(8, 14), QPoint(2, 8)
                    ])
                else:
                    painter.drawEllipse(2, 2, 12, 12)
                
                painter.end()
                icons[comp_type] = QIcon(pixmap)
            
            return icons
            
        except Exception as e:
            self.logger.error(f"アイコン作成エラー: {e}")
            return {}
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """行数を返す"""
        return len(self.items)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """データを返す"""
        try:
            if not index.isValid() or index.row() >= len(self.items):
                return None
            
            item = self.items[index.row()]
            
            if role == Qt.ItemDataRole.DisplayRole:
                return item.text
            elif role == Qt.ItemDataRole.DecorationRole:
                return self._icons.get(item.completion_type)
            elif role == Qt.ItemDataRole.ToolTipRole:
                tooltip = item.description
                if item.detail:
                    tooltip += f"\n\n{item.detail}"
                if item.documentation:
                    tooltip += f"\n\n{item.documentation}"
                return tooltip
            elif role == Qt.ItemDataRole.UserRole:
                return item
            
            return None
            
        except Exception as e:
            self.logger.error(f"データ取得エラー: {e}")
            return None
    
    def set_items(self, items: List[CompletionItem]):
        """アイテムを設定"""
        try:
            self.beginResetModel()
            self.items = items
            self.endResetModel()
            
        except Exception as e:
            self.logger.error(f"アイテム設定エラー: {e}")
    
    def clear(self):
        """アイテムをクリア"""
        try:
            self.beginResetModel()
            self.items.clear()
            self.endResetModel()
            
        except Exception as e:
            self.logger.error(f"アイテムクリアエラー: {e}")


class CompletionListView(QListView):
    """補完リストビュー"""
    
    item_selected = pyqtSignal(CompletionItem)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        
        # 外観設定
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setMaximumHeight(200)
        self.setMinimumWidth(300)
        
        # フォント設定
        font = QFont("Consolas", 10)
        self.setFont(font)
        
        # モデル設定
        self.model = CompletionModel(self)
        self.setModel(self.model)
        
        # シグナル接続
        self.clicked.connect(self._on_item_clicked)
    
    def keyPressEvent(self, event: QKeyEvent):
        """キーイベント処理"""
        try:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                current_index = self.currentIndex()
                if current_index.isValid():
                    item = self.model.data(current_index, Qt.ItemDataRole.UserRole)
                    if item:
                        self.item_selected.emit(item)
                        self.hide()
                        return
            elif event.key() == Qt.Key.Key_Escape:
                self.hide()
                return
            
            super().keyPressEvent(event)
            
        except Exception as e:
            self.logger.error(f"キーイベント処理エラー: {e}")
    
    def _on_item_clicked(self, index: QModelIndex):
        """アイテムクリック時の処理"""
        try:
            item = self.model.data(index, Qt.ItemDataRole.UserRole)
            if item:
                self.item_selected.emit(item)
                self.hide()
                
        except Exception as e:
            self.logger.error(f"アイテムクリック処理エラー: {e}")
    
    def set_items(self, items: List[CompletionItem]):
        """アイテムを設定"""
        try:
            self.model.set_items(items)
            if items:
                self.setCurrentIndex(self.model.index(0, 0))
                
        except Exception as e:
            self.logger.error(f"アイテム設定エラー: {e}")
    
    def show_at_position(self, position: QPoint):
        """指定位置に表示"""
        try:
            self.move(position)
            self.show()
            self.raise_()
            self.activateWindow()
            
        except Exception as e:
            self.logger.error(f"位置表示エラー: {e}")


class PythonCompletionProvider:
    """Python補完プロバイダー"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._builtin_functions = self._get_builtin_functions()
        self._keywords = self._get_keywords()
        self._snippets = self._get_snippets()
    
    def _get_builtin_functions(self) -> List[CompletionItem]:
        """組み込み関数を取得"""
        try:
            builtins = [
                'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
                'callable', 'chr', 'classmethod', 'compile', 'complex', 'delattr',
                'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec', 'filter',
                'float', 'format', 'frozenset', 'getattr', 'globals', 'hasattr',
                'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance',
                'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max',
                'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord',
                'pow', 'print', 'property', 'range', 'repr', 'reversed', 'round',
                'set', 'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum',
                'super', 'tuple', 'type', 'vars', 'zip', '__import__'
            ]
            
            return [
                CompletionItem(
                    text=func,
                    completion_type=CompletionType.BUILTIN,
                    description=f"組み込み関数: {func}",
                    insert_text=f"{func}()"
                )
                for func in builtins
            ]
            
        except Exception as e:
            self.logger.error(f"組み込み関数取得エラー: {e}")
            return []
    
    def _get_keywords(self) -> List[CompletionItem]:
        """キーワードを取得"""
        try:
            keywords = [
                CompletionItem(
                    text=kw,
                    completion_type=CompletionType.KEYWORD,
                    description=f"Pythonキーワード: {kw}"
                )
                for kw in keyword.kwlist
            ]
            
            return keywords
            
        except Exception as e:
            self.logger.error(f"キーワード取得エラー: {e}")
            return []
    
    def _get_snippets(self) -> List[CompletionItem]:
        """スニペットを取得"""
        try:
            snippets = [
                CompletionItem(
                    text="if",
                    completion_type=CompletionType.SNIPPET,
                    description="if文",
                    insert_text="if ${1:condition}:\n    ${2:pass}"
                ),
                CompletionItem(
                    text="for",
                    completion_type=CompletionType.SNIPPET,
                    description="for文",
                    insert_text="for ${1:item} in ${2:iterable}:\n    ${3:pass}"
                ),
                CompletionItem(
                    text="while",
                    completion_type=CompletionType.SNIPPET,
                    description="while文",
                    insert_text="while ${1:condition}:\n    ${2:pass}"
                ),
                CompletionItem(
                    text="def",
                    completion_type=CompletionType.SNIPPET,
                    description="関数定義",
                    insert_text="def ${1:function_name}(${2:args}):\n    \"\"\"${3:docstring}\"\"\"\n    ${4:pass}"
                ),
                CompletionItem(
                    text="class",
                    completion_type=CompletionType.SNIPPET,
                    description="クラス定義",
                    insert_text="class ${1:ClassName}:\n    \"\"\"${2:docstring}\"\"\"\n    \n    def __init__(self${3:, args}):\n        ${4:pass}"
                ),
                CompletionItem(
                    text="try",
                    completion_type=CompletionType.SNIPPET,
                    description="try-except文",
                    insert_text="try:\n    ${1:pass}\nexcept ${2:Exception} as ${3:e}:\n    ${4:pass}"
                ),
                CompletionItem(
                    text="with",
                    completion_type=CompletionType.SNIPPET,
                    description="with文",
                    insert_text="with ${1:expression} as ${2:variable}:\n    ${3:pass}"
                )
            ]
            
            return snippets
            
        except Exception as e:
            self.logger.error(f"スニペット取得エラー: {e}")
            return []
    
    def get_completions(self, text: str, cursor_position: int, 
                       file_path: str = None) -> List[CompletionItem]:
        """補完候補を取得"""
        try:
            completions = []
            
            # 現在の単語を取得
            current_word = self._get_current_word(text, cursor_position)
            if not current_word:
                return []
            
            # キーワード補完
            for item in self._keywords:
                if item.text.startswith(current_word):
                    completions.append(item)
            
            # 組み込み関数補完
            for item in self._builtin_functions:
                if item.text.startswith(current_word):
                    completions.append(item)
            
            # スニペット補完
            for item in self._snippets:
                if item.text.startswith(current_word):
                    completions.append(item)
            
            # ファイル内の変数・関数・クラス補完
            if file_path:
                file_completions = self._get_file_completions(text, current_word)
                completions.extend(file_completions)
            
            # ソート
            completions.sort(key=lambda x: (x.sort_text, x.text))
            
            return completions
            
        except Exception as e:
            self.logger.error(f"補完取得エラー: {e}")
            return []
    
    def _get_current_word(self, text: str, cursor_position: int) -> str:
        """現在の単語を取得"""
        try:
            if cursor_position <= 0:
                return ""
            
            # カーソル位置から後ろに向かって単語の開始位置を探す
            start = cursor_position - 1
            while start >= 0 and (text[start].isalnum() or text[start] == '_'):
                start -= 1
            start += 1
            
            # カーソル位置から前に向かって単語の終了位置を探す
            end = cursor_position
            while end < len(text) and (text[end].isalnum() or text[end] == '_'):
                end += 1
            
            return text[start:cursor_position]
            
        except Exception as e:
            self.logger.error(f"現在単語取得エラー: {e}")
            return ""
    
    def _get_file_completions(self, text: str, current_word: str) -> List[CompletionItem]:
        """ファイル内の補完候補を取得"""
        try:
            completions = []
            
            # ASTを使用してファイル内の定義を解析
            try:
                tree = ast.parse(text)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if node.name.startswith(current_word):
                            completions.append(CompletionItem(
                                text=node.name,
                                completion_type=CompletionType.FUNCTION,
                                description=f"関数: {node.name}",
                                insert_text=f"{node.name}()"
                            ))
                    
                    elif isinstance(node, ast.ClassDef):
                        if node.name.startswith(current_word):
                            completions.append(CompletionItem(
                                text=node.name,
                                completion_type=CompletionType.CLASS,
                                description=f"クラス: {node.name}"
                            ))
                    
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                if target.id.startswith(current_word):
                                    completions.append(CompletionItem(
                                        text=target.id,
                                        completion_type=CompletionType.VARIABLE,
                                        description=f"変数: {target.id}"
                                    ))
            
            except SyntaxError:
                # 構文エラーの場合は正規表現で簡単な解析
                self._get_regex_completions(text, current_word, completions)
            
            return completions
            
        except Exception as e:
            self.logger.error(f"ファイル補完取得エラー: {e}")
            return []
    
    def _get_regex_completions(self, text: str, current_word: str, 
                              completions: List[CompletionItem]):
        """正規表現を使用した補完候補取得"""
        try:
            # 関数定義
            func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            for match in re.finditer(func_pattern, text):
                func_name = match.group(1)
                if func_name.startswith(current_word):
                    completions.append(CompletionItem(
                        text=func_name,
                        completion_type=CompletionType.FUNCTION,
                        description=f"関数: {func_name}",
                        insert_text=f"{func_name}()"
                    ))
            
            # クラス定義
            class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            for match in re.finditer(class_pattern, text):
                class_name = match.group(1)
                if class_name.startswith(current_word):
                    completions.append(CompletionItem(
                        text=class_name,
                        completion_type=CompletionType.CLASS,
                        description=f"クラス: {class_name}"
                    ))
            
            # 変数代入
            var_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*='
            for match in re.finditer(var_pattern, text):
                var_name = match.group(1)
                if var_name.startswith(current_word) and var_name not in keyword.kwlist:
                    completions.append(CompletionItem(
                        text=var_name,
                        completion_type=CompletionType.VARIABLE,
                        description=f"変数: {var_name}"
                    ))
            
        except Exception as e:
            self.logger.error(f"正規表現補完エラー: {e}")


class AutoCompleteManager(QObject):
    """オートコンプリートマネージャー"""
    
    def __init__(self, text_edit: QTextEdit, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.text_edit = text_edit
        self.completion_list = CompletionListView()
        self.completion_timer = QTimer()
        self.completion_timer.setSingleShot(True)
        self.completion_timer.timeout.connect(self._show_completions)
        
        # プロバイダー
        self.python_provider = PythonCompletionProvider()
        
        # 設定
        self.completion_delay = 300  # ミリ秒
        self.min_completion_length = 2
        self.auto_completion_enabled = True
        
        # シグナル接続
        self.completion_list.item_selected.connect(self._insert_completion)
        
        # テキストエディタにイベントフィルタを設定
        self.text_edit.installEventFilter(self)
    
    def eventFilter(self, obj, event) -> bool:
        """イベントフィルタ"""
        try:
            if obj == self.text_edit and event.type() == event.Type.KeyPress:
                return self._handle_key_press(event)
            
            return super().eventFilter(obj, event)
            
        except Exception as e:
            self.logger.error(f"イベントフィルタエラー: {e}")
            return False
    
    def _handle_key_press(self, event: QKeyEvent) -> bool:
        """キーイベント処理"""
        try:
            key = event.key()
            modifiers = event.modifiers()
            
            # 補完リストが表示されている場合
            if self.completion_list.isVisible():
                if key in [Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Return, 
                          Qt.Key.Key_Enter, Qt.Key.Key_Escape]:
                    # 補完リストにイベントを転送
                    self.completion_list.keyPressEvent(event)
                    return True
                elif key == Qt.Key.Key_Backspace:
                    # バックスペースの場合は補完を更新
                    self.completion_list.hide()
                    self._start_completion_timer()
                    return False
                elif event.text().isprintable():
                    # 印刷可能文字の場合は補完を更新
                    self._start_completion_timer()
                    return False
                else:
                    # その他のキーは補完を隠す
                    self.completion_list.hide()
                    return False
            
            # Ctrl+Spaceで手動補完
            if (key == Qt.Key.Key_Space and 
                modifiers == Qt.KeyboardModifier.ControlModifier):
                self._show_completions()
                return True
            
            # 自動補完のトリガー
            if self.auto_completion_enabled and event.text().isprintable():
                self._start_completion_timer()
            
            return False
            
        except Exception as e:
            self.logger.error(f"キーイベント処理エラー: {e}")
            return False
    
    def _start_completion_timer(self):
        """補完タイマーを開始"""
        try:
            self.completion_timer.stop()
            self.completion_timer.start(self.completion_delay)
            
        except Exception as e:
            self.logger.error(f"補完タイマー開始エラー: {e}")
    
    def _show_completions(self):
        """補完を表示"""
        try:
            cursor = self.text_edit.textCursor()
            text = self.text_edit.toPlainText()
            cursor_position = cursor.position()
            
            # 現在の単語を取得
            current_word = self.python_provider._get_current_word(text, cursor_position)
            
            # 最小長チェック
            if len(current_word) < self.min_completion_length:
                self.completion_list.hide()
                return
            
            # 補完候補を取得
            completions = self.python_provider.get_completions(
                text, cursor_position, getattr(self.text_edit, 'file_path', None)
            )
            
            if not completions:
                self.completion_list.hide()
                return
            
            # 補完リストを更新
            self.completion_list.set_items(completions)
            
            # 表示位置を計算
            cursor_rect = self.text_edit.cursorRect()
            global_pos = self.text_edit.mapToGlobal(cursor_rect.bottomLeft())
            
            # 画面内に収まるように調整
            screen_rect = QApplication.primaryScreen().geometry()
            if global_pos.y() + self.completion_list.height() > screen_rect.bottom():
                global_pos.setY(self.text_edit.mapToGlobal(cursor_rect.topLeft()).y() - 
                               self.completion_list.height())
            
            self.completion_list.show_at_position(global_pos)
            
        except Exception as e:
            self.logger.error(f"補完表示エラー: {e}")
    
    def _insert_completion(self, item: CompletionItem):
        """補完を挿入"""
        try:
            cursor = self.text_edit.textCursor()
            text = self.text_edit.toPlainText()
            cursor_position = cursor.position()
            
            # 現在の単語を取得
            current_word = self.python_provider._get_current_word(text, cursor_position)
            
            # 現在の単語を選択
            cursor.movePosition(QTextCursor.MoveOperation.Left, 
                              QTextCursor.MoveMode.KeepAnchor, len(current_word))
            
            # 補完テキストを挿入
            insert_text = item.insert_text
            
            # スニペット処理（簡易版）
            if "${" in insert_text:
                # プレースホルダーを削除
                insert_text = re.sub(r'\$\{\d+:([^}]*)\}', r'\1', insert_text)
                insert_text = re.sub(r'\$\{\d+\}', '', insert_text)
            
            cursor.insertText(insert_text)
            
            # カーソル位置を調整（関数の場合は括弧内に移動）
            if item.completion_type == CompletionType.FUNCTION and insert_text.endswith('()'):
                cursor.movePosition(QTextCursor.MoveOperation.Left, 
                                  QTextCursor.MoveMode.MoveAnchor, 1)
                self.text_edit.setTextCursor(cursor)
            
        except Exception as e:
            self.logger.error(f"補完挿入エラー: {e}")
    
    def set_completion_enabled(self, enabled: bool):
        """補完の有効/無効を設定"""
        try:
            self.auto_completion_enabled = enabled
            if not enabled:
                self.completion_list.hide()
                
        except Exception as e:
            self.logger.error(f"補完有効設定エラー: {e}")
    
    def set_completion_delay(self, delay: int):
        """補完遅延を設定"""
        try:
            self.completion_delay = max(0, delay)
            
        except Exception as e:
            self.logger.error(f"補完遅延設定エラー: {e}")
    
    def set_min_completion_length(self, length: int):
        """最小補完長を設定"""
        try:
            self.min_completion_length = max(1, length)
            
        except Exception as e:
            self.logger.error(f"最小補完長設定エラー: {e}")
