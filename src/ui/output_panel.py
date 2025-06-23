# src/ui/output_panel.py
"""
出力パネル - ログ、実行結果、エラー情報の表示
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable, Dict, List, Any, Tuple, Union
import threading
import queue
import time
from datetime import datetime
from enum import Enum
import re
import json
from pathlib import Path

from ..core.config_manager import ConfigManager
from ..utils.file_utils import FileUtils


class LogLevel(Enum):
    """ログレベル列挙"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OutputType(Enum):
    """出力タイプ列挙"""
    LOG = "log"
    STDOUT = "stdout"
    STDERR = "stderr"
    RESULT = "result"
    COMMAND = "command"
    SYSTEM = "system"


class LogEntry:
    """ログエントリクラス"""
    
    def __init__(self, message: str, level: LogLevel = LogLevel.INFO, 
                 output_type: OutputType = OutputType.LOG, timestamp: datetime = None):
        self.message = message
        self.level = level
        self.output_type = output_type
        self.timestamp = timestamp or datetime.now()
        self.source = ""
        self.line_number = None
        self.thread_name = threading.current_thread().name
        
        # メッセージの解析
        self._parse_message()
    
    def _parse_message(self):
        """メッセージを解析してソース情報を抽出"""
        # ファイル名と行番号のパターン
        file_pattern = r'File "([^"]+)", line (\d+)'
        match = re.search(file_pattern, self.message)
        if match:
            self.source = match.group(1)
            self.line_number = int(match.group(2))
    
    def get_formatted_message(self, include_timestamp: bool = True, 
                            include_level: bool = True) -> str:
        """フォーマット済みメッセージを取得"""
        parts = []
        
        if include_timestamp:
            parts.append(self.timestamp.strftime("%H:%M:%S"))
        
        if include_level:
            parts.append(f"[{self.level.value}]")
        
        if self.source:
            source_name = Path(self.source).name
            if self.line_number:
                parts.append(f"{source_name}:{self.line_number}")
            else:
                parts.append(source_name)
        
        parts.append(self.message)
        
        return " ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'message': self.message,
            'level': self.level.value,
            'output_type': self.output_type.value,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'line_number': self.line_number,
            'thread_name': self.thread_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """辞書から復元"""
        entry = cls(
            message=data['message'],
            level=LogLevel(data['level']),
            output_type=OutputType(data['output_type']),
            timestamp=datetime.fromisoformat(data['timestamp'])
        )
        entry.source = data.get('source', '')
        entry.line_number = data.get('line_number')
        entry.thread_name = data.get('thread_name', '')
        return entry


class LogFilter:
    """ログフィルタークラス"""
    
    def __init__(self):
        self.enabled_levels: set = {LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL}
        self.enabled_types: set = {OutputType.LOG, OutputType.STDOUT, OutputType.STDERR, OutputType.RESULT}
        self.search_text: str = ""
        self.case_sensitive: bool = False
        self.use_regex: bool = False
        self.source_filter: str = ""
        self.time_range: Tuple[Optional[datetime], Optional[datetime]] = (None, None)
    
    def matches(self, entry: LogEntry) -> bool:
        """エントリがフィルター条件に一致するかチェック"""
        # レベルフィルター
        if entry.level not in self.enabled_levels:
            return False
        
        # タイプフィルター
        if entry.output_type not in self.enabled_types:
            return False
        
        # テキスト検索
        if self.search_text:
            text_to_search = entry.message
            search_text = self.search_text
            
            if not self.case_sensitive:
                text_to_search = text_to_search.lower()
                search_text = search_text.lower()
            
            if self.use_regex:
                try:
                    if not re.search(search_text, text_to_search):
                        return False
                except re.error:
                    # 正規表現エラーの場合は通常の文字列検索
                    if search_text not in text_to_search:
                        return False
            else:
                if search_text not in text_to_search:
                    return False
        
        # ソースフィルター
        if self.source_filter:
            if self.source_filter.lower() not in entry.source.lower():
                return False
        
        # 時間範囲フィルター
        start_time, end_time = self.time_range
        if start_time and entry.timestamp < start_time:
            return False
        if end_time and entry.timestamp > end_time:
            return False
        
        return True


class OutputPanelTab:
    """出力パネルタブクラス"""
    
    def __init__(self, name: str, output_types: List[OutputType] = None):
        self.name = name
        self.output_types = output_types or [OutputType.LOG]
        self.entries: List[LogEntry] = []
        self.filter = LogFilter()
        self.filter.enabled_types = set(self.output_types)
        self.max_entries = 10000
        self.auto_scroll = True
        self.word_wrap = True
    
    def add_entry(self, entry: LogEntry):
        """エントリを追加"""
        if entry.output_type in self.output_types:
            self.entries.append(entry)
            
            # 最大エントリ数を超えた場合は古いものを削除
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[-self.max_entries:]
    
    def get_filtered_entries(self) -> List[LogEntry]:
        """フィルター済みエントリを取得"""
        return [entry for entry in self.entries if self.filter.matches(entry)]
    
    def clear(self):
        """エントリをクリア"""
        self.entries.clear()


