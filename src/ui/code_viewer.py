# src/ui/code_viewer.py
"""
コードビューア - コードファイルの表示と編集機能
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable, Dict, List, Any, Tuple
from pathlib import Path
import re
import mimetypes
from datetime import datetime

try:
    # Pygmentsによるシンタックスハイライト
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename, get_lexer_by_name, guess_lexer
    from pygments.formatters import get_formatter_by_name
    from pygments.util import ClassNotFound
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


class LineNumbers(tk.Canvas):
    """行番号表示キャンバス"""
    
    def __init__(self, parent, text_widget, **kwargs):
        super().__init__(parent, **kwargs)
        self.text_widget = text_widget
        self.font = text_widget.cget('font')
        
        # スタイル設定
        self.config(
            width=50,
            bg='#F0F0F0',
            highlightthickness=0,
            bd=0
        )
        
        # テキストウィジェットのイベントにバインド
        self.text_widget.bind('<KeyPress>', self._on_text_change)
        self.text_widget.bind('<KeyRelease>', self._on_text_change)
        self.text_widget.bind('<Button-1>', self._on_text_change)
        self.text_widget.bind('<MouseWheel>', self._on_scroll)
        self.text_widget.bind('<Configure>', self._on_text_change)
        
        # 初期描画
        self.after_idle(self.redraw)
    
    def _on_text_change(self, event=None):
        """テキスト変更時の処理"""
        self.after_idle(self.redraw)
    
    def _on_scroll(self, event=None):
        """スクロール時の処理"""
        self.after_idle(self.redraw)
    
    def redraw(self):
        """行番号を再描画"""
        self.delete('all')
        
        # 表示されている行の範囲を取得
        top_line = int(self.text_widget.index('@0,0').split('.')[0])
        bottom_line = int(self.text_widget.index('@0,%d' % self.text_widget.winfo_height()).split('.')[0])
        
        # 行の高さを計算
        line_height = self.text_widget.winfo_height() / (bottom_line - top_line + 1)
        
        # 行番号を描画
        for line_num in range(top_line, bottom_line + 1):
            y = (line_num - top_line) * line_height + line_height / 2
            self.create_text(
                self.winfo_width() - 5,
                y,
                text=str(line_num),
                anchor=tk.E,
                font=self.font,
                fill='#666666'
            )


class SearchDialog:
    """検索・置換ダイアログ"""
    
    def __init__(self, parent, text_widget):
        self.parent = parent
        self.text_widget = text_widget
        self.dialog = None
        self.search_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.case_sensitive_var = tk.BooleanVar()
        self.regex_var = tk.BooleanVar()
        self.wrap_var = tk.BooleanVar(value=True)
        
        self.current_match_start = None
        self.current_match_end = None
        self.matches = []
        self.current_match_index = -1
    
    def show(self):
        """検索ダイアログを表示"""
        if self.dialog:
            self.dialog.lift()
            return
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("検索・置換")
        self.dialog.geometry("400x200")
        self.dialog.transient(self.parent)
        
        self._create_widgets()
        self._setup_bindings()
        
        # 選択されたテキストがあれば検索欄に設定
        try:
            selected_text = self.text_widget.selection_get()
            if selected_text and len(selected_text) < 100:
                self.search_var.set(selected_text)
        except tk.TclError:
            pass
        
        self.search_entry.focus()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 検索欄
        ttk.Label(main_frame, text="検索:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.search_entry = ttk.Entry(main_frame, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=(0, 5))
        
        # 置換欄
        ttk.Label(main_frame, text="置換:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.replace_entry = ttk.Entry(main_frame, textvariable=self.replace_var, width=30)
        self.replace_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=(0, 5))
        
        # オプション
        options_frame = ttk.LabelFrame(main_frame, text="オプション", padding=5)
        options_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=(10, 0))
        
        ttk.Checkbutton(options_frame, text="大文字小文字を区別", 
                       variable=self.case_sensitive_var).pack(anchor=tk.W)
        ttk.Checkbutton(options_frame, text="正規表現", 
                       variable=self.regex_var).pack(anchor=tk.W)
        ttk.Checkbutton(options_frame, text="折り返し検索", 
                       variable=self.wrap_var).pack(anchor=tk.W)
        
        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Button(button_frame, text="次を検索", command=self.find_next).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="前を検索", command=self.find_previous).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="置換", command=self.replace_current).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="全て置換", command=self.replace_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="閉じる", command=self.close).pack(side=tk.RIGHT)
        
        main_frame.columnconfigure(1, weight=1)
    
    def _setup_bindings(self):
        """キーバインドを設定"""
        self.dialog.bind('<Return>', lambda e: self.find_next())
        self.dialog.bind('<Escape>', lambda e: self.close())
        self.dialog.bind('<F3>', lambda e: self.find_next())
        self.dialog.bind('<Shift-F3>', lambda e: self.find_previous())
        self.dialog.protocol("WM_DELETE_WINDOW", self.close)
    
    def find_next(self):
        """次を検索"""
        self._find(forward=True)
    
    def find_previous(self):
        """前を検索"""
        self._find(forward=False)
    
    def _find(self, forward=True):
        """検索実行"""
        search_text = self.search_var.get()
        if not search_text:
            return
        
        # 検索オプション
        case_sensitive = self.case_sensitive_var.get()
        use_regex = self.regex_var.get()
        wrap_search = self.wrap_var.get()
        
        # 開始位置を決定
        if forward:
            start_pos = self.current_match_end if self.current_match_end else self.text_widget.index(tk.INSERT)
        else:
            start_pos = self.current_match_start if self.current_match_start else self.text_widget.index(tk.INSERT)
        
        try:
            if use_regex:
                # 正規表現検索
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
                
                # テキスト全体を取得
                text_content = self.text_widget.get('1.0', tk.END)
                
                # 検索実行
                matches = list(pattern.finditer(text_content))
                if not matches:
                    messagebox.showinfo("検索", "見つかりませんでした")
                    return
                
                # 現在位置に最も近いマッチを見つける
                current_index = self.text_widget.index(start_pos)
                current_line, current_col = map(int, current_index.split('.'))
                current_char_index = self._line_col_to_char_index(current_line, current_col)
                
                best_match = None
                if forward:
                    for match in matches:
                        if match.start() >= current_char_index:
                            best_match = match
                            break
                    if not best_match and wrap_search:
                        best_match = matches[0]
                else:
                    for match in reversed(matches):
                        if match.start() < current_char_index:
                            best_match = match
                            break
                    if not best_match and wrap_search:
                        best_match = matches[-1]
                
                if best_match:
                    self._highlight_match(best_match.start(), best_match.end())
                else:
                    messagebox.showinfo("検索", "見つかりませんでした")
            
            else:
                # 通常検索
                if forward:
                    pos = self.text_widget.search(
                        search_text, 
                        start_pos, 
                        tk.END,
                        nocase=not case_sensitive
                    )
                    if not pos and wrap_search:
                        pos = self.text_widget.search(
                            search_text, 
                            '1.0', 
                            start_pos,
                            nocase=not case_sensitive
                        )
                else:
                    pos = self.text_widget.search(
                        search_text, 
                        start_pos, 
                        '1.0',
                        backwards=True,
                        nocase=not case_sensitive
                    )
                    if not pos and wrap_search:
                        pos = self.text_widget.search(
                            search_text, 
                            tk.END, 
                            start_pos,
                            backwards=True,
                            nocase=not case_sensitive
                        )
                
                if pos:
                    end_pos = f"{pos}+{len(search_text)}c"
                    self.current_match_start = pos
                    self.current_match_end = end_pos
                    
                    # ハイライト
                    self.text_widget.tag_remove('search_highlight', '1.0', tk.END)
                    self.text_widget.tag_add('search_highlight', pos, end_pos)
                    self.text_widget.tag_config('search_highlight', background='yellow')
                    
                    # 表示位置を調整
                    self.text_widget.see(pos)
                    self.text_widget.mark_set(tk.INSERT, pos)
                else:
                    messagebox.showinfo("検索", "見つかりませんでした")
        
        except re.error as e:
            messagebox.showerror("正規表現エラー", f"正規表現が無効です: {e}")
        except Exception as e:
            messagebox.showerror("検索エラー", f"検索中にエラーが発生しました: {e}")
    
    def _line_col_to_char_index(self, line: int, col: int) -> int:
        """行・列番号を文字インデックスに変換"""
        char_index = 0
        lines = self.text_widget.get('1.0', tk.END).split('\n')
        
        for i in range(line - 1):
            if i < len(lines):
                char_index += len(lines[i]) + 1  # +1 for newline
        
        char_index += col
        return char_index
    
    def _highlight_match(self, start_char: int, end_char: int):
        """マッチをハイライト"""
        # 文字インデックスを行・列に変換
        lines = self.text_widget.get('1.0', tk.END).split('\n')
        current_char = 0
        start_line, start_col = 1, 0
        end_line, end_col = 1, 0
        
        for line_num, line in enumerate(lines, 1):
            if current_char <= start_char < current_char + len(line) + 1:
                start_line = line_num
                start_col = start_char - current_char
            if current_char <= end_char < current_char + len(line) + 1:
                end_line = line_num
                end_col = end_char - current_char
                break
            current_char += len(line) + 1
        
        start_pos = f"{start_line}.{start_col}"
        end_pos = f"{end_line}.{end_col}"
        
        self.current_match_start = start_pos
        self.current_match_end = end_pos
        
        # ハイライト
        self.text_widget.tag_remove('search_highlight', '1.0', tk.END)
        self.text_widget.tag_add('search_highlight', start_pos, end_pos)
        self.text_widget.tag_config('search_highlight', background='yellow')
        
        # 表示位置を調整
        self.text_widget.see(start_pos)
        self.text_widget.mark_set(tk.INSERT, start_pos)
    
    def replace_current(self):
        """現在のマッチを置換"""
        if not self.current_match_start or not self.current_match_end:
            messagebox.showwarning("置換", "置換する対象が選択されていません")
            return
        
        replace_text = self.replace_var.get()
        
        # 置換実行
        self.text_widget.delete(self.current_match_start, self.current_match_end)
        self.text_widget.insert(self.current_match_start, replace_text)
        
        # 次を検索
        self.find_next()
    
    def replace_all(self):
        """全て置換"""
        search_text = self.search_var.get()
        replace_text = self.replace_var.get()
        
        if not search_text:
            return
        
        # 確認ダイアログ
        if not messagebox.askyesno("確認", f"'{search_text}' を '{replace_text}' に全て置換しますか？"):
            return
        
        try:
            case_sensitive = self.case_sensitive_var.get()
            use_regex = self.regex_var.get()
            
            text_content = self.text_widget.get('1.0', tk.END)
            
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
                new_content = pattern.sub(replace_text, text_content)
                count = len(pattern.findall(text_content))
            else:
                if case_sensitive:
                    new_content = text_content.replace(search_text, replace_text)
                    count = text_content.count(search_text)
                else:
                    # 大文字小文字を無視した置換
                    pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                    new_content = pattern.sub(replace_text, text_content)
                    count = len(pattern.findall(text_content))
            
            if count > 0:
                self.text_widget.delete('1.0', tk.END)
                self.text_widget.insert('1.0', new_content)
                messagebox.showinfo("置換完了", f"{count} 箇所を置換しました")
            else:
                messagebox.showinfo("置換", "置換対象が見つかりませんでした")
        
        except re.error as e:
            messagebox.showerror("正規表現エラー", f"正規表現が無効です: {e}")
        except Exception as e:
            messagebox.showerror("置換エラー", f"置換中にエラーが発生しました: {e}")
    
    def close(self):
        """ダイアログを閉じる"""
        if self.dialog:
            # ハイライトを削除
            self.text_widget.tag_remove('search_highlight', '1.0', tk.END)
            self.dialog.destroy()
            self.dialog = None


class CodeViewer(ttk.Frame):
    """
    コードビューアクラス
    ファイルの表示、編集、シンタックスハイライト機能を提供
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # コールバック関数
        self.on_line_select: Optional[Callable[[int], None]] = None
        self.on_file_change: Optional[Callable[[str], None]] = None
        self.on_selection_change: Optional[Callable[[str], None]] = None
        
        # 状態管理
        self.current_file_path = None
        self.current_language = None
        self.is_modified = False
        self.original_content = ""
        self.supported_languages = self._get_supported_languages()
        
        # UI作成
        self._create_widgets()
        self._setup_styles()
        self._setup_bindings()
        
        # 検索ダイアログ
        self.search_dialog = None
        
        self.logger.info("コードビューア初期化完了")
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # ツールバー
        self._create_toolbar()
        
        # エディタエリア
        self._create_editor_area()
        
        # ステータスバー
        self._create_status_bar()
    
    def _create_toolbar(self):
        """ツールバーを作成"""
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # ファイル操作
        ttk.Button(self.toolbar, text="開く", command=self._open_file, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(self.toolbar, text="保存", command=self._save_file, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(self.toolbar, text="名前を付けて保存", command=self._save_as_file, width=12).pack(side=tk.LEFT, padx=(0, 5))
        
        # 区切り線
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 編集操作
        ttk.Button(self.toolbar, text="検索", command=self._show_search, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(self.toolbar, text="行へ移動", command=self._goto_line, width=10).pack(side=tk.LEFT, padx=(0, 5))
        
        # 区切り線
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 表示操作
        ttk.Button(self.toolbar, text="フォント", command=self._change_font, width=8).pack(side=tk.LEFT, padx=(0, 2))
        
        # 言語選択
        ttk.Label(self.toolbar, text="言語:").pack(side=tk.LEFT, padx=(5, 2))
        self.language_var = tk.StringVar()
        self.language_combo = ttk.Combobox(
            self.toolbar, 
            textvariable=self.language_var,
            values=list(self.supported_languages.keys()),
            width=10,
            state='readonly'
        )
        self.language_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.language_combo.bind('<<ComboboxSelected>>', self._on_language_change)
        
        # 右側のボタン
        ttk.Button(self.toolbar, text="設定", command=self._show_settings, width=8).pack(side=tk.RIGHT)
    
    def _create_editor_area(self):
        """エディタエリアを作成"""
        # エディタフレーム
        editor_frame = ttk.Frame(self)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        
        # 行番号とテキストエリアのフレーム
        text_frame = ttk.Frame(editor_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # テキストエリア
        self.text_area = tk.Text(
            text_frame,
            wrap=tk.NONE,
            font=('Consolas', 10),
            bg='white',
            fg='black',
            insertbackground='black',
            selectbackground='#316AC5',
            selectforeground='white',
            undo=True,
            maxundo=100,
            tabs='4c'
        )
        
        # 行番号
        self.line_numbers = LineNumbers(text_frame, self.text_area)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # スクロールバー
        v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        h_scrollbar = ttk.Scrollbar(editor_frame, orient=tk.HORIZONTAL, command=self.text_area.xview)
        
        self.text_area.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 配置
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _create_status_bar(self):
        """ステータスバーを作成"""
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # ファイル情報
        self.file_label = ttk.Label(self.status_frame, text="ファイル: なし")
        self.file_label.pack(side=tk.LEFT, padx=5)
        
        # カーソル位置
        self.cursor_label = ttk.Label(self.status_frame, text="行: 1, 列: 1")
        self.cursor_label.pack(side=tk.RIGHT, padx=5)
        
        # 変更状態
        self.modified_label = ttk.Label(self.status_frame, text="")
        self.modified_label.pack(side=tk.RIGHT, padx=5)
        
        # エンコーディング
        self.encoding_label = ttk.Label(self.status_frame, text="UTF-8")
        self.encoding_label.pack(side=tk.RIGHT, padx=5)
    
    def _setup_styles(self):
        """スタイルを設定"""
        # シンタックスハイライト用のタグ
        if PYGMENTS_AVAILABLE:
            self._setup_pygments_styles()
        else:
            self._setup_basic_styles()
    
    def _setup_pygments_styles(self):
        """Pygmentsスタイルを設定"""
        # 基本的なトークンタイプのスタイル
        styles = {
            'Token.Comment': {'foreground': '#008000', 'font': ('Consolas', 10, 'italic')},
            'Token.String': {'foreground': '#BA2121'},
            'Token.Number': {'foreground': '#666666'},
            'Token.Keyword': {'foreground': '#0000FF', 'font': ('Consolas', 10, 'bold')},
            'Token.Name.Function': {'foreground': '#0000FF'},
            'Token.Name.Class': {'foreground': '#0000FF', 'font': ('Consolas', 10, 'bold')},
            'Token.Operator': {'foreground': '#666666'},
            'Token.Error': {'background': '#FF0000', 'foreground': '#FFFFFF'}
        }
        
        for token_type, style in styles.items():
            tag_name = token_type.replace('.', '_')
            self.text_area.tag_configure(tag_name, **style)
    
    def _setup_basic_styles(self):
        """基本的なスタイルを設定"""
        # Pygmentsが利用できない場合の基本スタイル
        self.text_area.tag_configure('comment', foreground='#008000', font=('Consolas', 10, 'italic'))
        self.text_area.tag_configure('string', foreground='#BA2121')
        self.text_area.tag_configure('keyword', foreground='#0000FF', font=('Consolas', 10, 'bold'))
        self.text_area.tag_configure('number', foreground='#666666')
        self.text_area.tag_configure('error', background='#FF0000', foreground='#FFFFFF')
    
    def _setup_bindings(self):
        """キーバインドを設定"""
        # ファイル操作
        self.text_area.bind('<Control-o>', lambda e: self._open_file())
        self.text_area.bind('<Control-s>', lambda e: self._save_file())
        self.text_area.bind('<Control-Shift-S>', lambda e: self._save_as_file())
        
        # 編集操作
        self.text_area.bind('<Control-f>', lambda e: self._show_search())
        self.text_area.bind('<Control-g>', lambda e: self._goto_line())
        self.text_area.bind('<F3>', lambda e: self._find_next())
        
        # テキスト変更
        self.text_area.bind('<KeyPress>', self._on_text_change)
        self.text_area.bind('<Button-1>', self._on_cursor_move)
        self.text_area.bind('<KeyRelease>', self._on_cursor_move)
        
        # 選択変更
        self.text_area.bind('<ButtonRelease-1>', self._on_selection_change)
        self.text_area.bind('<KeyRelease>', self._on_selection_change)
        
        # 右クリックメニュー
        self.text_area.bind('<Button-3>', self._show_context_menu)
        
        # ドラッグ&ドロップ
        self.text_area.bind('<Button-1>', self._on_drag_start)
        self.text_area.bind('<B1-Motion>', self._on_drag_motion)
    
    def _get_supported_languages(self) -> Dict[str, str]:
        """サポートされている言語の一覧を取得"""
        languages = {
            'Auto': 'auto',
            'Python': 'python',
            'JavaScript': 'javascript',
            'TypeScript': 'typescript',
            'Java': 'java',
            'C': 'c',
            'C++': 'cpp',
            'C#': 'csharp',
            'Go': 'go',
            'Rust': 'rust',
            'PHP': 'php',
            'Ruby': 'ruby',
            'Swift': 'swift',
            'Kotlin': 'kotlin',
            'HTML': 'html',
            'CSS': 'css',
            'XML': 'xml',
            'JSON': 'json',
            'YAML': 'yaml',
            'SQL': 'sql',
            'Shell': 'bash',
            'PowerShell': 'powershell',
            'Markdown': 'markdown',
            'Text': 'text'
        }
        return languages
    
    # ===== 公開メソッド =====
    def load_file(self, file_path: str):
        """ファイルを読み込み"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                messagebox.showerror("エラー", f"ファイルが見つかりません: {file_path}")
                return False
            
            # ファイルサイズチェック（10MB以上は警告）
            file_size = file_path.stat().st_size
            if file_size > 10 * 1024 * 1024:
                if not messagebox.askyesno("確認", 
                    f"ファイルサイズが大きいです ({file_size // 1024 // 1024}MB)。\n読み込みますか？"):
                    return False
            
            # エンコーディングを自動検出
            encoding = self._detect_encoding(file_path)
            
            # ファイル読み込み
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # テキストエリアに設定
            self.text_area.delete('1.0', tk.END)
            self.text_area.insert('1.0', content)
            
            # 状態更新
            self.current_file_path = str(file_path)
            self.original_content = content
            self.is_modified = False
            
            # 言語を自動検出
            self._detect_and_set_language(file_path)
            
            # シンタックスハイライトを適用
            self._apply_syntax_highlighting()
            
            # UI更新
            self._update_status_bar()
            self._update_title()
            
            # カーソルを先頭に移動
            self.text_area.mark_set(tk.INSERT, '1.0')
            self.text_area.see('1.0')
            
            self.logger.info(f"ファイル読み込み完了: {file_path}")
            return True
            
        except UnicodeDecodeError as e:
            messagebox.showerror("エンコーディングエラー", 
                f"ファイルの読み込みに失敗しました。\nエンコーディングが正しくない可能性があります。\n{e}")
            return False
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー: {e}")
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{e}")
            return False
    
    def save_file(self, file_path: str = None) -> bool:
        """ファイルを保存"""
        try:
            if file_path is None:
                file_path = self.current_file_path
            
            if not file_path:
                return self._save_as_file()
            
            # 内容を取得
            content = self.text_area.get('1.0', tk.END + '-1c')
            
            # バックアップ作成（設定による）
            if self._should_create_backup(file_path):
                self._create_backup(file_path)
            
            # ファイル保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 状態更新
            self.current_file_path = file_path
            self.original_content = content
            self.is_modified = False
            
            # UI更新
            self._update_status_bar()
            self._update_title()
            
            self.logger.info(f"ファイル保存完了: {file_path}")
            
            # コールバック実行
            if self.on_file_change:
                self.on_file_change(file_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル保存エラー: {e}")
            messagebox.showerror("エラー", f"ファイルの保存に失敗しました:\n{e}")
            return False
    
    def get_content(self) -> str:
        """現在の内容を取得"""
        return self.text_area.get('1.0', tk.END + '-1c')
    
    def set_content(self, content: str):
        """内容を設定"""
        self.text_area.delete('1.0', tk.END)
        self.text_area.insert('1.0', content)
        self._apply_syntax_highlighting()
    
    def get_selected_text(self) -> str:
        """選択されたテキストを取得"""
        try:
            return self.text_area.selection_get()
        except tk.TclError:
            return ""
    
    def highlight_lines(self, line_numbers: List[int], tag_name: str = 'highlight'):
        """指定した行をハイライト"""
        # 既存のハイライトを削除
        self.text_area.tag_remove(tag_name, '1.0', tk.END)
        
        # 新しいハイライトを適用
        for line_num in line_numbers:
            start_index = f"{line_num}.0"
            end_index = f"{line_num}.end"
            self.text_area.tag_add(tag_name, start_index, end_index)
        
        # ハイライトスタイルを設定
        self.text_area.tag_configure(tag_name, background='#FFFF99')
        
        # 最初の行にスクロール
        if line_numbers:
            self.text_area.see(f"{line_numbers[0]}.0")
    
    def goto_line(self, line_number: int):
        """指定した行に移動"""
        self.text_area.mark_set(tk.INSERT, f"{line_number}.0")
        self.text_area.see(f"{line_number}.0")
        self.text_area.focus()
    
    def set_language(self, language: str):
        """言語を設定"""
        if language in self.supported_languages.values():
            self.current_language = language
            # コンボボックスの値を更新
            for name, lang in self.supported_languages.items():
                if lang == language:
                    self.language_var.set(name)
                    break
            self._apply_syntax_highlighting()
    
    def is_file_modified(self) -> bool:
        """ファイルが変更されているかチェック"""
        return self.is_modified
    
    def clear(self):
        """エディタをクリア"""
        self.text_area.delete('1.0', tk.END)
        self.current_file_path = None
        self.current_language = None
        self.is_modified = False
        self.original_content = ""
        self._update_status_bar()
        self._update_title()
    
    # ===== プライベートメソッド =====
    
    def _detect_encoding(self, file_path: Path) -> str:
        """ファイルのエンコーディングを検出"""
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # 最初の10KBを読み取り
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            if encoding.lower() in ['ascii', 'utf-8']:
                return 'utf-8'
            return encoding
        except ImportError:
            # chardetが利用できない場合はUTF-8を試す
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read(1000)
                return 'utf-8'
            except UnicodeDecodeError:
                return 'cp932'  # Windowsの場合
    
    def _detect_and_set_language(self, file_path: Path):
        """ファイル拡張子から言語を自動検出"""
        extension = file_path.suffix.lower()
        
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.xml': 'xml',
            '.json': 'json',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bash': 'bash',
            '.ps1': 'powershell',
            '.md': 'markdown',
            '.txt': 'text'
        }
        
        detected_language = extension_map.get(extension, 'text')
        self.current_language = detected_language
        
        # コンボボックスを更新
        for name, lang in self.supported_languages.items():
            if lang == detected_language:
                self.language_var.set(name)
                break
    
    def _apply_syntax_highlighting(self):
        """シンタックスハイライトを適用"""
        if not PYGMENTS_AVAILABLE or not self.current_language:
            return
        
        try:
            # 既存のハイライトを削除
            for tag in self.text_area.tag_names():
                if tag.startswith('Token_'):
                    self.text_area.tag_remove(tag, '1.0', tk.END)
            
            # コンテンツを取得
            content = self.text_area.get('1.0', tk.END + '-1c')
            if not content.strip():
                return
            
            # レキサーを取得
            if self.current_language == 'auto':
                lexer = guess_lexer(content)
            else:
                lexer = get_lexer_by_name(self.current_language)
            
            # トークンを取得
            tokens = list(lexer.get_tokens(content))
            
            # ハイライトを適用
            self._apply_token_highlighting(tokens, content)
            
        except ClassNotFound:
            self.logger.warning(f"レキサーが見つかりません: {self.current_language}")
        except Exception as e:
            self.logger.error(f"シンタックスハイライトエラー: {e}")
    
    def _apply_token_highlighting(self, tokens, content: str):
        """トークンベースのハイライトを適用"""
        lines = content.split('\n')
        current_line = 1
        current_col = 0
        
        for token_type, token_value in tokens:
            if not token_value:
                continue
            
            # トークンの位置を計算
            start_line = current_line
            start_col = current_col
            
            # 改行を含む場合の処理
            if '\n' in token_value:
                token_lines = token_value.split('\n')
                end_line = current_line + len(token_lines) - 1
                if len(token_lines) > 1:
                    end_col = len(token_lines[-1])
                    current_line = end_line
                    current_col = end_col
                else:
                    end_col = current_col + len(token_value)
                    current_col = end_col
            else:
                end_line = current_line
                end_col = current_col + len(token_value)
                current_col = end_col
            
            # タグを適用
            tag_name = str(token_type).replace('.', '_')
            start_index = f"{start_line}.{start_col}"
            end_index = f"{end_line}.{end_col}"
            
            try:
                self.text_area.tag_add(tag_name, start_index, end_index)
            except tk.TclError:
                # インデックスが無効な場合はスキップ
                continue
    
    def _on_text_change(self, event=None):
        """テキスト変更時の処理"""
        current_content = self.text_area.get('1.0', tk.END + '-1c')
        self.is_modified = (current_content != self.original_content)
        
        # 遅延ハイライト更新
        if hasattr(self, '_highlight_timer'):
            self.after_cancel(self._highlight_timer)
        self._highlight_timer = self.after(500, self._apply_syntax_highlighting)
        
        self._update_status_bar()
    
    def _on_cursor_move(self, event=None):
        """カーソル移動時の処理"""
        self._update_cursor_position()
        
        # 行選択コールバック
        if self.on_line_select:
            current_line = int(self.text_area.index(tk.INSERT).split('.')[0])
            self.on_line_select(current_line)
    
    def _on_selection_change(self, event=None):
        """選択変更時の処理"""
        try:
            selected_text = self.text_area.selection_get()
            if self.on_selection_change:
                self.on_selection_change(selected_text)
        except tk.TclError:
            # 選択されていない場合
            if self.on_selection_change:
                self.on_selection_change("")
    
    def _on_language_change(self, event=None):
        """言語変更時の処理"""
        selected_name = self.language_var.get()
        if selected_name in self.supported_languages:
            self.current_language = self.supported_languages[selected_name]
            self._apply_syntax_highlighting()
    
    def _update_status_bar(self):
        """ステータスバーを更新"""
        # ファイル情報
        if self.current_file_path:
            file_name = Path(self.current_file_path).name
            self.file_label.config(text=f"ファイル: {file_name}")
        else:
            self.file_label.config(text="ファイル: 新規")
        
        # 変更状態
        if self.is_modified:
            self.modified_label.config(text="*", foreground="red")
        else:
            self.modified_label.config(text="", foreground="black")
        
        # カーソル位置
        self._update_cursor_position()
    
    def _update_cursor_position(self):
        """カーソル位置を更新"""
        cursor_pos = self.text_area.index(tk.INSERT)
        line, col = cursor_pos.split('.')
        self.cursor_label.config(text=f"行: {line}, 列: {int(col) + 1}")
    
    def _update_title(self):
        """タイトルを更新"""
        # 親ウィンドウのタイトルを更新（可能な場合）
        try:
            if self.current_file_path:
                title = f"Code Viewer - {Path(self.current_file_path).name}"
                if self.is_modified:
                    title += " *"
                self.winfo_toplevel().title(title)
        except:
            pass
    
    def _open_file(self):
        """ファイルを開く"""
        if self.is_modified:
            result = messagebox.askyesnocancel("確認", "変更が保存されていません。保存しますか？")
            if result is True:
                if not self.save_file():
                    return
            elif result is None:
                return
        
        file_path = filedialog.askopenfilename(
            title="ファイルを開く",
            filetypes=[
                ("All files", "*.*"),
                ("Python files", "*.py"),
                ("JavaScript files", "*.js"),
                ("Text files", "*.txt"),
                ("HTML files", "*.html"),
                ("CSS files", "*.css"),
                ("JSON files", "*.json")
            ]
        )
        
        if file_path:
            self.load_file(file_path)
    
    def _save_file(self):
        """ファイルを保存"""
        return self.save_file()
    
    def _save_as_file(self):
        """名前を付けて保存"""
        file_path = filedialog.asksaveasfilename(
            title="名前を付けて保存",
            defaultextension=".txt",
            filetypes=[
                ("All files", "*.*"),
                ("Python files", "*.py"),
                ("JavaScript files", "*.js"),
                ("Text files", "*.txt"),
                ("HTML files", "*.html"),
                ("CSS files", "*.css"),
                ("JSON files", "*.json")
            ]
        )
        
        if file_path:
            return self.save_file(file_path)
        return False
    
    def _show_search(self):
        """検索ダイアログを表示"""
        if not self.search_dialog:
            self.search_dialog = SearchDialog(self, self.text_area)
        self.search_dialog.show()
    
    def _find_next(self):
        """次を検索"""
        if self.search_dialog:
            self.search_dialog.find_next()
    
    def _goto_line(self):
        """行へ移動"""
        dialog = tk.Toplevel(self)
        dialog.title("行へ移動")
        dialog.geometry("300x100")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="行番号:").pack(anchor=tk.W)
        
        line_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=line_var)
        entry.pack(fill=tk.X, pady=(5, 10))
        entry.focus()
        
        def go_to_line():
            try:
                line_num = int(line_var.get())
                self.goto_line(line_num)
                dialog.destroy()
            except ValueError:
                messagebox.showerror("エラー", "有効な行番号を入力してください")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="移動", command=go_to_line).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="キャンセル", command=dialog.destroy).pack(side=tk.RIGHT)
        
        entry.bind('<Return>', lambda e: go_to_line())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def _change_font(self):
        """フォントを変更"""
        from tkinter import font
        
        # フォント選択ダイアログ（簡易版）
        dialog = tk.Toplevel(self)
        dialog.title("フォント設定")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # フォントファミリー
        ttk.Label(frame, text="フォント:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        font_var = tk.StringVar(value="Consolas")
        font_combo = ttk.Combobox(frame, textvariable=font_var, 
                                 values=["Consolas", "Courier New", "Monaco", "DejaVu Sans Mono"])
        font_combo.grid(row=0, column=1, sticky=tk.EW)
        
        # フォントサイズ
        ttk.Label(frame, text="サイズ:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        size_var = tk.IntVar(value=10)
        size_spin = ttk.Spinbox(frame, from_=8, to=20, textvariable=size_var)
        size_spin.grid(row=1, column=1, sticky=tk.EW)
        
        frame.columnconfigure(1, weight=1)
        
        def apply_font():
            new_font = (font_var.get(), size_var.get())
            self.text_area.config(font=new_font)
            self.line_numbers.font = new_font
            self.line_numbers.redraw()
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="適用", command=apply_font).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="キャンセル", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def _show_settings(self):
        """設定ダイアログを表示"""
        # 設定ダイアログの実装（簡略化）
        messagebox.showinfo("設定", "設定機能は今後実装予定です")
    
    def _show_context_menu(self, event):
        """コンテキストメニューを表示"""
        context_menu = tk.Menu(self, tearoff=0)
        
        # 基本的な編集操作
        context_menu.add_command(label="切り取り", command=lambda: self.text_area.event_generate('<<Cut>>'))
        context_menu.add_command(label="コピー", command=lambda: self.text_area.event_generate('<<Copy>>'))
        context_menu.add_command(label="貼り付け", command=lambda: self.text_area.event_generate('<<Paste>>'))
        context_menu.add_separator()
        
        # 選択操作
        context_menu.add_command(label="全て選択", command=lambda: self.text_area.tag_add(tk.SEL, "1.0", tk.END))
        context_menu.add_separator()
        
        # 検索・移動
        context_menu.add_command(label="検索", command=self._show_search)
        context_menu.add_command(label="行へ移動", command=self._goto_line)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def _on_drag_start(self, event):
        """ドラッグ開始"""
        self._drag_start_index = self.text_area.index(f"@{event.x},{event.y}")
    
    def _on_drag_motion(self, event):
        """ドラッグ中"""
        current_index = self.text_area.index(f"@{event.x},{event.y}")
        if hasattr(self, '_drag_start_index'):
            self.text_area.tag_remove(tk.SEL, "1.0", tk.END)
            self.text_area.tag_add(tk.SEL, self._drag_start_index, current_index)
    
    def _should_create_backup(self, file_path: str) -> bool:
        """バックアップを作成すべきかチェック"""
        # 設定に基づいてバックアップの必要性を判断
        return True  # 簡略化
    
    def _create_backup(self, file_path: str):
        """バックアップファイルを作成"""
        try:
            backup_path = f"{file_path}.backup"
            import shutil
            shutil.copy2(file_path, backup_path)
        except Exception as e:
            self.logger.warning(f"バックアップ作成失敗: {e}")


# 使用例とテスト関数
def test_code_viewer():
    """コードビューアのテスト"""
    root = tk.Tk()
    root.title("Code Viewer Test")
    root.geometry("800x600")
    
    # コードビューアを作成
    viewer = CodeViewer(root)
    viewer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # テスト用のコードを設定
    test_code = '''#!/usr/bin/env python3
"""
テスト用のPythonコード
"""

import os
import sys
from typing import List, Dict, Optional

class TestClass:
    """テストクラス"""
    
    def __init__(self, name: str):
        self.name = name
        self.items: List[str] = []
    
    def add_item(self, item: str) -> None:
        """アイテムを追加"""
        if item not in self.items:
            self.items.append(item)
            print(f"Added: {item}")
    
    def get_items(self) -> List[str]:
        """アイテム一覧を取得"""
        return self.items.copy()

def main():
    """メイン関数"""
    test = TestClass("Test")
    
    # アイテムを追加
    for i in range(5):
        test.add_item(f"item_{i}")
    
    # 結果を表示
    items = test.get_items()
    print(f"Total items: {len(items)}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    
    viewer.set_content(test_code)
    viewer.set_language('python')
    
    # コールバック設定
    def on_line_select(line_num):
        print(f"Line selected: {line_num}")
    
    def on_selection_change(selected_text):
        if selected_text:
            print(f"Selection: {selected_text[:50]}...")
    
    viewer.on_line_select = on_line_select
    viewer.on_selection_change = on_selection_change
    
    root.mainloop()


if __name__ == "__main__":
    test_code_viewer()

