# src/ui/file_manager.py
"""
ファイル管理UIモジュール
ファイルの読み込み、保存、管理を行うGUIコンポーネント
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
import threading
from datetime import datetime
import shutil

from src.core.logger import get_logger
from src.file_processing.file_loader import get_file_loader

logger = get_logger(__name__)

class FileManagerWidget:
    """ファイル管理ウィジェットクラス"""
    
    def __init__(self, parent: tk.Widget, on_file_loaded: Optional[Callable] = None):
        """
        初期化
        
        Args:
            parent: 親ウィジェット
            on_file_loaded: ファイル読み込み完了時のコールバック関数
        """
        from src.core.config_manager import get_config
        self.parent = parent
        self.on_file_loaded = on_file_loaded
        self.logger = get_logger(self.__class__.__name__)
        
        # 設定とファイルローダーを取得
        self.config = get_config()
        self.file_loader = get_file_loader()
        
        # 現在のファイル情報
        self.current_files: Dict[str, Dict[str, Any]] = {}
        self.selected_file: Optional[str] = None
        
        # UI要素
        self.main_frame = None
        self.file_tree = None
        self.file_info_frame = None
        self.progress_var = None
        self.progress_bar = None
        self.status_label = None
        
        # 作業ディレクトリ
        self.work_directory = self.config.get('work_directory', os.getcwd())
        
        self._create_widgets()
        self._load_recent_files()
        
        self.logger.info("FileManagerWidget を初期化しました")
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        try:
            # メインフレーム
            self.main_frame = ttk.Frame(self.parent)
            self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # ツールバー
            self._create_toolbar()
            
            # ファイルツリーとプレビューのペイン
            paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
            paned_window.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
            
            # 左側: ファイルツリー
            tree_frame = ttk.Frame(paned_window)
            paned_window.add(tree_frame, weight=1)
            
            self._create_file_tree(tree_frame)
            
            # 右側: ファイル情報とプレビュー
            info_frame = ttk.Frame(paned_window)
            paned_window.add(info_frame, weight=1)
            
            self._create_file_info(info_frame)
            
            # ステータスバー
            self._create_status_bar()
            
        except Exception as e:
            self.logger.error(f"ウィジェット作成エラー: {e}")
            raise
    
    def _create_toolbar(self):
        """ツールバーを作成"""
        try:
            toolbar = ttk.Frame(self.main_frame)
            toolbar.pack(fill=tk.X, pady=(0, 5))
            
            # ファイル操作ボタン
            ttk.Button(toolbar, text="ファイルを開く", 
                      command=self.open_file).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(toolbar, text="フォルダを開く", 
                      command=self.open_folder).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
            
            ttk.Button(toolbar, text="更新", 
                      command=self.refresh).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(toolbar, text="削除", 
                      command=self.remove_file).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(toolbar, text="すべてクリア", 
                      command=self.clear_all).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
            
            # 作業ディレクトリ選択
            ttk.Label(toolbar, text="作業ディレクトリ:").pack(side=tk.LEFT, padx=(0, 5))
            
            self.work_dir_var = tk.StringVar(value=self.work_directory)
            work_dir_entry = ttk.Entry(toolbar, textvariable=self.work_dir_var, width=30)
            work_dir_entry.pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(toolbar, text="参照", 
                      command=self.browse_work_directory).pack(side=tk.LEFT)
            
        except Exception as e:
            self.logger.error(f"ツールバー作成エラー: {e}")
            raise
    
    def _create_file_tree(self, parent):
        """ファイルツリーを作成"""
        try:
            # ツリービューフレーム
            tree_frame = ttk.Frame(parent)
            tree_frame.pack(fill=tk.BOTH, expand=True)
            
            # ラベル
            ttk.Label(tree_frame, text="読み込み済みファイル").pack(anchor=tk.W, pady=(0, 5))
            
            # ツリービュー
            columns = ('size', 'type', 'modified', 'status')
            self.file_tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings')
            
            # ヘッダー設定
            self.file_tree.heading('#0', text='ファイル名')
            self.file_tree.heading('size', text='サイズ')
            self.file_tree.heading('type', text='種類')
            self.file_tree.heading('modified', text='更新日時')
            self.file_tree.heading('status', text='状態')
            
            # 列幅設定
            self.file_tree.column('#0', width=200, minwidth=150)
            self.file_tree.column('size', width=80, minwidth=60)
            self.file_tree.column('type', width=80, minwidth=60)
            self.file_tree.column('modified', width=120, minwidth=100)
            self.file_tree.column('status', width=80, minwidth=60)
            
            # スクロールバー
            tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
            self.file_tree.configure(yscrollcommand=tree_scroll.set)
            
            # 配置
            self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            # イベントバインド
            self.file_tree.bind('<<TreeviewSelect>>', self._on_file_selected)
            self.file_tree.bind('<Double-1>', self._on_file_double_click)
            self.file_tree.bind('<Button-3>', self._on_file_right_click)
            
        except Exception as e:
            self.logger.error(f"ファイルツリー作成エラー: {e}")
            raise
    
    def _create_file_info(self, parent):
        """ファイル情報パネルを作成"""
        try:
            # ファイル情報フレーム
            self.file_info_frame = ttk.Frame(parent)
            self.file_info_frame.pack(fill=tk.BOTH, expand=True)
            
            # ラベル
            ttk.Label(self.file_info_frame, text="ファイル情報").pack(anchor=tk.W, pady=(0, 5))
            
            # 情報表示用のノートブック
            info_notebook = ttk.Notebook(self.file_info_frame)
            info_notebook.pack(fill=tk.BOTH, expand=True)
            
            # 基本情報タブ
            basic_frame = ttk.Frame(info_notebook, padding="10")
            info_notebook.add(basic_frame, text="基本情報")
            
            self.info_text = tk.Text(basic_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
            info_scroll = ttk.Scrollbar(basic_frame, orient=tk.VERTICAL, command=self.info_text.yview)
            self.info_text.configure(yscrollcommand=info_scroll.set)
            
            self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            # プレビュータブ
            preview_frame = ttk.Frame(info_notebook, padding="10")
            info_notebook.add(preview_frame, text="プレビュー")
            
            self.preview_text = tk.Text(preview_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
            preview_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
            self.preview_text.configure(yscrollcommand=preview_scroll.set)
            
            self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 操作ボタンフレーム
            button_frame = ttk.Frame(self.file_info_frame)
            button_frame.pack(fill=tk.X, pady=(5, 0))
            
            ttk.Button(button_frame, text="再読み込み", 
                      command=self.reload_selected_file).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(button_frame, text="エクスポート", 
                      command=self.export_selected_file).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(button_frame, text="チャットに送信", 
                      command=self.send_to_chat).pack(side=tk.LEFT, padx=(0, 5))
            
        except Exception as e:
            self.logger.error(f"ファイル情報パネル作成エラー: {e}")
            raise
    
    def _create_status_bar(self):
        """ステータスバーを作成"""
        try:
            status_frame = ttk.Frame(self.main_frame)
            status_frame.pack(fill=tk.X, pady=(5, 0))
            
            # ステータスラベル
            self.status_label = ttk.Label(status_frame, text="準備完了")
            self.status_label.pack(side=tk.LEFT)
            
            # プログレスバー
            self.progress_var = tk.DoubleVar()
            self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, 
                                              length=200, mode='determinate')
            self.progress_bar.pack(side=tk.RIGHT, padx=(5, 0))
            
        except Exception as e:
            self.logger.error(f"ステータスバー作成エラー: {e}")
            raise
    
    def _load_recent_files(self):
        """最近使用したファイルを読み込み"""
        try:
            recent_files = self.config.get('recent_files', [])
            
            for file_path in recent_files:
                if os.path.exists(file_path):
                    self._add_file_to_tree(file_path, status="未読み込み")
            
            self.logger.debug(f"{len(recent_files)} 個の最近のファイルを読み込みました")
            
        except Exception as e:
            self.logger.error(f"最近のファイル読み込みエラー: {e}")
    
    def open_file(self):
        """ファイルを開く"""
        try:
            file_paths = filedialog.askopenfilenames(
                title="ファイルを選択",
                initialdir=self.work_directory,
                filetypes=[
                    ("すべてのサポートファイル", "*.txt *.md *.py *.js *.html *.css *.json *.xml *.csv"),
                    ("テキストファイル", "*.txt"),
                    ("Markdownファイル", "*.md"),
                    ("Pythonファイル", "*.py"),
                    ("JavaScriptファイル", "*.js"),
                    ("HTMLファイル", "*.html"),
                    ("CSSファイル", "*.css"),
                    ("JSONファイル", "*.json"),
                    ("XMLファイル", "*.xml"),
                    ("CSVファイル", "*.csv"),
                    ("すべてのファイル", "*.*")
                ]
            )
            
            if file_paths:
                for file_path in file_paths:
                    self.load_file(file_path)
                
        except Exception as e:
            self.logger.error(f"ファイル選択エラー: {e}")
            messagebox.showerror("エラー", f"ファイルの選択に失敗しました: {e}")
    
    def open_folder(self):
        """フォルダを開く"""
        try:
            folder_path = filedialog.askdirectory(
                title="フォルダを選択",
                initialdir=self.work_directory
            )
            
            if folder_path:
                self.load_folder(folder_path)
                
        except Exception as e:
            self.logger.error(f"フォルダ選択エラー: {e}")
            messagebox.showerror("エラー", f"フォルダの選択に失敗しました: {e}")
    
    def load_file(self, file_path: str):
        """ファイルを読み込み"""
        try:
            if file_path in self.current_files:
                messagebox.showinfo("情報", "このファイルは既に読み込まれています。")
                return
            
            # ファイルをツリーに追加
            self._add_file_to_tree(file_path, status="読み込み中")
            
            # バックグラウンドで読み込み
            threading.Thread(target=self._load_file_async, args=(file_path,), daemon=True).start()
            
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー {file_path}: {e}")
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました: {e}")
    
    def _load_file_async(self, file_path: str):
        """非同期でファイルを読み込み"""
        try:
            # プログレスバーを開始
            self.main_frame.after(0, lambda: self._set_status("ファイルを読み込み中..."))
            self.main_frame.after(0, lambda: self.progress_bar.configure(mode='indeterminate'))
            self.main_frame.after(0, lambda: self.progress_bar.start())
            
            # ファイルローダーで読み込み
            file_content = self.file_loader.load_file(file_path)
            
            # ファイル情報を作成
            file_info = {
                'path': file_path,
                'name': os.path.basename(file_path),
                'size': os.path.getsize(file_path),
                'type': Path(file_path).suffix.lower(),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)),
                'content': file_content,
                'status': '読み込み完了'
            }
            
            # メインスレッドで結果を処理
            self.main_frame.after(0, lambda: self._on_file_loaded(file_path, file_info))
            
        except Exception as e:
            self.logger.error(f"非同期ファイル読み込みエラー {file_path}: {e}")
            self.main_frame.after(0, lambda: self._on_file_load_error(file_path, str(e)))
    
    def _on_file_loaded(self, file_path: str, file_info: Dict[str, Any]):
        """ファイル読み込み完了時の処理"""
        try:
            # ファイル情報を保存
            self.current_files[file_path] = file_info
            
            # ツリーを更新
            self._update_file_in_tree(file_path, file_info)
            
            # 最近のファイルリストを更新
            self._update_recent_files(file_path)
            
            # コールバック関数を呼び出し
            if self.on_file_loaded:
                self.on_file_loaded(file_path, file_info)
            
            # ステータスを更新
            self._set_status(f"ファイルを読み込みました: {os.path.basename(file_path)}")
            self.progress_bar.stop()
            self.progress_bar.configure(mode='determinate')
            self.progress_var.set(0)
            
            self.logger.info(f"ファイルを読み込みました: {file_path}")
            
        except Exception as e:
            self.logger.error(f"ファイル読み込み完了処理エラー: {e}")
    
    def _on_file_load_error(self, file_path: str, error_message: str):
        """ファイル読み込みエラー時の処理"""
        try:
            # ツリーから削除
            self._remove_file_from_tree(file_path)
            
            # エラーメッセージを表示
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{file_path}\n\nエラー: {error_message}")
            
            # ステータスを更新
            self._set_status("ファイル読み込みエラー")
            self.progress_bar.stop()
            self.progress_bar.configure(mode='determinate')
            self.progress_var.set(0)
            
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー処理エラー: {e}")
    
    def load_folder(self, folder_path: str):
        """フォルダ内のファイルを読み込み"""
        try:
            supported_extensions = {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'}
            
            files_to_load = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if Path(file_path).suffix.lower() in supported_extensions:
                        files_to_load.append(file_path)
            
            if not files_to_load:
                messagebox.showinfo("情報", "サポートされているファイルが見つかりませんでした。")
                return
            
            # 確認ダイアログ
            result = messagebox.askyesno(
                "確認", 
                f"{len(files_to_load)} 個のファイルが見つかりました。\nすべて読み込みますか？"
            )
            
            if result:
                for file_path in files_to_load:
                    if file_path not in self.current_files:
                        self.load_file(file_path)
            
        except Exception as e:
            self.logger.error(f"フォルダ読み込みエラー {folder_path}: {e}")
            messagebox.showerror("エラー", f"フォルダの読み込みに失敗しました: {e}")
    
    def _add_file_to_tree(self, file_path: str, status: str = "未読み込み"):
        """ファイルをツリーに追加"""
        try:
            file_name = os.path.basename(file_path)
            file_size = self._format_file_size(os.path.getsize(file_path)) if os.path.exists(file_path) else "不明"
            file_type = Path(file_path).suffix.lower() or "不明"
            modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M") if os.path.exists(file_path) else "不明"
            
            item_id = self.file_tree.insert('', tk.END, text=file_name, 
                                          values=(file_size, file_type, modified_time, status))
            
            # ファイルパスをアイテムIDにマッピング
            self.file_tree.set(item_id, 'path', file_path)
            
        except Exception as e:
            self.logger.error(f"ツリーへのファイル追加エラー {file_path}: {e}")
    
    def _update_file_in_tree(self, file_path: str, file_info: Dict[str, Any]):
        """ツリー内のファイル情報を更新"""
        try:
            # 該当するアイテムを検索
            for item_id in self.file_tree.get_children():
                if self.file_tree.set(item_id, 'path') == file_path:
                    # 情報を更新
                    file_size = self._format_file_size(file_info['size'])
                    modified_time = file_info['modified'].strftime("%Y-%m-%d %H:%M")
                    
                    self.file_tree.item(item_id, values=(file_size, file_info['type'], modified_time, file_info['status']))
                    break
                    
        except Exception as e:
            self.logger.error(f"ツリーファイル更新エラー {file_path}: {e}")
    
    def _remove_file_from_tree(self, file_path: str):
        """ツリーからファイルを削除"""
        try:
            for item_id in self.file_tree.get_children():
                if self.file_tree.set(item_id, 'path') == file_path:
                    self.file_tree.delete(item_id)
                    break
                    
        except Exception as e:
            self.logger.error(f"ツリーファイル削除エラー {file_path}: {e}")
    
    def _format_file_size(self, size_bytes: int) -> str:
        """ファイルサイズをフォーマット"""
        try:
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        except:
            return "不明"
    def _on_file_selected(self, event):
        """ファイル選択時の処理"""
        try:
            selection = self.file_tree.selection()
            if not selection:
                return
            
            item_id = selection[0]
            file_path = self.file_tree.set(item_id, 'path')
            
            if file_path and file_path in self.current_files:
                self.selected_file = file_path
                self._display_file_info(self.current_files[file_path])
            else:
                self.selected_file = file_path
                self._display_basic_info(file_path)
                
        except Exception as e:
            self.logger.error(f"ファイル選択処理エラー: {e}")
    
    def _on_file_double_click(self, event):
        """ファイルダブルクリック時の処理"""
        try:
            if self.selected_file:
                if self.selected_file in self.current_files:
                    # 既に読み込み済みの場合はチャットに送信
                    self.send_to_chat()
                else:
                    # 未読み込みの場合は読み込み
                    self.load_file(self.selected_file)
                    
        except Exception as e:
            self.logger.error(f"ファイルダブルクリック処理エラー: {e}")
    
    def _on_file_right_click(self, event):
        """ファイル右クリック時の処理"""
        try:
            # 右クリックメニューを表示
            item_id = self.file_tree.identify_row(event.y)
            if item_id:
                self.file_tree.selection_set(item_id)
                self._show_context_menu(event)
                
        except Exception as e:
            self.logger.error(f"ファイル右クリック処理エラー: {e}")
    
    def _show_context_menu(self, event):
        """コンテキストメニューを表示"""
        try:
            context_menu = tk.Menu(self.file_tree, tearoff=0)
            
            if self.selected_file in self.current_files:
                context_menu.add_command(label="チャットに送信", command=self.send_to_chat)
                context_menu.add_command(label="再読み込み", command=self.reload_selected_file)
                context_menu.add_command(label="エクスポート", command=self.export_selected_file)
                context_menu.add_separator()
            else:
                context_menu.add_command(label="読み込み", command=lambda: self.load_file(self.selected_file))
                context_menu.add_separator()
            
            context_menu.add_command(label="ファイルを開く", command=self._open_file_externally)
            context_menu.add_command(label="フォルダを開く", command=self._open_folder_externally)
            context_menu.add_separator()
            context_menu.add_command(label="削除", command=self.remove_file)
            
            context_menu.post(event.x_root, event.y_root)
            
        except Exception as e:
            self.logger.error(f"コンテキストメニュー表示エラー: {e}")
    
    def _display_file_info(self, file_info: Dict[str, Any]):
        """ファイル情報を表示"""
        try:
            # 基本情報を表示
            info_text = f"""ファイル名: {file_info['name']}