class OutputPanel(ttk.Frame):
    """
    出力パネルクラス
    ログ、実行結果、エラー情報の表示機能を提供
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # 設定管理
        self.config_manager = ConfigManager()
        
        # コールバック関数
        self.on_error_click: Optional[Callable[[LogEntry], None]] = None
        self.on_clear_request: Optional[Callable[[], None]] = None
        self.on_export_request: Optional[Callable[[List[LogEntry]], None]] = None
        
        # 状態管理
        self.tabs: Dict[str, OutputPanelTab] = {}
        self.current_tab: Optional[str] = None
        self.message_queue = queue.Queue()
        self.is_paused = False
        self.follow_tail = True
        
        # UI要素
        self.notebook = None
        self.text_widgets: Dict[str, tk.Text] = {}
        self.scrollbars: Dict[str, ttk.Scrollbar] = {}
        
        # 統計情報
        self.stats = {
            'total_messages': 0,
            'error_count': 0,
            'warning_count': 0,
            'session_start': datetime.now()
        }
        
        # UI作成
        self._create_widgets()
        self._setup_styles()
        self._setup_default_tabs()
        self._start_message_processor()
        
        # 設定読み込み
        self._load_settings()
        
        self.logger.info("出力パネル初期化完了")
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ツールバー
        self._create_toolbar(main_frame)
        
        # タブ付きノートブック
        self._create_notebook(main_frame)
        
        # ステータスバー
        self._create_status_bar(main_frame)
    
    def _create_toolbar(self, parent):
        """ツールバーを作成"""
        self.toolbar = ttk.Frame(parent)
        self.toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # 左側のボタン
        left_frame = ttk.Frame(self.toolbar)
        left_frame.pack(side=tk.LEFT)
        
        # クリア
        ttk.Button(
            left_frame,
            text="クリア",
            command=self._clear_current_tab,
            width=8
        ).pack(side=tk.LEFT, padx=(0, 2))
        
        # 一時停止/再開
        self.pause_var = tk.BooleanVar()
        self.pause_button = ttk.Checkbutton(
            left_frame,
            text="一時停止",
            variable=self.pause_var,
            command=self._toggle_pause
        )
        self.pause_button.pack(side=tk.LEFT, padx=(0, 2))
        
        # 自動スクロール
        self.autoscroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            left_frame,
            text="自動スクロール",
            variable=self.autoscroll_var,
            command=self._toggle_autoscroll
        ).pack(side=tk.LEFT, padx=(0, 2))
        
        # 右側のボタン
        right_frame = ttk.Frame(self.toolbar)
        right_frame.pack(side=tk.RIGHT)
        
        # エクスポート
        ttk.Button(
            right_frame,
            text="エクスポート",
            command=self._export_logs,
            width=10
        ).pack(side=tk.RIGHT, padx=(2, 0))
        
        # 検索
        ttk.Button(
            right_frame,
            text="検索",
            command=self._show_search_dialog,
            width=8
        ).pack(side=tk.RIGHT, padx=(2, 0))
        
        # フィルター
        ttk.Button(
            right_frame,
            text="フィルター",
            command=self._show_filter_dialog,
            width=8
        ).pack(side=tk.RIGHT, padx=(2, 0))
    
    def _create_notebook(self, parent):
        """ノートブックを作成"""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # タブ変更イベント
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
    
    def _create_status_bar(self, parent):
        """ステータスバーを作成"""
        self.status_frame = ttk.Frame(parent)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        # ステータスラベル
        self.status_label = ttk.Label(self.status_frame, text="準備完了")
        self.status_label.pack(side=tk.LEFT)
        
        # 統計情報
        self.stats_label = ttk.Label(self.status_frame, text="")
        self.stats_label.pack(side=tk.RIGHT)
        
        # 定期的にステータスを更新
        self._update_status()
    
    def _setup_styles(self):
        """スタイルを設定"""
        # テキストウィジェットのタグ設定
        self.text_tags = {
            LogLevel.DEBUG: {'foreground': '#808080'},
            LogLevel.INFO: {'foreground': '#000000'},
            LogLevel.WARNING: {'foreground': '#FF8C00', 'font': ('TkDefaultFont', 9, 'bold')},
            LogLevel.ERROR: {'foreground': '#DC143C', 'font': ('TkDefaultFont', 9, 'bold')},
            LogLevel.CRITICAL: {'foreground': '#8B0000', 'font': ('TkDefaultFont', 9, 'bold'), 'background': '#FFE4E1'},
            
            # 出力タイプ別
            OutputType.STDOUT: {'foreground': '#006400'},
            OutputType.STDERR: {'foreground': '#DC143C'},
            OutputType.COMMAND: {'foreground': '#4169E1', 'font': ('TkDefaultFont', 9, 'bold')},
            OutputType.SYSTEM: {'foreground': '#9932CC'},
            
            # 特殊タグ
            'timestamp': {'foreground': '#696969', 'font': ('TkDefaultFont', 8)},
            'source': {'foreground': '#4682B4', 'underline': True},
            'selected': {'background': '#E6F3FF'},
            'search_highlight': {'background': '#FFFF00'}
        }
    
    def _setup_default_tabs(self):
        """デフォルトタブを設定"""
        # 全ログタブ
        self.add_tab("すべて", [OutputType.LOG, OutputType.STDOUT, OutputType.STDERR, 
                               OutputType.RESULT, OutputType.COMMAND, OutputType.SYSTEM])
        
        # ログタブ
        self.add_tab("ログ", [OutputType.LOG])
        
        # 出力タブ
        self.add_tab("出力", [OutputType.STDOUT, OutputType.RESULT])
        
        # エラータブ
        self.add_tab("エラー", [OutputType.STDERR])
        
        # 最初のタブを選択
        if self.tabs:
            first_tab = list(self.tabs.keys())[0]
            self.current_tab = first_tab
    
    def _start_message_processor(self):
        """メッセージ処理スレッドを開始"""
        def process_messages():
            while True:
                try:
                    # キューからメッセージを取得（タイムアウト付き）
                    entry = self.message_queue.get(timeout=0.1)
                    
                    if not self.is_paused:
                        # UIスレッドでメッセージを表示
                        self.after_idle(self._display_entry, entry)
                    
                    self.message_queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    self.logger.error(f"メッセージ処理エラー: {e}")
        
        self.message_thread = threading.Thread(target=process_messages, daemon=True)
        self.message_thread.start()
    
    # ===== 公開メソッド =====
    
    def add_tab(self, name: str, output_types: List[OutputType]):
        """タブを追加"""
        if name in self.tabs:
            self.logger.warning(f"タブ '{name}' は既に存在します")
            return
        
        # タブオブジェクトを作成
        tab = OutputPanelTab(name, output_types)
        self.tabs[name] = tab
        
        # UIタブを作成
        self._create_tab_ui(name, tab)
        
        self.logger.debug(f"タブ追加: {name}")
    
    def remove_tab(self, name: str):
        """タブを削除"""
        if name not in self.tabs:
            return
        
        # UIタブを削除
        for i, tab_id in enumerate(self.notebook.tabs()):
            if self.notebook.tab(tab_id, 'text') == name:
                self.notebook.forget(i)
                break
        
        # テキストウィジェットを削除
        if name in self.text_widgets:
            del self.text_widgets[name]
        if name in self.scrollbars:
            del self.scrollbars[name]
        
        # タブオブジェクトを削除
        del self.tabs[name]
        
        # 現在のタブが削除された場合
        if self.current_tab == name:
            if self.tabs:
                self.current_tab = list(self.tabs.keys())[0]
            else:
                self.current_tab = None
        
        self.logger.debug(f"タブ削除: {name}")
    
    def log(self, message: str, level: LogLevel = LogLevel.INFO, 
            output_type: OutputType = OutputType.LOG):
        """ログメッセージを追加"""
        entry = LogEntry(message, level, output_type)
        self.add_entry(entry)
    
    def add_entry(self, entry: LogEntry):
        """ログエントリを追加"""
        # 統計更新
        self.stats['total_messages'] += 1
        if entry.level == LogLevel.ERROR:
            self.stats['error_count'] += 1
        elif entry.level == LogLevel.WARNING:
            self.stats['warning_count'] += 1
        
        # キューに追加
        try:
            self.message_queue.put_nowait(entry)
        except queue.Full:
            # キューが満杯の場合は古いメッセージを削除
            try:
                self.message_queue.get_nowait()
                self.message_queue.put_nowait(entry)
            except queue.Empty:
                pass
    
    def clear_tab(self, tab_name: str):
        """指定タブをクリア"""
        if tab_name in self.tabs:
            self.tabs[tab_name].clear()
            if tab_name in self.text_widgets:
                self.text_widgets[tab_name].delete(1.0, tk.END)
            self.logger.debug(f"タブクリア: {tab_name}")
    
    def clear_all(self):
        """すべてのタブをクリア"""
        for tab_name in self.tabs:
            self.clear_tab(tab_name)
        
        # 統計リセット
        self.stats = {
            'total_messages': 0,
            'error_count': 0,
            'warning_count': 0,
            'session_start': datetime.now()
        }
        
        self.logger.debug("全タブクリア")
    
    def set_filter(self, tab_name: str, filter_obj: LogFilter):
        """フィルターを設定"""
        if tab_name in self.tabs:
            self.tabs[tab_name].filter = filter_obj
            self._refresh_tab_display(tab_name)
    
    def search(self, text: str, case_sensitive: bool = False, use_regex: bool = False):
        """テキスト検索"""
        if not self.current_tab or self.current_tab not in self.text_widgets:
            return
        
        text_widget = self.text_widgets[self.current_tab]
        
        # 既存のハイライトをクリア
        text_widget.tag_remove('search_highlight', 1.0, tk.END)
        
        if not text:
            return
        
        # 検索実行
        search_text = text
        content = text_widget.get(1.0, tk.END)
        
        if not case_sensitive:
            search_text = search_text.lower()
            content = content.lower()
        
        start_pos = 1.0
        count = 0
        
        while True:
            if use_regex:
                try:
                    import re
                    match = re.search(search_text, content[text_widget.index(start_pos):])
                    if not match:
                        break
                    
                    # マッチ位置を計算
                    match_start = text_widget.index(f"{start_pos}+{match.start()}c")
                    match_end = text_widget.index(f"{start_pos}+{match.end()}c")
                    
                except re.error:
                    # 正規表現エラーの場合は通常検索
                    pos = text_widget.search(text, start_pos, tk.END, nocase=not case_sensitive)
                    if not pos:
                        break
                    match_start = pos
                    match_end = f"{pos}+{len(text)}c"
            else:
                pos = text_widget.search(text, start_pos, tk.END, nocase=not case_sensitive)
                if not pos:
                    break
                match_start = pos
                match_end = f"{pos}+{len(text)}c"
            
            # ハイライト
            text_widget.tag_add('search_highlight', match_start, match_end)
            start_pos = match_end
            count += 1
        
        # 最初のマッチにスクロール
        if count > 0:
            first_match = text_widget.tag_ranges('search_highlight')[0]
            text_widget.see(first_match)
        
        self.logger.debug(f"検索結果: {count} 件")
        return count
    
    def export_logs(self, tab_name: str, file_path: str, format_type: str = 'txt'):
        """ログをエクスポート"""
        if tab_name not in self.tabs:
            return False
        
        try:
            tab = self.tabs[tab_name]
            entries = tab.get_filtered_entries()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if format_type == 'json':
                    # JSON形式
                    data = {
                        'tab_name': tab_name,
                        'export_time': datetime.now().isoformat(),
                        'entries': [entry.to_dict() for entry in entries]
                    }
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
                elif format_type == 'csv':
                    # CSV形式
                    import csv
                    writer = csv.writer(f)
                    writer.writerow(['Timestamp', 'Level', 'Type', 'Source', 'Line', 'Message'])
                    
                    for entry in entries:
                        writer.writerow([
                            entry.timestamp.isoformat(),
                            entry.level.value,
                            entry.output_type.value,
                            entry.source,
                            entry.line_number or '',
                            entry.message
                        ])
                else:
                    # テキスト形式
                    f.write(f"# {tab_name} ログエクスポート\n")
                    f.write(f"# エクスポート日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# エントリ数: {len(entries)}\n\n")
                    
                    for entry in entries:
                        f.write(entry.get_formatted_message() + '\n')
            
            self.logger.info(f"ログエクスポート完了: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ログエクスポートエラー: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        runtime = datetime.now() - self.stats['session_start']
        
        return {
            **self.stats,
            'runtime_seconds': runtime.total_seconds(),
            'runtime_formatted': str(runtime).split('.')[0],
            'tabs_count': len(self.tabs),
            'current_tab': self.current_tab,
            'is_paused': self.is_paused
        }
    
    # ===== プライベートメソッド =====
    
    def _create_tab_ui(self, name: str, tab: OutputPanelTab):
        """タブのUIを作成"""
        # タブフレーム
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=name)
        
        # テキストウィジェットとスクロールバー
        text_frame = ttk.Frame(tab_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # テキストウィジェット
        text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD if tab.word_wrap else tk.NONE,
            state=tk.DISABLED,
            font=('Consolas', 9),
            bg='white',
            fg='black'
        )
        
        # スクロールバー
        v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        h_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
        
        text_widget.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 配置
        text_widget.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        # タグ設定
        for tag, style in self.text_tags.items():
            text_widget.tag_configure(str(tag), **style)
        
        # イベントバインド
        text_widget.bind('<Button-3>', lambda e: self._show_context_menu(e, name))
        text_widget.bind('<Double-Button-1>', lambda e: self._on_text_double_click(e, name))
        
        # ウィジェットを保存
        self.text_widgets[name] = text_widget
        self.scrollbars[name] = v_scrollbar
    
    def _display_entry(self, entry: LogEntry):
        """エントリを表示"""
        # 該当するタブに追加
        for tab_name, tab in self.tabs.items():
            if entry.output_type in tab.output_types:
                tab.add_entry(entry)
                
                # フィルターチェック
                if tab.filter.matches(entry):
                    self._append_to_text_widget(tab_name, entry)
    
    def _append_to_text_widget(self, tab_name: str, entry: LogEntry):
        """テキストウィジェットにエントリを追加"""
        if tab_name not in self.text_widgets:
            return
        
        text_widget = self.text_widgets[tab_name]
        
        # テキストウィジェットを一時的に編集可能にする
        text_widget.config(state=tk.NORMAL)
        
        try:
            # 現在の位置を記録
            at_end = text_widget.yview()[1] == 1.0
            
            # メッセージを構築
            formatted_message = entry.get_formatted_message()
            
            # テキストを挿入
            start_pos = text_widget.index(tk.END + '-1c')
            text_widget.insert(tk.END, formatted_message + '\n')
            end_pos = text_widget.index(tk.END + '-1c')
            
            # タグを適用
            self._apply_tags(text_widget, start_pos, end_pos, entry)
            
            # 自動スクロール
            if self.autoscroll_var.get() and at_end:
                text_widget.see(tk.END)
            
            # 最大行数制限
            self._limit_text_lines(text_widget, tab_name)
            
        finally:
            # テキストウィジェットを読み取り専用に戻す
            text_widget.config(state=tk.DISABLED)

    def _apply_tags(self, text_widget: tk.Text, start_pos: str, end_pos: str, entry: LogEntry):
        """テキストにタグを適用"""
        # レベル別タグ
        text_widget.tag_add(str(entry.level), start_pos, end_pos)
        
        # 出力タイプ別タグ
        text_widget.tag_add(str(entry.output_type), start_pos, end_pos)
        
        # 行の内容を取得してタグを適用
        line_content = text_widget.get(start_pos, end_pos)
        
        # タイムスタンプ部分
        timestamp_match = re.match(r'(\d{2}:\d{2}:\d{2})', line_content)
        if timestamp_match:
            ts_end = f"{start_pos}+{timestamp_match.end()}c"
            text_widget.tag_add('timestamp', start_pos, ts_end)
        
        # ソース情報（ファイル名:行番号）
        source_pattern = r'([^/\\]+\.\w+:\d+)'
        source_matches = re.finditer(source_pattern, line_content)
        for match in source_matches:
            source_start = f"{start_pos}+{match.start()}c"
            source_end = f"{start_pos}+{match.end()}c"
            text_widget.tag_add('source', source_start, source_end)
        
        # エラーレベルの場合は行全体を強調
        if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            text_widget.tag_add('error_line', start_pos, end_pos)
    
    def _limit_text_lines(self, text_widget: tk.Text, tab_name: str):
        """テキストの最大行数を制限"""
        if tab_name not in self.tabs:
            return
        
        max_lines = self.tabs[tab_name].max_entries
        current_lines = int(text_widget.index(tk.END).split('.')[0]) - 1
        
        if current_lines > max_lines:
            # 古い行を削除
            lines_to_delete = current_lines - max_lines
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, f"{lines_to_delete + 1}.0")
            text_widget.config(state=tk.DISABLED)
    
    def _refresh_tab_display(self, tab_name: str):
        """タブ表示を更新"""
        if tab_name not in self.tabs or tab_name not in self.text_widgets:
            return
        
        tab = self.tabs[tab_name]
        text_widget = self.text_widgets[tab_name]
        
        # テキストをクリア
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        
        # フィルター済みエントリを再表示
        filtered_entries = tab.get_filtered_entries()
        for entry in filtered_entries:
            self._append_to_text_widget(tab_name, entry)
        
        text_widget.config(state=tk.DISABLED)
    
    def _update_status(self):
        """ステータスを更新"""
        try:
            # 基本ステータス
            if self.is_paused:
                status_text = "一時停止中"
            elif self.current_tab:
                tab = self.tabs[self.current_tab]
                filtered_count = len(tab.get_filtered_entries())
                total_count = len(tab.entries)
                status_text = f"{self.current_tab}: {filtered_count}/{total_count} 件"
            else:
                status_text = "準備完了"
            
            self.status_label.config(text=status_text)
            
            # 統計情報
            stats = self.get_statistics()
            stats_text = f"総計: {stats['total_messages']} | エラー: {stats['error_count']} | 警告: {stats['warning_count']} | 実行時間: {stats['runtime_formatted']}"
            self.stats_label.config(text=stats_text)
            
        except Exception as e:
            self.logger.error(f"ステータス更新エラー: {e}")
        
        # 5秒後に再実行
        self.after(5000, self._update_status)
    
    # ===== イベントハンドラー =====
    
    def _on_tab_changed(self, event):
        """タブ変更イベント"""
        try:
            current_index = self.notebook.index(self.notebook.select())
            tab_names = list(self.tabs.keys())
            if 0 <= current_index < len(tab_names):
                self.current_tab = tab_names[current_index]
                self.logger.debug(f"タブ変更: {self.current_tab}")
        except Exception as e:
            self.logger.error(f"タブ変更エラー: {e}")
    
    def _clear_current_tab(self):
        """現在のタブをクリア"""
        if self.current_tab:
            if messagebox.askyesno("確認", f"'{self.current_tab}' タブの内容をクリアしますか？"):
                self.clear_tab(self.current_tab)
                
                # コールバック実行
                if self.on_clear_request:
                    self.on_clear_request()
    
    def _toggle_pause(self):
        """一時停止/再開を切り替え"""
        self.is_paused = self.pause_var.get()
        status = "一時停止" if self.is_paused else "再開"
        self.logger.debug(f"出力パネル{status}")
    
    def _toggle_autoscroll(self):
        """自動スクロールを切り替え"""
        auto_scroll = self.autoscroll_var.get()
        for tab_name, tab in self.tabs.items():
            tab.auto_scroll = auto_scroll
        
        self.logger.debug(f"自動スクロール: {'有効' if auto_scroll else '無効'}")
    
    def _show_search_dialog(self):
        """検索ダイアログを表示"""
        dialog = SearchDialog(self, self)
        dialog.show()
    
    def _show_filter_dialog(self):
        """フィルターダイアログを表示"""
        if not self.current_tab:
            messagebox.showwarning("警告", "タブが選択されていません")
            return
        
        dialog = FilterDialog(self, self.tabs[self.current_tab].filter, self.current_tab)
        if dialog.show():
            self._refresh_tab_display(self.current_tab)
    
    def _export_logs(self):
        """ログをエクスポート"""
        if not self.current_tab:
            messagebox.showwarning("警告", "タブが選択されていません")
            return
        
        # ファイル選択ダイアログ
        file_types = [
            ("テキストファイル", "*.txt"),
            ("JSONファイル", "*.json"),
            ("CSVファイル", "*.csv"),
            ("すべてのファイル", "*.*")
        ]
        
        file_path = filedialog.asksaveasfilename(
            title="ログをエクスポート",
            defaultextension=".txt",
            filetypes=file_types,
            initialfilename=f"{self.current_tab}_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        if file_path:
            # ファイル形式を判定
            format_type = 'txt'
            if file_path.endswith('.json'):
                format_type = 'json'
            elif file_path.endswith('.csv'):
                format_type = 'csv'
            
            if self.export_logs(self.current_tab, file_path, format_type):
                messagebox.showinfo("完了", f"ログをエクスポートしました:\n{file_path}")
                
                # コールバック実行
                if self.on_export_request:
                    tab = self.tabs[self.current_tab]
                    self.on_export_request(tab.get_filtered_entries())
            else:
                messagebox.showerror("エラー", "ログのエクスポートに失敗しました")
    
    def _show_context_menu(self, event, tab_name: str):
        """コンテキストメニューを表示"""
        menu = tk.Menu(self, tearoff=0)
        
        # コピー
        menu.add_command(label="コピー", command=lambda: self._copy_selection(tab_name))
        menu.add_command(label="すべて選択", command=lambda: self._select_all(tab_name))
        menu.add_separator()
        
        # 検索
        menu.add_command(label="検索", command=self._show_search_dialog)
        menu.add_command(label="フィルター", command=self._show_filter_dialog)
        menu.add_separator()
        
        # クリア
        menu.add_command(label="クリア", command=lambda: self.clear_tab(tab_name))
        menu.add_command(label="エクスポート", command=self._export_logs)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def _on_text_double_click(self, event, tab_name: str):
        """テキストダブルクリックイベント"""
        if tab_name not in self.text_widgets:
            return
        
        text_widget = self.text_widgets[tab_name]
        
        # クリック位置の行を取得
        line_index = text_widget.index(f"@{event.x},{event.y}").split('.')[0]
        line_content = text_widget.get(f"{line_index}.0", f"{line_index}.end")
        
        # ソース情報を抽出
        source_pattern = r'([^/\\]+\.\w+):(\d+)'
        match = re.search(source_pattern, line_content)
        
        if match and self.on_error_click:
            # LogEntryを作成してコールバック実行
            entry = LogEntry(line_content)
            entry.source = match.group(1)
            entry.line_number = int(match.group(2))
            self.on_error_click(entry)
    
    def _copy_selection(self, tab_name: str):
        """選択テキストをコピー"""
        if tab_name not in self.text_widgets:
            return
        
        text_widget = self.text_widgets[tab_name]
        try:
            selected_text = text_widget.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            # 選択されていない場合は何もしない
            pass
    
    def _select_all(self, tab_name: str):
        """すべてのテキストを選択"""
        if tab_name not in self.text_widgets:
            return
        
        text_widget = self.text_widgets[tab_name]
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, "1.0")
        text_widget.see(tk.INSERT)
    
    def _load_settings(self):
        """設定を読み込み"""
        try:
            settings = self.config_manager.get_section('output_panel', {})
            
            # フィルター設定
            for tab_name, tab in self.tabs.items():
                tab_settings = settings.get(f'tab_{tab_name}', {})
                
                # フィルター設定を復元
                filter_settings = tab_settings.get('filter', {})
                if 'enabled_levels' in filter_settings:
                    tab.filter.enabled_levels = {LogLevel(level) for level in filter_settings['enabled_levels']}
                if 'search_text' in filter_settings:
                    tab.filter.search_text = filter_settings['search_text']
                if 'case_sensitive' in filter_settings:
                    tab.filter.case_sensitive = filter_settings['case_sensitive']
                
                # 表示設定
                if 'auto_scroll' in tab_settings:
                    tab.auto_scroll = tab_settings['auto_scroll']
                if 'word_wrap' in tab_settings:
                    tab.word_wrap = tab_settings['word_wrap']
                if 'max_entries' in tab_settings:
                    tab.max_entries = tab_settings['max_entries']
            
            # UI設定
            ui_settings = settings.get('ui', {})
            if 'follow_tail' in ui_settings:
                self.follow_tail = ui_settings['follow_tail']
                self.autoscroll_var.set(self.follow_tail)
            
            self.logger.debug("出力パネル設定読み込み完了")
            
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {e}")
    
    def _save_settings(self):
        """設定を保存"""
        try:
            settings = {}
            
            # タブ別設定
            for tab_name, tab in self.tabs.items():
                tab_settings = {
                    'filter': {
                        'enabled_levels': [level.value for level in tab.filter.enabled_levels],
                        'search_text': tab.filter.search_text,
                        'case_sensitive': tab.filter.case_sensitive,
                        'use_regex': tab.filter.use_regex
                    },
                    'auto_scroll': tab.auto_scroll,
                    'word_wrap': tab.word_wrap,
                    'max_entries': tab.max_entries
                }
                settings[f'tab_{tab_name}'] = tab_settings
            
            # UI設定
            settings['ui'] = {
                'follow_tail': self.autoscroll_var.get(),
                'current_tab': self.current_tab
            }
            
            self.config_manager.set_section('output_panel', settings)
            self.logger.debug("出力パネル設定保存完了")
            
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
    
    def destroy(self):
        """クリーンアップ"""
        # 設定を保存
        self._save_settings()
        
        # メッセージ処理を停止
        if hasattr(self, 'message_thread'):
            # キューに終了シグナルを送信
            try:
                self.message_queue.put_nowait(None)
            except queue.Full:
                pass
        
        super().destroy()


class SearchDialog:
    """検索ダイアログ"""
    
    def __init__(self, parent, output_panel: OutputPanel):
        self.parent = parent
        self.output_panel = output_panel
        self.dialog = None
        self.search_count = 0
    
    def show(self):
        """検索ダイアログを表示"""
        if self.dialog:
            self.dialog.lift()
            return
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("検索")
        self.dialog.geometry("400x200")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._center_dialog()
        
        self.search_entry.focus()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 検索テキスト
        ttk.Label(main_frame, text="検索テキスト:").pack(anchor=tk.W)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(main_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(fill=tk.X, pady=(5, 15))
        
        # オプション
        options_frame = ttk.LabelFrame(main_frame, text="オプション", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="大文字小文字を区別", 
                       variable=self.case_sensitive_var).pack(anchor=tk.W)
        
        self.use_regex_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="正規表現を使用", 
                       variable=self.use_regex_var).pack(anchor=tk.W)
        
        # 結果表示
        self.result_label = ttk.Label(main_frame, text="")
        self.result_label.pack(anchor=tk.W, pady=(0, 15))
        
        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="閉じる", command=self._close).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="すべてクリア", command=self._clear_highlights).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="検索", command=self._search).pack(side=tk.RIGHT)
        
        # イベントバインド
        self.search_entry.bind('<Return>', lambda e: self._search())
        self.dialog.bind('<Escape>', lambda e: self._close())
    
    def _center_dialog(self):
        """ダイアログを中央に配置"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _search(self):
        """検索実行"""
        search_text = self.search_var.get().strip()
        if not search_text:
            return
        
        case_sensitive = self.case_sensitive_var.get()
        use_regex = self.use_regex_var.get()
        
        count = self.output_panel.search(search_text, case_sensitive, use_regex)
        
        if count > 0:
            self.result_label.config(text=f"{count} 件見つかりました", foreground="green")
        else:
            self.result_label.config(text="見つかりませんでした", foreground="red")
        
        self.search_count = count
    
    def _clear_highlights(self):
        """ハイライトをクリア"""
        self.output_panel.search("")  # 空文字で検索してハイライトをクリア
        self.result_label.config(text="ハイライトをクリアしました")
    
    def _close(self):
        """ダイアログを閉じる"""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None


