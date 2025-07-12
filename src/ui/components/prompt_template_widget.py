"""
プロンプトテンプレートウィジェットモジュール
PyQt6を使用したプロンプトテンプレート管理コンポーネント
"""

import sys
import json
import os
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
        QPushButton, QComboBox, QLabel, QGroupBox, QListWidget,
        QListWidgetItem, QSplitter, QTabWidget, QFormLayout,
        QMessageBox, QFileDialog, QInputDialog, QMenu, QToolBar,
        QScrollArea, QFrame, QCheckBox, QSpinBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QTimer
    from PyQt6.QtGui import QFont, QAction, QIcon, QTextCursor
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

from ...core.logger import get_logger
from ...core.config_manager import get_config

class PromptTemplate(QWidget):
    """プロンプトテンプレートウィジェット"""
    
    # シグナル定義
    template_selected = pyqtSignal(dict)  # テンプレートが選択された時
    template_applied = pyqtSignal(str)  # テンプレートが適用された時
    template_saved = pyqtSignal(dict)  # テンプレートが保存された時
    template_deleted = pyqtSignal(str)  # テンプレートが削除された時
    
    def __init__(self, parent=None):
        """
        初期化
        
        Args:
            parent: 親ウィジェット
        """
        if not PYQT6_AVAILABLE:
            raise ImportError("PyQt6が利用できません")
        
        super().__init__(parent)
        
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        
        # テンプレートデータ
        self.templates = {}
        self.current_template = None
        self.template_file = Path(self.config.get('paths.templates', 'templates/prompts.json'))
        
        # UI要素
        self.template_list = None
        self.template_editor = None
        self.name_edit = None
        self.description_edit = None
        self.category_combo = None
        self.tags_edit = None
        self.variables_list = None
        self.preview_text = None
        
        # 変数置換用
        self.variable_values = {}
        
        self._setup_ui()
        self._load_templates()
        
        self.logger.debug("PromptTemplate初期化完了")
    
    def _setup_ui(self):
        """UIを設定"""
        try:
            main_layout = QHBoxLayout(self)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # スプリッター
            splitter = QSplitter(Qt.Orientation.Horizontal)
            main_layout.addWidget(splitter)
            
            # 左側: テンプレート一覧
            left_widget = self._create_template_list_widget()
            splitter.addWidget(left_widget)
            
            # 右側: テンプレート編集
            right_widget = self._create_template_editor_widget()
            splitter.addWidget(right_widget)
            
            # スプリッターの比率設定
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 2)
            
        except Exception as e:
            self.logger.error(f"UI設定エラー: {e}")
            raise
    
    def _create_template_list_widget(self) -> QWidget:
        """テンプレート一覧ウィジェットを作成"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(8)
            
            # タイトル
            title_label = QLabel("プロンプトテンプレート")
            title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            layout.addWidget(title_label)
            
            # 検索・フィルター
            search_layout = QHBoxLayout()
            
            self.search_edit = QLineEdit()
            self.search_edit.setPlaceholderText("検索...")
            self.search_edit.textChanged.connect(self._filter_templates)
            search_layout.addWidget(self.search_edit)
            
            self.category_filter = QComboBox()
            self.category_filter.addItem("全て")
            self.category_filter.currentTextChanged.connect(self._filter_templates)
            search_layout.addWidget(self.category_filter)
            
            layout.addLayout(search_layout)
            
            # テンプレート一覧
            self.template_list = QListWidget()
            self.template_list.itemClicked.connect(self._on_template_selected)
            self.template_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.template_list.customContextMenuRequested.connect(self._show_template_context_menu)
            layout.addWidget(self.template_list)
            
            # ボタン
            button_layout = QHBoxLayout()
            
            new_button = QPushButton("新規")
            new_button.clicked.connect(self._create_new_template)
            button_layout.addWidget(new_button)
            
            import_button = QPushButton("インポート")
            import_button.clicked.connect(self._import_templates)
            button_layout.addWidget(import_button)
            
            export_button = QPushButton("エクスポート")
            export_button.clicked.connect(self._export_templates)
            button_layout.addWidget(export_button)
            
            layout.addLayout(button_layout)
            
            return widget
            
        except Exception as e:
            self.logger.error(f"テンプレート一覧ウィジェット作成エラー: {e}")
            raise
    
    def _create_template_editor_widget(self) -> QWidget:
        """テンプレート編集ウィジェットを作成"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(8)
            
            # タブウィジェット
            tab_widget = QTabWidget()
            layout.addWidget(tab_widget)
            
            # 編集タブ
            edit_tab = self._create_edit_tab()
            tab_widget.addTab(edit_tab, "編集")
            
            # プレビュータブ
            preview_tab = self._create_preview_tab()
            tab_widget.addTab(preview_tab, "プレビュー")
            
            # 変数タブ
            variables_tab = self._create_variables_tab()
            tab_widget.addTab(variables_tab, "変数")
            
            # ボタン
            button_layout = QHBoxLayout()
            
            save_button = QPushButton("保存")
            save_button.clicked.connect(self._save_current_template)
            button_layout.addWidget(save_button)
            
            apply_button = QPushButton("適用")
            apply_button.clicked.connect(self._apply_current_template)
            button_layout.addWidget(apply_button)
            
            delete_button = QPushButton("削除")
            delete_button.clicked.connect(self._delete_current_template)
            button_layout.addWidget(delete_button)
            
            button_layout.addStretch()
            
            layout.addLayout(button_layout)
            
            return widget
            
        except Exception as e:
            self.logger.error(f"テンプレート編集ウィジェット作成エラー: {e}")
            raise
    
    def _create_edit_tab(self) -> QWidget:
        """編集タブを作成"""
        try:
            tab = QWidget()
            layout = QFormLayout(tab)
            layout.setSpacing(10)
            
            # 名前
            self.name_edit = QLineEdit()
            self.name_edit.setPlaceholderText("テンプレート名")
            self.name_edit.textChanged.connect(self._on_template_modified)
            layout.addRow("名前:", self.name_edit)
            
            # カテゴリ
            self.category_combo = QComboBox()
            self.category_combo.setEditable(True)
            self.category_combo.addItems(["一般", "コーディング", "文章作成", "分析", "翻訳", "その他"])
            self.category_combo.currentTextChanged.connect(self._on_template_modified)
            layout.addRow("カテゴリ:", self.category_combo)
            
            # 説明
            self.description_edit = QTextEdit()
            self.description_edit.setMaximumHeight(80)
            self.description_edit.setPlaceholderText("テンプレートの説明")
            self.description_edit.textChanged.connect(self._on_template_modified)
            layout.addRow("説明:", self.description_edit)
            
            # タグ
            self.tags_edit = QLineEdit()
            self.tags_edit.setPlaceholderText("タグ (カンマ区切り)")
            self.tags_edit.textChanged.connect(self._on_template_modified)
            layout.addRow("タグ:", self.tags_edit)
            
            # プロンプトテンプレート
            template_label = QLabel("プロンプトテンプレート:")
            layout.addRow(template_label)
            
            self.template_editor = QTextEdit()
            self.template_editor.setMinimumHeight(200)
            self.template_editor.setPlaceholderText(
                "プロンプトテンプレートを入力してください。\n"
                "変数は {{変数名}} の形式で記述できます。\n"
                "例: こんにちは、{{name}}さん。{{task}}を実行してください。"
            )
            self.template_editor.textChanged.connect(self._on_template_modified)
            layout.addRow(self.template_editor)
            
            return tab
            
        except Exception as e:
            self.logger.error(f"編集タブ作成エラー: {e}")
            raise
    
    def _create_preview_tab(self) -> QWidget:
        """プレビュータブを作成"""
        try:
            tab = QWidget()
            layout = QVBoxLayout(tab)
            layout.setSpacing(10)
            
            # 更新ボタン
            update_button = QPushButton("プレビュー更新")
            update_button.clicked.connect(self._update_preview)
            layout.addWidget(update_button)
            
            # プレビューテキスト
            self.preview_text = QTextEdit()
            self.preview_text.setReadOnly(True)
            self.preview_text.setFont(QFont("Consolas", 10))
            layout.addWidget(self.preview_text)
            
            return tab
            
        except Exception as e:
            self.logger.error(f"プレビュータブ作成エラー: {e}")
            raise
    
    def _create_variables_tab(self) -> QWidget:
        """変数タブを作成"""
        try:
            tab = QWidget()
            layout = QVBoxLayout(tab)
            layout.setSpacing(10)
            
            # 説明
            info_label = QLabel("テンプレート内の変数に値を設定してプレビューを確認できます。")
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            # 変数一覧
            self.variables_list = QListWidget()
            layout.addWidget(self.variables_list)
            
            # 変数値設定ボタン
            set_value_button = QPushButton("変数値を設定")
            set_value_button.clicked.connect(self._set_variable_value)
            layout.addWidget(set_value_button)
            
            # 変数をクリア
            clear_button = QPushButton("変数値をクリア")
            clear_button.clicked.connect(self._clear_variable_values)
            layout.addWidget(clear_button)
            
            return tab
            
        except Exception as e:
            self.logger.error(f"変数タブ作成エラー: {e}")
            raise
    
    def _load_templates(self):
        """テンプレートを読み込み"""
        try:
            if self.template_file.exists():
                with open(self.template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.templates = data.get('templates', {})
            else:
                # デフォルトテンプレートを作成
                self.templates = self._get_default_templates()
                self._save_templates()
            
            self._update_template_list()
            self._update_category_filter()
            
            self.logger.debug(f"{len(self.templates)}個のテンプレートを読み込みました")
            
        except Exception as e:
            self.logger.error(f"テンプレート読み込みエラー: {e}")
            self.templates = self._get_default_templates()
    
    def _save_templates(self):
        """テンプレートを保存"""
        try:
            # ディレクトリを作成
            self.template_file.parent.mkdir(parents=True, exist_ok=True)
            
            # データを保存
            data = {
                'templates': self.templates,
                'version': '1.0',
                'updated': datetime.now().isoformat()
            }
            
            with open(self.template_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug("テンプレートを保存しました")
            
        except Exception as e:
            self.logger.error(f"テンプレート保存エラー: {e}")
    
    def _get_default_templates(self) -> Dict[str, Dict]:
        """デフォルトテンプレートを取得"""
        return {
            "basic_chat": {
                "name": "基本チャット",
                "category": "一般",
                "description": "基本的なチャット用テンプレート",
                "template": "{{user_input}}",
                "tags": ["基本", "チャット"],
                "variables": ["user_input"],
                "created": datetime.now().isoformat()
            },
            "code_review": {
                "name": "コードレビュー",
                "category": "コーディング",
                "description": "コードレビュー用テンプレート",
                "template": "以下のコードをレビューしてください。改善点や問題点があれば指摘してください。\n\n```{{language}}\n{{code}}\n```",
                "tags": ["コード", "レビュー", "プログラミング"],
                "variables": ["language", "code"],
                "created": datetime.now().isoformat()
            },
            "translation": {
                "name": "翻訳",
                "category": "翻訳",
                "description": "翻訳用テンプレート",
                "template": "以下の文章を{{target_language}}に翻訳してください。\n\n{{text}}",
                "tags": ["翻訳", "言語"],
                "variables": ["target_language", "text"],
                "created": datetime.now().isoformat()
            },
            "summarize": {
                "name": "要約",
                "category": "分析",
                "description": "文章要約用テンプレート",
                "template": "以下の文章を{{length}}で要約してください。\n\n{{text}}",
                "tags": ["要約", "分析"],
                "variables": ["length", "text"],
                "created": datetime.now().isoformat()
                    },
            "explain_concept": {
                "name": "概念説明",
                "category": "一般",
                "description": "概念や用語を説明するテンプレート",
                "template": "{{concept}}について、{{level}}レベルで分かりやすく説明してください。具体例も含めて教えてください。",
                "tags": ["説明", "教育", "概念"],
                "variables": ["concept", "level"],
                "created": datetime.now().isoformat()
            },
            "creative_writing": {
                "name": "創作文章",
                "category": "文章作成",
                "description": "創作文章作成用テンプレート",
                "template": "{{genre}}の{{length}}の物語を書いてください。テーマは「{{theme}}」で、主人公は{{character}}です。",
                "tags": ["創作", "文章", "物語"],
                "variables": ["genre", "length", "theme", "character"],
                "created": datetime.now().isoformat()
            }
        }
    
    def _update_template_list(self):
        """テンプレート一覧を更新"""
        try:
            self.template_list.clear()
            
            search_text = self.search_edit.text().lower() if hasattr(self, 'search_edit') else ""
            category_filter = self.category_filter.currentText() if hasattr(self, 'category_filter') else "全て"
            
            for template_id, template in self.templates.items():
                # フィルター適用
                if search_text and search_text not in template.get('name', '').lower():
                    continue
                
                if category_filter != "全て" and template.get('category', '') != category_filter:
                    continue
                
                # リストアイテムを作成
                item = QListWidgetItem()
                item.setText(template.get('name', template_id))
                item.setData(Qt.ItemDataRole.UserRole, template_id)
                
                # ツールチップを設定
                tooltip = f"名前: {template.get('name', '')}\n"
                tooltip += f"カテゴリ: {template.get('category', '')}\n"
                tooltip += f"説明: {template.get('description', '')}"
                item.setToolTip(tooltip)
                
                self.template_list.addItem(item)
            
        except Exception as e:
            self.logger.error(f"テンプレート一覧更新エラー: {e}")
    
    def _update_category_filter(self):
        """カテゴリフィルターを更新"""
        try:
            if not hasattr(self, 'category_filter'):
                return
            
            current_text = self.category_filter.currentText()
            self.category_filter.clear()
            self.category_filter.addItem("全て")
            
            # 使用されているカテゴリを収集
            categories = set()
            for template in self.templates.values():
                category = template.get('category', '')
                if category:
                    categories.add(category)
            
            # カテゴリを追加
            for category in sorted(categories):
                self.category_filter.addItem(category)
            
            # 以前の選択を復元
            index = self.category_filter.findText(current_text)
            if index >= 0:
                self.category_filter.setCurrentIndex(index)
            
        except Exception as e:
            self.logger.error(f"カテゴリフィルター更新エラー: {e}")
    
    def _filter_templates(self):
        """テンプレートをフィルター"""
        try:
            self._update_template_list()
            
        except Exception as e:
            self.logger.error(f"テンプレートフィルターエラー: {e}")
    
    def _on_template_selected(self, item: QListWidgetItem):
        """テンプレート選択時の処理"""
        try:
            template_id = item.data(Qt.ItemDataRole.UserRole)
            if template_id in self.templates:
                self.current_template = template_id
                self._load_template_to_editor(self.templates[template_id])
                self.template_selected.emit(self.templates[template_id])
            
        except Exception as e:
            self.logger.error(f"テンプレート選択エラー: {e}")
    
    def _load_template_to_editor(self, template: Dict):
        """テンプレートをエディターに読み込み"""
        try:
            # 基本情報
            self.name_edit.setText(template.get('name', ''))
            self.description_edit.setPlainText(template.get('description', ''))
            
            # カテゴリ
            category = template.get('category', '')
            index = self.category_combo.findText(category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            else:
                self.category_combo.setCurrentText(category)
            
            # タグ
            tags = template.get('tags', [])
            if isinstance(tags, list):
                self.tags_edit.setText(', '.join(tags))
            else:
                self.tags_edit.setText(str(tags))
            
            # テンプレート
            self.template_editor.setPlainText(template.get('template', ''))
            
            # 変数を更新
            self._update_variables_list()
            
            # プレビューを更新
            self._update_preview()
            
        except Exception as e:
            self.logger.error(f"テンプレート読み込みエラー: {e}")
    
    def _on_template_modified(self):
        """テンプレート変更時の処理"""
        try:
            # 変数リストを更新
            self._update_variables_list()
            
        except Exception as e:
            self.logger.error(f"テンプレート変更処理エラー: {e}")
    
    def _update_variables_list(self):
        """変数リストを更新"""
        try:
            self.variables_list.clear()
            
            # テンプレートから変数を抽出
            template_text = self.template_editor.toPlainText()
            variables = self._extract_variables(template_text)
            
            for var in variables:
                item = QListWidgetItem()
                value = self.variable_values.get(var, '<未設定>')
                item.setText(f"{var}: {value}")
                item.setData(Qt.ItemDataRole.UserRole, var)
                self.variables_list.addItem(item)
            
        except Exception as e:
            self.logger.error(f"変数リスト更新エラー: {e}")
    
    def _extract_variables(self, template: str) -> List[str]:
        """テンプレートから変数を抽出"""
        try:
            import re
            pattern = r'\{\{([^}]+)\}\}'
            matches = re.findall(pattern, template)
            return list(set(matches))  # 重複を除去
            
        except Exception as e:
            self.logger.error(f"変数抽出エラー: {e}")
            return []
    
    def _set_variable_value(self):
        """変数値を設定"""
        try:
            current_item = self.variables_list.currentItem()
            if not current_item:
                QMessageBox.information(self, "情報", "変数を選択してください")
                return
            
            var_name = current_item.data(Qt.ItemDataRole.UserRole)
            current_value = self.variable_values.get(var_name, '')
            
            value, ok = QInputDialog.getText(
                self, "変数値設定", 
                f"変数 '{var_name}' の値を入力してください:",
                text=current_value
            )
            
            if ok:
                self.variable_values[var_name] = value
                self._update_variables_list()
                self._update_preview()
            
        except Exception as e:
            self.logger.error(f"変数値設定エラー: {e}")
    
    def _clear_variable_values(self):
        """変数値をクリア"""
        try:
            self.variable_values.clear()
            self._update_variables_list()
            self._update_preview()
            
        except Exception as e:
            self.logger.error(f"変数値クリアエラー: {e}")
    
    def _update_preview(self):
        """プレビューを更新"""
        try:
            template_text = self.template_editor.toPlainText()
            
            # 変数を置換
            preview_text = template_text
            for var, value in self.variable_values.items():
                preview_text = preview_text.replace(f"{{{{{var}}}}}", value)
            
            # 未設定の変数をハイライト
            variables = self._extract_variables(preview_text)
            for var in variables:
                preview_text = preview_text.replace(f"{{{{{var}}}}}", f"[{var}: 未設定]")
            
            self.preview_text.setPlainText(preview_text)
            
        except Exception as e:
            self.logger.error(f"プレビュー更新エラー: {e}")
    
    def _create_new_template(self):
        """新しいテンプレートを作成"""
        try:
            name, ok = QInputDialog.getText(self, "新規テンプレート", "テンプレート名を入力してください:")
            
            if ok and name.strip():
                template_id = f"template_{len(self.templates) + 1}"
                
                new_template = {
                    "name": name.strip(),
                    "category": "一般",
                    "description": "",
                    "template": "",
                    "tags": [],
                    "variables": [],
                    "created": datetime.now().isoformat()
                }
                
                self.templates[template_id] = new_template
                self.current_template = template_id
                
                self._update_template_list()
                self._update_category_filter()
                self._load_template_to_editor(new_template)
                
                # 新しいテンプレートを選択
                for i in range(self.template_list.count()):
                    item = self.template_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == template_id:
                        self.template_list.setCurrentItem(item)
                        break
            
        except Exception as e:
            self.logger.error(f"新規テンプレート作成エラー: {e}")
    
    def _save_current_template(self):
        """現在のテンプレートを保存"""
        try:
            if not self.current_template:
                QMessageBox.warning(self, "警告", "保存するテンプレートが選択されていません")
                return
            
            # エディターから情報を取得
            template_data = {
                "name": self.name_edit.text().strip(),
                "category": self.category_combo.currentText().strip(),
                "description": self.description_edit.toPlainText().strip(),
                "template": self.template_editor.toPlainText(),
                "tags": [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()],
                "variables": self._extract_variables(self.template_editor.toPlainText()),
                "updated": datetime.now().isoformat()
            }
            
            # 既存のテンプレートの作成日時を保持
            if self.current_template in self.templates:
                template_data["created"] = self.templates[self.current_template].get("created", datetime.now().isoformat())
            else:
                template_data["created"] = datetime.now().isoformat()
            
            # テンプレートを更新
            self.templates[self.current_template] = template_data
            
            # ファイルに保存
            self._save_templates()
            
            # UIを更新
            self._update_template_list()
            self._update_category_filter()
            
            # シグナルを発行
            self.template_saved.emit(template_data)
            
            QMessageBox.information(self, "成功", "テンプレートを保存しました")
            
        except Exception as e:
            self.logger.error(f"テンプレート保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"テンプレートの保存に失敗しました: {e}")
    
    def _apply_current_template(self):
        """現在のテンプレートを適用"""
        try:
            template_text = self.template_editor.toPlainText()
            
            if not template_text.strip():
                QMessageBox.warning(self, "警告", "テンプレートが空です")
                return
            
            # 変数を置換
            applied_text = template_text
            for var, value in self.variable_values.items():
                applied_text = applied_text.replace(f"{{{{{var}}}}}", value)
            
            # 未設定の変数がある場合は確認
            remaining_vars = self._extract_variables(applied_text)
            if remaining_vars:
                reply = QMessageBox.question(
                    self, "確認",
                    f"未設定の変数があります: {', '.join(remaining_vars)}\n"
                    "このまま適用しますか？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # シグナルを発行
            self.template_applied.emit(applied_text)
            
            QMessageBox.information(self, "成功", "テンプレートを適用しました")
            
        except Exception as e:
            self.logger.error(f"テンプレート適用エラー: {e}")
            QMessageBox.critical(self, "エラー", f"テンプレートの適用に失敗しました: {e}")
    
    def _delete_current_template(self):
        """現在のテンプレートを削除"""
        try:
            if not self.current_template:
                QMessageBox.warning(self, "警告", "削除するテンプレートが選択されていません")
                return
            
            template_name = self.templates[self.current_template].get('name', self.current_template)
            
            reply = QMessageBox.question(
                self, "確認",
                f"テンプレート '{template_name}' を削除しますか？\n"
                "この操作は取り消せません。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # テンプレートを削除
                del self.templates[self.current_template]
                
                # ファイルに保存
                self._save_templates()
                
                # UIを更新
                self._update_template_list()
                self._update_category_filter()
                
                # エディターをクリア
                self._clear_editor()
                
                # シグナルを発行
                self.template_deleted.emit(self.current_template)
                
                self.current_template = None
                
                QMessageBox.information(self, "成功", "テンプレートを削除しました")
            
        except Exception as e:
            self.logger.error(f"テンプレート削除エラー: {e}")
            QMessageBox.critical(self, "エラー", f"テンプレートの削除に失敗しました: {e}")
    
    def _clear_editor(self):
        """エディターをクリア"""
        try:
            self.name_edit.clear()
            self.description_edit.clear()
            self.category_combo.setCurrentIndex(0)
            self.tags_edit.clear()
            self.template_editor.clear()
            self.variables_list.clear()
            self.preview_text.clear()
            self.variable_values.clear()
            
        except Exception as e:
            self.logger.error(f"エディタークリアエラー: {e}")
    
    def _show_template_context_menu(self, position):
        """テンプレートのコンテキストメニューを表示"""
        try:
            item = self.template_list.itemAt(position)
            if not item:
                return
            
            menu = QMenu(self)
            
            # 編集アクション
            edit_action = QAction("編集", self)
            edit_action.triggered.connect(lambda: self._on_template_selected(item))
            menu.addAction(edit_action)
            
            # 複製アクション
            duplicate_action = QAction("複製", self)
            duplicate_action.triggered.connect(lambda: self._duplicate_template(item))
            menu.addAction(duplicate_action)
            
            menu.addSeparator()
            
            # 削除アクション
            delete_action = QAction("削除", self)
            delete_action.triggered.connect(lambda: self._delete_template(item))
            menu.addAction(delete_action)
            
            menu.exec(self.template_list.mapToGlobal(position))
            
        except Exception as e:
            self.logger.error(f"コンテキストメニュー表示エラー: {e}")
    
    def _duplicate_template(self, item: QListWidgetItem):
        """テンプレートを複製"""
        try:
            template_id = item.data(Qt.ItemDataRole.UserRole)
            if template_id not in self.templates:
                return
            
            original_template = self.templates[template_id]
            
            # 新しいIDと名前を生成
            new_id = f"{template_id}_copy_{len(self.templates) + 1}"
            new_name = f"{original_template['name']} (コピー)"
            
            # テンプレートを複製
            new_template = original_template.copy()
            new_template['name'] = new_name
            new_template['created'] = datetime.now().isoformat()
            new_template['updated'] = datetime.now().isoformat()
            
            self.templates[new_id] = new_template
            
            # UIを更新
            self._update_template_list()
            
            QMessageBox.information(self, "成功", f"テンプレート '{new_name}' を作成しました")
            
        except Exception as e:
            self.logger.error(f"テンプレート複製エラー: {e}")
    
    def _delete_template(self, item: QListWidgetItem):
        """指定されたテンプレートを削除"""
        try:
            template_id = item.data(Qt.ItemDataRole.UserRole)
            if template_id not in self.templates:
                return
            
            template_name = self.templates[template_id].get('name', template_id)
            
            reply = QMessageBox.question(
                self, "確認",
                f"テンプレート '{template_name}' を削除しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del self.templates[template_id]
                self._save_templates()
                self._update_template_list()
                
                if self.current_template == template_id:
                    self._clear_editor()
                    self.current_template = None
                
                QMessageBox.information(self, "成功", "テンプレートを削除しました")
            
        except Exception as e:
            self.logger.error(f"テンプレート削除エラー: {e}")
    
    def _import_templates(self):
        """テンプレートをインポート"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "テンプレートファイルを選択",
                "", "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                imported_templates = data.get('templates', {})
                imported_count = 0
                
                for template_id, template in imported_templates.items():
                    # 重複チェック
                    if template_id in self.templates:
                        template_id = f"{template_id}_imported_{len(self.templates) + 1}"
                    
                    self.templates[template_id] = template
                    imported_count += 1
                
                # 保存と更新
                self._save_templates()
                self._update_template_list()
                self._update_category_filter()
                
                QMessageBox.information(
                    self, "成功", 
                    f"{imported_count}個のテンプレートをインポートしました"
                )
            
        except Exception as e:
            self.logger.error(f"テンプレートインポートエラー: {e}")
            QMessageBox.critical(self, "エラー", f"インポートに失敗しました: {e}")
    
    def _export_templates(self):
        """テンプレートをエクスポート"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "エクスポート先を選択",
                "prompt_templates.json", "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                data = {
                    'templates': self.templates,
                    'version': '1.0',
                    'exported': datetime.now().isoformat(),
                    'count': len(self.templates)
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(
                    self, "成功", 
                    f"{len(self.templates)}個のテンプレートをエクスポートしました"
                )
            
        except Exception as e:
            self.logger.error(f"テンプレートエクスポートエラー: {e}")
            QMessageBox.critical(self, "エラー", f"エクスポートに失敗しました: {e}")
    
    def get_current_template(self) -> Optional[Dict]:
        """現在のテンプレートを取得"""
        if self.current_template and self.current_template in self.templates:
            return self.templates[self.current_template].copy()
        return None
    
    def get_all_templates(self) -> Dict[str, Dict]:
        """全テンプレートを取得"""
        return self.templates.copy()
    
    def set_variable_values(self, values: Dict[str, str]):
        """変数値を設定（外部用）"""
        try:
            self.variable_values.update(values)
            self._update_variables_list()
            self._update_preview()
            
        except Exception as e:
            self.logger.error(f"変数値設定エラー: {e}")
    
    def get_rendered_template(self, template_id: Optional[str] = None) -> str:
        """変数を置換したテンプレートを取得"""
        try:
            if template_id:
                if template_id not in self.templates:
                    return ""
                template_text = self.templates[template_id]['template']
            else:
                template_text = self.template_editor.toPlainText()
            
            # 変数を置換
            rendered_text = template_text
            for var, value in self.variable_values.items():
                rendered_text = rendered_text.replace(f"{{{{{var}}}}}", value)
            
            return rendered_text
            
        except Exception as e:
            self.logger.error(f"テンプレート描画エラー: {e}")
            return ""

