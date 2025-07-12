# src/ui/settings_dialog.py
"""
設定ダイアログモジュール
アプリケーションの各種設定を管理するGUIダイアログ
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from ..core.logger import get_logger
from ..core.config_manager import get_config
from ..llm.llm_factory import get_llm_factory

logger = get_logger(__name__)

class SettingsDialog:
    """設定ダイアログクラス"""
    
    def __init__(self, parent: tk.Tk, on_settings_changed: Optional[Callable] = None):
        """
        初期化
        
        Args:
            parent: 親ウィンドウ
            on_settings_changed: 設定変更時のコールバック関数
        """
        self.parent = parent
        self.on_settings_changed = on_settings_changed
        self.logger = get_logger(self.__class__.__name__)
        
        # 設定管理とLLMファクトリーを取得
        self.config = get_config()
        self.llm_factory = get_llm_factory()
        
        # ダイアログウィンドウ
        self.dialog = None
        
        # 設定値を保持する変数
        self.settings_vars = {}
        
        # タブ別のフレーム
        self.tab_frames = {}
        
        self.logger.info("SettingsDialog を初期化しました")
    
    def show(self):
        """設定ダイアログを表示"""
        try:
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.lift()
                self.dialog.focus_force()
                return
            
            self._create_dialog()
            self._create_widgets()
            self._load_current_settings()
            
            # ダイアログを中央に配置
            self._center_dialog()
            
            # モーダルダイアログとして表示
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            self.dialog.focus_set()
            
            self.logger.info("設定ダイアログを表示しました")
            
        except Exception as e:
            self.logger.error(f"設定ダイアログ表示エラー: {e}")
            messagebox.showerror("エラー", f"設定ダイアログの表示に失敗しました: {e}")
    
    def _create_dialog(self):
        """ダイアログウィンドウを作成"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("設定")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        
        # ダイアログが閉じられた時の処理
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        try:
            # メインフレーム
            main_frame = ttk.Frame(self.dialog, padding="10")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # タブノートブック
            self.notebook = ttk.Notebook(main_frame)
            self.notebook.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
            
            # 各タブを作成
            self._create_llm_tab()
            self._create_ui_tab()
            self._create_file_tab()
            self._create_advanced_tab()
            
            # ボタンフレーム
            button_frame = ttk.Frame(main_frame)
            button_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
            
            # ボタン
            ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="キャンセル", command=self._on_cancel).pack(side=tk.RIGHT)
            ttk.Button(button_frame, text="適用", command=self._on_apply).pack(side=tk.RIGHT, padx=(0, 5))
            ttk.Button(button_frame, text="デフォルトに戻す", command=self._on_reset_defaults).pack(side=tk.LEFT)
            
            # グリッドの重みを設定
            main_frame.columnconfigure(0, weight=1)
            main_frame.rowconfigure(0, weight=1)
            self.dialog.columnconfigure(0, weight=1)
            self.dialog.rowconfigure(0, weight=1)
            
        except Exception as e:
            self.logger.error(f"ウィジェット作成エラー: {e}")
            raise
    
    def _create_llm_tab(self):
        """LLM設定タブを作成"""
        try:
            # LLMタブフレーム
            llm_frame = ttk.Frame(self.notebook, padding="10")
            self.notebook.add(llm_frame, text="LLM設定")
            self.tab_frames['llm'] = llm_frame
            
            # スクロール可能フレーム
            canvas = tk.Canvas(llm_frame)
            scrollbar = ttk.Scrollbar(llm_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # デフォルトプロバイダー設定
            provider_group = ttk.LabelFrame(scrollable_frame, text="デフォルトプロバイダー", padding="10")
            provider_group.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(provider_group, text="プロバイダー:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.settings_vars['default_provider'] = tk.StringVar()
            provider_combo = ttk.Combobox(provider_group, textvariable=self.settings_vars['default_provider'],
                                        values=list(self.llm_factory.get_available_providers()), state="readonly")
            provider_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            ttk.Label(provider_group, text="モデル:").grid(row=1, column=0, sticky=tk.W, pady=2)
            self.settings_vars['default_model'] = tk.StringVar()
            self.model_combo = ttk.Combobox(provider_group, textvariable=self.settings_vars['default_model'])
            self.model_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            # プロバイダー変更時にモデルリストを更新
            provider_combo.bind('<<ComboboxSelected>>', self._on_provider_changed)
            
            provider_group.columnconfigure(1, weight=1)
            
            # OpenAI設定
            openai_group = ttk.LabelFrame(scrollable_frame, text="OpenAI設定", padding="10")
            openai_group.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(openai_group, text="API キー:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.settings_vars['openai_api_key'] = tk.StringVar()
            api_key_entry = ttk.Entry(openai_group, textvariable=self.settings_vars['openai_api_key'], show="*")
            api_key_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            ttk.Label(openai_group, text="ベースURL:").grid(row=1, column=0, sticky=tk.W, pady=2)
            self.settings_vars['openai_base_url'] = tk.StringVar()
            ttk.Entry(openai_group, textvariable=self.settings_vars['openai_base_url']).grid(
                row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            ttk.Label(openai_group, text="温度:").grid(row=2, column=0, sticky=tk.W, pady=2)
            self.settings_vars['openai_temperature'] = tk.DoubleVar()
            temp_scale = ttk.Scale(openai_group, from_=0.0, to=2.0, 
                                 variable=self.settings_vars['openai_temperature'], orient=tk.HORIZONTAL)
            temp_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            openai_group.columnconfigure(1, weight=1)
            
            # Anthropic設定
            anthropic_group = ttk.LabelFrame(scrollable_frame, text="Anthropic設定", padding="10")
            anthropic_group.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(anthropic_group, text="API キー:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.settings_vars['anthropic_api_key'] = tk.StringVar()
            ttk.Entry(anthropic_group, textvariable=self.settings_vars['anthropic_api_key'], show="*").grid(
                row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            ttk.Label(anthropic_group, text="温度:").grid(row=1, column=0, sticky=tk.W, pady=2)
            self.settings_vars['anthropic_temperature'] = tk.DoubleVar()
            ttk.Scale(anthropic_group, from_=0.0, to=1.0, 
                     variable=self.settings_vars['anthropic_temperature'], orient=tk.HORIZONTAL).grid(
                row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            anthropic_group.columnconfigure(1, weight=1)
            
            # Ollama設定
            ollama_group = ttk.LabelFrame(scrollable_frame, text="Ollama設定", padding="10")
            ollama_group.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(ollama_group, text="ベースURL:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.settings_vars['ollama_base_url'] = tk.StringVar()
            ttk.Entry(ollama_group, textvariable=self.settings_vars['ollama_base_url']).grid(
                row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            ollama_group.columnconfigure(1, weight=1)
            
            # スクロールバーの配置
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.logger.error(f"LLMタブ作成エラー: {e}")
            raise
    
    def _create_ui_tab(self):
        """UI設定タブを作成"""
        try:
            # UIタブフレーム
            ui_frame = ttk.Frame(self.notebook, padding="10")
            self.notebook.add(ui_frame, text="UI設定")
            self.tab_frames['ui'] = ui_frame
            
            # 外観設定
            appearance_group = ttk.LabelFrame(ui_frame, text="外観", padding="10")
            appearance_group.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(appearance_group, text="テーマ:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.settings_vars['theme'] = tk.StringVar()
            theme_combo = ttk.Combobox(appearance_group, textvariable=self.settings_vars['theme'],
                                     values=["default", "clam", "alt", "classic"], state="readonly")
            theme_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            ttk.Label(appearance_group, text="フォントサイズ:").grid(row=1, column=0, sticky=tk.W, pady=2)
            self.settings_vars['font_size'] = tk.IntVar()
            font_scale = ttk.Scale(appearance_group, from_=8, to=20, 
                                 variable=self.settings_vars['font_size'], orient=tk.HORIZONTAL)
            font_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            appearance_group.columnconfigure(1, weight=1)
            
            # チャット設定
            chat_group = ttk.LabelFrame(ui_frame, text="チャット", padding="10")
            chat_group.pack(fill=tk.X, pady=(0, 10))
            
            self.settings_vars['auto_scroll'] = tk.BooleanVar()
            ttk.Checkbutton(chat_group, text="自動スクロール", 
                          variable=self.settings_vars['auto_scroll']).pack(anchor=tk.W, pady=2)
            
            self.settings_vars['show_timestamps'] = tk.BooleanVar()
            ttk.Checkbutton(chat_group, text="タイムスタンプを表示", 
                          variable=self.settings_vars['show_timestamps']).pack(anchor=tk.W, pady=2)
            
            self.settings_vars['word_wrap'] = tk.BooleanVar()
            ttk.Checkbutton(chat_group, text="テキストの折り返し", 
                          variable=self.settings_vars['word_wrap']).pack(anchor=tk.W, pady=2)
            
            ttk.Label(chat_group, text="最大履歴数:").pack(anchor=tk.W, pady=(10, 2))
            self.settings_vars['max_history'] = tk.IntVar()
            ttk.Scale(chat_group, from_=10, to=1000, 
                     variable=self.settings_vars['max_history'], orient=tk.HORIZONTAL).pack(
                fill=tk.X, pady=2)
            
        except Exception as e:
            self.logger.error(f"UIタブ作成エラー: {e}")
            raise
    
    def _create_file_tab(self):
        """ファイル設定タブを作成"""
        try:
            # ファイルタブフレーム
            file_frame = ttk.Frame(self.notebook, padding="10")
            self.notebook.add(file_frame, text="ファイル設定")
            self.tab_frames['file'] = file_frame
            
            # デフォルトディレクトリ設定
            dir_group = ttk.LabelFrame(file_frame, text="デフォルトディレクトリ", padding="10")
            dir_group.pack(fill=tk.X, pady=(0, 10))
            
            # 作業ディレクトリ
            ttk.Label(dir_group, text="作業ディレクトリ:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.settings_vars['work_directory'] = tk.StringVar()
            work_dir_frame = ttk.Frame(dir_group)
            work_dir_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            ttk.Entry(work_dir_frame, textvariable=self.settings_vars['work_directory']).pack(
                side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(work_dir_frame, text="参照", 
                      command=lambda: self._browse_directory('work_directory')).pack(side=tk.RIGHT, padx=(5, 0))
            
            # エクスポートディレクトリ
            ttk.Label(dir_group, text="エクスポートディレクトリ:").grid(row=1, column=0, sticky=tk.W, pady=2)
            self.settings_vars['export_directory'] = tk.StringVar()
            export_dir_frame = ttk.Frame(dir_group)
            export_dir_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            ttk.Entry(export_dir_frame, textvariable=self.settings_vars['export_directory']).pack(
                side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(export_dir_frame, text="参照", 
                      command=lambda: self._browse_directory('export_directory')).pack(side=tk.RIGHT, padx=(5, 0))
            
            dir_group.columnconfigure(1, weight=1)
            
            # ファイル処理設定
            processing_group = ttk.LabelFrame(file_frame, text="ファイル処理", padding="10")
            processing_group.pack(fill=tk.X, pady=(0, 10))
            
            self.settings_vars['auto_save'] = tk.BooleanVar()
            ttk.Checkbutton(processing_group, text="自動保存", 
                          variable=self.settings_vars['auto_save']).pack(anchor=tk.W, pady=2)
            
            self.settings_vars['backup_files'] = tk.BooleanVar()
            ttk.Checkbutton(processing_group, text="バックアップファイルを作成", 
                          variable=self.settings_vars['backup_files']).pack(anchor=tk.W, pady=2)
            
            ttk.Label(processing_group, text="最大ファイルサイズ (MB):").pack(anchor=tk.W, pady=(10, 2))
            self.settings_vars['max_file_size'] = tk.IntVar()
            ttk.Scale(processing_group, from_=1, to=100, 
                     variable=self.settings_vars['max_file_size'], orient=tk.HORIZONTAL).pack(
                fill=tk.X, pady=2)
            
        except Exception as e:
            self.logger.error(f"ファイルタブ作成エラー: {e}")
            raise
    
    def _create_advanced_tab(self):
        """高度な設定タブを作成"""
        try:
            # 高度な設定タブフレーム
            advanced_frame = ttk.Frame(self.notebook, padding="10")
            self.notebook.add(advanced_frame, text="高度な設定")
            self.tab_frames['advanced'] = advanced_frame
            
            # ログ設定
            log_group = ttk.LabelFrame(advanced_frame, text="ログ設定", padding="10")
            log_group.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(log_group, text="ログレベル:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.settings_vars['log_level'] = tk.StringVar()
            log_combo = ttk.Combobox(log_group, textvariable=self.settings_vars['log_level'],
                                   values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly")
            log_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            self.settings_vars['enable_file_logging'] = tk.BooleanVar()
            ttk.Checkbutton(log_group, text="ファイルログを有効化", 
                          variable=self.settings_vars['enable_file_logging']).grid(
                row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
            
            log_group.columnconfigure(1, weight=1)
            
            # パフォーマンス設定
            perf_group = ttk.LabelFrame(advanced_frame, text="パフォーマンス", padding="10")
            perf_group.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(perf_group, text="並行リクエスト数:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.settings_vars['max_concurrent_requests'] = tk.IntVar()
            ttk.Scale(perf_group, from_=1, to=10, 
                     variable=self.settings_vars['max_concurrent_requests'], orient=tk.HORIZONTAL).grid(
                row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            ttk.Label(perf_group, text="タイムアウト (秒):").grid(row=1, column=0, sticky=tk.W, pady=2)
            self.settings_vars['request_timeout'] = tk.IntVar()
            ttk.Scale(perf_group, from_=10, to=300, 
                     variable=self.settings_vars['request_timeout'], orient=tk.HORIZONTAL).grid(
                row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            
            perf_group.columnconfigure(1, weight=1)
            
            # セキュリティ設定
            security_group = ttk.LabelFrame(advanced_frame, text="セキュリティ", padding="10")
            security_group.pack(fill=tk.X, pady=(0, 10))
            
            self.settings_vars['encrypt_api_keys'] = tk.BooleanVar()
            ttk.Checkbutton(security_group, text="APIキーを暗号化", 
                          variable=self.settings_vars['encrypt_api_keys']).pack(anchor=tk.W, pady=2)
            
            self.settings_vars['clear_clipboard'] = tk.BooleanVar()
            ttk.Checkbutton(security_group, text="コピー後にクリップボードをクリア", 
                          variable=self.settings_vars['clear_clipboard']).pack(anchor=tk.W, pady=2)
            
        except Exception as e:
            self.logger.error(f"高度な設定タブ作成エラー: {e}")
            raise
    
    def _on_provider_changed(self, event):
        """プロバイダー変更時の処理"""
        try:
            provider = self.settings_vars['default_provider'].get()
            if provider:
                # 選択されたプロバイダーの利用可能なモデルを取得
                available_models = self.llm_factory.get_available_models(provider)
                self.model_combo['values'] = available_models
                
                # デフォルトモデルを設定
                if available_models:
                    self.settings_vars['default_model'].set(available_models[0])
                
        except Exception as e:
            self.logger.error(f"プロバイダー変更処理エラー: {e}")
    
    def _browse_directory(self, var_name: str):
        """ディレクトリ選択ダイアログを表示"""
        try:
            current_dir = self.settings_vars[var_name].get()
            if not current_dir:
                current_dir = os.getcwd()
            
            directory = filedialog.askdirectory(
                title="ディレクトリを選択",
                initialdir=current_dir
            )
            
            if directory:
                self.settings_vars[var_name].set(directory)
                
        except Exception as e:
            self.logger.error(f"ディレクトリ選択エラー: {e}")
            messagebox.showerror("エラー", f"ディレクトリの選択に失敗しました: {e}")
    
    def _load_current_settings(self):
        """現在の設定値を読み込み"""
        try:
            # 設定値を取得
            settings = self.config.get_all_settings()
            
            # 各設定値を対応する変数に設定
            for key, var in self.settings_vars.items():
                if key in settings:
                    var.set(settings[key])
                else:
                    # デフォルト値を設定
                    self._set_default_value(key, var)
            
            # プロバイダー変更時の処理を実行
            if 'default_provider' in self.settings_vars:
                self._on_provider_changed(None)
            
            self.logger.debug("現在の設定値を読み込みました")
            
        except Exception as e:
            self.logger.error(f"設定値読み込みエラー: {e}")
            messagebox.showerror("エラー", f"設定値の読み込みに失敗しました: {e}")
    
    def _set_default_value(self, key: str, var):
        """デフォルト値を設定"""
        defaults = {
            'default_provider': 'openai',
            'default_model': 'gpt-3.5-turbo',
            'openai_api_key': '',
            'openai_base_url': 'https://api.openai.com/v1',
            'openai_temperature': 0.7,
            'anthropic_api_key': '',
            'anthropic_temperature': 0.7,
            'ollama_base_url': 'http://localhost:11434',
            'theme': 'default',
            'font_size': 12,
            'auto_scroll': True,
            'show_timestamps': True,
            'word_wrap': True,
            'max_history': 100,
            'work_directory': os.getcwd(),
            'export_directory': os.path.join(os.getcwd(), 'exports'),
            'auto_save': True,
            'backup_files': True,
            'max_file_size': 10,
            'log_level': 'INFO',
            'enable_file_logging': True,
            'max_concurrent_requests': 3,
            'request_timeout': 60,
            'encrypt_api_keys': False,
            'clear_clipboard': False
        }
        
        if key in defaults:
            var.set(defaults[key])
    
    def _center_dialog(self):
        """ダイアログを画面中央に配置"""
        try:
            self.dialog.update_idletasks()
            width = self.dialog.winfo_width()
            height = self.dialog.winfo_height()
            x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
            self.dialog.geometry(f"{width}x{height}+{x}+{y}")
            
        except Exception as e:
            self.logger.error(f"ダイアログ中央配置エラー: {e}")
    
    def _on_ok(self):
        """OKボタンクリック時の処理"""
        try:
            if self._apply_settings():
                self.dialog.destroy()
                
        except Exception as e:
            self.logger.error(f"OK処理エラー: {e}")
            messagebox.showerror("エラー", f"設定の適用に失敗しました: {e}")
    
    def _on_cancel(self):
        """キャンセルボタンクリック時の処理"""
        try:
            self.dialog.destroy()
            
        except Exception as e:
            self.logger.error(f"キャンセル処理エラー: {e}")
    
    def _on_apply(self):
        """適用ボタンクリック時の処理"""
        try:
            self._apply_settings()
            
        except Exception as e:
            self.logger.error(f"適用処理エラー: {e}")
            messagebox.showerror("エラー", f"設定の適用に失敗しました: {e}")
    
    def _on_reset_defaults(self):
        """デフォルトに戻すボタンクリック時の処理"""
        try:
            result = messagebox.askyesno(
                "確認", 
                "すべての設定をデフォルト値に戻しますか？\nこの操作は元に戻せません。"
            )
            
            if result:
                # すべての設定変数にデフォルト値を設定
                for key, var in self.settings_vars.items():
                    self._set_default_value(key, var)
                
                # プロバイダー変更時の処理を実行
                if 'default_provider' in self.settings_vars:
                    self._on_provider_changed(None)
                
                messagebox.showinfo("完了", "設定をデフォルト値に戻しました。")
                
        except Exception as e:
            self.logger.error(f"デフォルト復元エラー: {e}")
            messagebox.showerror("エラー", f"デフォルト値の復元に失敗しました: {e}")
    
    def _apply_settings(self) -> bool:
        """設定を適用"""
        try:
            # 設定値を検証
            if not self._validate_settings():
                return False
            
            # 設定値を辞書に変換
            new_settings = {}
            for key, var in self.settings_vars.items():
                new_settings[key] = var.get()
            
            # 設定を保存
            for key, value in new_settings.items():
                self.config.set(key, value)
            
            self.config.save()
            
            # コールバック関数を呼び出し
            if self.on_settings_changed:
                self.on_settings_changed(new_settings)
            
            messagebox.showinfo("完了", "設定を保存しました。")
            self.logger.info("設定を適用しました")
            return True
            
        except Exception as e:
            self.logger.error(f"設定適用エラー: {e}")
            messagebox.showerror("エラー", f"設定の適用に失敗しました: {e}")
            return False
    
    def _validate_settings(self) -> bool:
        """設定値を検証"""
        try:
            # APIキーの検証
            openai_key = self.settings_vars.get('openai_api_key', tk.StringVar()).get()
            anthropic_key = self.settings_vars.get('anthropic_api_key', tk.StringVar()).get()
            
            if not openai_key and not anthropic_key:
                result = messagebox.askyesno(
                    "警告", 
                    "APIキーが設定されていません。\n"
                    "LLMサービスを使用するにはAPIキーが必要です。\n"
                    "このまま続行しますか？"
                )
                if not result:
                    return False
            
            # ディレクトリの検証
            work_dir = self.settings_vars.get('work_directory', tk.StringVar()).get()
            if work_dir and not os.path.exists(work_dir):
                result = messagebox.askyesno(
                    "確認", 
                    f"作業ディレクトリが存在しません: {work_dir}\n"
                    "ディレクトリを作成しますか？"
                )
                if result:
                    try:
                        os.makedirs(work_dir, exist_ok=True)
                    except Exception as e:
                        messagebox.showerror("エラー", f"ディレクトリの作成に失敗しました: {e}")
                        return False
                else:
                    return False
            
            export_dir = self.settings_vars.get('export_directory', tk.StringVar()).get()
            if export_dir and not os.path.exists(export_dir):
                result = messagebox.askyesno(
                    "確認", 
                    f"エクスポートディレクトリが存在しません: {export_dir}\n"
                    "ディレクトリを作成しますか？"
                )
                if result:
                    try:
                        os.makedirs(export_dir, exist_ok=True)
                    except Exception as e:
                        messagebox.showerror("エラー", f"ディレクトリの作成に失敗しました: {e}")
                        return False
                else:
                    return False
            
            # 数値範囲の検証
            font_size = self.settings_vars.get('font_size', tk.IntVar()).get()
            if font_size < 8 or font_size > 20:
                messagebox.showerror("エラー", "フォントサイズは8-20の範囲で設定してください。")
                return False
            
            max_history = self.settings_vars.get('max_history', tk.IntVar()).get()
            if max_history < 10 or max_history > 1000:
                messagebox.showerror("エラー", "最大履歴数は10-1000の範囲で設定してください。")
                return False
            
            max_file_size = self.settings_vars.get('max_file_size', tk.IntVar()).get()
            if max_file_size < 1 or max_file_size > 100:
                messagebox.showerror("エラー", "最大ファイルサイズは1-100MBの範囲で設定してください。")
                return False
            
            timeout = self.settings_vars.get('request_timeout', tk.IntVar()).get()
            if timeout < 10 or timeout > 300:
                messagebox.showerror("エラー", "タイムアウトは10-300秒の範囲で設定してください。")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"設定検証エラー: {e}")
            messagebox.showerror("エラー", f"設定の検証に失敗しました: {e}")
            return False
    
    def get_current_settings(self) -> Dict[str, Any]:
        """現在の設定値を取得"""
        try:
            settings = {}
            for key, var in self.settings_vars.items():
                settings[key] = var.get()
            return settings
            
        except Exception as e:
            self.logger.error(f"設定値取得エラー: {e}")
            return {}
    
    def update_setting(self, key: str, value: Any):
        """特定の設定値を更新"""
        try:
            if key in self.settings_vars:
                self.settings_vars[key].set(value)
                self.logger.debug(f"設定値を更新しました: {key} = {value}")
            else:
                self.logger.warning(f"不明な設定キー: {key}")
                
        except Exception as e:
            self.logger.error(f"設定値更新エラー {key}: {e}")
    
    def export_settings(self):
        """設定をファイルにエクスポート"""
        try:
            file_path = filedialog.asksaveasfilename(
                title="設定をエクスポート",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if file_path:
                settings = self.get_current_settings()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("完了", f"設定をエクスポートしました: {file_path}")
                self.logger.info(f"設定をエクスポートしました: {file_path}")
                
        except Exception as e:
            self.logger.error(f"設定エクスポートエラー: {e}")
            messagebox.showerror("エラー", f"設定のエクスポートに失敗しました: {e}")
    
    def import_settings(self):
        """設定をファイルからインポート"""
        try:
            file_path = filedialog.askopenfilename(
                title="設定をインポート",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import json
                    imported_settings = json.load(f)
                
                # 設定値を適用
                for key, value in imported_settings.items():
                    if key in self.settings_vars:
                        self.settings_vars[key].set(value)
                
                # プロバイダー変更時の処理を実行
                if 'default_provider' in self.settings_vars:
                    self._on_provider_changed(None)
                
                messagebox.showinfo("完了", f"設定をインポートしました: {file_path}")
                self.logger.info(f"設定をインポートしました: {file_path}")
                
        except Exception as e:
            self.logger.error(f"設定インポートエラー: {e}")
            messagebox.showerror("エラー", f"設定のインポートに失敗しました: {e}")
    
    def test_connection(self):
        """LLM接続テスト"""
        try:
            provider = self.settings_vars.get('default_provider', tk.StringVar()).get()
            model = self.settings_vars.get('default_model', tk.StringVar()).get()
            
            if not provider or not model:
                messagebox.showerror("エラー", "プロバイダーとモデルを選択してください。")
                return
            
            # 接続テスト用の設定を作成
            test_config = {}
            if provider == 'openai':
                api_key = self.settings_vars.get('openai_api_key', tk.StringVar()).get()
                base_url = self.settings_vars.get('openai_base_url', tk.StringVar()).get()
                if not api_key:
                    messagebox.showerror("エラー", "OpenAI APIキーを設定してください。")
                    return
                test_config = {
                    'api_key': api_key,
                    'base_url': base_url
                }
            elif provider == 'anthropic':
                api_key = self.settings_vars.get('anthropic_api_key', tk.StringVar()).get()
                if not api_key:
                    messagebox.showerror("エラー", "Anthropic APIキーを設定してください。")
                    return
                test_config = {
                    'api_key': api_key
                }
            elif provider == 'ollama':
                base_url = self.settings_vars.get('ollama_base_url', tk.StringVar()).get()
                test_config = {
                    'base_url': base_url
                }
            
            # 接続テストを実行（非同期処理のため、別スレッドで実行）
            import threading
            
            def test_thread():
                try:
                    # LLMクライアントを作成してテスト
                    client = self.llm_factory.create_client(provider, test_config)
                    
                    # 簡単なテストメッセージを送信
                    response = client.generate_response("Hello", model)
                    
                    # メインスレッドでメッセージボックスを表示
                    self.dialog.after(0, lambda: messagebox.showinfo(
                        "接続テスト成功", 
                        f"LLMサービスへの接続に成功しました。\n"
                        f"プロバイダー: {provider}\n"
                        f"モデル: {model}\n"
                        f"レスポンス: {response[:100]}..."
                    ))
                    
                except Exception as e:
                    # メインスレッドでエラーメッセージを表示
                    self.dialog.after(0, lambda: messagebox.showerror(
                        "接続テスト失敗", 
                        f"LLMサービスへの接続に失敗しました。\n"
                        f"エラー: {str(e)}"
                    ))
            
            # プログレスダイアログを表示
            progress_dialog = tk.Toplevel(self.dialog)
            progress_dialog.title("接続テスト中...")
            progress_dialog.geometry("300x100")
            progress_dialog.transient(self.dialog)
            progress_dialog.grab_set()
            
            ttk.Label(progress_dialog, text="LLMサービスに接続しています...").pack(pady=20)
            progress_bar = ttk.Progressbar(progress_dialog, mode='indeterminate')
            progress_bar.pack(pady=10, padx=20, fill=tk.X)
            progress_bar.start()
            
            # テストスレッドを開始
            thread = threading.Thread(target=test_thread)
            thread.daemon = True
            thread.start()
            
            # プログレスダイアログを一定時間後に閉じる
            def close_progress():
                if progress_dialog.winfo_exists():
                    progress_dialog.destroy()
            
            self.dialog.after(10000, close_progress)  # 10秒後に閉じる
            
        except Exception as e:
            self.logger.error(f"接続テストエラー: {e}")
            messagebox.showerror("エラー", f"接続テストに失敗しました: {e}")

def show_settings_dialog(parent: tk.Tk, on_settings_changed: Optional[Callable] = None):
    """
    設定ダイアログを表示する便利関数
    
    Args:
        parent: 親ウィンドウ
        on_settings_changed: 設定変更時のコールバック関数
    """
    try:
        dialog = SettingsDialog(parent, on_settings_changed)
        dialog.show()
        
    except Exception as e:
        logger.error(f"設定ダイアログ表示エラー: {e}")
        messagebox.showerror("エラー", f"設定ダイアログの表示に失敗しました: {e}")