class FilterDialog:
    """フィルターダイアログ"""
    
    def __init__(self, parent, filter_obj: LogFilter, tab_name: str):
        self.parent = parent
        self.filter = filter_obj
        self.tab_name = tab_name
        self.dialog = None
        self.result = False
    
    def show(self) -> bool:
        """フィルターダイアログを表示"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"フィルター - {self.tab_name}")
        self.dialog.geometry("450x400")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._load_current_settings()
        self._center_dialog()
        
        self.dialog.wait_window()
        return self.result
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ログレベルフィルター
        level_frame = ttk.LabelFrame(main_frame, text="ログレベル", padding=10)
        level_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.level_vars = {}
        for level in LogLevel:
            var = tk.BooleanVar()
            ttk.Checkbutton(level_frame, text=level.value, variable=var).pack(anchor=tk.W)
            self.level_vars[level] = var
        
        # テキスト検索フィルター
        text_frame = ttk.LabelFrame(main_frame, text="テキスト検索", padding=10)
        text_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(text_frame, text="検索テキスト:").pack(anchor=tk.W)
        self.search_var = tk.StringVar()
        ttk.Entry(text_frame, textvariable=self.search_var, width=40).pack(fill=tk.X, pady=(5, 10))
        
        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(text_frame, text="大文字小文字を区別", 
                       variable=self.case_sensitive_var).pack(anchor=tk.W)
        
        self.use_regex_var = tk.BooleanVar()
        ttk.Checkbutton(text_frame, text="正規表現を使用", 
                       variable=self.use_regex_var).pack(anchor=tk.W)
        
        # ソースフィルター
        source_frame = ttk.LabelFrame(main_frame, text="ソースフィルター", padding=10)
        source_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(source_frame, text="ソースファイル:").pack(anchor=tk.W)
        self.source_var = tk.StringVar()
        ttk.Entry(source_frame, textvariable=self.source_var, width=40).pack(fill=tk.X, pady=(5, 0))
        
        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        ttk.Button(button_frame, text="キャンセル", command=self._cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="リセット", command=self._reset).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="適用", command=self._apply).pack(side=tk.RIGHT)
    
    def _center_dialog(self):
        """ダイアログを中央に配置"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _load_current_settings(self):
        """現在の設定を読み込み"""
        # ログレベル
        for level, var in self.level_vars.items():
            var.set(level in self.filter.enabled_levels)
        
        # テキスト検索
        self.search_var.set(self.filter.search_text)
        self.case_sensitive_var.set(self.filter.case_sensitive)
        self.use_regex_var.set(self.filter.use_regex)
        
        # ソースフィルター
        self.source_var.set(self.filter.source_filter)
    
    def _apply(self):
        """フィルターを適用"""
        # ログレベル
        self.filter.enabled_levels = {level for level, var in self.level_vars.items() if var.get()}
        
        # テキスト検索
        self.filter.search_text = self.search_var.get()
        self.filter.case_sensitive = self.case_sensitive_var.get()
        self.filter.use_regex = self.use_regex_var.get()
        
        # ソースフィルター
        self.filter.source_filter = self.source_var.get()
        
        self.result = True
        self.dialog.destroy()
    
    def _reset(self):
        """フィルターをリセット"""
        # すべてのレベルを有効にする
        for var in self.level_vars.values():
            var.set(True)
        
        # テキスト検索をクリア
        self.search_var.set("")
        self.case_sensitive_var.set(False)
        self.use_regex_var.set(False)
        
        # ソースフィルターをクリア
        self.source_var.set("")
    
    def _cancel(self):
        """キャンセル"""
        self.result = False
        self.dialog.destroy()


