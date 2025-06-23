# src/ui/settings_dialog.py
"""
設定ダイアログ - アプリケーション全体の設定管理UI
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser, font
from typing import Dict, Any, Optional, Callable, List, Tuple, Union
import json
import os
from pathlib import Path
from enum import Enum
import threading
import queue
from datetime import datetime

from ..core.config_manager import ConfigManager
from ..core.llm_interface import LLMProvider
from ..utils.file_utils import FileUtils


class SettingsCategory(Enum):
    """設定カテゴリ列挙"""
    GENERAL = "general"
    LLM = "llm"
    EDITOR = "editor"
    UI = "ui"
    ADVANCED = "advanced"
    PLUGINS = "plugins"


class SettingsValidator:
    """設定値バリデーター"""
    
    @staticmethod
    def validate_port(value: str) -> Tuple[bool, str]:
        """ポート番号の検証"""
        try:
            port = int(value)
            if 1 <= port <= 65535:
                return True, ""
            else:
                return False, "ポート番号は1-65535の範囲で入力してください"
        except ValueError:
            return False, "有効な数値を入力してください"
    
    @staticmethod
    def validate_path(value: str) -> Tuple[bool, str]:
        """パスの検証"""
        if not value.strip():
            return False, "パスを入力してください"
        
        path = Path(value)
        if path.exists():
            return True, ""
        else:
            return False, "指定されたパスが存在しません"
    
    @staticmethod
    def validate_api_key(value: str) -> Tuple[bool, str]:
        """APIキーの検証"""
        if not value.strip():
            return False, "APIキーを入力してください"
        
        if len(value) < 10:
            return False, "APIキーが短すぎます"
        
        return True, ""
    
    @staticmethod
    def validate_positive_int(value: str, min_val: int = 1) -> Tuple[bool, str]:
        """正の整数の検証"""
        try:
            num = int(value)
            if num >= min_val:
                return True, ""
            else:
                return False, f"{min_val}以上の値を入力してください"
        except ValueError:
            return False, "有効な数値を入力してください"
    
    @staticmethod
    def validate_float_range(value: str, min_val: float, max_val: float) -> Tuple[bool, str]:
        """浮動小数点数の範囲検証"""
        try:
            num = float(value)
            if min_val <= num <= max_val:
                return True, ""
            else:
                return False, f"{min_val}から{max_val}の範囲で入力してください"
        except ValueError:
            return False, "有効な数値を入力してください"


class SettingsWidget:
    """設定ウィジェットの基底クラス"""
    
    def __init__(self, parent, key: str, label: str, description: str = ""):
        self.parent = parent
        self.key = key
        self.label = label
        self.description = description
        self.widget = None
        self.var = None
        self.validator = None
        self.on_change: Optional[Callable] = None
        
    def create_widget(self, frame: ttk.Frame) -> ttk.Widget:
        """ウィジェットを作成（サブクラスで実装）"""
        raise NotImplementedError
    
    def get_value(self) -> Any:
        """現在の値を取得（サブクラスで実装）"""
        raise NotImplementedError
    
    def set_value(self, value: Any):
        """値を設定（サブクラスで実装）"""
        raise NotImplementedError
    
    def validate(self) -> Tuple[bool, str]:
        """値を検証"""
        if self.validator:
            return self.validator(str(self.get_value()))
        return True, ""
    
    def _on_change(self, *args):
        """値変更時のコールバック"""
        if self.on_change:
            self.on_change(self.key, self.get_value())


class StringSettingsWidget(SettingsWidget):
    """文字列設定ウィジェット"""
    
    def __init__(self, parent, key: str, label: str, description: str = "", 
                 placeholder: str = "", password: bool = False):
        super().__init__(parent, key, label, description)
        self.placeholder = placeholder
        self.password = password
    
    def create_widget(self, frame: ttk.Frame) -> ttk.Widget:
        """ウィジェットを作成"""
        # ラベル
        ttk.Label(frame, text=self.label).pack(anchor=tk.W)
        
        # 説明
        if self.description:
            desc_label = ttk.Label(frame, text=self.description, 
                                 font=('TkDefaultFont', 8), foreground='gray')
            desc_label.pack(anchor=tk.W, pady=(0, 5))
        
        # エントリ
        self.var = tk.StringVar()
        self.var.trace('w', self._on_change)
        
        if self.password:
            self.widget = ttk.Entry(frame, textvariable=self.var, show='*', width=50)
        else:
            self.widget = ttk.Entry(frame, textvariable=self.var, width=50)
        
        self.widget.pack(fill=tk.X, pady=(0, 10))
        
        # プレースホルダー設定
        if self.placeholder and not self.password:
            self._setup_placeholder()
        
        return self.widget
    
    def _setup_placeholder(self):
        """プレースホルダーを設定"""
        def on_focus_in(event):
            if self.var.get() == self.placeholder:
                self.var.set('')
                self.widget.config(foreground='black')
        
        def on_focus_out(event):
            if not self.var.get():
                self.var.set(self.placeholder)
                self.widget.config(foreground='gray')
        
        self.widget.bind('<FocusIn>', on_focus_in)
        self.widget.bind('<FocusOut>', on_focus_out)
        
        # 初期状態
        if not self.var.get():
            self.var.set(self.placeholder)
            self.widget.config(foreground='gray')
    
    def get_value(self) -> str:
        """現在の値を取得"""
        value = self.var.get()
        if value == self.placeholder:
            return ""
        return value
    
    def set_value(self, value: str):
        """値を設定"""
        self.var.set(value or "")
        if not value and self.placeholder:
            self.var.set(self.placeholder)
            self.widget.config(foreground='gray')
        else:
            self.widget.config(foreground='black')


class NumberSettingsWidget(SettingsWidget):
    """数値設定ウィジェット"""
    
    def __init__(self, parent, key: str, label: str, description: str = "",
                 min_val: float = None, max_val: float = None, 
                 is_integer: bool = True, step: float = 1.0):
        super().__init__(parent, key, label, description)
        self.min_val = min_val
        self.max_val = max_val
        self.is_integer = is_integer
        self.step = step
    
    def create_widget(self, frame: ttk.Frame) -> ttk.Widget:
        """ウィジェットを作成"""
        # ラベル
        ttk.Label(frame, text=self.label).pack(anchor=tk.W)
        
        # 説明
        if self.description:
            desc_label = ttk.Label(frame, text=self.description,
                                 font=('TkDefaultFont', 8), foreground='gray')
            desc_label.pack(anchor=tk.W, pady=(0, 5))
        
        # スピンボックス
        self.var = tk.StringVar()
        self.var.trace('w', self._on_change)
        
        if self.min_val is not None and self.max_val is not None:
            self.widget = ttk.Spinbox(
                frame, 
                textvariable=self.var,
                from_=self.min_val,
                to=self.max_val,
                increment=self.step,
                width=20
            )
        else:
            self.widget = ttk.Entry(frame, textvariable=self.var, width=20)
        
        self.widget.pack(anchor=tk.W, pady=(0, 10))
        
        return self.widget
    
    def get_value(self) -> Union[int, float]:
        """現在の値を取得"""
        try:
            value = self.var.get()
            if self.is_integer:
                return int(value)
            else:
                return float(value)
        except ValueError:
            return 0 if self.is_integer else 0.0
    
    def set_value(self, value: Union[int, float]):
        """値を設定"""
        self.var.set(str(value))


class BooleanSettingsWidget(SettingsWidget):
    """真偽値設定ウィジェット"""
    
    def create_widget(self, frame: ttk.Frame) -> ttk.Widget:
        """ウィジェットを作成"""
        self.var = tk.BooleanVar()
        self.var.trace('w', self._on_change)
        
        self.widget = ttk.Checkbutton(frame, text=self.label, variable=self.var)
        self.widget.pack(anchor=tk.W, pady=(0, 5))
        
        # 説明
        if self.description:
            desc_label = ttk.Label(frame, text=self.description,
                                 font=('TkDefaultFont', 8), foreground='gray')
            desc_label.pack(anchor=tk.W, pady=(0, 10))
        
        return self.widget
    
    def get_value(self) -> bool:
        """現在の値を取得"""
        return self.var.get()
    
    def set_value(self, value: bool):
        """値を設定"""
        self.var.set(bool(value))


class ChoiceSettingsWidget(SettingsWidget):
    """選択肢設定ウィジェット"""
    
    def __init__(self, parent, key: str, label: str, description: str = "",
                 choices: List[Tuple[str, str]] = None):
        super().__init__(parent, key, label, description)
        self.choices = choices or []  # (value, display_name) のリスト
    
    def create_widget(self, frame: ttk.Frame) -> ttk.Widget:
        """ウィジェットを作成"""
        # ラベル
        ttk.Label(frame, text=self.label).pack(anchor=tk.W)
        
        # 説明
        if self.description:
            desc_label = ttk.Label(frame, text=self.description,
                                 font=('TkDefaultFont', 8), foreground='gray')
            desc_label.pack(anchor=tk.W, pady=(0, 5))
        
        # コンボボックス
        self.var = tk.StringVar()
        self.var.trace('w', self._on_change)
        
        display_values = [choice[1] for choice in self.choices]
        self.widget = ttk.Combobox(frame, textvariable=self.var, 
                                  values=display_values, state='readonly', width=30)
        self.widget.pack(anchor=tk.W, pady=(0, 10))
        
        return self.widget
    
    def get_value(self) -> str:
        """現在の値を取得"""
        display_value = self.var.get()
        for value, display in self.choices:
            if display == display_value:
                return value
        return ""
    
    def set_value(self, value: str):
        """値を設定"""
        for val, display in self.choices:
            if val == value:
                self.var.set(display)
                break


class FilePathSettingsWidget(SettingsWidget):
    """ファイルパス設定ウィジェット"""
    
    def __init__(self, parent, key: str, label: str, description: str = "",
                 is_directory: bool = False, file_types: List[Tuple[str, str]] = None):
        super().__init__(parent, key, label, description)
        self.is_directory = is_directory
        self.file_types = file_types or [("すべてのファイル", "*.*")]
    
    def create_widget(self, frame: ttk.Frame) -> ttk.Widget:
        """ウィジェットを作成"""
        # ラベル
        ttk.Label(frame, text=self.label).pack(anchor=tk.W)
        
        # 説明
        if self.description:
            desc_label = ttk.Label(frame, text=self.description,
                                 font=('TkDefaultFont', 8), foreground='gray')
            desc_label.pack(anchor=tk.W, pady=(0, 5))
        
        # パス入力フレーム
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        # エントリ
        self.var = tk.StringVar()
        self.var.trace('w', self._on_change)
        
        self.widget = ttk.Entry(path_frame, textvariable=self.var)
        self.widget.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # 参照ボタン
        ttk.Button(path_frame, text="参照", 
                  command=self._browse_path, width=8).pack(side=tk.RIGHT)
        
        return self.widget
    
    def _browse_path(self):
        """パス参照ダイアログを表示"""
        if self.is_directory:
            path = filedialog.askdirectory(title=f"{self.label}を選択")
        else:
            path = filedialog.askopenfilename(
                title=f"{self.label}を選択",
                filetypes=self.file_types
            )
        
        if path:
            self.var.set(path)
    
    def get_value(self) -> str:
        """現在の値を取得"""
        return self.var.get()
    
    def set_value(self, value: str):
        """値を設定"""
        self.var.set(value or "")


class ColorSettingsWidget(SettingsWidget):
    """色設定ウィジェット"""
    
    def create_widget(self, frame: ttk.Frame) -> ttk.Widget:
        """ウィジェットを作成"""
        # ラベル
        ttk.Label(frame, text=self.label).pack(anchor=tk.W)
        
        # 説明
        if self.description:
            desc_label = ttk.Label(frame, text=self.description,
                                 font=('TkDefaultFont', 8), foreground='gray')
            desc_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 色選択フレーム
        color_frame = ttk.Frame(frame)
        color_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 色表示ラベル
        self.color_var = tk.StringVar(value="#FFFFFF")
        self.color_display = tk.Label(
            color_frame, 
            text="■■■", 
            bg=self.color_var.get(),
            width=5,
            relief=tk.RAISED
        )
        self.color_display.pack(side=tk.LEFT, padx=(0, 5))
        
        # 色コードエントリ
        self.widget = ttk.Entry(color_frame, textvariable=self.color_var, width=10)
        self.widget.pack(side=tk.LEFT, padx=(0, 5))
        
        # 色選択ボタン
        ttk.Button(color_frame, text="選択", 
                  command=self._choose_color, width=8).pack(side=tk.LEFT)
        
        # 色変更時の更新
        self.color_var.trace('w', self._update_color_display)
        self.color_var.trace('w', self._on_change)
        
        return self.widget
    
    def _choose_color(self):
        """色選択ダイアログを表示"""
        color = colorchooser.askcolor(
            title=f"{self.label}を選択",
            initialcolor=self.color_var.get()
        )
        
        if color[1]:  # color[1] は16進数カラーコード
            self.color_var.set(color[1])
    
    def _update_color_display(self, *args):
        """色表示を更新"""
        try:
            color = self.color_var.get()
            self.color_display.config(bg=color)
        except tk.TclError:
            # 無効な色の場合はデフォルト色
            self.color_display.config(bg="#FFFFFF")
    
    def get_value(self) -> str:
        """現在の値を取得"""
        return self.color_var.get()
    
    def set_value(self, value: str):
        """値を設定"""
        self.color_var.set(value or "#FFFFFF")


class FontSettingsWidget(SettingsWidget):
    """フォント設定ウィジェット"""
    
    def create_widget(self, frame: ttk.Frame) -> ttk.Widget:
        """ウィジェットを作成"""
        # ラベル
        ttk.Label(frame, text=self.label).pack(anchor=tk.W)
        
        # 説明
        if self.description:
            desc_label = ttk.Label(frame, text=self.description,
                                 font=('TkDefaultFont', 8), foreground='gray')
            desc_label.pack(anchor=tk.W, pady=(0, 5))
        
        # フォント選択フレーム
        font_frame = ttk.Frame(frame)
        font_frame.pack(fill=tk.X, pady=(0, 10))
        
        # フォント表示ラベル
        self.font_var = tk.StringVar(value="TkDefaultFont 9")
        self.font_display = ttk.Label(font_frame, textvariable=self.font_var, width=30)
        self.font_display.pack(side=tk.LEFT, padx=(0, 5))
        
        # フォント選択ボタン
        ttk.Button(font_frame, text="選択", 
                  command=self._choose_font, width=8).pack(side=tk.LEFT)
        
        self.widget = self.font_display
        return self.widget
    
    def _choose_font(self):
        """フォント選択ダイアログを表示"""
        try:
            # 現在のフォント情報を解析
            current_font = self.font_var.get().split()
            family = current_font[0] if current_font else "TkDefaultFont"
            size = int(current_font[1]) if len(current_font) > 1 else 9
            
            # フォント選択ダイアログ（簡易版）
            dialog = FontSelectionDialog(self.parent, family, size)
            result = dialog.show()
            
            if result:
                family, size, style = result
                font_str = f"{family} {size}"
                if style:
                    font_str += f" {style}"
                self.font_var.set(font_str)
                self._on_change()
                
        except Exception as e:
            logging.getLogger(__name__).error(f"フォント選択エラー: {e}")
    
    def get_value(self) -> str:
        """現在の値を取得"""
        return self.font_var.get()
    
    def set_value(self, value: str):
        """値を設定"""
        self.font_var.set(value or "TkDefaultFont 9")


class SettingsDialog:
    """
    設定ダイアログクラス
    アプリケーション全体の設定を管理するUI
    """
    
    def __init__(self, parent, config_manager: ConfigManager = None):
        self.parent = parent
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)
        
        # ダイアログ
        self.dialog = None
        self.result = False
        
        # 設定ウィジェット
        self.widgets: Dict[str, SettingsWidget] = {}
        self.categories: Dict[SettingsCategory, ttk.Frame] = {}
        
        # UI要素
        self.notebook = None
        self.category_tree = None
        self.content_frame = None
        
        # 変更追跡
        self.changed_settings: Dict[str, Any] = {}
        self.validation_errors: Dict[str, str] = {}
        
        # コールバック
        self.on_settings_changed: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_settings_reset: Optional[Callable[[], None]] = None
        
        self.logger.info("設定ダイアログ初期化完了")
    
    def show(self) -> bool:
        """設定ダイアログを表示"""
        if self.dialog:
            self.dialog.lift()
            return False
        
        self._create_dialog()
        self._create_widgets()
        self._load_current_settings()
        self._center_dialog()
        
        self.dialog.wait_window()
        return self.result
    
    def _create_dialog(self):
        """ダイアログを作成"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("設定")
        self.dialog.geometry("800x600")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # ダイアログのクローズイベント
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 上部フレーム（カテゴリ選択とコンテンツ）
        content_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        content_paned.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # カテゴリ選択
        self._create_category_panel(content_paned)
        
        # 設定コンテンツ
        self._create_content_panel(content_paned)
        
        # ボタンフレーム
        self._create_button_frame(main_frame)
    
    def _create_category_panel(self, parent):
        """カテゴリ選択パネルを作成"""
        category_frame = ttk.Frame(parent)
        parent.add(category_frame, weight=1)
        
        # カテゴリツリー
        ttk.Label(category_frame, text="カテゴリ", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        tree_frame = ttk.Frame(category_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.category_tree = ttk.Treeview(tree_frame, show='tree', selectmode='browse')
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.category_tree.yview)
        self.category_tree.configure(yscrollcommand=scrollbar.set)
        
        self.category_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # カテゴリ項目を追加
        categories = [
            (SettingsCategory.GENERAL, "一般", "🔧"),
            (SettingsCategory.LLM, "LLM設定", "🤖"),
            (SettingsCategory.EDITOR, "エディタ", "📝"),
            (SettingsCategory.UI, "ユーザーインターフェース", "🎨"),
            (SettingsCategory.ADVANCED, "詳細設定", "⚙️"),
            (SettingsCategory.PLUGINS, "プラグイン", "🔌")
        ]
        
        for category, name, icon in categories:
            item_id = self.category_tree.insert('', 'end', text=f"{icon} {name}", 
                                               values=(category.value,))
        
        # カテゴリ選択イベント
        self.category_tree.bind('<<TreeviewSelect>>', self._on_category_selected)
        
        # 最初のカテゴリを選択
        first_item = self.category_tree.get_children()[0]
        self.category_tree.selection_set(first_item)
    
    def _create_content_panel(self, parent):
        """設定コンテンツパネルを作成"""
        content_outer = ttk.Frame(parent)
        parent.add(content_outer, weight=3)
        
        # タイトル
        self.content_title = ttk.Label(content_outer, text="", 
                                      font=('TkDefaultFont', 12, 'bold'))
        self.content_title.pack(anchor=tk.W, pady=(0, 10))
        
        # スクロール可能なコンテンツフレーム
        canvas = tk.Canvas(content_outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_outer, orient=tk.VERTICAL, command=canvas.yview)
        self.content_frame = ttk.Frame(canvas)
        
        self.content_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # マウスホイールバインド
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
    
    def _create_button_frame(self, parent):
        """ボタンフレームを作成"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 左側のボタン
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)
        
        ttk.Button(left_frame, text="デフォルトに戻す", 
                  command=self._reset_to_defaults).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_frame, text="設定をエクスポート", 
                  command=self._export_settings).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_frame, text="設定をインポート", 
                  command=self._import_settings).pack(side=tk.LEFT)
        
        # 右側のボタン
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(right_frame, text="キャンセル", 
                  command=self._on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(right_frame, text="適用", 
                  command=self._on_apply).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(right_frame, text="OK", 
                  command=self._on_ok).pack(side=tk.RIGHT)
    
    def _create_widgets(self):
        """設定ウィジェットを作成"""
        # 各カテゴリの設定ウィジェットを定義
        self._create_general_settings()
        self._create_llm_settings()
        self._create_editor_settings()
        self._create_ui_settings()
        self._create_advanced_settings()
        self._create_plugin_settings()
    
    def _create_general_settings(self):
        """一般設定を作成"""
        category_frame = ttk.Frame(self.content_frame)
        self.categories[SettingsCategory.GENERAL] = category_frame
        
        # 言語設定
        language_widget = ChoiceSettingsWidget(
            self, "general.language", "言語",
            "アプリケーションの表示言語を選択してください",
            [("ja", "日本語"), ("en", "English"), ("zh", "中文")]
        )
        language_widget.validator = lambda x: (True, "")
        self.widgets["general.language"] = language_widget
        
        # 自動保存設定
        autosave_widget = BooleanSettingsWidget(
            self, "general.auto_save", "自動保存を有効にする",
            "ファイルの変更を自動的に保存します"
        )
        self.widgets["general.auto_save"] = autosave_widget
        
        # 自動保存間隔
        autosave_interval_widget = NumberSettingsWidget(
            self, "general.auto_save_interval", "自動保存間隔（秒）",
            "自動保存を実行する間隔を秒単位で指定してください",
            min_val=10, max_val=3600, is_integer=True
        )
        autosave_interval_widget.validator = lambda x: SettingsValidator.validate_positive_int(x, 10)
        self.widgets["general.auto_save_interval"] = autosave_interval_widget
        
        # 最近使用したファイル数
        recent_files_widget = NumberSettingsWidget(
            self, "general.recent_files_count", "最近使用したファイル数",
            "メニューに表示する最近使用したファイルの数",
            min_val=0, max_val=20, is_integer=True
        )
        self.widgets["general.recent_files_count"] = recent_files_widget
        
        # 作業ディレクトリ
        workspace_widget = FilePathSettingsWidget(
            self, "general.workspace_path", "デフォルト作業ディレクトリ",
            "プロジェクトファイルのデフォルト保存場所",
            is_directory=True
        )
        workspace_widget.validator = SettingsValidator.validate_path
        self.widgets["general.workspace_path"] = workspace_widget
    
    def _create_llm_settings(self):
        """LLM設定を作成"""
        category_frame = ttk.Frame(self.content_frame)
        self.categories[SettingsCategory.LLM] = category_frame
        
        # LLMプロバイダー選択
        provider_widget = ChoiceSettingsWidget(
            self, "llm.provider", "LLMプロバイダー",
            "使用するLLMサービスを選択してください",
            [(provider.value, provider.value.upper()) for provider in LLMProvider]
        )
        self.widgets["llm.provider"] = provider_widget
        
        # OpenAI設定
        openai_frame = ttk.LabelFrame(category_frame, text="OpenAI設定", padding=10)
        
        openai_api_key_widget = StringSettingsWidget(
            self, "llm.openai.api_key", "APIキー",
            "OpenAI APIキーを入力してください",
            password=True
        )
        openai_api_key_widget.validator = SettingsValidator.validate_api_key
        self.widgets["llm.openai.api_key"] = openai_api_key_widget
        
        openai_model_widget = ChoiceSettingsWidget(
            self, "llm.openai.model", "モデル",
            "使用するOpenAIモデルを選択してください",
            [
                ("gpt-4", "GPT-4"),
                ("gpt-4-turbo", "GPT-4 Turbo"),
                ("gpt-3.5-turbo", "GPT-3.5 Turbo")
            ]
        )
        self.widgets["llm.openai.model"] = openai_model_widget
        
        openai_temperature_widget = NumberSettingsWidget(
            self, "llm.openai.temperature", "Temperature",
            "応答の創造性を制御します（0.0-2.0）",
            min_val=0.0, max_val=2.0, is_integer=False, step=0.1
        )
        openai_temperature_widget.validator = lambda x: SettingsValidator.validate_float_range(x, 0.0, 2.0)
        self.widgets["llm.openai.temperature"] = openai_temperature_widget
        
        # Claude設定
        claude_frame = ttk.LabelFrame(category_frame, text="Claude設定", padding=10)
        
        claude_api_key_widget = StringSettingsWidget(
            self, "llm.claude.api_key", "APIキー",
            "Anthropic APIキーを入力してください",
            password=True
        )
        claude_api_key_widget.validator = SettingsValidator.validate_api_key
        self.widgets["llm.claude.api_key"] = claude_api_key_widget
        
        claude_model_widget = ChoiceSettingsWidget(
            self, "llm.claude.model", "モデル",
            "使用するClaudeモデルを選択してください",
            [
                ("claude-3-opus-20240229", "Claude 3 Opus"),
                ("claude-3-sonnet-20240229", "Claude 3 Sonnet"),
                ("claude-3-haiku-20240307", "Claude 3 Haiku")
            ]
        )
        self.widgets["llm.claude.model"] = claude_model_widget
        
        # ローカルLLM設定
        local_frame = ttk.LabelFrame(category_frame, text="ローカルLLM設定", padding=10)
        
        local_endpoint_widget = StringSettingsWidget(
            self, "llm.local.endpoint", "エンドポイントURL",
            "ローカルLLMサーバーのエンドポイントURL"
        )
        self.widgets["llm.local.endpoint"] = local_endpoint_widget
        
        local_model_widget = StringSettingsWidget(
            self, "llm.local.model_name", "モデル名",
            "使用するローカルモデルの名前"
        )
        self.widgets["llm.local.model_name"] = local_model_widget
    
    def _create_editor_settings(self):
        """エディタ設定を作成"""
        category_frame = ttk.Frame(self.content_frame)
        self.categories[SettingsCategory.EDITOR] = category_frame
        
        # フォント設定
        font_widget = FontSettingsWidget(
            self, "editor.font", "エディタフォント",
            "コードエディタで使用するフォント"
        )
        self.widgets["editor.font"] = font_widget
        
        # タブサイズ
        tab_size_widget = NumberSettingsWidget(
            self, "editor.tab_size", "タブサイズ",
            "タブ文字のスペース数",
            min_val=1, max_val=8, is_integer=True
        )
        self.widgets["editor.tab_size"] = tab_size_widget
        
        # 行番号表示
        line_numbers_widget = BooleanSettingsWidget(
            self, "editor.show_line_numbers", "行番号を表示",
            "エディタに行番号を表示します"
        )
        self.widgets["editor.show_line_numbers"] = line_numbers_widget
        
        # シンタックスハイライト
        syntax_highlight_widget = BooleanSettingsWidget(
            self, "editor.syntax_highlighting", "シンタックスハイライト",
            "コードのシンタックスハイライトを有効にします"
        )
        self.widgets["editor.syntax_highlighting"] = syntax_highlight_widget
        
        # 自動インデント
        auto_indent_widget = BooleanSettingsWidget(
            self, "editor.auto_indent", "自動インデント",
            "新しい行で自動的にインデントを調整します"
        )
        self.widgets["editor.auto_indent"] = auto_indent_widget
        
        # 単語の折り返し
        word_wrap_widget = BooleanSettingsWidget(
            self, "editor.word_wrap", "単語の折り返し",
            "長い行を自動的に折り返します"
        )
        self.widgets["editor.word_wrap"] = word_wrap_widget
    
    def _create_ui_settings(self):
        """UI設定を作成"""
        category_frame = ttk.Frame(self.content_frame)
        self.categories[SettingsCategory.UI] = category_frame
        
        # テーマ設定
        theme_widget = ChoiceSettingsWidget(
            self, "ui.theme", "テーマ",
            "アプリケーションのテーマを選択してください",
            [
                ("light", "ライト"),
                ("dark", "ダーク"),
                ("auto", "システム設定に従う")
            ]
        )
        self.widgets["ui.theme"] = theme_widget
        
        # ウィンドウサイズ記憶
        remember_size_widget = BooleanSettingsWidget(
            self, "ui.remember_window_size", "ウィンドウサイズを記憶",
            "アプリケーション終了時のウィンドウサイズを記憶します"
        )
        self.widgets["ui.remember_window_size"] = remember_size_widget
        
        # ツールバー表示
        show_toolbar_widget = BooleanSettingsWidget(
            self, "ui.show_toolbar", "ツールバーを表示",
            "メインウィンドウにツールバーを表示します"
        )
        self.widgets["ui.show_toolbar"] = show_toolbar_widget
        
        # ステータスバー表示
        show_statusbar_widget = BooleanSettingsWidget(
            self, "ui.show_statusbar", "ステータスバーを表示",
            "メインウィンドウにステータスバーを表示します"
        )
        self.widgets["ui.show_statusbar"] = show_statusbar_widget
        
        # アニメーション
        animations_widget = BooleanSettingsWidget(
            self, "ui.enable_animations", "アニメーションを有効にする",
            "UI要素のアニメーション効果を有効にします"
        )
        self.widgets["ui.enable_animations"] = animations_widget
        
        # 色設定
        colors_frame = ttk.LabelFrame(category_frame, text="色設定", padding=10)
        
        # 背景色
        bg_color_widget = ColorSettingsWidget(
            self, "ui.colors.background", "背景色",
            "エディタの背景色"
        )
        self.widgets["ui.colors.background"] = bg_color_widget
        
        # テキスト色
        text_color_widget = ColorSettingsWidget(
            self, "ui.colors.text", "テキスト色",
            "エディタのテキスト色"
        )
        self.widgets["ui.colors.text"] = text_color_widget
        
        # 選択色
        selection_color_widget = ColorSettingsWidget(
            self, "ui.colors.selection", "選択色",
            "テキスト選択時の背景色"
        )
        self.widgets["ui.colors.selection"] = selection_color_widget
    
    def _create_advanced_settings(self):
        """詳細設定を作成"""
        category_frame = ttk.Frame(self.content_frame)
        self.categories[SettingsCategory.ADVANCED] = category_frame
        
        # ログレベル
        log_level_widget = ChoiceSettingsWidget(
            self, "advanced.log_level", "ログレベル",
            "アプリケーションのログレベルを設定します",
            [
                ("DEBUG", "DEBUG"),
                ("INFO", "INFO"),
                ("WARNING", "WARNING"),
                ("ERROR", "ERROR"),
                ("CRITICAL", "CRITICAL")
            ]
        )
        self.widgets["advanced.log_level"] = log_level_widget
        
        # ログファイルパス
        log_file_widget = FilePathSettingsWidget(
            self, "advanced.log_file", "ログファイル",
            "ログを保存するファイルパス",
            file_types=[("ログファイル", "*.log"), ("すべてのファイル", "*.*")]
        )
        self.widgets["advanced.log_file"] = log_file_widget
        
        # デバッグモード
        debug_mode_widget = BooleanSettingsWidget(
            self, "advanced.debug_mode", "デバッグモードを有効にする",
            "詳細なデバッグ情報を表示します"
        )
        self.widgets["advanced.debug_mode"] = debug_mode_widget
        
        # パフォーマンス設定
        perf_frame = ttk.LabelFrame(category_frame, text="パフォーマンス設定", padding=10)
        
        # 最大メモリ使用量
        max_memory_widget = NumberSettingsWidget(
            self, "advanced.max_memory_mb", "最大メモリ使用量（MB）",
            "アプリケーションの最大メモリ使用量",
            min_val=128, max_val=8192, is_integer=True
        )
        self.widgets["advanced.max_memory_mb"] = max_memory_widget
        
        # キャッシュサイズ
        cache_size_widget = NumberSettingsWidget(
            self, "advanced.cache_size", "キャッシュサイズ",
            "ファイルキャッシュのサイズ",
            min_val=10, max_val=1000, is_integer=True
        )
        self.widgets["advanced.cache_size"] = cache_size_widget
        
        # 並列処理数
        thread_count_widget = NumberSettingsWidget(
            self, "advanced.thread_count", "並列処理数",
            "同時実行するスレッド数",
            min_val=1, max_val=16, is_integer=True
        )
        self.widgets["advanced.thread_count"] = thread_count_widget
    
    def _create_plugin_settings(self):
        """プラグイン設定を作成"""
        category_frame = ttk.Frame(self.content_frame)
        self.categories[SettingsCategory.PLUGINS] = category_frame
        
        # プラグイン有効化
        plugins_enabled_widget = BooleanSettingsWidget(
            self, "plugins.enabled", "プラグインを有効にする",
            "サードパーティプラグインの使用を許可します"
        )
        self.widgets["plugins.enabled"] = plugins_enabled_widget
        
        # プラグインディレクトリ
        plugins_dir_widget = FilePathSettingsWidget(
            self, "plugins.directory", "プラグインディレクトリ",
            "プラグインファイルを検索するディレクトリ",
            is_directory=True
        )
        self.widgets["plugins.directory"] = plugins_dir_widget
        
        # 自動更新
        auto_update_widget = BooleanSettingsWidget(
            self, "plugins.auto_update", "プラグインの自動更新",
            "プラグインを自動的に更新します"
        )
        self.widgets["plugins.auto_update"] = auto_update_widget
        
        # プラグインリスト
        plugins_list_frame = ttk.LabelFrame(category_frame, text="インストール済みプラグイン", padding=10)
        
        # プラグインリストビュー（実装は簡略化）
        plugins_tree = ttk.Treeview(plugins_list_frame, 
                                   columns=('name', 'version', 'status'), 
                                   show='headings', height=6)
        plugins_tree.heading('name', text='名前')
        plugins_tree.heading('version', text='バージョン')
        plugins_tree.heading('status', text='状態')
        
        plugins_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # プラグインボタン
        plugin_buttons = ttk.Frame(plugins_list_frame)
        plugin_buttons.pack(fill=tk.X)
        
        ttk.Button(plugin_buttons, text="インストール", width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(plugin_buttons, text="アンインストール", width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(plugin_buttons, text="更新", width=12).pack(side=tk.LEFT)
    
    def _on_category_selected(self, event):
        """カテゴリ選択時の処理"""
        selection = self.category_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        category_value = self.category_tree.item(item, 'values')[0]
        category = SettingsCategory(category_value)
        
        # コンテンツフレームをクリア
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 選択されたカテゴリのウィジェットを表示
        self._show_category_content(category)
    
    def _show_category_content(self, category: SettingsCategory):
        """カテゴリのコンテンツを表示"""
        category_titles = {
            SettingsCategory.GENERAL: "一般設定",
            SettingsCategory.LLM: "LLM設定", 
            SettingsCategory.EDITOR: "エディタ設定",
            SettingsCategory.UI: "ユーザーインターフェース設定",
            SettingsCategory.ADVANCED: "詳細設定",
            SettingsCategory.PLUGINS: "プラグイン設定"
        }
        
        self.content_title.config(text=category_titles.get(category, "設定"))
        
        # カテゴリ別のウィジェットを作成・表示
        category_widgets = [widget for key, widget in self.widgets.items() 
                           if key.startswith(category.value)]
        
        for widget in category_widgets:
            widget.create_widget(self.content_frame)
            
            # 変更コールバックを設定
            widget.on_change = self._on_setting_changed
    
    def _on_setting_changed(self, key: str, value: Any):
        """設定値変更時の処理"""
        self.changed_settings[key] = value
        
        # バリデーション実行
        if key in self.widgets:
            widget = self.widgets[key]
            is_valid, error_msg = widget.validate()
            
            if is_valid:
                self.validation_errors.pop(key, None)
            else:
                self.validation_errors[key] = error_msg
        
        self.logger.debug(f"設定変更: {key} = {value}")
    
    def _load_current_settings(self):
        """現在の設定値をロード"""
        try:
            for key, widget in self.widgets.items():
                value = self.config_manager.get(key)
                if value is not None:
                    widget.set_value(value)
            
            self.logger.info("現在の設定値をロードしました")
            
        except Exception as e:
            self.logger.error(f"設定値ロードエラー: {e}")
            messagebox.showerror("エラー", f"設定値の読み込みに失敗しました: {e}")
    
    def _validate_all_settings(self) -> bool:
        """すべての設定を検証"""
        self.validation_errors.clear()
        
        for key, widget in self.widgets.items():
            is_valid, error_msg = widget.validate()
            if not is_valid:
                self.validation_errors[key] = error_msg
        
        if self.validation_errors:
            error_messages = []
            for key, msg in self.validation_errors.items():
                widget = self.widgets[key]
                error_messages.append(f"• {widget.label}: {msg}")
            
            messagebox.showerror(
                "入力エラー", 
                "以下の設定項目に問題があります:\n\n" + "\n".join(error_messages)
            )
            return False
        
        return True
    
    def _apply_settings(self):
        """設定を適用"""
        if not self._validate_all_settings():
            return False
        
        try:
            # 変更された設定を保存
            for key, value in self.changed_settings.items():
                self.config_manager.set(key, value)
            
            # 設定ファイルに保存
            self.config_manager.save()
            
            # コールバック実行
            if self.on_settings_changed and self.changed_settings:
                self.on_settings_changed(self.changed_settings.copy())
            
            self.changed_settings.clear()
            self.logger.info("設定を適用しました")
            return True
            
        except Exception as e:
            self.logger.error(f"設定適用エラー: {e}")
            messagebox.showerror("エラー", f"設定の保存に失敗しました: {e}")
            return False
    
    def _reset_to_defaults(self):
        """設定をデフォルトに戻す"""
        result = messagebox.askyesno(
            "確認", 
            "すべての設定をデフォルト値に戻しますか？\nこの操作は元に戻せません。"
        )
        
        if result:
            try:
                # デフォルト設定をロード
                self.config_manager.reset_to_defaults()
                
                # ウィジェットの値を更新
                self._load_current_settings()
                
                # コールバック実行
                if self.on_settings_reset:
                    self.on_settings_reset()
                
                self.logger.info("設定をデフォルトに戻しました")
                messagebox.showinfo("完了", "設定をデフォルト値に戻しました")
                
            except Exception as e:
                self.logger.error(f"デフォルト復元エラー: {e}")
                messagebox.showerror("エラー", f"デフォルト設定の復元に失敗しました: {e}")
    
    def _export_settings(self):
        """設定をエクスポート"""
        file_path = filedialog.asksaveasfilename(
            title="設定をエクスポート",
            defaultextension=".json",
            filetypes=[
                ("JSON設定ファイル", "*.json"),
                ("すべてのファイル", "*.*")
            ]
        )
        
        if file_path:
            try:
                settings_data = {
                    "exported_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "settings": {}
                }
                
                # 現在の設定値を収集
                for key, widget in self.widgets.items():
                    settings_data["settings"][key] = widget.get_value()
                
                # ファイルに保存
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings_data, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"設定をエクスポートしました: {file_path}")
                messagebox.showinfo("完了", f"設定をエクスポートしました:\n{file_path}")
                
            except Exception as e:
                self.logger.error(f"設定エクスポートエラー: {e}")
                messagebox.showerror("エラー", f"設定のエクスポートに失敗しました: {e}")
    
    def _import_settings(self):
        """設定をインポート"""
        file_path = filedialog.askopenfilename(
            title="設定をインポート",
            filetypes=[
                ("JSON設定ファイル", "*.json"),
                ("すべてのファイル", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                
                if "settings" not in settings_data:
                    raise ValueError("無効な設定ファイル形式です")
                
                # 設定値を適用
                imported_count = 0
                for key, value in settings_data["settings"].items():
                    if key in self.widgets:
                        self.widgets[key].set_value(value)
                        self.changed_settings[key] = value
                        imported_count += 1
                
                self.logger.info(f"設定をインポートしました: {file_path} ({imported_count}項目)")
                messagebox.showinfo("完了", f"設定をインポートしました:\n{imported_count}項目が更新されました")
                
            except Exception as e:
                self.logger.error(f"設定インポートエラー: {e}")
                messagebox.showerror("エラー", f"設定のインポートに失敗しました: {e}")
    
    def _center_dialog(self):
        """ダイアログを画面中央に配置"""
        self.dialog.update_idletasks()
        
        # 画面サイズを取得
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        
        # ダイアログサイズを取得
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # 中央座標を計算
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _on_ok(self):
        """OKボタン押下時の処理"""
        if self._apply_settings():
            self.result = True
            self.dialog.destroy()
            self.dialog = None
    
    def _on_apply(self):
        """適用ボタン押下時の処理"""
        self._apply_settings()
    
    def _on_cancel(self):
        """キャンセルボタン押下時の処理"""
        if self.changed_settings:
            result = messagebox.askyesnocancel(
                "確認",
                "変更された設定があります。保存しますか？"
            )
            
            if result is True:  # 保存する
                if not self._apply_settings():
                    return
            elif result is None:  # キャンセル
                return
        
        self.result = False
        self.dialog.destroy()
        self.dialog = None


class FontSelectionDialog:
    """フォント選択ダイアログ（簡易版）"""
    
    def __init__(self, parent, current_family: str = "TkDefaultFont", current_size: int = 9):
        self.parent = parent
        self.current_family = current_family
        self.current_size = current_size
        self.result = None
        
        self.dialog = None
        self.family_var = None
        self.size_var = None
        self.style_var = None
    
    def show(self) -> Optional[Tuple[str, int, str]]:
        """フォント選択ダイアログを表示"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("フォント選択")
        self.dialog.geometry("400x300")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._center_dialog()
        
        self.dialog.wait_window()
        return self.result
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # フォントファミリー選択
        ttk.Label(main_frame, text="フォントファミリー:").pack(anchor=tk.W)
        
        self.family_var = tk.StringVar(value=self.current_family)
        family_combo = ttk.Combobox(main_frame, textvariable=self.family_var, 
                                   values=list(font.families()), state='readonly')
        family_combo.pack(fill=tk.X, pady=(0, 10))
        
        # フォントサイズ選択
        ttk.Label(main_frame, text="サイズ:").pack(anchor=tk.W)
        
        self.size_var = tk.StringVar(value=str(self.current_size))
        size_combo = ttk.Combobox(main_frame, textvariable=self.size_var,
                                 values=[str(i) for i in range(8, 72, 2)], width=10)
        size_combo.pack(anchor=tk.W, pady=(0, 10))
        
        # スタイル選択
        ttk.Label(main_frame, text="スタイル:").pack(anchor=tk.W)
        
        self.style_var = tk.StringVar(value="normal")
        style_frame = ttk.Frame(main_frame)
        style_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Radiobutton(style_frame, text="標準", variable=self.style_var, 
                       value="normal").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(style_frame, text="太字", variable=self.style_var, 
                       value="bold").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(style_frame, text="斜体", variable=self.style_var, 
                       value="italic").pack(side=tk.LEFT)
        
        # プレビュー
        ttk.Label(main_frame, text="プレビュー:").pack(anchor=tk.W, pady=(10, 0))
        
        self.preview_label = ttk.Label(main_frame, text="サンプルテキスト Sample Text 123",
                                      relief=tk.SUNKEN, padding=10)
        self.preview_label.pack(fill=tk.X, pady=(0, 10))
        
        # プレビュー更新
        self.family_var.trace('w', self._update_preview)
        self.size_var.trace('w', self._update_preview)
        self.style_var.trace('w', self._update_preview)
        self._update_preview()
        
        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="キャンセル", 
                  command=self._on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="OK", 
                  command=self._on_ok).pack(side=tk.RIGHT)
    
    def _update_preview(self, *args):
        """プレビューを更新"""
        try:
            family = self.family_var.get()
            size = int(self.size_var.get())
            style = self.style_var.get()
            
            preview_font = (family, size, style)
            self.preview_label.config(font=preview_font)
        except (ValueError, tk.TclError):
            pass
    
    def _center_dialog(self):
        """ダイアログを中央に配置"""
        self.dialog.update_idletasks()
        
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _on_ok(self):
        """OK押下時の処理"""
        try:
            family = self.family_var.get()
            size = int(self.size_var.get())
            style = self.style_var.get()
            
            self.result = (family, size, style)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("エラー", "有効なフォントサイズを入力してください")
    
    def _on_cancel(self):
        """キャンセル押下時の処理"""
        self.result = None
        self.dialog.destroy()