パス: {file_info['path']}
サイズ: {self._format_file_size(file_info['size'])}
種類: {file_info['type']}
更新日時: {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')}
状態: {file_info['status']}

内容の文字数: {len(file_info['content'])} 文字
内容の行数: {file_info['content'].count(chr(10)) + 1} 行
"""
            
            self.info_text.configure(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, info_text)
            self.info_text.configure(state=tk.DISABLED)
            
            # プレビューを表示（最初の1000文字）
            preview_content = file_info['content'][:1000]
            if len(file_info['content']) > 1000:
                preview_content += "\n\n... (続きがあります)"
            
            self.preview_text.configure(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, preview_content)
            self.preview_text.configure(state=tk.DISABLED)
            
        except Exception as e:
            self.logger.error(f"ファイル情報表示エラー: {e}")
    
    def _display_basic_info(self, file_path: str):
        """基本情報のみを表示（未読み込みファイル用）"""
        try:
            if not os.path.exists(file_path):
                info_text = f"ファイルが見つかりません: {file_path}"
            else:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_type = Path(file_path).suffix.lower()
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                info_text = f"""ファイル名: {file_name}
パス: {file_path}
サイズ: {self._format_file_size(file_size)}
種類: {file_type}
更新日時: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}
状態: 未読み込み