# 使用例とテスト関数
def test_output_panel():
    """出力パネルのテスト"""
    root = tk.Tk()
    root.title("Output Panel Test")
    root.geometry("800x600")
    
    # 出力パネルを作成
    output_panel = OutputPanel(root)
    output_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # コールバック設定
    def on_error_click(entry: LogEntry):
        print(f"Error clicked: {entry.source}:{entry.line_number}")
        messagebox.showinfo("エラークリック", f"ファイル: {entry.source}\n行番号: {entry.line_number}")
    
    def on_clear_request():
        print("Clear requested")
    
    def on_export_request(entries: List[LogEntry]):
        print(f"Export requested: {len(entries)} entries")
    
    # コールバックを設定
    output_panel.on_error_click = on_error_click
    output_panel.on_clear_request = on_clear_request
    output_panel.on_export_request = on_export_request
    
    # テスト用のログメッセージを生成
    def generate_test_logs():
        import random
        
        messages = [
            "アプリケーション開始",
            "設定ファイルを読み込み中...",
            "データベース接続成功",
            "ユーザー認証完了",
            "処理を開始します",
            "File \"main.py\", line 42, in process_data\n    result = calculate(data)",
            "警告: メモリ使用量が高くなっています",
            "File \"utils.py\", line 15, in validate_input\n    raise ValueError('Invalid input')",
            "エラー: データベース接続に失敗しました",
            "致命的エラー: システムリソースが不足しています",
            "処理が正常に完了しました",
            "アプリケーション終了"
        ]
        
        levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
        types = [OutputType.LOG, OutputType.STDOUT, OutputType.STDERR, OutputType.RESULT]
        
        for i in range(50):
            message = random.choice(messages)
            level = random.choice(levels)
            output_type = random.choice(types)
            
            output_panel.log(f"{message} ({i+1})", level, output_type)
            
            # 少し待機
            root.update()
            time.sleep(0.1)
    
    # テストボタンを追加
    test_frame = ttk.Frame(root)
    test_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    ttk.Button(test_frame, text="テストログ生成", command=generate_test_logs).pack(side=tk.LEFT, padx=(0, 5))
    ttk.Button(test_frame, text="エラーログ", 
              command=lambda: output_panel.log("テストエラーメッセージ", LogLevel.ERROR, OutputType.STDERR)).pack(side=tk.LEFT, padx=(0, 5))
    ttk.Button(test_frame, text="警告ログ", 
              command=lambda: output_panel.log("テスト警告メッセージ", LogLevel.WARNING)).pack(side=tk.LEFT, padx=(0, 5))
    ttk.Button(test_frame, text="情報ログ", 
              command=lambda: output_panel.log("テスト情報メッセージ", LogLevel.INFO)).pack(side=tk.LEFT)
    
    print("出力パネルをテストしてください:")
    print("- 各タブの表示")
    print("- ログメッセージの追加")
    print("- フィルター機能")
    print("- 検索機能")
    print("- エクスポート機能")
    print("- コンテキストメニュー")
    print("- エラー行のダブルクリック")
    
    root.mainloop()


if __name__ == "__main__":
    test_output_panel()

