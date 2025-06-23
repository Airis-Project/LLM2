# src/ui/find_replace_dialog.py
"""
Find Replace Dialog - 検索・置換ダイアログ

このモジュールは、テキストエディタでの検索・置換機能を提供するダイアログを実装します。
通常検索、正規表現検索、大文字小文字の区別、単語単位検索などの機能を含みます。
"""

import re
from typing import Optional, List, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QPushButton, QCheckBox, QComboBox, QTextEdit,
    QGroupBox, QMessageBox, QFrame, QSplitter, QListWidget,
    QListWidgetItem, QTabWidget, QWidget,QTextDocument
)
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QIcon

from ..core.logger import get_logger

logger = get_logger(__name__)


class SearchResult:
    """検索結果を表すクラス"""
    
    def __init__(self, start: int, end: int, text: str, line_number: int):
        self.start = start
        self.end = end
        self.text = text
        self.line_number = line_number


class FindReplaceDialog(QDialog):
    """
    検索・置換ダイアログクラス
    
    テキストエディタでの高度な検索・置換機能を提供します。
    通常検索、正規表現、大文字小文字の区別、単語単位検索、
    すべて検索、すべて置換などの機能を含みます。
    """
    
    # シグナル定義
    find_requested = pyqtSignal(str, dict)  # 検索要求
    replace_requested = pyqtSignal(str, str, dict)  # 置換要求
    replace_all_requested = pyqtSignal(str, str, dict)  # すべて置換要求
    
    def __init__(self, parent: Optional[QWidget] = None, text_editor: Optional[QTextEdit] = None):
        """
        FindReplaceDialogを初期化
        
        Args:
            parent: 親ウィジェット
            text_editor: 対象のテキストエディタ
        """
        super().__init__(parent)
        
        self.text_editor = text_editor
        self.search_results: List[SearchResult] = []
        self.current_result_index = -1
        self.last_search_text = ""
        
        # 検索履歴
        self.search_history: List[str] = []
        self.replace_history: List[str] = []
        self.max_history = 20
        
        self._setup_ui()
        self._connect_signals()
        self._load_settings()
        
        logger.debug("FindReplaceDialog initialized")
    
    def _setup_ui(self) -> None:
        """UIコンポーネントのセットアップ"""
        try:
            self.setWindowTitle("検索・置換")
            self.setFixedSize(600, 500)
            self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
            
            # メインレイアウト
            layout = QVBoxLayout()
            layout.setSpacing(10)
            layout.setContentsMargins(15, 15, 15, 15)
            
            # タブウィジェット
            tab_widget = QTabWidget()
            
            # 検索タブ
            find_tab = self._create_find_tab()
            tab_widget.addTab(find_tab, "検索")
            
            # 置換タブ
            replace_tab = self._create_replace_tab()
            tab_widget.addTab(replace_tab, "置換")
            
            # 結果タブ
            results_tab = self._create_results_tab()
            tab_widget.addTab(results_tab, "結果")
            
            layout.addWidget(tab_widget)
            
            # ボタン部分
            button_layout = self._create_buttons()
            layout.addLayout(button_layout)
            
            self.setLayout(layout)
            
        except Exception as e:
            logger.error(f"UI setup failed: {e}")
            raise
    
    def _create_find_tab(self) -> QWidget:
        """検索タブの作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 検索フィールド
        search_group = QGroupBox("検索")
        search_layout = QGridLayout()
        
        # 検索テキスト
        search_layout.addWidget(QLabel("検索文字列:"), 0, 0)
        self.find_text = QComboBox()
        self.find_text.setEditable(True)
        self.find_text.setMinimumWidth(300)
        search_layout.addWidget(self.find_text, 0, 1)
        
        # 検索ボタン
        self.find_button = QPushButton("検索")
        self.find_button.setDefault(True)
        search_layout.addWidget(self.find_button, 0, 2)
        
        # 前を検索ボタン
        self.find_prev_button = QPushButton("前を検索")
        search_layout.addWidget(self.find_prev_button, 1, 1)
        
        # 次を検索ボタン
        self.find_next_button = QPushButton("次を検索")
        search_layout.addWidget(self.find_next_button, 1, 2)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # オプション
        options_group = QGroupBox("オプション")
        options_layout = QVBoxLayout()
        
        # チェックボックス
        self.case_sensitive = QCheckBox("大文字小文字を区別する")
        options_layout.addWidget(self.case_sensitive)
        
        self.whole_words = QCheckBox("単語単位で検索")
        options_layout.addWidget(self.whole_words)
        
        self.regex_search = QCheckBox("正規表現を使用")
        options_layout.addWidget(self.regex_search)
        
        self.wrap_search = QCheckBox("検索をループする")
        self.wrap_search.setChecked(True)
        options_layout.addWidget(self.wrap_search)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 検索範囲
        scope_group = QGroupBox("検索範囲")
        scope_layout = QVBoxLayout()
        
        self.search_all = QCheckBox("ドキュメント全体")
        self.search_all.setChecked(True)
        scope_layout.addWidget(self.search_all)
        
        self.search_selection = QCheckBox("選択範囲のみ")
        scope_layout.addWidget(self.search_selection)
        
        scope_group.setLayout(scope_layout)
        layout.addWidget(scope_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_replace_tab(self) -> QWidget:
        """置換タブの作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 置換フィールド
        replace_group = QGroupBox("置換")
        replace_layout = QGridLayout()
        
        # 検索テキスト
        replace_layout.addWidget(QLabel("検索文字列:"), 0, 0)
        self.replace_find_text = QComboBox()
        self.replace_find_text.setEditable(True)
        self.replace_find_text.setMinimumWidth(300)
        replace_layout.addWidget(self.replace_find_text, 0, 1)
        
        # 置換テキスト
        replace_layout.addWidget(QLabel("置換文字列:"), 1, 0)
        self.replace_text = QComboBox()
        self.replace_text.setEditable(True)
        self.replace_text.setMinimumWidth(300)
        replace_layout.addWidget(self.replace_text, 1, 1)
        
        # ボタン
        self.replace_button = QPushButton("置換")
        replace_layout.addWidget(self.replace_button, 0, 2)
        
        self.replace_all_button = QPushButton("すべて置換")
        replace_layout.addWidget(self.replace_all_button, 1, 2)
        
        replace_group.setLayout(replace_layout)
        layout.addWidget(replace_group)
        
        # 置換オプション（検索タブと同じオプションを参照）
        options_group = QGroupBox("オプション")
        options_layout = QVBoxLayout()
        
        self.replace_case_sensitive = QCheckBox("大文字小文字を区別する")
        options_layout.addWidget(self.replace_case_sensitive)
        
        self.replace_whole_words = QCheckBox("単語単位で検索")
        options_layout.addWidget(self.replace_whole_words)
        
        self.replace_regex = QCheckBox("正規表現を使用")
        options_layout.addWidget(self.replace_regex)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # プレビュー
        preview_group = QGroupBox("プレビュー")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(100)
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Courier", 9))
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_results_tab(self) -> QWidget:
        """結果タブの作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 結果情報
        info_layout = QHBoxLayout()
        self.results_info = QLabel("検索結果: 0件")
        self.results_info.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addWidget(self.results_info)
        info_layout.addStretch()
        
        # クリアボタン
        clear_button = QPushButton("クリア")
        clear_button.clicked.connect(self._clear_results)
        info_layout.addWidget(clear_button)
        
        layout.addLayout(info_layout)
        
        # 結果リスト
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self._goto_result)
        layout.addWidget(self.results_list)
        
        widget.setLayout(layout)
        return widget
    
    def _create_buttons(self) -> QHBoxLayout:
        """ボタン部分の作成"""
        button_layout = QHBoxLayout()
        
        # 全て検索ボタン
        self.find_all_button = QPushButton("すべて検索")
        button_layout.addWidget(self.find_all_button)
        
        button_layout.addStretch()
        
        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        return button_layout
    
    def _connect_signals(self) -> None:
        """シグナルの接続"""
        try:
            # 検索ボタン
            self.find_button.clicked.connect(self._find_text)
            self.find_prev_button.clicked.connect(self._find_previous)
            self.find_next_button.clicked.connect(self._find_next)
            self.find_all_button.clicked.connect(self._find_all)
            
            # 置換ボタン
            self.replace_button.clicked.connect(self._replace_text)
            self.replace_all_button.clicked.connect(self._replace_all)
            
            # テキスト変更
            self.find_text.lineEdit().textChanged.connect(self._on_find_text_changed)
            self.replace_find_text.lineEdit().textChanged.connect(self._on_replace_find_text_changed)
            self.replace_text.lineEdit().textChanged.connect(self._update_preview)
            
            # オプション変更
            self.regex_search.toggled.connect(self._validate_regex)
            self.replace_regex.toggled.connect(self._validate_replace_regex)
            
            # Enterキーでの検索
            self.find_text.lineEdit().returnPressed.connect(self._find_text)
            self.replace_find_text.lineEdit().returnPressed.connect(self._replace_text)
            
        except Exception as e:
            logger.error(f"Signal connection failed: {e}")
            raise
    
    def _find_text(self) -> None:
        """テキスト検索"""
        try:
            search_text = self.find_text.currentText().strip()
            if not search_text:
                return
            
            # 検索オプション
            options = self._get_search_options()
            
            # 検索実行
            if self.text_editor:
                self._perform_search(search_text, options)
            
            # 履歴に追加
            self._add_to_history(self.find_text, search_text)
            
            logger.debug(f"Text search: {search_text}")
            
        except Exception as e:
            logger.error(f"Find text failed: {e}")
            self._show_error("検索エラー", f"検索中にエラーが発生しました: {e}")
    
    def _find_previous(self) -> None:
        """前を検索"""
        if self.search_results and self.current_result_index > 0:
            self.current_result_index -= 1
            self._highlight_current_result()
    
    def _find_next(self) -> None:
        """次を検索"""
        if self.search_results and self.current_result_index < len(self.search_results) - 1:
            self.current_result_index += 1
            self._highlight_current_result()
    
    def _find_all(self) -> None:
        """すべて検索"""
        try:
            search_text = self.find_text.currentText().strip()
            if not search_text:
                return
            
            options = self._get_search_options()
            
            if self.text_editor:
                results = self._find_all_matches(search_text, options)
                self._display_all_results(results, search_text)
            
            logger.debug(f"Find all: {search_text}, found {len(results)} matches")
            
        except Exception as e:
            logger.error(f"Find all failed: {e}")
            self._show_error("検索エラー", f"全体検索中にエラーが発生しました: {e}")
    
    def _replace_text(self) -> None:
        """テキスト置換"""
        try:
            find_text = self.replace_find_text.currentText().strip()
            replace_text = self.replace_text.currentText().strip()
            
            if not find_text:
                return
            
            options = self._get_replace_options()
            
            if self.text_editor:
                success = self._perform_replace(find_text, replace_text, options)
                if success:
                    # 履歴に追加
                    self._add_to_history(self.replace_find_text, find_text)
                    self._add_to_history(self.replace_text, replace_text)
            
            logger.debug(f"Text replace: {find_text} -> {replace_text}")
            
        except Exception as e:
            logger.error(f"Replace text failed: {e}")
            self._show_error("置換エラー", f"置換中にエラーが発生しました: {e}")
    
    def _replace_all(self) -> None:
        """すべて置換"""
        try:
            find_text = self.replace_find_text.currentText().strip()
            replace_text = self.replace_text.currentText().strip()
            
            if not find_text:
                return
            
            # 確認ダイアログ
            reply = QMessageBox.question(
                self,
                "確認",
                f"すべての '{find_text}' を '{replace_text}' に置換しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                options = self._get_replace_options()
                
                if self.text_editor:
                    count = self._perform_replace_all(find_text, replace_text, options)
                    QMessageBox.information(
                        self,
                        "置換完了",
                        f"{count}件の置換を実行しました。"
                    )
                    
                    # 履歴に追加
                    self._add_to_history(self.replace_find_text, find_text)
                    self._add_to_history(self.replace_text, replace_text)
            
            logger.debug(f"Replace all: {find_text} -> {replace_text}")
            
        except Exception as e:
            logger.error(f"Replace all failed: {e}")
            self._show_error("置換エラー", f"全体置換中にエラーが発生しました: {e}")
    
    def _perform_search(self, search_text: str, options: dict) -> bool:
        """検索の実行"""
        if not self.text_editor:
            return False
        
        cursor = self.text_editor.textCursor()
        document = self.text_editor.document()
        
        # 検索フラグの設定
        flags = QTextDocument.FindFlag(0)
        if options['case_sensitive']:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if options['whole_words']:
            flags |= QTextDocument.FindFlag.FindWholeWords
        
        # 正規表現検索
        if options['regex']:
            try:
                regex = QRegularExpression(search_text)
                if not regex.isValid():
                    self._show_error("正規表現エラー", "無効な正規表現です。")
                    return False
                
                found_cursor = document.find(regex, cursor, flags)
            except Exception as e:
                self._show_error("正規表現エラー", f"正規表現エラー: {e}")
                return False
        else:
            found_cursor = document.find(search_text, cursor, flags)
        
        # 検索結果の処理
        if not found_cursor.isNull():
            self.text_editor.setTextCursor(found_cursor)
            return True
        elif options['wrap'] and cursor.position() > 0:
            # ラップ検索
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.text_editor.setTextCursor(cursor)
            return self._perform_search(search_text, {**options, 'wrap': False})
        else:
            QMessageBox.information(self, "検索", "検索文字列が見つかりませんでした。")
            return False
    
    def _find_all_matches(self, search_text: str, options: dict) -> List[SearchResult]:
        """すべてのマッチを検索"""
        results = []
        
        if not self.text_editor:
            return results
        
        document = self.text_editor.document()
        text = document.toPlainText()
        
        try:
            if options['regex']:
                pattern = search_text
                if not options['case_sensitive']:
                    pattern = f"(?i){pattern}"
                
                matches = re.finditer(pattern, text)
                for match in matches:
                    line_number = text[:match.start()].count('\n') + 1
                    results.append(SearchResult(
                        match.start(),
                        match.end(),
                        match.group(),
                        line_number
                    ))
            else:
                # 通常検索
                search_flags = 0 if options['case_sensitive'] else re.IGNORECASE
                
                if options['whole_words']:
                    pattern = r'\b' + re.escape(search_text) + r'\b'
                else:
                    pattern = re.escape(search_text)
                
                matches = re.finditer(pattern, text, search_flags)
                for match in matches:
                    line_number = text[:match.start()].count('\n') + 1
                    results.append(SearchResult(
                        match.start(),
                        match.end(),
                        match.group(),
                        line_number
                    ))
        
        except Exception as e:
            logger.error(f"Find all matches failed: {e}")
            raise
        
        return results
    
    def _perform_replace(self, find_text: str, replace_text: str, options: dict) -> bool:
        """置換の実行"""
        # まず検索を実行
        if self._perform_search(find_text, options):
            cursor = self.text_editor.textCursor()
            if cursor.hasSelection():
                cursor.insertText(replace_text)
                return True
        return False
    
    def _perform_replace_all(self, find_text: str, replace_text: str, options: dict) -> int:
        """すべて置換の実行"""
        if not self.text_editor:
            return 0
        
        results = self._find_all_matches(find_text, options)
        
        if not results:
            return 0
        
        # 後ろから置換（位置がずれないように）
        cursor = self.text_editor.textCursor()
        cursor.beginEditBlock()
        
        try:
            for result in reversed(results):
                cursor.setPosition(result.start)
                cursor.setPosition(result.end, QTextCursor.MoveMode.KeepAnchor)
                cursor.insertText(replace_text)
        finally:
            cursor.endEditBlock()
        
        return len(results)
    
    def _display_all_results(self, results: List[SearchResult], search_text: str) -> None:
        """すべての結果を表示"""
        self.search_results = results
        self.results_list.clear()
        
        self.results_info.setText(f"検索結果: {len(results)}件")
        
        for i, result in enumerate(results):
            # 行のテキストを取得
            lines = self.text_editor.toPlainText().split('\n')
            if result.line_number <= len(lines):
                line_text = lines[result.line_number - 1].strip()
                item_text = f"行 {result.line_number}: {line_text}"
            else:
                item_text = f"行 {result.line_number}: {result.text}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.results_list.addItem(item)
    
    def _goto_result(self, item: QListWidgetItem) -> None:
        """結果の位置に移動"""
        index = item.data(Qt.ItemDataRole.UserRole)
        if 0 <= index < len(self.search_results):
            result = self.search_results[index]
            
            cursor = self.text_editor.textCursor()
            cursor.setPosition(result.start)
            cursor.setPosition(result.end, QTextCursor.MoveMode.KeepAnchor)
            self.text_editor.setTextCursor(cursor)
            self.text_editor.setFocus()
    
    def _highlight_current_result(self) -> None:
        """現在の結果をハイライト"""
        if (0 <= self.current_result_index < len(self.search_results) and 
            self.text_editor):
            
            result = self.search_results[self.current_result_index]
            cursor = self.text_editor.textCursor()
            cursor.setPosition(result.start)
            cursor.setPosition(result.end, QTextCursor.MoveMode.KeepAnchor)
            self.text_editor.setTextCursor(cursor)
    
    def _get_search_options(self) -> dict:
        """検索オプションを取得"""
        return {
            'case_sensitive': self.case_sensitive.isChecked(),
            'whole_words': self.whole_words.isChecked(),
            'regex': self.regex_search.isChecked(),
            'wrap': self.wrap_search.isChecked(),
            'selection_only': self.search_selection.isChecked()
        }
    
    def _get_replace_options(self) -> dict:
        """置換オプションを取得"""
        return {
            'case_sensitive': self.replace_case_sensitive.isChecked(),
            'whole_words': self.replace_whole_words.isChecked(),
            'regex': self.replace_regex.isChecked(),
            'wrap': True,
            'selection_only': False
        }
    
    def _add_to_history(self, combo: QComboBox, text: str) -> None:
        """履歴に追加"""
        if text and text not in [combo.itemText(i) for i in range(combo.count())]:
            combo.insertItem(0, text)
            if combo.count() > self.max_history:
                combo.removeItem(combo.count() - 1)
    
    def _validate_regex(self) -> None:
        """正規表現の検証"""
        if self.regex_search.isChecked():
            text = self.find_text.currentText()
            if text:
                try:
                    re.compile(text)
                    self.find_text.setStyleSheet("")
                except re.error:
                    self.find_text.setStyleSheet("border: 2px solid red;")
    
    def _validate_replace_regex(self) -> None:
        """置換正規表現の検証"""
        if self.replace_regex.isChecked():
            text = self.replace_find_text.currentText()
            if text:
                try:
                    re.compile(text)
                    self.replace_find_text.setStyleSheet("")
                except re.error:
                    self.replace_find_text.setStyleSheet("border: 2px solid red;")
    
    def _update_preview(self) -> None:
        """プレビューの更新"""
        find_text = self.replace_find_text.currentText()
        replace_text = self.replace_text.currentText()
        
        if find_text and self.text_editor:
            cursor = self.text_editor.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText()
                preview = selected_text.replace(find_text, replace_text)
                self.preview_text.setPlainText(f"置換前: {selected_text}\n置換後: {preview}")
    
    def _on_find_text_changed(self) -> None:
        """検索テキスト変更時の処理"""
        self._validate_regex()
    
    def _on_replace_find_text_changed(self) -> None:
        """置換検索テキスト変更時の処理"""
        self._validate_replace_regex()
        self._update_preview()
    
    def _clear_results(self) -> None:
        """結果をクリア"""
        self.search_results.clear()
        self.results_list.clear()
        self.results_info.setText("検索結果: 0件")
        self.current_result_index = -1
    
    def _load_settings(self) -> None:
        """設定の読み込み"""
        # TODO: 設定ファイルから履歴や設定を読み込み
        pass
    
    def _save_settings(self) -> None:
        """設定の保存"""
        # TODO: 履歴や設定を設定ファイルに保存
        pass
    
    def _show_error(self, title: str, message: str) -> None:
        """エラーメッセージの表示"""
        QMessageBox.critical(self, title, message)
    
    def closeEvent(self, event) -> None:
        """ダイアログクローズイベント"""
        self._save_settings()
        super().closeEvent(event)
    
    def set_find_text(self, text: str) -> None:
        """検索テキストを設定"""
        self.find_text.setCurrentText(text)
        self.replace_find_text.setCurrentText(text)
    
    def set_text_editor(self, editor: QTextEdit) -> None:
        """テキストエディタを設定"""
        self.text_editor = editor

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QPushButton
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Find Replace Dialog Test")
            self.setGeometry(100, 100, 800, 600)
            
            # 中央ウィジェット
            central_widget = QWidget()
            layout = QVBoxLayout()
            
            # テストボタン
            test_button = QPushButton("検索・置換ダイアログを開く")
            test_button.clicked.connect(self.open_find_replace)
            layout.addWidget(test_button)
            
            # テキストエディタ
            self.text_editor = QTextEdit()
            self.text_editor.setPlainText("""
これはテスト用のテキストです。
検索・置換機能をテストするための
サンプルテキストが含まれています。

Python プログラミング言語は
非常に人気があります。
python は学習しやすく、
Python の文法は直感的です。

正規表現のテスト:
- メールアドレス: test@example.com
- 電話番号: 03-1234-5678
- URL: https://www.example.com

繰り返しテキスト:
テスト テスト テスト
test test test
TEST TEST TEST
            """.strip())
            layout.addWidget(self.text_editor)
            
            central_widget.setLayout(layout)
            self.setCentralWidget(central_widget)
        
        def open_find_replace(self):
            dialog = FindReplaceDialog(self, self.text_editor)
            dialog.show()
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
