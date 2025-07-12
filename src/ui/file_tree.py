# src/ui/file_tree.py
"""
ファイルツリー - プロジェクトファイルの階層表示と管理
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable, Dict, List, Any, Set, Tuple
from pathlib import Path
import os
import mimetypes
import threading
import time
from datetime import datetime

from src.utils.file_utils import FileUtils

def get_config_manager():
        from src.core.config_manager import ConfigManager
        return ConfigManager()

class FileTreeNode:
    """ファイルツリーノードクラス"""
    
    def __init__(self, path: Path, parent: Optional['FileTreeNode'] = None):
        self.path = path
        self.parent = parent
        self.children: List['FileTreeNode'] = []
        self.is_expanded = False
        self.is_loaded = False
        self.tree_item_id = None
        
        # ファイル情報
        self.is_directory = path.is_dir()
        self.size = path.stat().st_size if path.exists() and not self.is_directory else 0
        self.modified_time = datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else None
        
        # 表示用の名前
        self.display_name = path.name if path.name else str(path)
    
    def add_child(self, child_node: 'FileTreeNode'):
        """子ノードを追加"""
        child_node.parent = self
        self.children.append(child_node)
        self.children.sort(key=lambda x: (not x.is_directory, x.display_name.lower()))
    
    def remove_child(self, child_node: 'FileTreeNode'):
        """子ノードを削除"""
        if child_node in self.children:
            self.children.remove(child_node)
            child_node.parent = None
    
    def get_full_path(self) -> str:
        """フルパスを取得"""
        return str(self.path.resolve())
    
    def get_relative_path(self, root_path: Path) -> str:
        """ルートからの相対パスを取得"""
        try:
            return str(self.path.relative_to(root_path))
        except ValueError:
            return str(self.path)
    
    def is_hidden(self) -> bool:
        """隠しファイル/フォルダかチェック"""
        return self.display_name.startswith('.')
    
    def get_file_type(self) -> str:
        """ファイルタイプを取得"""
        if self.is_directory:
            return "folder"
        
        mime_type, _ = mimetypes.guess_type(str(self.path))
        if mime_type:
            return mime_type.split('/')[0]
        
        # 拡張子ベースの判定
        suffix = self.path.suffix.lower()
        if suffix in ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c']:
            return "code"
        elif suffix in ['.txt', '.md', '.rst']:
            return "text"
        elif suffix in ['.jpg', '.png', '.gif', '.bmp']:
            return "image"
        else:
            return "file"


class FileTreeFilter:
    """ファイルツリーフィルタークラス"""
    
    def __init__(self):
        self.show_hidden_files = False
        self.file_patterns: List[str] = []
        self.exclude_patterns: List[str] = [
            '*.pyc', '__pycache__', '.git', '.svn', 
            'node_modules', '.DS_Store', 'Thumbs.db'
        ]
        self.max_depth = 10
        self.max_files_per_dir = 1000
    
    def should_show_file(self, node: FileTreeNode, depth: int = 0) -> bool:
        """ファイルを表示すべきかチェック"""
        # 深度チェック
        if depth > self.max_depth:
            return False
        
        # 隠しファイルチェック
        if node.is_hidden() and not self.show_hidden_files:
            return False
        
        # 除外パターンチェック
        if self._matches_patterns(node.display_name, self.exclude_patterns):
            return False
        
        # ファイルパターンチェック（指定されている場合）
        if self.file_patterns and not node.is_directory:
            if not self._matches_patterns(node.display_name, self.file_patterns):
                return False
        
        return True
    
    def _matches_patterns(self, filename: str, patterns: List[str]) -> bool:
        """パターンマッチング"""
        import fnmatch
        for pattern in patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False


class FileTreeContextMenu:
    """ファイルツリーコンテキストメニュー"""
    
    def __init__(self, file_tree: 'FileTree'):
        self.file_tree = file_tree
        self.menu = None
    
    def show(self, event, node: FileTreeNode):
        """コンテキストメニューを表示"""
        if self.menu:
            self.menu.destroy()
        
        self.menu = tk.Menu(self.file_tree, tearoff=0)
        
        if node.is_directory:
            self._add_directory_menu_items(node)
        else:
            self._add_file_menu_items(node)
        
        self._add_common_menu_items(node)
        
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()
    
    def _add_file_menu_items(self, node: FileTreeNode):
        """ファイル用メニューアイテム"""
        self.menu.add_command(
            label="開く",
            command=lambda: self.file_tree._open_file(node)
        )
        self.menu.add_command(
            label="エディタで開く",
            command=lambda: self.file_tree._open_in_editor(node)
        )
        self.menu.add_separator()
    
    def _add_directory_menu_items(self, node: FileTreeNode):
        """ディレクトリ用メニューアイテム"""
        if node.is_expanded:
            self.menu.add_command(
                label="折りたたむ",
                command=lambda: self.file_tree._collapse_node(node)
            )
        else:
            self.menu.add_command(
                label="展開",
                command=lambda: self.file_tree._expand_node(node)
            )
        
        self.menu.add_command(
            label="新しいファイル",
            command=lambda: self.file_tree._create_new_file(node)
        )
        self.menu.add_command(
            label="新しいフォルダ",
            command=lambda: self.file_tree._create_new_folder(node)
        )
        self.menu.add_separator()
    
    def _add_common_menu_items(self, node: FileTreeNode):
        """共通メニューアイテム"""
        self.menu.add_command(
            label="名前を変更",
            command=lambda: self.file_tree._rename_item(node)
        )
        self.menu.add_command(
            label="削除",
            command=lambda: self.file_tree._delete_item(node)
        )
        self.menu.add_separator()
        
        self.menu.add_command(
            label="コピー",
            command=lambda: self.file_tree._copy_item(node)
        )
        self.menu.add_command(
            label="切り取り",
            command=lambda: self.file_tree._cut_item(node)
        )
        
        if self.file_tree.clipboard_items:
            self.menu.add_command(
                label="貼り付け",
                command=lambda: self.file_tree._paste_items(node)
            )
        
        self.menu.add_separator()
        self.menu.add_command(
            label="プロパティ",
            command=lambda: self.file_tree._show_properties(node)
        )


class FileTree(ttk.Frame):
    """
    ファイルツリークラス
    プロジェクトファイルの階層表示と管理機能を提供
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # 設定管理
        self.config_manager = get_config_manager()
        
        # コールバック関数
        self.on_file_select: Optional[Callable[[str], None]] = None
        self.on_file_open: Optional[Callable[[str], None]] = None
        self.on_directory_change: Optional[Callable[[str], None]] = None
        self.on_file_create: Optional[Callable[[str], None]] = None
        self.on_file_delete: Optional[Callable[[str], None]] = None
        self.on_file_rename: Optional[Callable[[str, str], None]] = None
        
        # 状態管理
        self.root_path: Optional[Path] = None
        self.root_node: Optional[FileTreeNode] = None
        self.selected_node: Optional[FileTreeNode] = None
        self.expanded_nodes: Set[str] = set()
        self.clipboard_items: List[Tuple[FileTreeNode, str]] = []  # (node, operation)
        
        # フィルター
        self.filter = FileTreeFilter()
        
        # ノードマップ（高速検索用）
        self.node_map: Dict[str, FileTreeNode] = {}
        
        # UI作成
        self._create_widgets()
        self._setup_styles()
        self._setup_bindings()
        
        # コンテキストメニュー
        self.context_menu = FileTreeContextMenu(self)
        
        # ファイル監視
        self.file_watcher = None
        self.watch_thread = None
        
        self.logger.info("ファイルツリー初期化完了")
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # ツールバー
        self._create_toolbar()
        
        # ツリービュー
        self._create_tree_view()
        
        # ステータス表示
        self._create_status_area()
    
    def _create_toolbar(self):
        """ツールバーを作成"""
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # フォルダ選択
        ttk.Button(
            self.toolbar, 
            text="フォルダを開く", 
            command=self._select_root_folder,
            width=12
        ).pack(side=tk.LEFT, padx=(0, 2))
        
        # 更新
        ttk.Button(
            self.toolbar, 
            text="更新", 
            command=self._refresh_tree,
            width=8
        ).pack(side=tk.LEFT, padx=(0, 2))
        
        # フィルター切り替え
        self.show_hidden_var = tk.BooleanVar(value=self.filter.show_hidden_files)
        ttk.Checkbutton(
            self.toolbar,
            text="隠しファイル",
            variable=self.show_hidden_var,
            command=self._toggle_hidden_files
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # 検索
        ttk.Button(
            self.toolbar,
            text="検索",
            command=self._show_search_dialog,
            width=8
        ).pack(side=tk.RIGHT)
    
    def _create_tree_view(self):
        """ツリービューを作成"""
        # フレーム
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # ツリービュー
        self.tree = ttk.Treeview(
            tree_frame,
            columns=('size', 'modified'),
            show='tree headings'
        )
        
        # 列設定
        self.tree.heading('#0', text='名前', anchor=tk.W)
        self.tree.heading('size', text='サイズ', anchor=tk.E)
        self.tree.heading('modified', text='更新日時', anchor=tk.W)
        
        self.tree.column('#0', width=300, minwidth=200)
        self.tree.column('size', width=80, minwidth=60)
        self.tree.column('modified', width=150, minwidth=120)
        
        # スクロールバー
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 配置
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
    
    def _create_status_area(self):
        """ステータスエリアを作成"""
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_frame, text="フォルダが選択されていません")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.item_count_label = ttk.Label(self.status_frame, text="")
        self.item_count_label.pack(side=tk.RIGHT, padx=5)
    
    def _setup_styles(self):
        """スタイルを設定"""
        style = ttk.Style()
        
        # ファイルタイプ別のアイコン（テキストベース）
        self.file_icons = {
            'folder': '📁',
            'folder_open': '📂',
            'code': '📄',
            'text': '📝',
            'image': '🖼️',
            'file': '📄'
        }
        
        # タグ設定
        self.tree.tag_configure('directory', foreground='#0066CC')
        self.tree.tag_configure('code_file', foreground='#006600')
        self.tree.tag_configure('text_file', foreground='#333333')
        self.tree.tag_configure('image_file', foreground='#CC6600')
        self.tree.tag_configure('hidden_file', foreground='#999999')
        self.tree.tag_configure('selected', background='#E6F3FF')
    
    def _setup_bindings(self):
        """イベントバインドを設定"""
        # ツリービューイベント
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.tree.bind('<Double-Button-1>', self._on_tree_double_click)
        self.tree.bind('<Button-3>', self._on_tree_right_click)
        self.tree.bind('<<TreeviewOpen>>', self._on_tree_expand)
        self.tree.bind('<<TreeviewClose>>', self._on_tree_collapse)
        
        # キーボードショートカット
        self.tree.bind('<Return>', self._on_tree_enter)
        self.tree.bind('<Delete>', self._on_tree_delete)
        self.tree.bind('<F2>', self._on_tree_rename)
        self.tree.bind('<Control-c>', self._on_tree_copy)
        self.tree.bind('<Control-x>', self._on_tree_cut)
        self.tree.bind('<Control-v>', self._on_tree_paste)
        self.tree.bind('<F5>', lambda e: self._refresh_tree())
        
        # ドラッグ&ドロップ（簡易実装）
        self.tree.bind('<Button-1>', self._on_drag_start)
        self.tree.bind('<B1-Motion>', self._on_drag_motion)
        self.tree.bind('<ButtonRelease-1>', self._on_drag_end)
    
    # ===== 公開メソッド =====
    
    def set_root_path(self, path: str):
        """ルートパスを設定"""
        try:
            root_path = Path(path).resolve()
            if not root_path.exists():
                raise FileNotFoundError(f"パスが存在しません: {path}")
            
            if not root_path.is_dir():
                raise NotADirectoryError(f"ディレクトリではありません: {path}")
            
            self.root_path = root_path
            self._load_tree()
            
            # ファイル監視を開始
            self._start_file_watching()
            
            # コールバック実行
            if self.on_directory_change:
                self.on_directory_change(str(root_path))
            
            self.logger.info(f"ルートパス設定: {root_path}")
            
        except Exception as e:
            self.logger.error(f"ルートパス設定エラー: {e}")
            messagebox.showerror("エラー", f"フォルダの設定に失敗しました:\n{e}")
    
    def get_selected_path(self) -> Optional[str]:
        """選択されたパスを取得"""
        if self.selected_node:
            return str(self.selected_node.path)
        return None
    
    def get_selected_node(self) -> Optional[FileTreeNode]:
        """選択されたノードを取得"""
        return self.selected_node
    
    def refresh(self):
        """ツリーを更新"""
        self._refresh_tree()
    
    def expand_path(self, path: str):
        """指定パスまで展開"""
        try:
            target_path = Path(path).resolve()
            if not self.root_path or not target_path.is_relative_to(self.root_path):
                return
            
            # パスの各レベルを展開
            current_path = self.root_path
            current_node = self.root_node
            
            relative_path = target_path.relative_to(self.root_path)
            parts = relative_path.parts
            
            for part in parts:
                current_path = current_path / part
                
                # 子ノードを検索
                child_node = None
                for child in current_node.children:
                    if child.path.name == part:
                        child_node = child
                        break
                
                if child_node:
                    self._expand_node(child_node)
                    current_node = child_node
                else:
                    break
            
            # 最終ノードを選択
            if current_node and current_node.tree_item_id:
                self.tree.selection_set(current_node.tree_item_id)
                self.tree.see(current_node.tree_item_id)
                
        except Exception as e:
            self.logger.error(f"パス展開エラー: {e}")
    
    def find_files(self, pattern: str, case_sensitive: bool = False) -> List[FileTreeNode]:
        """ファイルを検索"""
        results = []
        
        def search_node(node: FileTreeNode):
            import fnmatch
            
            filename = node.display_name
            search_pattern = pattern if case_sensitive else pattern.lower()
            search_filename = filename if case_sensitive else filename.lower()
            
            if fnmatch.fnmatch(search_filename, search_pattern):
                results.append(node)
            
            for child in node.children:
                search_node(child)
        
        if self.root_node:
            search_node(self.root_node)
        
        return results
    
    def get_file_count(self) -> Dict[str, int]:
        """ファイル数統計を取得"""
        stats = {'files': 0, 'directories': 0, 'total_size': 0}
        
        def count_node(node: FileTreeNode):
            if node.is_directory:
                stats['directories'] += 1
            else:
                stats['files'] += 1
                stats['total_size'] += node.size
            
            for child in node.children:
                count_node(child)
        
        if self.root_node:
            count_node(self.root_node)
        
        return stats
    
    def set_filter(self, show_hidden: bool = None, file_patterns: List[str] = None, 
                   exclude_patterns: List[str] = None):
        """フィルターを設定"""
        if show_hidden is not None:
            self.filter.show_hidden_files = show_hidden
            self.show_hidden_var.set(show_hidden)
        
        if file_patterns is not None:
            self.filter.file_patterns = file_patterns
        
        if exclude_patterns is not None:
            self.filter.exclude_patterns = exclude_patterns
        
        self._refresh_tree()
    
    # ===== プライベートメソッド =====
    
    def _load_tree(self):
        """ツリーを読み込み"""
        if not self.root_path:
            return
        
        # 既存のツリーをクリア
        self.tree.delete(*self.tree.get_children())
        self.node_map.clear()
        
        # ルートノードを作成
        self.root_node = FileTreeNode(self.root_path)
        self.root_node.tree_item_id = self.tree.insert(
            '', 'end',
            text=self.root_node.display_name,
            values=('', ''),
            tags=('directory',),
            open=True
        )
        
        self.node_map[self.root_node.tree_item_id] = self.root_node
        
        # 子ノードを読み込み
        self._load_children(self.root_node)
        
        # ステータス更新
        self._update_status()
    
    def _load_children(self, parent_node: FileTreeNode, depth: int = 0):
        """子ノードを読み込み"""
        if not parent_node.is_directory or parent_node.is_loaded:
            return
        
        try:
            # ディレクトリ内容を取得
            items = list(parent_node.path.iterdir())
            
            # フィルタリングとソート
            filtered_items = []
            for item in items:
                child_node = FileTreeNode(item, parent_node)
                if self.filter.should_show_file(child_node, depth):
                    filtered_items.append(child_node)
            
            # ソート（ディレクトリ優先、名前順）
            filtered_items.sort(key=lambda x: (not x.is_directory, x.display_name.lower()))
            
            # ツリーアイテムを作成
            for child_node in filtered_items:
                # アイコンとタグを決定
                icon = self._get_file_icon(child_node)
                tags = self._get_file_tags(child_node)
                
                # サイズと更新日時
                size_text = self._format_file_size(child_node.size) if not child_node.is_directory else ''
                modified_text = child_node.modified_time.strftime('%Y-%m-%d %H:%M') if child_node.modified_time else ''
                
                # ツリーアイテムを挿入
                child_node.tree_item_id = self.tree.insert(
                    parent_node.tree_item_id, 'end',
                    text=f"{icon} {child_node.display_name}",
                    values=(size_text, modified_text),
                    tags=tags
                )
                
                parent_node.add_child(child_node)
                self.node_map[child_node.tree_item_id] = child_node
                
                # ディレクトリの場合は展開可能にする
                if child_node.is_directory:
                    # ダミーアイテムを追加（遅延読み込み用）
                    self.tree.insert(child_node.tree_item_id, 'end', text='読み込み中...')
            
            parent_node.is_loaded = True
            
        except PermissionError:
            self.logger.warning(f"アクセス権限なし: {parent_node.path}")
        except Exception as e:
            self.logger.error(f"子ノード読み込みエラー: {e}")
    
    def _get_file_icon(self, node: FileTreeNode) -> str:
        """ファイルアイコンを取得"""
        if node.is_directory:
            return self.file_icons['folder_open'] if node.is_expanded else self.file_icons['folder']
        else:
            file_type = node.get_file_type()
            return self.file_icons.get(file_type, self.file_icons['file'])
    
    def _get_file_tags(self, node: FileTreeNode) -> Tuple[str, ...]:
        """ファイルタグを取得"""
        tags = []
        
        if node.is_directory:
            tags.append('directory')
        else:
            file_type = node.get_file_type()
            if file_type == 'code':
                tags.append('code_file')
            elif file_type == 'text':
                tags.append('text_file')
            elif file_type == 'image':
                tags.append('image_file')
        
        if node.is_hidden():
            tags.append('hidden_file')
        
        return tuple(tags)
    
    def _format_file_size(self, size: int) -> str:
        """ファイルサイズをフォーマット"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
    
    def _refresh_tree(self):
        """ツリーを更新"""
        if self.root_path:
            # 展開状態を保存
            self._save_expanded_state()
            
            # ツリーを再読み込み
            self._load_tree()
            
            # 展開状態を復元
            self._restore_expanded_state()
    
    def _save_expanded_state(self):
        """展開状態を保存"""
        self.expanded_nodes.clear()
        
        def save_state(item_id):
            if self.tree.item(item_id, 'open'):
                node = self.node_map.get(item_id)
                if node:
                    self.expanded_nodes.add(str(node.path))
            
            for child_id in self.tree.get_children(item_id):
                save_state(child_id)
        
        for root_id in self.tree.get_children():
            save_state(root_id)
    
    def _restore_expanded_state(self):
        """展開状態を復元"""
        def restore_state(item_id):
            node = self.node_map.get(item_id)
            if node and str(node.path) in self.expanded_nodes:
                self._expand_node(node)
            
            for child_id in self.tree.get_children(item_id):
                restore_state(child_id)
        
        for root_id in self.tree.get_children():
            restore_state(root_id)
    
    def _update_status(self):
        """ステータスを更新"""
        if self.root_path:
            self.status_label.config(text=f"フォルダ: {self.root_path.name}")
            
            # ファイル数統計
            stats = self.get_file_count()
            count_text = f"ファイル: {stats['files']}, フォルダ: {stats['directories']}"
            if stats['total_size'] > 0:
                size_text = self._format_file_size(stats['total_size'])
                count_text += f", サイズ: {size_text}"
            
            self.item_count_label.config(text=count_text)
        else:
            self.status_label.config(text="フォルダが選択されていません")
            self.item_count_label.config(text="")
    
    # ===== イベントハンドラー =====
    
    def _on_tree_select(self, event):
        """ツリー選択イベント"""
        selection = self.tree.selection()
        if selection:
            item_id = selection[0]
            node = self.node_map.get(item_id)
            if node:
                self.selecte
    def _on_tree_select(self, event):
        """ツリー選択イベント"""
        selection = self.tree.selection()
        if selection:
            item_id = selection[0]
            node = self.node_map.get(item_id)
            if node:
                self.selected_node = node
                
                # 選択ハイライト
                self.tree.item(item_id, tags=self.tree.item(item_id, 'tags') + ('selected',))
                
                # コールバック実行
                if self.on_file_select:
                    self.on_file_select(str(node.path))
                
                self.logger.debug(f"ファイル選択: {node.path}")
    
    def _on_tree_double_click(self, event):
        """ツリーダブルクリックイベント"""
        if self.selected_node:
            if self.selected_node.is_directory:
                # ディレクトリの場合は展開/折りたたみ
                if self.selected_node.is_expanded:
                    self._collapse_node(self.selected_node)
                else:
                    self._expand_node(self.selected_node)
            else:
                # ファイルの場合は開く
                self._open_file(self.selected_node)
    
    def _on_tree_right_click(self, event):
        """ツリー右クリックイベント"""
        # クリック位置のアイテムを選択
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            node = self.node_map.get(item_id)
            if node:
                self.selected_node = node
                self.context_menu.show(event, node)
    
    def _on_tree_expand(self, event):
        """ツリー展開イベント"""
        item_id = self.tree.focus()
        node = self.node_map.get(item_id)
        if node and node.is_directory:
            self._expand_node(node)
    
    def _on_tree_collapse(self, event):
        """ツリー折りたたみイベント"""
        item_id = self.tree.focus()
        node = self.node_map.get(item_id)
        if node and node.is_directory:
            self._collapse_node(node)
    
    def _on_tree_enter(self, event):
        """Enterキーイベント"""
        if self.selected_node:
            if self.selected_node.is_directory:
                if self.selected_node.is_expanded:
                    self._collapse_node(self.selected_node)
                else:
                    self._expand_node(self.selected_node)
            else:
                self._open_file(self.selected_node)
    
    def _on_tree_delete(self, event):
        """Deleteキーイベント"""
        if self.selected_node:
            self._delete_item(self.selected_node)
    
    def _on_tree_rename(self, event):
        """F2キーイベント（名前変更）"""
        if self.selected_node:
            self._rename_item(self.selected_node)
    
    def _on_tree_copy(self, event):
        """Ctrl+Cイベント"""
        if self.selected_node:
            self._copy_item(self.selected_node)
    
    def _on_tree_cut(self, event):
        """Ctrl+Xイベント"""
        if self.selected_node:
            self._cut_item(self.selected_node)
    
    def _on_tree_paste(self, event):
        """Ctrl+Vイベント"""
        if self.selected_node and self.clipboard_items:
            self._paste_items(self.selected_node)
    
    def _on_drag_start(self, event):
        """ドラッグ開始イベント"""
        self.drag_start_item = self.tree.identify_row(event.y)
        self.drag_start_node = self.node_map.get(self.drag_start_item) if self.drag_start_item else None
    
    def _on_drag_motion(self, event):
        """ドラッグ中イベント"""
        if hasattr(self, 'drag_start_item') and self.drag_start_item:
            # ドラッグ先のアイテムをハイライト
            target_item = self.tree.identify_row(event.y)
            if target_item and target_item != self.drag_start_item:
                # ハイライト処理（簡易実装）
                pass
    
    def _on_drag_end(self, event):
        """ドラッグ終了イベント"""
        if hasattr(self, 'drag_start_node') and self.drag_start_node:
            target_item = self.tree.identify_row(event.y)
            target_node = self.node_map.get(target_item) if target_item else None
            
            if target_node and target_node != self.drag_start_node:
                self._move_item(self.drag_start_node, target_node)
        
        # ドラッグ状態をリセット
        if hasattr(self, 'drag_start_item'):
            delattr(self, 'drag_start_item')
        if hasattr(self, 'drag_start_node'):
            delattr(self, 'drag_start_node')
    
    # ===== ツールバーイベント =====
    
    def _select_root_folder(self):
        """ルートフォルダ選択"""
        folder_path = filedialog.askdirectory(
            title="プロジェクトフォルダを選択",
            initialdir=str(self.root_path) if self.root_path else None
        )
        
        if folder_path:
            self.set_root_path(folder_path)
    
    def _toggle_hidden_files(self):
        """隠しファイル表示切り替え"""
        self.filter.show_hidden_files = self.show_hidden_var.get()
        self._refresh_tree()
    
    def _show_search_dialog(self):
        """検索ダイアログ表示"""
        dialog = FileSearchDialog(self, self)
        dialog.show()
    
    # ===== ファイル操作 =====
    
    def _expand_node(self, node: FileTreeNode):
        """ノードを展開"""
        if not node.is_directory or node.is_expanded:
            return
        
        try:
            # ダミーアイテムを削除
            children = self.tree.get_children(node.tree_item_id)
            for child_id in children:
                child_node = self.node_map.get(child_id)
                if not child_node:  # ダミーアイテム
                    self.tree.delete(child_id)
            
            # 子ノードを読み込み（まだ読み込まれていない場合）
            if not node.is_loaded:
                self._load_children(node)
            
            # 展開状態を更新
            node.is_expanded = True
            self.tree.item(node.tree_item_id, open=True)
            
            # アイコンを更新
            current_text = self.tree.item(node.tree_item_id, 'text')
            icon = self._get_file_icon(node)
            new_text = f"{icon} {node.display_name}"
            self.tree.item(node.tree_item_id, text=new_text)
            
        except Exception as e:
            self.logger.error(f"ノード展開エラー: {e}")
            messagebox.showerror("エラー", f"フォルダの展開に失敗しました:\n{e}")
    
    def _collapse_node(self, node: FileTreeNode):
        """ノードを折りたたみ"""
        if not node.is_directory or not node.is_expanded:
            return
        
        try:
            # 折りたたみ状態を更新
            node.is_expanded = False
            self.tree.item(node.tree_item_id, open=False)
            
            # アイコンを更新
            icon = self._get_file_icon(node)
            new_text = f"{icon} {node.display_name}"
            self.tree.item(node.tree_item_id, text=new_text)
            
        except Exception as e:
            self.logger.error(f"ノード折りたたみエラー: {e}")
    
    def _open_file(self, node: FileTreeNode):
        """ファイルを開く"""
        if node.is_directory:
            return
        
        try:
            # コールバック実行
            if self.on_file_open:
                self.on_file_open(str(node.path))
            else:
                # デフォルトアプリケーションで開く
                import subprocess
                import sys
                
                if sys.platform == "win32":
                    os.startfile(str(node.path))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(node.path)])
                else:
                    subprocess.run(["xdg-open", str(node.path)])
            
            self.logger.info(f"ファイルを開く: {node.path}")
            
        except Exception as e:
            self.logger.error(f"ファイルオープンエラー: {e}")
            messagebox.showerror("エラー", f"ファイルを開けませんでした:\n{e}")
    
    def _open_in_editor(self, node: FileTreeNode):
        """エディタでファイルを開く"""
        if node.is_directory:
            return
        
        # コールバック実行（エディタ用）
        if self.on_file_open:
            self.on_file_open(str(node.path))
    
    def _create_new_file(self, parent_node: FileTreeNode):
        """新しいファイルを作成"""
        if not parent_node.is_directory:
            parent_node = parent_node.parent
        
        if not parent_node:
            return
        
        # ファイル名入力ダイアログ
        dialog = FileNameDialog(self, "新しいファイル", "ファイル名を入力してください:")
        filename = dialog.get_result()
        
        if filename:
            try:
                new_file_path = parent_node.path / filename
                
                # ファイルが既に存在するかチェック
                if new_file_path.exists():
                    messagebox.showerror("エラー", "同名のファイルが既に存在します")
                    return
                
                # ファイルを作成
                new_file_path.touch()
                
                # ツリーを更新
                self._refresh_node(parent_node)
                
                # コールバック実行
                if self.on_file_create:
                    self.on_file_create(str(new_file_path))
                
                self.logger.info(f"ファイル作成: {new_file_path}")
                
            except Exception as e:
                self.logger.error(f"ファイル作成エラー: {e}")
                messagebox.showerror("エラー", f"ファイルの作成に失敗しました:\n{e}")
    
    def _create_new_folder(self, parent_node: FileTreeNode):
        """新しいフォルダを作成"""
        if not parent_node.is_directory:
            parent_node = parent_node.parent
        
        if not parent_node:
            return
        
        # フォルダ名入力ダイアログ
        dialog = FileNameDialog(self, "新しいフォルダ", "フォルダ名を入力してください:")
        foldername = dialog.get_result()
        
        if foldername:
            try:
                new_folder_path = parent_node.path / foldername
                
                # フォルダが既に存在するかチェック
                if new_folder_path.exists():
                    messagebox.showerror("エラー", "同名のフォルダが既に存在します")
                    return
                
                # フォルダを作成
                new_folder_path.mkdir()
                
                # ツリーを更新
                self._refresh_node(parent_node)
                
                self.logger.info(f"フォルダ作成: {new_folder_path}")
                
            except Exception as e:
                self.logger.error(f"フォルダ作成エラー: {e}")
                messagebox.showerror("エラー", f"フォルダの作成に失敗しました:\n{e}")
    
    def _rename_item(self, node: FileTreeNode):
        """アイテムの名前を変更"""
        # 現在の名前を取得
        current_name = node.display_name
        
        # 新しい名前入力ダイアログ
        dialog = FileNameDialog(self, "名前の変更", "新しい名前を入力してください:", current_name)
        new_name = dialog.get_result()
        
        if new_name and new_name != current_name:
            try:
                old_path = node.path
                new_path = node.path.parent / new_name
                
                # 同名のファイル/フォルダが既に存在するかチェック
                if new_path.exists():
                    messagebox.showerror("エラー", "同名のファイル/フォルダが既に存在します")
                    return
                
                # 名前を変更
                old_path.rename(new_path)
                
                # ノード情報を更新
                node.path = new_path
                node.display_name = new_name
                
                # ツリー表示を更新
                icon = self._get_file_icon(node)
                self.tree.item(node.tree_item_id, text=f"{icon} {new_name}")
                
                # コールバック実行
                if self.on_file_rename:
                    self.on_file_rename(str(old_path), str(new_path))
                
                self.logger.info(f"名前変更: {old_path} -> {new_path}")
                
            except Exception as e:
                self.logger.error(f"名前変更エラー: {e}")
                messagebox.showerror("エラー", f"名前の変更に失敗しました:\n{e}")
    
    def _delete_item(self, node: FileTreeNode):
        """アイテムを削除"""
        # 確認ダイアログ
        item_type = "フォルダ" if node.is_directory else "ファイル"
        if not messagebox.askyesno("確認", f"{item_type} '{node.display_name}' を削除しますか？"):
            return
        
        try:
            path_to_delete = node.path
            
            # 削除実行
            if node.is_directory:
                import shutil
                shutil.rmtree(path_to_delete)
            else:
                path_to_delete.unlink()
            
            # ツリーから削除
            self.tree.delete(node.tree_item_id)
            
            # ノードマップから削除
            if node.tree_item_id in self.node_map:
                del self.node_map[node.tree_item_id]
            
            # 親ノードから削除
            if node.parent:
                node.parent.remove_child(node)
            
            # 選択状態をクリア
            if self.selected_node == node:
                self.selected_node = None
            
            # コールバック実行
            if self.on_file_delete:
                self.on_file_delete(str(path_to_delete))
            
            self.logger.info(f"削除: {path_to_delete}")
            
        except Exception as e:
            self.logger.error(f"削除エラー: {e}")
            messagebox.showerror("エラー", f"削除に失敗しました:\n{e}")
    
    def _copy_item(self, node: FileTreeNode):
        """アイテムをコピー"""
        self.clipboard_items = [(node, 'copy')]
        self.logger.debug(f"コピー: {node.path}")
    
    def _cut_item(self, node: FileTreeNode):
        """アイテムを切り取り"""
        self.clipboard_items = [(node, 'cut')]
        self.logger.debug(f"切り取り: {node.path}")
    
    def _paste_items(self, target_node: FileTreeNode):
        """アイテムを貼り付け"""
        if not self.clipboard_items:
            return
        
        # 貼り付け先がディレクトリでない場合は親ディレクトリを使用
        if not target_node.is_directory:
            target_node = target_node.parent
        
        if not target_node:
            return
        
        try:
            for source_node, operation in self.clipboard_items:
                source_path = source_node.path
                target_path = target_node.path / source_path.name
                
                # 同名ファイルが存在する場合は名前を変更
                counter = 1
                original_target_path = target_path
                while target_path.exists():
                    if source_path.is_dir():
                        target_path = target_node.path / f"{original_target_path.stem}_copy{counter}"
                    else:
                        target_path = target_node.path / f"{original_target_path.stem}_copy{counter}{original_target_path.suffix}"
                    counter += 1
                
                # コピーまたは移動を実行
                if operation == 'copy':
                    if source_path.is_dir():
                        import shutil
                        shutil.copytree(source_path, target_path)
                    else:
                        import shutil
                        shutil.copy2(source_path, target_path)
                elif operation == 'cut':
                    source_path.rename(target_path)
                    # 切り取りの場合は元のノードを削除
                    if source_node.tree_item_id:
                        self.tree.delete(source_node.tree_item_id)
                        if source_node.tree_item_id in self.node_map:
                            del self.node_map[source_node.tree_item_id]
                
                self.logger.info(f"{operation}: {source_path} -> {target_path}")
            
            # ツリーを更新
            self._refresh_node(target_node)
            
            # 切り取りの場合はクリップボードをクリア
            if any(op == 'cut' for _, op in self.clipboard_items):
                self.clipboard_items.clear()
            
        except Exception as e:
            self.logger.error(f"貼り付けエラー: {e}")
            messagebox.showerror("エラー", f"貼り付けに失敗しました:\n{e}")
    
    def _move_item(self, source_node: FileTreeNode, target_node: FileTreeNode):
        """アイテムを移動（ドラッグ&ドロップ）"""
        if not target_node.is_directory:
            target_node = target_node.parent
        
        if not target_node or source_node == target_node:
            return
        
        try:
            source_path = source_node.path
            target_path = target_node.path / source_path.name
            
            # 同名ファイルが存在する場合は確認
            if target_path.exists():
                if not messagebox.askyesno("確認", f"'{target_path.name}' は既に存在します。置き換えますか？"):
                    return
            
            # 移動実行
            source_path.rename(target_path)
            
            # ツリーを更新
            self._refresh_tree()
            
            self.logger.info(f"移動: {source_path} -> {target_path}")
            
        except Exception as e:
            self.logger.error(f"移動エラー: {e}")
            messagebox.showerror("エラー", f"移動に失敗しました:\n{e}")
    
    def _show_properties(self, node: FileTreeNode):
        """プロパティを表示"""
        dialog = FilePropertiesDialog(self, node)
        dialog.show()
    
    def _refresh_node(self, node: FileTreeNode):
        """特定のノードを更新"""
        if node.is_directory:
            # 子ノードをクリア
            for child in node.children:
                if child.tree_item_id:
                    self.tree.delete(child.tree_item_id)
                    if child.tree_item_id in self.node_map:
                        del self.node_map[child.tree_item_id]
            
            node.children.clear()
            node.is_loaded = False
            
            # 再読み込み
            if node.is_expanded:
                self._load_children(node)
    
    # ===== ファイル監視 =====
    
    def _start_file_watching(self):
        """ファイル監視を開始"""
        if not self.root_path:
            return
        
        try:
            # watchdogが利用可能な場合のみファイル監視を開始
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class TreeFileHandler(FileSystemEventHandler):
                def __init__(self, file_tree):
                    self.file_tree = file_tree
                
                def on_any_event(self, event):
                    # UIスレッドで更新を実行
                    self.file_tree.after_idle(self.file_tree._refresh_tree)
            
            if self.file_watcher:
                self.file_watcher.stop()
                self.file_watcher.join()
            
            self.file_watcher = Observer()
            self.file_watcher.schedule(
                TreeFileHandler(self), 
                str(self.root_path), 
                recursive=True
            )
            self.file_watcher.start()
            
            self.logger.info("ファイル監視開始")
            
        except ImportError:
            self.logger.warning("watchdogが利用できません。ファイル監視は無効です")
        except Exception as e:
            self.logger.error(f"ファイル監視開始エラー: {e}")
    
    def _stop_file_watching(self):
        """ファイル監視を停止"""
        if self.file_watcher:
            try:
                self.file_watcher.stop()
                self.file_watcher.join()
                self.file_watcher = None
                self.logger.info("ファイル監視停止")
            except Exception as e:
                self.logger.error(f"ファイル監視停止エラー: {e}")
    
    def destroy(self):
        """クリーンアップ"""
        self._stop_file_watching()
        super().destroy()


class FileNameDialog:
    """ファイル名入力ダイアログ"""
    
    def __init__(self, parent, title: str, message: str, initial_value: str = ""):
        self.parent = parent
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets(message, initial_value)
        self._center_dialog()
        
        self.entry.focus()
        self.entry.select_range(0, tk.END)
    
    def _create_widgets(self, message: str, initial_value: str):
        """ウィジェットを作成"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # メッセージ
        ttk.Label(main_frame, text=message).pack(anchor=tk.W, pady=(0, 10))
        
        # 入力欄
        self.name_var = tk.StringVar(value=initial_value)
        self.entry = ttk.Entry(main_frame, textvariable=self.name_var, width=40)
        self.entry.pack(fill=tk.X, pady=(0, 20))
        
        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="キャンセル", command=self._cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="OK", command=self._ok).pack(side=tk.RIGHT)
        
        # キーバインド
        self.entry.bind('<Return>', lambda e: self._ok())
        self.dialog.bind('<Escape>', lambda e: self._cancel())
    
    def _center_dialog(self):
        """ダイアログを中央に配置"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _ok(self):
        """OK処理"""
        name = self.name_var.get().strip()
        if name:
            # ファイル名の妥当性チェック
            invalid_chars = '<>:"/\\|?*'
            if any(char in name for char in invalid_chars):
                messagebox.showerror("エラー", "ファイル名に使用できない文字が含まれています")
                return
            
            self.result = name
            self.dialog.destroy()
        else:
            messagebox.showerror("エラー", "ファイル名を入力してください")
    
    def _cancel(self):
        """キャンセル処理"""
        self.result = None
        self.dialog.destroy()
    
    def get_result(self) -> Optional[str]:
        """結果を取得"""
        self.dialog.wait_window()
        return self.result


class FilePropertiesDialog:
    """ファイルプロパティダイアログ"""
    
    def __init__(self, parent, node: FileTreeNode):
        self.parent = parent
        self.node = node
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"プロパティ - {node.display_name}")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._center_dialog()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 基本情報
        info_frame = ttk.LabelFrame(main_frame, text="基本情報", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 名前
        ttk.Label(info_frame, text="名前:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(info_frame, text=self.node.display_name).grid(row=0, column=1, sticky=tk.W)
        
        # タイプ
        item_type = "フォルダ" if self.node.is_directory else "ファイル"
        ttk.Label(info_frame, text="タイプ:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(info_frame, text=item_type).grid(row=1, column=1, sticky=tk.W)
        
        # パス
        ttk.Label(info_frame, text="場所:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(info_frame, text=str(self.node.path.parent)).grid(row=2, column=1, sticky=tk.W)
        
        # サイズ（ファイルの場合）
        if not self.node.is_directory:
            ttk.Label(info_frame, text="サイズ:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
            size_text = self._format_file_size(self.node.size)
            ttk.Label(info_frame, text=size_text).grid(row=3, column=1, sticky=tk.W)
        
        # 更新日時
        if self.node.modified_time:
            ttk.Label(info_frame, text="更新日時:").grid(row=4, column=0, sticky=tk.W, padx=(0, 10))
            time_text = self.node.modified_time.strftime('%Y-%m-%d %H:%M:%S')
            ttk.Label(info_frame, text=time_text).grid(row=4, column=1, sticky=tk.W)
        
        info_frame.columnconfigure(1, weight=1)
        
        # 閉じるボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="閉じる", command=self.dialog.destroy).pack(side=tk.RIGHT)
    
    def _center_dialog(self):
        """ダイアログを中央に配置"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _format_file_size(self, size: int) -> str:
        """ファイルサイズをフォーマット"""
        if size < 1024:
            return f"{size} バイト"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB ({size:,} バイト)"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB ({size:,} バイト)"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB ({size:,} バイト)"
    
    def show(self):
        """ダイアログを表示"""
        self.dialog.wait_window()