このファイルを読み込むには、ダブルクリックするか「読み込み」ボタンをクリックしてください。
"""
            
            self.info_text.configure(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, info_text)
            self.info_text.configure(state=tk.DISABLED)
            
            # プレビューをクリア
            self.preview_text.configure(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, "ファイルが読み込まれていません。")
            self.preview_text.configure(state=tk.DISABLED)
            
        except Exception as e:
            self.logger.error(f"基本情報表示エラー: {e}")
    
    def _open_file_externally(self):
        """外部アプリケーションでファイルを開く"""
        try:
            if self.selected_file and os.path.exists(self.selected_file):
                import subprocess
                import platform
                
                if platform.system() == 'Windows':
                    os.startfile(self.selected_file)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', self.selected_file])
                else:  # Linux
                    subprocess.run(['xdg-open', self.selected_file])
                    
        except Exception as e:
            self.logger.error(f"外部ファイル開くエラー: {e}")
            messagebox.showerror("エラー", f"ファイルを開けませんでした: {e}")
    
    def _open_folder_externally(self):
        """外部アプリケーションでフォルダを開く"""
        try:
            if self.selected_file:
                folder_path = os.path.dirname(self.selected_file)
                if os.path.exists(folder_path):
                    import subprocess
                    import platform
                    
                    if platform.system() == 'Windows':
                        subprocess.run(['explorer', folder_path])
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', folder_path])
                    else:  # Linux
                        subprocess.run(['xdg-open', folder_path])
                        
        except Exception as e:
            self.logger.error(f"外部フォルダ開くエラー: {e}")
            messagebox.showerror("エラー", f"フォルダを開けませんでした: {e}")
    
    def reload_selected_file(self):
        """選択されたファイルを再読み込み"""
        try:
            if not self.selected_file:
                messagebox.showwarning("警告", "ファイルが選択されていません。")
                return
            
            if self.selected_file in self.current_files:
                # 既存の情報を削除
                del self.current_files[self.selected_file]
                
                # ツリーの状態を更新
                self._update_file_status_in_tree(self.selected_file, "再読み込み中")
                
                # 再読み込み
                threading.Thread(target=self._load_file_async, args=(self.selected_file,), daemon=True).start()
            else:
                # 初回読み込み
                self.load_file(self.selected_file)
                
        except Exception as e:
            self.logger.error(f"ファイル再読み込みエラー: {e}")
            messagebox.showerror("エラー", f"ファイルの再読み込みに失敗しました: {e}")
    
    def _update_file_status_in_tree(self, file_path: str, status: str):
        """ツリー内のファイル状態を更新"""
        try:
            for item_id in self.file_tree.get_children():
                if self.file_tree.set(item_id, 'path') == file_path:
                    current_values = list(self.file_tree.item(item_id, 'values'))
                    current_values[3] = status  # status列を更新
                    self.file_tree.item(item_id, values=current_values)
                    break
                    
        except Exception as e:
            self.logger.error(f"ファイル状態更新エラー {file_path}: {e}")
    
    def export_selected_file(self):
        """選択されたファイルをエクスポート"""
        try:
            if not self.selected_file or self.selected_file not in self.current_files:
                messagebox.showwarning("警告", "読み込み済みのファイルが選択されていません。")
                return
            
            file_info = self.current_files[self.selected_file]
            
            # エクスポート先を選択
            export_path = filedialog.asksaveasfilename(
                title="エクスポート先を選択",
                initialdir=self.config.get('export_directory', os.getcwd()),
                initialfilename=f"exported_{file_info['name']}",
                defaultextension=file_info['type'],
                filetypes=[
                    ("テキストファイル", "*.txt"),
                    ("Markdownファイル", "*.md"),
                    ("すべてのファイル", "*.*")
                ]
            )
            
            if export_path:
                with open(export_path, 'w', encoding='utf-8') as f:
                    f.write(file_info['content'])
                
                messagebox.showinfo("完了", f"ファイルをエクスポートしました:\n{export_path}")
                self.logger.info(f"ファイルをエクスポートしました: {export_path}")
                
        except Exception as e:
            self.logger.error(f"ファイルエクスポートエラー: {e}")
            messagebox.showerror("エラー", f"ファイルのエクスポートに失敗しました: {e}")
    
    def send_to_chat(self):
        """選択されたファイルをチャットに送信"""
        try:
            if not self.selected_file or self.selected_file not in self.current_files:
                messagebox.showwarning("警告", "読み込み済みのファイルが選択されていません。")
                return
            
            file_info = self.current_files[self.selected_file]
            
            # コールバック関数を呼び出し
            if self.on_file_loaded:
                self.on_file_loaded(self.selected_file, file_info)
            
            self._set_status(f"ファイルをチャットに送信しました: {file_info['name']}")
            
        except Exception as e:
            self.logger.error(f"チャット送信エラー: {e}")
            messagebox.showerror("エラー", f"チャットへの送信に失敗しました: {e}")
    
    def remove_file(self):
        """選択されたファイルを削除"""
        try:
            if not self.selected_file:
                messagebox.showwarning("警告", "ファイルが選択されていません。")
                return
            
            file_name = os.path.basename(self.selected_file)
            result = messagebox.askyesno("確認", f"ファイル '{file_name}' をリストから削除しますか？")
            
            if result:
                # ファイル情報を削除
                if self.selected_file in self.current_files:
                    del self.current_files[self.selected_file]
                
                # ツリーから削除
                self._remove_file_from_tree(self.selected_file)
                
                # 最近のファイルリストからも削除
                self._remove_from_recent_files(self.selected_file)
                
                # 選択をクリア
                self.selected_file = None
                
                # 情報パネルをクリア
                self.info_text.configure(state=tk.NORMAL)
                self.info_text.delete(1.0, tk.END)
                self.info_text.configure(state=tk.DISABLED)
                
                self.preview_text.configure(state=tk.NORMAL)
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.configure(state=tk.DISABLED)
                
                self._set_status(f"ファイルを削除しました: {file_name}")
                
        except Exception as e:
            self.logger.error(f"ファイル削除エラー: {e}")
            messagebox.showerror("エラー", f"ファイルの削除に失敗しました: {e}")
    
    def clear_all(self):
        """すべてのファイルをクリア"""
        try:
            if not self.current_files and not self.file_tree.get_children():
                messagebox.showinfo("情報", "クリアするファイルがありません。")
                return
            
            result = messagebox.askyesno("確認", "すべてのファイルをクリアしますか？")
            
            if result:
                # すべてのファイル情報を削除
                self.current_files.clear()
                
                # ツリーをクリア
                for item in self.file_tree.get_children():
                    self.file_tree.delete(item)
                
                # 選択をクリア
                self.selected_file = None
                
                # 情報パネルをクリア
                self.info_text.configure(state=tk.NORMAL)
                self.info_text.delete(1.0, tk.END)
                self.info_text.configure(state=tk.DISABLED)
                
                self.preview_text.configure(state=tk.NORMAL)
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.configure(state=tk.DISABLED)
                
                self._set_status("すべてのファイルをクリアしました")
                
        except Exception as e:
            self.logger.error(f"全クリアエラー: {e}")
            messagebox.showerror("エラー", f"ファイルのクリアに失敗しました: {e}")
    
    def refresh(self):
        """ファイルリストを更新"""
        try:
            # 存在しないファイルを削除
            files_to_remove = []
            for file_path in self.current_files:
                if not os.path.exists(file_path):
                    files_to_remove.append(file_path)
            
            for file_path in files_to_remove:
                del self.current_files[file_path]
                self._remove_file_from_tree(file_path)
            
            # 既存ファイルの更新時刻をチェック
            for file_path, file_info in self.current_files.items():
                if os.path.exists(file_path):
                    current_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if current_mtime > file_info['modified']:
                        # ファイルが更新されている
                        self._update_file_status_in_tree(file_path, "更新あり")
            
            if files_to_remove:
                self._set_status(f"{len(files_to_remove)} 個の存在しないファイルを削除しました")
            else:
                self._set_status("ファイルリストを更新しました")
                
        except Exception as e:
            self.logger.error(f"リフレッシュエラー: {e}")
            messagebox.showerror("エラー", f"ファイルリストの更新に失敗しました: {e}")
    
    def browse_work_directory(self):
        """作業ディレクトリを参照"""
        try:
            directory = filedialog.askdirectory(
                title="作業ディレクトリを選択",
                initialdir=self.work_directory
            )
            
            if directory:
                self.work_directory = directory
                self.work_dir_var.set(directory)
                self.config.set('work_directory', directory)
                self.config.save()
                
                self._set_status(f"作業ディレクトリを変更しました: {directory}")
                
        except Exception as e:
            self.logger.error(f"作業ディレクトリ選択エラー: {e}")
            messagebox.showerror("エラー", f"作業ディレクトリの選択に失敗しました: {e}")
    
    def _update_recent_files(self, file_path: str):
        """最近のファイルリストを更新"""
        try:
            recent_files = self.config.get('recent_files', [])
            
            # 既存のエントリを削除
            if file_path in recent_files:
                recent_files.remove(file_path)
            
            # 先頭に追加
            recent_files.insert(0, file_path)
            
            # 最大10個まで保持
            recent_files = recent_files[:10]
            
            self.config.set('recent_files', recent_files)
            self.config.save()
            
        except Exception as e:
            self.logger.error(f"最近のファイル更新エラー: {e}")
    
    def _remove_from_recent_files(self, file_path: str):
        """最近のファイルリストから削除"""
        try:
            recent_files = self.config.get('recent_files', [])
            
            if file_path in recent_files:
                recent_files.remove(file_path)
                self.config.set('recent_files', recent_files)
                self.config.save()
                
        except Exception as e:
            self.logger.error(f"最近のファイル削除エラー: {e}")
    
    def _set_status(self, message: str):
        """ステータスメッセージを設定"""
        try:
            self.status_label.configure(text=message)
            
        except Exception as e:
            self.logger.error(f"ステータス設定エラー: {e}")
    
    def get_loaded_files(self) -> Dict[str, Dict[str, Any]]:
        """読み込み済みファイルの情報を取得"""
        return self.current_files.copy()
    
    def get_selected_file_info(self) -> Optional[Dict[str, Any]]:
        """選択されたファイルの情報を取得"""
        if self.selected_file and self.selected_file in self.current_files:
            return self.current_files[self.selected_file].copy()
        return None
    
    def set_on_file_loaded_callback(self, callback: Callable):
        """ファイル読み込み完了時のコールバック関数を設定"""
        self.on_file_loaded = callback

def create_file_manager(parent: tk.Widget, on_file_loaded: Optional[Callable] = None) -> FileManagerWidget:
    """
    ファイルマネージャーウィジェットを作成する便利関数
    
    Args:
        parent: 親ウィジェット
        on_file_loaded: ファイル読み込み完了時のコールバック関数
        
    Returns:
        FileManagerWidget: 作成されたファイルマネージャーウィジェット
    """
    try:
        return FileManagerWidget(parent, on_file_loaded)
        
    except Exception as e:
        logger.error(f"ファイルマネージャー作成エラー: {e}")
        raise