# 使用例とテスト用のコード
if __name__ == "__main__":
    import sys
    import os
    
    # パスを追加してモジュールをインポート可能にする
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    
    from src.core.config_manager import ConfigManager
    
    class TestApplication:
        """テスト用アプリケーション"""
        
        def __init__(self):
            self.root = tk.Tk()
            self.root.title("設定ダイアログテスト")
            self.root.geometry("300x200")
            
            self.config_manager = ConfigManager()
            
            # テスト用ボタン
            ttk.Button(self.root, text="設定を開く", 
                      command=self.open_settings).pack(pady=20)
            
            ttk.Button(self.root, text="現在の設定を表示", 
                      command=self.show_current_settings).pack(pady=10)
            
            ttk.Button(self.root, text="終了", 
                      command=self.root.quit).pack(pady=10)
        
        def open_settings(self):
            """設定ダイアログを開く"""
            dialog = SettingsDialog(self.root, self.config_manager)
            
            # コールバックを設定
            dialog.on_settings_changed = self.on_settings_changed
            dialog.on_settings_reset = self.on_settings_reset
            
            result = dialog.show()
            
            if result:
                print("設定が保存されました")
            else:
                print("設定がキャンセルされました")
        
        def on_settings_changed(self, changed_settings: Dict[str, Any]):
            """設定変更時のコールバック"""
            print("設定が変更されました:")
            for key, value in changed_settings.items():
                print(f"  {key}: {value}")
        
        def on_settings_reset(self):
            """設定リセット時のコールバック"""
            print("設定がリセットされました")
        
        def show_current_settings(self):
            """現在の設定を表示"""
            settings = self.config_manager.get_all()
            
            # 新しいウィンドウで設定を表示
            settings_window = tk.Toplevel(self.root)
            settings_window.title("現在の設定")
            settings_window.geometry("500x400")
            
            # テキストウィジェット
            text_frame = ttk.Frame(settings_window, padding=10)
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, 
                                     command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 設定内容を表示
            text_widget.insert(tk.END, "現在の設定:\n\n")
            for key, value in sorted(settings.items()):
                text_widget.insert(tk.END, f"{key}: {value}\n")
            
            text_widget.config(state=tk.DISABLED)
        
        def run(self):
            """アプリケーションを実行"""
            self.root.mainloop()
    
    # テストアプリケーションを実行
    if __name__ == "__main__":
        app = TestApplication()
        app.run()