class FileSearchDialog:
    """ファイル検索ダイアログ"""
    
    def __init__(self, parent, file_tree: FileTree):
        self.parent = parent
        self.file_tree = file_tree
        self.dialog = None
        self.search_results = []
    
    def show(self):
        """検索ダイアログを表示"""
        if self.dialog:
            self.dialog.lift()
            return
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("ファイル検索")
        self.dialog.geometry("500x400")
        self.dialog.transient(self.parent)
        
        self._create_widgets()
        self._center_dialog()
        
        self.search_entry.focus()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 検索条件
        search_frame = ttk.LabelFrame(main_frame, text="検索条件", padding=10)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 検索パターン
        ttk.Label(search_frame, text="ファイル名:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))
        
        # 検索ボタン
        ttk.Button(search_frame, text="検索", command=self._search).grid(row=0, column=2)
        
        # オプション
        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(search_frame, text="大文字小文字を区別", 
                       variable=self.case_sensitive_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        search_frame.columnconfigure(1, weight=1)
        
        # 検索結果
        result_frame = ttk.LabelFrame(main_frame, text="検索結果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 結果リスト
        self.result_tree = ttk.Treeview(
            result_frame,
            columns=('path', 'size', 'modified'),
            show='tree headings'
        )
        
        self.result_tree.heading('#0', text='名前', anchor=tk.W)
        self.result_tree.heading('path', text='パス', anchor=tk.W)
        self.result_tree.heading('size', text='サイズ', anchor=tk.E)
        self.result_tree.heading('modified', text='更新日時', anchor=tk.W)
        
        self.result_tree.column('#0', width=150)
        self.result_tree.column('path', width=200)
        self.result_tree.column('size', width=80)
        self.result_tree.column('modified', width=120)
        
        # スクロールバー
        result_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scrollbar.set)
        
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # イベントバインド
        self.result_tree.bind('<Double-Button-1>', self._on_result_double_click)
        self.search_entry.bind('<Return>', lambda e: self._search())
        self.dialog.bind('<Escape>', lambda e: self._close())
        
        # 閉じるボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="閉じる", command=self._close).pack(side=tk.RIGHT)
    
    def _center_dialog(self):
        """ダイアログを中央に配置"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _search(self):
        """検索実行"""
        pattern = self.search_var.get().strip()
        if not pattern:
            return
        
        # 結果をクリア
        self.result_tree.delete(*self.result_tree.get_children())
        self.search_results.clear()
        
        try:
            # ワイルドカードパターンに変換
            if '*' not in pattern and '?' not in pattern:
                pattern = f"*{pattern}*"
            
            # 検索実行
            case_sensitive = self.case_sensitive_var.get()
            results = self.file_tree.find_files(pattern, case_sensitive)
            
            # 結果を表示
            for node in results:
                # アイコン
                icon = self.file_tree._get_file_icon(node)
                
                # 相対パス
                if self.file_tree.root_path:
                    rel_path = node.get_relative_path(self.file_tree.root_path)
                else:
                    rel_path = str(node.path)
                
                # サイズ
                size_text = self.file_tree._format_file_size(node.size) if not node.is_directory else ''
                
                # 更新日時
                modified_text = node.modified_time.strftime('%Y-%m-%d %H:%M') if node.modified_time else ''
                
                # ツリーアイテムを追加
                item_id = self.result_tree.insert(
                    '', 'end',
                    text=f"{icon} {node.display_name}",
                    values=(rel_path, size_text, modified_text)
                )
                
                self.search_results.append((item_id, node))
            
            # 結果数を表示
            count = len(results)
            self.dialog.title(f"ファイル検索 - {count} 件見つかりました")
            
        except Exception as e:
            messagebox.showerror("検索エラー", f"検索中にエラーが発生しました:\n{e}")
    
    def _on_result_double_click(self, event):
        """検索結果ダブルクリック"""
        selection = self.result_tree.selection()
        if selection:
            item_id = selection[0]
            
            # 対応するノードを検索
            for result_id, node in self.search_results:
                if result_id == item_id:
                    # ファイルツリーで該当パスを展開・選択
                    self.file_tree.expand_path(str(node.path))
                    
                    # ファイルを開く
                    if not node.is_directory:
                        self.file_tree._open_file(node)
                    
                    break
    
    def _close(self):
        """ダイアログを閉じる"""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None


# 使用例とテスト関数
def test_file_tree():
    """ファイルツリーのテスト"""
    root = tk.Tk()
    root.title("File Tree Test")
    root.geometry("800x600")
    
    # ファイルツリーを作成
    file_tree = FileTree(root)
    file_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # コールバック設定
    def on_file_select(path):
        print(f"File selected: {path}")
    
    def on_file_open(path):
        print(f"File opened: {path}")
        # 実際のアプリケーションではエディタで開く処理を実装
    
    def on_directory_change(path):
        print(f"Directory changed: {path}")
    
    def on_file_create(path):
        print(f"File created: {path}")
    
    def on_file_delete(path):
        print(f"File deleted: {path}")
    
    def on_file_rename(old_path, new_path):
        print(f"File renamed: {old_path} -> {new_path}")
    
    # コールバックを設定
    file_tree.on_file_select = on_file_select
    file_tree.on_file_open = on_file_open
    file_tree.on_directory_change = on_directory_change
    file_tree.on_file_create = on_file_create
    file_tree.on_file_delete = on_file_delete
    file_tree.on_file_rename = on_file_rename
    
    # テスト用のプロジェクトフォルダを設定
    import tempfile
    import os
    
    # 一時ディレクトリを作成
    test_dir = Path(tempfile.mkdtemp(prefix="file_tree_test_"))
    
    # テスト用のファイル構造を作成
    (test_dir / "src").mkdir()
    (test_dir / "src" / "main.py").write_text("print('Hello, World!')")
    (test_dir / "src" / "utils.py").write_text("def helper(): pass")
    
    (test_dir / "docs").mkdir()
    (test_dir / "docs" / "README.md").write_text("# Test Project")
    
    (test_dir / "tests").mkdir()
    (test_dir / "tests" / "test_main.py").write_text("import unittest")
    
    (test_dir / "config.json").write_text('{"name": "test"}')
    (test_dir / ".gitignore").write_text("*.pyc\n__pycache__/")
    
    # ファイルツリーにテストディレクトリを設定
    file_tree.set_root_path(str(test_dir))
    
    # クリーンアップ関数
    def cleanup():
        import shutil
        try:
            shutil.rmtree(test_dir)
        except:
            pass
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", cleanup)
    
    print(f"Test directory created: {test_dir}")
    print("ファイルツリーをテストしてください:")
    print("- フォルダの展開/折りたたみ")
    print("- ファイルの選択とダブルクリック")
    print("- 右クリックメニュー")
    print("- 新しいファイル/フォルダの作成")
    print("- 名前の変更")
    print("- ファイルの削除")
    print("- 検索機能")
    
    root.mainloop()


if __name__ == "__main__":
    test_file_tree()
