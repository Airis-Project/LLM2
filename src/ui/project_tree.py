# src/ui/project_tree.py
"""
プロジェクトツリー表示コンポーネント
ファイル・フォルダの階層表示、操作機能を提供
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from enum import Enum

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QInputDialog,
    QFileDialog, QApplication, QHeaderView, QAbstractItemView,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit,
    QLabel, QSplitter, QFrame, QToolButton, QCheckBox
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QThread, QObject, QMimeData,
    QUrl, QModelIndex, QFileSystemWatcher, QSettings
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QDrag, QAction, QFont, QPalette,
    QKeySequence, QShortcut
)

from ..core.logger import get_logger
from ..core.file_manager import FileManager
from ..utils.file_utils import (
    get_file_size, get_file_extension, is_text_file,
    get_file_icon_path, format_file_size
)


class TreeItemType(Enum):
    """ツリーアイテムタイプ"""
    ROOT = "root"
    FOLDER = "folder"
    FILE = "file"
    SYMLINK = "symlink"


class FileWatcherThread(QThread):
    """ファイル変更監視スレッド"""
    
    file_changed = pyqtSignal(str)
    folder_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.watcher = QFileSystemWatcher()
        self.logger = get_logger(__name__)
        self.watched_paths: Set[str] = set()
        
        # シグナル接続
        self.watcher.fileChanged.connect(self._on_file_changed)
        self.watcher.directoryChanged.connect(self._on_directory_changed)
    
    def add_path(self, path: str):
        """監視パスを追加"""
        try:
            if path not in self.watched_paths:
                self.watcher.addPath(path)
                self.watched_paths.add(path)
                
        except Exception as e:
            self.logger.error(f"パス監視追加エラー: {e}")
    
    def remove_path(self, path: str):
        """監視パスを削除"""
        try:
            if path in self.watched_paths:
                self.watcher.removePath(path)
                self.watched_paths.discard(path)
                
        except Exception as e:
            self.logger.error(f"パス監視削除エラー: {e}")
    
    def _on_file_changed(self, path: str):
        """ファイル変更イベント"""
        self.file_changed.emit(path)
    
    def _on_directory_changed(self, path: str):
        """ディレクトリ変更イベント"""
        self.folder_changed.emit(path)
    
    def cleanup(self):
        """クリーンアップ"""
        try:
            self.watcher.removePaths(list(self.watched_paths))
            self.watched_paths.clear()
            
        except Exception as e:
            self.logger.error(f"ファイル監視クリーンアップエラー: {e}")


class ProjectTreeItem(QTreeWidgetItem):
    """プロジェクトツリーアイテム"""
    
    def __init__(self, parent=None, item_type: TreeItemType = TreeItemType.FILE):
        super().__init__(parent)
        self.item_type = item_type
        self.file_path: Optional[str] = None
        self.file_size: int = 0
        self.is_expanded_state: bool = False
        self.children_loaded: bool = False
        
    def set_file_info(self, file_path: str):
        """ファイル情報を設定"""
        try:
            self.file_path = file_path
            path_obj = Path(file_path)
            
            # ファイル名を設定
            self.setText(0, path_obj.name)
            
            # アイテムタイプを判定
            if path_obj.is_dir():
                self.item_type = TreeItemType.FOLDER
                self.setText(1, "フォルダ")
            elif path_obj.is_symlink():
                self.item_type = TreeItemType.SYMLINK
                self.setText(1, "シンボリックリンク")
            else:
                self.item_type = TreeItemType.FILE
                self.file_size = get_file_size(file_path)
                self.setText(1, format_file_size(self.file_size))
                self.setText(2, get_file_extension(file_path))
            
            # 最終更新日時
            if path_obj.exists():
                mtime = path_obj.stat().st_mtime
                from datetime import datetime
                dt = datetime.fromtimestamp(mtime)
                self.setText(3, dt.strftime("%Y/%m/%d %H:%M"))
            
            # アイコンを設定
            self._set_icon()
            
        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"ファイル情報設定エラー: {e}")
    
    def _set_icon(self):
        """アイコンを設定"""
        try:
            if self.item_type == TreeItemType.FOLDER:
                icon_path = "assets/icons/file_icons/folder.png"
            else:
                icon_path = get_file_icon_path(self.file_path)
            
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                self.setIcon(0, icon)
                
        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"アイコン設定エラー: {e}")
    
    def is_folder(self) -> bool:
        """フォルダかどうか"""
        return self.item_type == TreeItemType.FOLDER
    
    def is_file(self) -> bool:
        """ファイルかどうか"""
        return self.item_type == TreeItemType.FILE
    
    def get_full_path(self) -> str:
        """フルパスを取得"""
        return self.file_path or ""


class ProjectTree(QTreeWidget):
    """プロジェクトツリーウィジェット"""
    
    # シグナル定義
    file_opened = pyqtSignal(str)  # ファイルが開かれた
    file_selected = pyqtSignal(str)  # ファイルが選択された
    folder_selected = pyqtSignal(str)  # フォルダが選択された
    file_created = pyqtSignal(str)  # ファイルが作成された
    file_deleted = pyqtSignal(str)  # ファイルが削除された
    file_renamed = pyqtSignal(str, str)  # ファイルがリネームされた
    project_changed = pyqtSignal(str)  # プロジェクトが変更された
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.file_manager = FileManager()
        self.current_project_path: Optional[str] = None
        self.settings = QSettings()
        
        # ファイル監視
        self.file_watcher = FileWatcherThread()
        self.file_watcher.file_changed.connect(self._on_file_changed)
        self.file_watcher.folder_changed.connect(self._on_folder_changed)
        self.file_watcher.start()
        
        # フィルタ設定
        self.show_hidden_files = False
        self.file_filters: Set[str] = {'.pyc', '.pyo', '__pycache__', '.git', '.svn'}
        self.search_filter = ""
        
        # 選択状態
        self.selected_items: List[ProjectTreeItem] = []
        
        self._init_ui()
        self._setup_connections()
        self._load_settings()
    
    def _init_ui(self):
        """UI初期化"""
        try:
            # ヘッダー設定
            self.setHeaderLabels(["名前", "サイズ", "種類", "更新日時"])
            
            # ヘッダーサイズ調整
            header = self.header()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            
            # 選択設定
            self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            
            # ドラッグ&ドロップ設定
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.setDropIndicatorShown(True)
            self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            
            # その他設定
            self.setAlternatingRowColors(True)
            self.setRootIsDecorated(True)
            self.setExpandsOnDoubleClick(False)
            self.setSortingEnabled(True)
            self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
            
            # コンテキストメニュー
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            
            # スタイル設定
            self._apply_style()
            
        except Exception as e:
            self.logger.error(f"UI初期化エラー: {e}")
    
    def _apply_style(self):
        """スタイルを適用"""
        try:
            style = """
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                selection-background-color: #3daee9;
                selection-color: white;
                outline: none;
            }
            
            QTreeWidget::item {
                height: 24px;
                border: none;
                padding: 2px;
            }
            
            QTreeWidget::item:hover {
                background-color: #f0f0f0;
            }
            
            QTreeWidget::item:selected {
                background-color: #3daee9;
                color: white;
            }
            
            QTreeWidget::branch {
                background: transparent;
            }
            
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                image: url(assets/icons/toolbar_icons/arrow_right.png);
            }
            
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                image: url(assets/icons/toolbar_icons/arrow_down.png);
            }
            """
            self.setStyleSheet(style)
            
        except Exception as e:
            self.logger.error(f"スタイル適用エラー: {e}")
    
    def _setup_connections(self):
        """シグナル接続"""
        try:
            # アイテム操作
            self.itemDoubleClicked.connect(self._on_item_double_clicked)
            self.itemClicked.connect(self._on_item_clicked)
            self.itemSelectionChanged.connect(self._on_selection_changed)
            self.itemExpanded.connect(self._on_item_expanded)
            self.itemCollapsed.connect(self._on_item_collapsed)
            
            # コンテキストメニュー
            self.customContextMenuRequested.connect(self._show_context_menu)
            
            # キーボードショートカット
            self._setup_shortcuts()
            
        except Exception as e:
            self.logger.error(f"シグナル接続エラー: {e}")
    
    def _setup_shortcuts(self):
        """キーボードショートカット設定"""
        try:
            # ファイル作成
            new_file_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
            new_file_shortcut.activated.connect(self._create_new_file)
            
            # フォルダ作成
            new_folder_shortcut = QShortcut(QKeySequence("Ctrl+Shift+N"), self)
            new_folder_shortcut.activated.connect(self._create_new_folder)
            
            # 削除
            delete_shortcut = QShortcut(QKeySequence.StandardKey.Delete, self)
            delete_shortcut.activated.connect(self._delete_selected)
            
            # リネーム
            rename_shortcut = QShortcut(QKeySequence("F2"), self)
            rename_shortcut.activated.connect(self._rename_selected)
            
            # 更新
            refresh_shortcut = QShortcut(QKeySequence("F5"), self)
            refresh_shortcut.activated.connect(self.refresh)
            
            # コピー
            copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
            copy_shortcut.activated.connect(self._copy_selected)
            
            # 切り取り
            cut_shortcut = QShortcut(QKeySequence.StandardKey.Cut, self)
            cut_shortcut.activated.connect(self._cut_selected)
            
            # 貼り付け
            paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
            paste_shortcut.activated.connect(self._paste_selected)
            
        except Exception as e:
            self.logger.error(f"ショートカット設定エラー: {e}")
    
    def _load_settings(self):
        """設定を読み込み"""
        try:
            # 表示設定
            self.show_hidden_files = self.settings.value(
                "project_tree/show_hidden_files", False, type=bool
            )
            
            # フィルタ設定
            filters = self.settings.value("project_tree/file_filters", [])
            if filters:
                self.file_filters = set(filters)
            
            # カラム幅
            for i in range(self.columnCount()):
                width = self.settings.value(f"project_tree/column_{i}_width", 100, type=int)
                self.setColumnWidth(i, width)
            
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {e}")
    
    def _save_settings(self):
        """設定を保存"""
        try:
            # 表示設定
            self.settings.setValue("project_tree/show_hidden_files", self.show_hidden_files)
            
            # フィルタ設定
            self.settings.setValue("project_tree/file_filters", list(self.file_filters))
            
            # カラム幅
            for i in range(self.columnCount()):
                self.settings.setValue(f"project_tree/column_{i}_width", self.columnWidth(i))
            
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
    
    # プロジェクト操作
    def open_project(self, project_path: str):
        """プロジェクトを開く"""
        try:
            if not os.path.exists(project_path):
                QMessageBox.warning(self, "エラー", f"プロジェクトパスが存在しません: {project_path}")
                return False
            
            if not os.path.isdir(project_path):
                QMessageBox.warning(self, "エラー", f"プロジェクトパスがディレクトリではありません: {project_path}")
                return False
            
            # 既存の監視を停止
            if self.current_project_path:
                self.file_watcher.remove_path(self.current_project_path)
            
            # 新しいプロジェクトを設定
            self.current_project_path = project_path
            self.file_watcher.add_path(project_path)
            
            # ツリーを構築
            self._build_tree()
            
            # シグナル発行
            self.project_changed.emit(project_path)
            
            self.logger.info(f"プロジェクトを開きました: {project_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"プロジェクトオープンエラー: {e}")
            QMessageBox.critical(self, "エラー", f"プロジェクトを開けませんでした: {e}")
            return False
    
    def close_project(self):
        """プロジェクトを閉じる"""
        try:
            if self.current_project_path:
                self.file_watcher.remove_path(self.current_project_path)
                self.current_project_path = None
            
            self.clear()
            self.logger.info("プロジェクトを閉じました")
            
        except Exception as e:
            self.logger.error(f"プロジェクトクローズエラー: {e}")
    
    def refresh(self):
        """ツリーを更新"""
        try:
            if self.current_project_path:
                # 展開状態を保存
                expanded_items = self._get_expanded_items()
                
                # ツリーを再構築
                self._build_tree()
                
                # 展開状態を復元
                self._restore_expanded_items(expanded_items)
                
                self.logger.info("プロジェクトツリーを更新しました")
            
        except Exception as e:
            self.logger.error(f"ツリー更新エラー: {e}")
    
    def _build_tree(self):
        """ツリーを構築"""
        try:
            if not self.current_project_path:
                return
            
            self.clear()
            
            # ルートアイテムを作成
            root_item = ProjectTreeItem(item_type=TreeItemType.ROOT)
            root_item.set_file_info(self.current_project_path)
            self.addTopLevelItem(root_item)
            
            # 子アイテムを追加
            self._populate_item(root_item)
            
            # ルートを展開
            root_item.setExpanded(True)
            
        except Exception as e:
            self.logger.error(f"ツリー構築エラー: {e}")
    
    def _populate_item(self, parent_item: ProjectTreeItem):
        """アイテムに子要素を追加"""
        try:
            if not parent_item.is_folder():
                return
            
            parent_path = parent_item.get_full_path()
            if not os.path.exists(parent_path):
                return
            
            # 既存の子アイテムをクリア
            parent_item.takeChildren()
            
            # ディレクトリ内容を取得
            try:
                entries = list(os.listdir(parent_path))
            except PermissionError:
                self.logger.warning(f"アクセス権限がありません: {parent_path}")
                return
            
            # ソート（フォルダ優先、その後名前順）
            entries.sort(key=lambda x: (
                not os.path.isdir(os.path.join(parent_path, x)),
                x.lower()
            ))
            
            for entry in entries:
                entry_path = os.path.join(parent_path, entry)
                
                # フィルタリング
                if not self._should_show_item(entry, entry_path):
                    continue
                
                # 子アイテムを作成
                child_item = ProjectTreeItem(parent_item)
                child_item.set_file_info(entry_path)
                
                # フォルダの場合は監視対象に追加
                if child_item.is_folder():
                    self.file_watcher.add_path(entry_path)
                    
                    # 子フォルダがある場合はダミーアイテムを追加（遅延読み込み用）
                    if self._has_children(entry_path):
                        dummy_item = ProjectTreeItem(child_item)
                        dummy_item.setText(0, "読み込み中...")
            
            parent_item.children_loaded = True
            
        except Exception as e:
            self.logger.error(f"アイテム作成エラー: {e}")
    
    def _should_show_item(self, name: str, path: str) -> bool:
        """アイテムを表示するかどうか判定"""
        try:
            # 隠しファイル
            if not self.show_hidden_files and name.startswith('.'):
                return False
            
            # フィルタ
            if any(filter_item in name for filter_item in self.file_filters):
                return False
            
            # 検索フィルタ
            if self.search_filter and self.search_filter.lower() not in name.lower():
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"アイテム表示判定エラー: {e}")
            return True
    
    def _has_children(self, path: str) -> bool:
        """子要素があるかどうか判定"""
        try:
            if not os.path.isdir(path):
                return False
            
            try:
                entries = os.listdir(path)
                for entry in entries:
                    entry_path = os.path.join(path, entry)
                    if self._should_show_item(entry, entry_path):
                        return True
                return False
                
            except PermissionError:
                return False
            
        except Exception as e:
            self.logger.error(f"子要素判定エラー: {e}")
            return False
    
    def _get_expanded_items(self) -> List[str]:
        """展開されているアイテムのパスを取得"""
        try:
            expanded_paths = []
            
            def collect_expanded(item: QTreeWidgetItem):
                if isinstance(item, ProjectTreeItem) and item.isExpanded():
                    expanded_paths.append(item.get_full_path())
                
                for i in range(item.childCount()):
                    collect_expanded(item.child(i))
            
            for i in range(self.topLevelItemCount()):
                collect_expanded(self.topLevelItem(i))
            
            return expanded_paths
            
        except Exception as e:
            self.logger.error(f"展開アイテム取得エラー: {e}")
            return []
    
    def _restore_expanded_items(self, expanded_paths: List[str]):
        """展開状態を復元"""
        try:
            def restore_expanded(item: QTreeWidgetItem):
                if isinstance(item, ProjectTreeItem):
                    if item.get_full_path() in expanded_paths:
                        item.setExpanded(True)
                
                for i in range(item.childCount()):
                    restore_expanded(item.child(i))
            
            for i in range(self.topLevelItemCount()):
                restore_expanded(self.topLevelItem(i))
            
        except Exception as e:
            self.logger.error(f"展開状態復元エラー: {e}")
    
    # イベントハンドラ
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """アイテムダブルクリック"""
        try:
            if isinstance(item, ProjectTreeItem):
                if item.is_file():
                    # ファイルを開く
                    self.file_opened.emit(item.get_full_path())
                elif item.is_folder():
                    # フォルダを展開/折りたたみ
                    item.setExpanded(not item.isExpanded())
            
        except Exception as e:
            self.logger.error(f"ダブルクリック処理エラー: {e}")
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """アイテムクリック"""
        try:
            if isinstance(item, ProjectTreeItem):
                if item.is_file():
                    self.file_selected.emit(item.get_full_path())
                elif item.is_folder():
                    self.folder_selected.emit(item.get_full_path())
            
        except Exception as e:
            self.logger.error(f"クリック処理エラー: {e}")
    
    def _on_selection_changed(self):
        """選択変更"""
        try:
            self.selected_items = []
            for item in self.selectedItems():
                if isinstance(item, ProjectTreeItem):
                    self.selected_items.append(item)
            
        except Exception as e:
            self.logger.error(f"選択変更処理エラー: {e}")
    
    def _on_item_expanded(self, item: QTreeWidgetItem):
        """アイテム展開"""
        try:
            if isinstance(item, ProjectTreeItem) and item.is_folder():
                # 遅延読み込み
                if not item.children_loaded:
                    # ダミーアイテムを削除
                    item.takeChildren()
                    # 実際の子アイテムを読み込み
                    self._populate_item(item)
                
                item.is_expanded_state = True
            
        except Exception as e:
            self.logger.error(f"アイテム展開処理エラー: {e}")
    
    def _on_item_collapsed(self, item: QTreeWidgetItem):
        """アイテム折りたたみ"""
        try:
            if isinstance(item, ProjectTreeItem):
                item.is_expanded_state = False
            
        except Exception as e:
            self.logger.error(f"アイテム折りたたみ処理エラー: {e}")
    
    def _on_file_changed(self, path: str):
        """ファイル変更通知"""
        try:
            # 該当するアイテムを更新
            item = self._find_item_by_path(path)
            if item:
                item.set_file_info(path)
            
        except Exception as e:
            self.logger.error(f"ファイル変更処理エラー: {e}")
    
    def _on_folder_changed(self, path: str):
        """フォルダ変更通知"""
        try:
            # 該当するフォルダアイテムを更新
            item = self._find_item_by_path(path)
            if item and item.is_folder():
                if item.isExpanded():
                    self._populate_item(item)
            
        except Exception as e:
            self.logger.error(f"フォルダ変更処理エラー: {e}")
    
    def _find_item_by_path(self, path: str) -> Optional[ProjectTreeItem]:
        """パスでアイテムを検索"""
        try:
            def search_item(item: QTreeWidgetItem) -> Optional[ProjectTreeItem]:
                if isinstance(item, ProjectTreeItem):
                    if item.get_full_path() == path:
                        return item
                
                for i in range(item.childCount()):
                    result = search_item(item.child(i))
                    if result:
                        return result
                
                return None
            
            for i in range(self.topLevelItemCount()):
                result = search_item(self.topLevelItem(i))
                if result:
                    return result
            
            return None
            
        except Exception as e:
            self.logger.error(f"アイテム検索エラー: {e}")
            return None
    # コンテキストメニュー
    def _show_context_menu(self, position):
        """コンテキストメニューを表示"""
        try:
            item = self.itemAt(position)
            menu = QMenu(self)
            
            if item and isinstance(item, ProjectTreeItem):
                # ファイル/フォルダ固有のメニュー
                if item.is_file():
                    self._add_file_menu_actions(menu, item)
                elif item.is_folder():
                    self._add_folder_menu_actions(menu, item)
            else:
                # 空白部分のメニュー
                self._add_empty_area_menu_actions(menu)
            
            # 共通メニュー
            self._add_common_menu_actions(menu)
            
            # メニューを表示
            if not menu.isEmpty():
                menu.exec(self.mapToGlobal(position))
            
        except Exception as e:
            self.logger.error(f"コンテキストメニュー表示エラー: {e}")
    
    def _add_file_menu_actions(self, menu: QMenu, item: ProjectTreeItem):
        """ファイル用メニューアクションを追加"""
        try:
            # 開く
            open_action = QAction("開く", self)
            open_action.triggered.connect(lambda: self.file_opened.emit(item.get_full_path()))
            menu.addAction(open_action)
            
            # 既定のアプリケーションで開く
            open_external_action = QAction("既定のアプリケーションで開く", self)
            open_external_action.triggered.connect(lambda: self._open_external(item.get_full_path()))
            menu.addAction(open_external_action)
            
            menu.addSeparator()
            
            # 切り取り
            cut_action = QAction("切り取り", self)
            cut_action.setShortcut(QKeySequence.StandardKey.Cut)
            cut_action.triggered.connect(lambda: self._cut_item(item))
            menu.addAction(cut_action)
            
            # コピー
            copy_action = QAction("コピー", self)
            copy_action.setShortcut(QKeySequence.StandardKey.Copy)
            copy_action.triggered.connect(lambda: self._copy_item(item))
            menu.addAction(copy_action)
            
            menu.addSeparator()
            
            # 削除
            delete_action = QAction("削除", self)
            delete_action.setShortcut(QKeySequence.StandardKey.Delete)
            delete_action.triggered.connect(lambda: self._delete_item(item))
            menu.addAction(delete_action)
            
            # リネーム
            rename_action = QAction("名前の変更", self)
            rename_action.setShortcut(QKeySequence("F2"))
            rename_action.triggered.connect(lambda: self._rename_item(item))
            menu.addAction(rename_action)
            
            menu.addSeparator()
            
            # プロパティ
            properties_action = QAction("プロパティ", self)
            properties_action.triggered.connect(lambda: self._show_properties(item))
            menu.addAction(properties_action)
            
        except Exception as e:
            self.logger.error(f"ファイルメニュー追加エラー: {e}")
    
    def _add_folder_menu_actions(self, menu: QMenu, item: ProjectTreeItem):
        """フォルダ用メニューアクションを追加"""
        try:
            # 新しいファイル
            new_file_action = QAction("新しいファイル", self)
            new_file_action.triggered.connect(lambda: self._create_new_file(item.get_full_path()))
            menu.addAction(new_file_action)
            
            # 新しいフォルダ
            new_folder_action = QAction("新しいフォルダ", self)
            new_folder_action.triggered.connect(lambda: self._create_new_folder(item.get_full_path()))
            menu.addAction(new_folder_action)
            
            menu.addSeparator()
            
            # エクスプローラーで開く
            open_explorer_action = QAction("エクスプローラーで開く", self)
            open_explorer_action.triggered.connect(lambda: self._open_in_explorer(item.get_full_path()))
            menu.addAction(open_explorer_action)
            
            menu.addSeparator()
            
            # 切り取り
            cut_action = QAction("切り取り", self)
            cut_action.triggered.connect(lambda: self._cut_item(item))
            menu.addAction(cut_action)
            
            # コピー
            copy_action = QAction("コピー", self)
            copy_action.triggered.connect(lambda: self._copy_item(item))
            menu.addAction(copy_action)
            
            # 貼り付け
            paste_action = QAction("貼り付け", self)
            paste_action.setEnabled(self._can_paste())
            paste_action.triggered.connect(lambda: self._paste_to_folder(item.get_full_path()))
            menu.addAction(paste_action)
            
            menu.addSeparator()
            
            # 削除
            delete_action = QAction("削除", self)
            delete_action.triggered.connect(lambda: self._delete_item(item))
            menu.addAction(delete_action)
            
            # リネーム
            rename_action = QAction("名前の変更", self)
            rename_action.triggered.connect(lambda: self._rename_item(item))
            menu.addAction(rename_action)
            
            menu.addSeparator()
            
            # プロパティ
            properties_action = QAction("プロパティ", self)
            properties_action.triggered.connect(lambda: self._show_properties(item))
            menu.addAction(properties_action)
            
        except Exception as e:
            self.logger.error(f"フォルダメニュー追加エラー: {e}")
    
    def _add_empty_area_menu_actions(self, menu: QMenu):
        """空白エリア用メニューアクションを追加"""
        try:
            if self.current_project_path:
                # 新しいファイル
                new_file_action = QAction("新しいファイル", self)
                new_file_action.triggered.connect(lambda: self._create_new_file(self.current_project_path))
                menu.addAction(new_file_action)
                
                # 新しいフォルダ
                new_folder_action = QAction("新しいフォルダ", self)
                new_folder_action.triggered.connect(lambda: self._create_new_folder(self.current_project_path))
                menu.addAction(new_folder_action)
                
                menu.addSeparator()
                
                # 貼り付け
                paste_action = QAction("貼り付け", self)
                paste_action.setEnabled(self._can_paste())
                paste_action.triggered.connect(lambda: self._paste_to_folder(self.current_project_path))
                menu.addAction(paste_action)
            
        except Exception as e:
            self.logger.error(f"空白エリアメニュー追加エラー: {e}")
    
    def _add_common_menu_actions(self, menu: QMenu):
        """共通メニューアクションを追加"""
        try:
            menu.addSeparator()
            
            # 更新
            refresh_action = QAction("更新", self)
            refresh_action.setShortcut(QKeySequence("F5"))
            refresh_action.triggered.connect(self.refresh)
            menu.addAction(refresh_action)
            
            # 設定
            settings_action = QAction("表示設定", self)
            settings_action.triggered.connect(self._show_display_settings)
            menu.addAction(settings_action)
            
        except Exception as e:
            self.logger.error(f"共通メニュー追加エラー: {e}")
    
    # ファイル操作
    def _create_new_file(self, parent_path: str = None):
        """新しいファイルを作成"""
        try:
            if parent_path is None:
                parent_path = self.current_project_path
            
            if not parent_path:
                return
            
            # ファイル名を入力
            name, ok = QInputDialog.getText(
                self, "新しいファイル", "ファイル名を入力してください:"
            )
            
            if not ok or not name.strip():
                return
            
            name = name.strip()
            file_path = os.path.join(parent_path, name)
            
            # 既存チェック
            if os.path.exists(file_path):
                QMessageBox.warning(self, "エラー", f"ファイルが既に存在します: {name}")
                return
            
            # ファイル作成
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('')
                
                self.logger.info(f"ファイルを作成しました: {file_path}")
                self.file_created.emit(file_path)
                
                # ツリーを更新
                self.refresh()
                
                # 作成したファイルを選択
                QTimer.singleShot(100, lambda: self._select_item_by_path(file_path))
                
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"ファイルの作成に失敗しました: {e}")
            
        except Exception as e:
            self.logger.error(f"ファイル作成エラー: {e}")
    
    def _create_new_folder(self, parent_path: str = None):
        """新しいフォルダを作成"""
        try:
            if parent_path is None:
                parent_path = self.current_project_path
            
            if not parent_path:
                return
            
            # フォルダ名を入力
            name, ok = QInputDialog.getText(
                self, "新しいフォルダ", "フォルダ名を入力してください:"
            )
            
            if not ok or not name.strip():
                return
            
            name = name.strip()
            folder_path = os.path.join(parent_path, name)
            
            # 既存チェック
            if os.path.exists(folder_path):
                QMessageBox.warning(self, "エラー", f"フォルダが既に存在します: {name}")
                return
            
            # フォルダ作成
            try:
                os.makedirs(folder_path)
                
                self.logger.info(f"フォルダを作成しました: {folder_path}")
                
                # ツリーを更新
                self.refresh()
                
                # 作成したフォルダを選択
                QTimer.singleShot(100, lambda: self._select_item_by_path(folder_path))
                
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"フォルダの作成に失敗しました: {e}")
            
        except Exception as e:
            self.logger.error(f"フォルダ作成エラー: {e}")
    
    def _delete_item(self, item: ProjectTreeItem):
        """アイテムを削除"""
        try:
            file_path = item.get_full_path()
            file_name = os.path.basename(file_path)
            
            # 確認ダイアログ
            reply = QMessageBox.question(
                self, "削除の確認",
                f"'{file_name}' を削除しますか？\n\nこの操作は元に戻せません。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # 削除実行
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                
                self.logger.info(f"削除しました: {file_path}")
                self.file_deleted.emit(file_path)
                
                # ツリーを更新
                self.refresh()
                
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"削除に失敗しました: {e}")
            
        except Exception as e:
            self.logger.error(f"削除エラー: {e}")
    
    def _rename_item(self, item: ProjectTreeItem):
        """アイテムをリネーム"""
        try:
            old_path = item.get_full_path()
            old_name = os.path.basename(old_path)
            
            # 新しい名前を入力
            new_name, ok = QInputDialog.getText(
                self, "名前の変更", "新しい名前を入力してください:", text=old_name
            )
            
            if not ok or not new_name.strip() or new_name.strip() == old_name:
                return
            
            new_name = new_name.strip()
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            
            # 既存チェック
            if os.path.exists(new_path):
                QMessageBox.warning(self, "エラー", f"同名のファイル/フォルダが既に存在します: {new_name}")
                return
            
            # リネーム実行
            try:
                os.rename(old_path, new_path)
                
                self.logger.info(f"リネームしました: {old_path} -> {new_path}")
                self.file_renamed.emit(old_path, new_path)
                
                # ツリーを更新
                self.refresh()
                
                # リネームしたアイテムを選択
                QTimer.singleShot(100, lambda: self._select_item_by_path(new_path))
                
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"名前の変更に失敗しました: {e}")
            
        except Exception as e:
            self.logger.error(f"リネームエラー: {e}")
    
    def _copy_item(self, item: ProjectTreeItem):
        """アイテムをコピー"""
        try:
            clipboard = QApplication.clipboard()
            mime_data = QMimeData()
            
            # ファイルパスをクリップボードに設定
            urls = [QUrl.fromLocalFile(item.get_full_path())]
            mime_data.setUrls(urls)
            mime_data.setText(item.get_full_path())
            
            clipboard.setMimeData(mime_data)
            
            self.logger.info(f"コピーしました: {item.get_full_path()}")
            
        except Exception as e:
            self.logger.error(f"コピーエラー: {e}")
    
    def _cut_item(self, item: ProjectTreeItem):
        """アイテムを切り取り"""
        try:
            # コピーと同じ処理だが、切り取りフラグを設定
            self._copy_item(item)
            
            # 切り取り状態を視覚的に表示（グレーアウトなど）
            item.setForeground(0, item.foreground(0).color().lighter(150))
            
            self.logger.info(f"切り取りました: {item.get_full_path()}")
            
        except Exception as e:
            self.logger.error(f"切り取りエラー: {e}")
    
    def _can_paste(self) -> bool:
        """貼り付け可能かどうか"""
        try:
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            
            return mime_data.hasUrls() or mime_data.hasText()
            
        except Exception as e:
            self.logger.error(f"貼り付け可能性チェックエラー: {e}")
            return False
    
    def _paste_to_folder(self, target_folder: str):
        """フォルダに貼り付け"""
        try:
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            
            if mime_data.hasUrls():
                for url in mime_data.urls():
                    source_path = url.toLocalFile()
                    if os.path.exists(source_path):
                        self._copy_file_to_folder(source_path, target_folder)
            
            elif mime_data.hasText():
                source_path = mime_data.text()
                if os.path.exists(source_path):
                    self._copy_file_to_folder(source_path, target_folder)
            
            # ツリーを更新
            self.refresh()
            
        except Exception as e:
            self.logger.error(f"貼り付けエラー: {e}")
            QMessageBox.critical(self, "エラー", f"貼り付けに失敗しました: {e}")
    
    def _copy_file_to_folder(self, source_path: str, target_folder: str):
        """ファイルをフォルダにコピー"""
        try:
            source_name = os.path.basename(source_path)
            target_path = os.path.join(target_folder, source_name)
            
            # 重複チェック
            if os.path.exists(target_path):
                # 新しい名前を生成
                base_name, ext = os.path.splitext(source_name)
                counter = 1
                while os.path.exists(target_path):
                    new_name = f"{base_name}_copy{counter}{ext}"
                    target_path = os.path.join(target_folder, new_name)
                    counter += 1
            
            # コピー実行
            if os.path.isdir(source_path):
                shutil.copytree(source_path, target_path)
            else:
                shutil.copy2(source_path, target_path)
            
            self.logger.info(f"コピーしました: {source_path} -> {target_path}")
            
        except Exception as e:
            self.logger.error(f"ファイルコピーエラー: {e}")
            raise
    
    # ユーティリティメソッド
    def _select_item_by_path(self, path: str):
        """パスでアイテムを選択"""
        try:
            item = self._find_item_by_path(path)
            if item:
                self.setCurrentItem(item)
                self.scrollToItem(item)
            
        except Exception as e:
            self.logger.error(f"アイテム選択エラー: {e}")
    
    def _open_external(self, file_path: str):
        """外部アプリケーションで開く"""
        try:
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
            
            self.logger.info(f"外部アプリケーションで開きました: {file_path}")
            
        except Exception as e:
            self.logger.error(f"外部アプリケーション起動エラー: {e}")
            QMessageBox.warning(self, "エラー", f"ファイルを開けませんでした: {e}")
    
    def _open_in_explorer(self, folder_path: str):
        """エクスプローラーで開く"""
        try:
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Windows":
                subprocess.run(["explorer", folder_path])
            elif system == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
            
            self.logger.info(f"エクスプローラーで開きました: {folder_path}")
            
        except Exception as e:
            self.logger.error(f"エクスプローラー起動エラー: {e}")
            QMessageBox.warning(self, "エラー", f"フォルダを開けませんでした: {e}")
    
    def _show_properties(self, item: ProjectTreeItem):
        """プロパティダイアログを表示"""
        try:
            from .components.custom_widgets import FilePropertiesDialog
            
            dialog = FilePropertiesDialog(item.get_full_path(), self)
            dialog.exec()
            
        except Exception as e:
            self.logger.error(f"プロパティ表示エラー: {e}")
    
    def _show_display_settings(self):
        """表示設定ダイアログを表示"""
        try:
            from .components.custom_widgets import TreeDisplaySettingsDialog
            
            dialog = TreeDisplaySettingsDialog(self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                # 設定を適用
                self.show_hidden_files = dialog.show_hidden_files
                self.file_filters = dialog.file_filters
                
                # ツリーを更新
                self.refresh()
                
                # 設定を保存
                self._save_settings()
            
        except Exception as e:
            self.logger.error(f"表示設定エラー: {e}")
    
    # ショートカット操作
    def _copy_selected(self):
        """選択アイテムをコピー"""
        try:
            if self.selected_items:
                self._copy_item(self.selected_items[0])
            
        except Exception as e:
            self.logger.error(f"選択コピーエラー: {e}")
    
    def _cut_selected(self):
        """選択アイテムを切り取り"""
        try:
            if self.selected_items:
                self._cut_item(self.selected_items[0])
            
        except Exception as e:
            self.logger.error(f"選択切り取りエラー: {e}")
    
    def _paste_selected(self):
        """選択位置に貼り付け"""
        try:
            if self.selected_items:
                item = self.selected_items[0]
                if item.is_folder():
                    self._paste_to_folder(item.get_full_path())
                else:
                    # ファイルの場合は親フォルダに貼り付け
                    parent_path = os.path.dirname(item.get_full_path())
                    self._paste_to_folder(parent_path)
            elif self.current_project_path:
                self._paste_to_folder(self.current_project_path)
            
        except Exception as e:
            self.logger.error(f"選択貼り付けエラー: {e}")
    
    def _delete_selected(self):
        """選択アイテムを削除"""
        try:
            if self.selected_items:
                for item in self.selected_items:
                    self._delete_item(item)
            
        except Exception as e:
            self.logger.error(f"選択削除エラー: {e}")
    
    def _rename_selected(self):
        """選択アイテムをリネーム"""
        try:
            if self.selected_items:
                self._rename_item(self.selected_items[0])
            
        except Exception as e:
            self.logger.error(f"選択リネームエラー: {e}")
    
    # 検索機能
    def set_search_filter(self, filter_text: str):
        """検索フィルタを設定"""
        try:
            self.search_filter = filter_text
            self.refresh()
            
        except Exception as e:
            self.logger.error(f"検索フィルタ設定エラー: {e}")
    
    def clear_search_filter(self):
        """検索フィルタをクリア"""
        try:
            self.search_filter = ""
            self.refresh()
            
        except Exception as e:
            self.logger.error(f"検索フィルタクリアエラー: {e}")
    
    # 設定
    def set_show_hidden_files(self, show: bool):
        """隠しファイル表示設定"""
        try:
            self.show_hidden_files = show
            self.refresh()
            self._save_settings()
            
        except Exception as e:
            self.logger.error(f"隠しファイル表示設定エラー: {e}")
    
    def add_file_filter(self, filter_pattern: str):
        """ファイルフィルタを追加"""
        try:
            self.file_filters.add(filter_pattern)
            self.refresh()
            self._save_settings()
            
        except Exception as e:
            self.logger.error(f"ファイルフィルタ追加エラー: {e}")
    
    def remove_file_filter(self, filter_pattern: str):
        """ファイルフィルタを削除"""
        try:
            self.file_filters.discard(filter_pattern)
            self.refresh()
            self._save_settings()
            
        except Exception as e:
            self.logger.error(f"ファイルフィルタ削除エラー: {e}")
    
    # クリーンアップ
    def cleanup(self):
        """クリーンアップ"""
        try:
            # 設定を保存
            self._save_settings()
            
            # ファイル監視を停止
            self.file_watcher.cleanup()
            self.file_watcher.quit()
            self.file_watcher.wait()
            
            self.logger.info("ProjectTree をクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")
