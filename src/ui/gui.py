# src/ui/gui.py
"""
メインGUIアプリケーション
LLMチャットインターフェースとコード生成機能を提供
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import asyncio
from datetime import datetime
import traceback
from typing import Dict, List, Optional, Any
import json
import os

# 修正されたimport文
from src.llm.llm_service import LLMServiceCore, TaskType, TaskPriority, LLMTask, LLMResult
from src.llm.base_llm import LLMConfig, LLMRole
from src.llm.prompt_templates import create_code_generation_prompt, create_code_review_prompt
from src.llm.response_parser import parse_llm_response, ResponseType
from src.core.logger import get_logger

logger = get_logger(__name__)

class ChatGUI:
    """チャットGUIクラス"""
    
    def __init__(self, root):
        """
        初期化
        
        Args:
            root: Tkinterルートウィンドウ
        """
        from src.llm.llm_service import get_llm_service
        from src.llm.llm_factory import get_llm_factory
        from src.llm.prompt_templates import get_prompt_template_manager
        from src.llm.response_parser import get_response_parser
        from src.core.config_manager import get_config
        from src.utils.file_utils import FileUtils
        from src.utils.text_utils import TextUtils

        self.root = root
        self.logger = get_logger(self.__class__.__name__)
        
        # サービス初期化
        self.llm_service = get_llm_service()
        self.llm_factory = get_llm_factory()
        self.template_manager = get_prompt_template_manager()
        self.response_parser = get_response_parser()
        
        # ユーティリティ
        self.file_utils = FileUtils()
        self.text_utils = TextUtils()
        
        # 設定
        self.config = get_config()
        
        # 状態管理
        self.current_conversation = []
        self.chat_history = []
        self.current_provider = None
        self.current_model = None
        self.is_processing = False
        
        # GUI初期化
        self.setup_gui()
        self.setup_event_handlers()
        
        # 初期設定
        self.load_providers()
        self.load_settings()
        
        self.logger.info("ChatGUI を初期化しました")
    
    def setup_gui(self):
        """GUI要素をセットアップ"""
        try:
            self.root.title("LLM Chat Assistant")
            self.root.geometry("1200x800")
            
            # メインフレーム
            main_frame = ttk.Frame(self.root)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 上部コントロールパネル
            self.setup_control_panel(main_frame)
            
            # 中央チャットエリア
            self.setup_chat_area(main_frame)
            
            # 下部入力エリア
            self.setup_input_area(main_frame)
            
            # サイドパネル
            self.setup_side_panel(main_frame)
            
            # ステータスバー
            self.setup_status_bar(main_frame)
            
        except Exception as e:
            self.logger.error(f"GUI セットアップエラー: {e}")
            messagebox.showerror("エラー", f"GUI初期化に失敗しました: {e}")
    
    def setup_control_panel(self, parent):
        """コントロールパネルをセットアップ"""
        control_frame = ttk.LabelFrame(parent, text="設定", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # プロバイダー選択
        ttk.Label(control_frame, text="プロバイダー:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.provider_var = tk.StringVar()
        self.provider_combo = ttk.Combobox(control_frame, textvariable=self.provider_var, state="readonly", width=15)
        self.provider_combo.grid(row=0, column=1, padx=(0, 20))
        self.provider_combo.bind('<<ComboboxSelected>>', self.on_provider_changed)
        
        # モデル選択
        ttk.Label(control_frame, text="モデル:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(control_frame, textvariable=self.model_var, state="readonly", width=20)
        self.model_combo.grid(row=0, column=3, padx=(0, 20))
        
        # タスクタイプ選択
        ttk.Label(control_frame, text="タスク:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.task_type_var = tk.StringVar(value=TaskType.GENERAL_CHAT.value)
        self.task_type_combo = ttk.Combobox(control_frame, textvariable=self.task_type_var, state="readonly", width=15)
        self.task_type_combo['values'] = [task_type.value for task_type in TaskType]
        self.task_type_combo.grid(row=0, column=5, padx=(0, 20))
        
        # 設定ボタン
        ttk.Button(control_frame, text="詳細設定", command=self.open_settings_dialog).grid(row=0, column=6)
        
        # 統計ボタン
        ttk.Button(control_frame, text="統計", command=self.show_statistics).grid(row=0, column=7, padx=(10, 0))
    
    def setup_chat_area(self, parent):
        """チャットエリアをセットアップ"""
        # チャット表示エリア
        chat_frame = ttk.LabelFrame(parent, text="チャット", padding=10)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # チャット履歴表示
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=("Consolas", 10),
            bg="#f8f9fa",
            fg="#333333"
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # タグ設定（メッセージタイプ別の色分け）
        self.chat_display.tag_configure("user", foreground="#2563eb", font=("Consolas", 10, "bold"))
        self.chat_display.tag_configure("assistant", foreground="#059669", font=("Consolas", 10))
        self.chat_display.tag_configure("system", foreground="#dc2626", font=("Consolas", 9, "italic"))
        self.chat_display.tag_configure("error", foreground="#dc2626", background="#fef2f2")
        self.chat_display.tag_configure("code", background="#f1f5f9", font=("Consolas", 9))
    
    def setup_input_area(self, parent):
        """入力エリアをセットアップ"""
        input_frame = ttk.LabelFrame(parent, text="入力", padding=10)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 入力テキストエリア
        self.input_text = scrolledtext.ScrolledText(
            input_frame, 
            height=4, 
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # ボタンフレーム
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X)
        
        # 送信ボタン
        self.send_button = ttk.Button(button_frame, text="送信 (Ctrl+Enter)", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # クリアボタン
        ttk.Button(button_frame, text="クリア", command=self.clear_input).pack(side=tk.LEFT, padx=(0, 10))
        
        # ファイル読み込みボタン
        ttk.Button(button_frame, text="ファイル読み込み", command=self.load_file).pack(side=tk.LEFT, padx=(0, 10))
        
        # テンプレートボタン
        ttk.Button(button_frame, text="テンプレート", command=self.show_template_dialog).pack(side=tk.LEFT, padx=(0, 10))
        
        # ストリーミングチェックボックス
        self.streaming_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(button_frame, text="ストリーミング", variable=self.streaming_var).pack(side=tk.RIGHT)
        
        # キーバインド
        self.input_text.bind('<Control-Return>', lambda e: self.send_message())
        self.input_text.bind('<Control-l>', lambda e: self.clear_input())
    
    def setup_side_panel(self, parent):
        """サイドパネルをセットアップ"""
        # 現在は実装をスキップ（将来の拡張用）
        pass
    
    def setup_status_bar(self, parent):
        """ステータスバーをセットアップ"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X)
        
        # ステータスラベル
        self.status_var = tk.StringVar(value="準備完了")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT)
        
        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            status_frame, 
            variable=self.progress_var, 
            mode='indeterminate',
            length=200
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))
    
    def setup_event_handlers(self):
        """イベントハンドラーをセットアップ"""
        try:
            from src.core.event_system import get_event_system
            # イベントシステムからの通知を受信
            event_system = get_event_system()
            event_system.subscribe('llm_task_started', self.on_task_started)
            event_system.subscribe('llm_task_completed', self.on_task_completed)
            event_system.subscribe('llm_task_failed', self.on_task_failed)
            
        except Exception as e:
            self.logger.error(f"イベントハンドラーセットアップエラー: {e}")
    
    def load_providers(self):
        """利用可能なプロバイダーを読み込み"""
        try:
            providers = self.llm_factory.get_available_providers()
            self.provider_combo['values'] = providers
            
            if providers:
                # デフォルトプロバイダーを設定
                default_provider = self.llm_factory.get_default_provider()
                if default_provider and default_provider in providers:
                    self.provider_var.set(default_provider)
                else:
                    self.provider_var.set(providers[0])
                
                self.on_provider_changed()
            
        except Exception as e:
            self.logger.error(f"プロバイダー読み込みエラー: {e}")
            messagebox.showerror("エラー", f"プロバイダーの読み込みに失敗しました: {e}")
    
    def on_provider_changed(self, event=None):
        """プロバイダー変更時の処理"""
        try:
            provider = self.provider_var.get()
            if not provider:
                return
            
            self.current_provider = provider
            
            # 利用可能なモデルを取得
            models = self.llm_service.get_available_models(provider)
            self.model_combo['values'] = models
            
            if models:
                # プロバイダー情報からデフォルトモデルを取得
                provider_info = self.llm_factory.get_provider_info(provider)
                if provider_info and provider_info.default_config:
                    default_model = provider_info.default_config.get('model')
                    if default_model and default_model in models:
                        self.model_var.set(default_model)
                    else:
                        self.model_var.set(models[0])
                else:
                    self.model_var.set(models[0])
                
                self.current_model = self.model_var.get()
            
            self.update_status(f"プロバイダー: {provider}")
            
        except Exception as e:
            self.logger.error(f"プロバイダー変更エラー: {e}")
    
    def load_settings(self):
        """設定を読み込み"""
        try:
            # 設定ファイルから初期値を読み込み
            gui_config = self.config.get('gui', {})
            
            # ウィンドウサイズ
            if 'window_size' in gui_config:
                size = gui_config['window_size']
                self.root.geometry(f"{size['width']}x{size['height']}")
            
            # ストリーミング設定
            self.streaming_var.set(gui_config.get('streaming', False))
            
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {e}")
    
    def send_message(self):
        """メッセージを送信"""
        if self.is_processing:
            messagebox.showwarning("警告", "処理中です。しばらくお待ちください。")
            return
        
        message = self.input_text.get(1.0, tk.END).strip()
        if not message:
            return
        
        try:
            # メッセージを表示
            self.add_message_to_chat("user", message)
            
            # 入力をクリア
            self.clear_input()
            
            # 非同期でメッセージを処理
            threading.Thread(target=self.process_message_async, args=(message,), daemon=True).start()
            
        except Exception as e:
            self.logger.error(f"メッセージ送信エラー: {e}")
            messagebox.showerror("エラー", f"メッセージの送信に失敗しました: {e}")
    
    def process_message_async(self, message: str):
        """メッセージを非同期で処理"""
        try:
            self.is_processing = True
            
            # タスクを作成
            task = self.llm_service.create_task(
                task_type=TaskType(self.task_type_var.get()),
                prompt=message,
                priority=TaskPriority.NORMAL,
                provider=self.current_provider,
                model=self.current_model
            )
            
            # ストリーミング処理
            if self.streaming_var.get():
                self.process_streaming_task(task)
            else:
                self.process_standard_task(task)
            
        except Exception as e:
            self.logger.error(f"メッセージ処理エラー: {e}")
            self.root.after(0, lambda: self.add_message_to_chat("error", f"エラー: {e}"))
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.update_status("準備完了"))
    
    def process_standard_task(self, task: LLMTask):
        """標準タスク処理"""
        try:
            # タスクを実行
            result = self.llm_service.execute_task(task)
            
            if result.success:
                # レスポンスを解析
                parsed_response = self.response_parser.parse_response(
                    result.content, 
                    expected_type=self.get_expected_response_type(task.task_type)
                )
                
                # フォーマットして表示
                formatted_response = self.response_parser.format_parsed_response(
                    parsed_response, 
                    format_type="text"
                )
                
                self.root.after(0, lambda: self.add_message_to_chat("assistant", formatted_response))
                
                # 会話履歴に追加
                self.current_conversation.extend([
                    {"role": "user", "content": task.prompt},
                    {"role": "assistant", "content": result.content}
                ])
                
            else:
                self.root.after(0, lambda: self.add_message_to_chat("error", f"エラー: {result.error}"))
            
        except Exception as e:
            self.logger.error(f"標準タスク処理エラー: {e}")
            self.root.after(0, lambda: self.add_message_to_chat("error", f"処理エラー: {e}"))
    
    def process_streaming_task(self, task: LLMTask):
        """ストリーミングタスク処理"""
        try:
            # ストリーミング処理は将来の実装
            # 現在は標準処理で代替
            self.process_standard_task(task)
            
        except Exception as e:
            self.logger.error(f"ストリーミングタスク処理エラー: {e}")
            self.root.after(0, lambda: self.add_message_to_chat("error", f"ストリーミングエラー: {e}"))
    
    def get_expected_response_type(self, task_type: TaskType) -> Optional[ResponseType]:
        """タスクタイプから期待するレスポンスタイプを取得"""
        mapping = {
            TaskType.CODE_GENERATION: ResponseType.CODE,
            TaskType.CODE_REVIEW: ResponseType.REVIEW,
            TaskType.DEBUG_ASSISTANCE: ResponseType.DEBUG,
            TaskType.DOCUMENTATION: ResponseType.DOCUMENTATION,
            TaskType.CODE_EXPLANATION: ResponseType.EXPLANATION,
        }
        return mapping.get(task_type)
    
    def add_message_to_chat(self, role: str, content: str):
        """チャットにメッセージを追加"""
        try:
            self.chat_display.config(state=tk.NORMAL)
            
            # タイムスタンプ
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # ロール表示
            role_display = {
                "user": "あなた",
                "assistant": "AI",
                "system": "システム",
                "error": "エラー"
            }.get(role, role)
            
            # メッセージを追加
            self.chat_display.insert(tk.END, f"[{timestamp}] {role_display}:\n", role)
            self.chat_display.insert(tk.END, f"{content}\n\n")
            
            # 自動スクロール
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
        except Exception as e:
            self.logger.error(f"チャットメッセージ追加エラー: {e}")
    
    def clear_input(self):
        """入力をクリア"""
        self.input_text.delete(1.0, tk.END)
    
    def clear_chat(self):
        """チャットをクリア"""
        try:
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            self.current_conversation.clear()
            
        except Exception as e:
            self.logger.error(f"チャットクリアエラー: {e}")
    
    def load_file(self):
        """ファイルを読み込み"""
        try:
            file_path = filedialog.askopenfilename(
                title="ファイルを選択",
                filetypes=[
                    ("テキストファイル", "*.txt"),
                    ("Pythonファイル", "*.py"),
                    ("JavaScriptファイル", "*.js"),
                    ("すべてのファイル", "*.*")
                ]
            )
            
            if file_path:
                content = self.file_utils.read_file(file_path)
                
                # 現在の入力に追加
                current_text = self.input_text.get(1.0, tk.END).strip()
                if current_text:
                    self.input_text.insert(tk.END, f"\n\n--- {os.path.basename(file_path)} ---\n")
                else:
                    self.input_text.insert(1.0, f"--- {os.path.basename(file_path)} ---\n")
                
                self.input_text.insert(tk.END, content)
                
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー: {e}")
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました: {e}")
    
    def show_template_dialog(self):
        """テンプレートダイアログを表示"""
        try:
            # 簡易テンプレート選択ダイアログ
            templates = self.template_manager.get_all_templates()
            
            if not templates:
                messagebox.showinfo("情報", "利用可能なテンプレートがありません")
                return
            
            # テンプレート選択ウィンドウ
            template_window = tk.Toplevel(self.root)
            template_window.title("テンプレート選択")
            template_window.geometry("600x400")
            
            # テンプレートリスト
            listbox = tk.Listbox(template_window)
            listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            for template_id, template in templates.items():
                listbox.insert(tk.END, f"{template.name} ({template_id})")
            
            # 選択ボタン
            def select_template():
                selection = listbox.curselection()
                if selection:
                    template_id = list(templates.keys())[selection[0]]
                    template = templates[template_id]
                    
                    # 変数入力ダイアログを表示（簡易版）
                    if template.variables:
                        self.show_variable_input_dialog(template)
                    else:
                        self.input_text.insert(tk.END, template.template)
                    
                    template_window.destroy()
            
            ttk.Button(template_window, text="選択", command=select_template).pack(pady=10)
            
        except Exception as e:
            self.logger.error(f"テンプレートダイアログエラー: {e}")
            messagebox.showerror("エラー", f"テンプレートダイアログの表示に失敗しました: {e}")
    
    def show_variable_input_dialog(self, template):
        """変数入力ダイアログを表示"""
        try:
            var_window = tk.Toplevel(self.root)
            var_window.title(f"変数入力 - {template.name}")
            var_window.geometry("500x400")
            
            variables = {}
            entries = {}
            
            # 変数入力フィールド
            for i, var in enumerate(template.variables):
                ttk.Label(var_window, text=f"{var.name}:").grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
                ttk.Label(var_window, text=var.description, font=("Arial", 8)).grid(row=i, column=1, sticky=tk.W, padx=10)
                
                entry = tk.Text(var_window, height=2, width=40)
                entry.grid(row=i, column=2, padx=10, pady=5)
                
                if var.default_value:
                    entry.insert(1.0, var.default_value)
                
                entries[var.name] = entry
            
            # 適用ボタン
            def apply_template():
                try:
                    for var_name, entry in entries.items():
                        variables[var_name] = entry.get(1.0, tk.END).strip()
                    
                    rendered = self.template_manager.render_template(template.id, variables)
                    self.input_text.insert(tk.END, rendered)
                    var_window.destroy()
                    
                except Exception as e:
                    messagebox.showerror("エラー", f"テンプレート適用エラー: {e}")
            
            ttk.Button(var_window, text="適用", command=apply_template).grid(row=len(template.variables), column=2, pady=20)
            
        except Exception as e:
            self.logger.error(f"変数入力ダイアログエラー: {e}")
    
    def open_settings_dialog(self):
        """設定ダイアログを開く"""
        try:
            settings_window = tk.Toplevel(self.root)
            settings_window.title("詳細設定")
            settings_window.geometry("500x600")
            
            # 設定項目（簡易版）
            notebook = ttk.Notebook(settings_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # LLM設定タブ
            llm_frame = ttk.Frame(notebook)
            notebook.add(llm_frame, text="LLM設定")
            
            # Temperature設定
            ttk.Label(llm_frame, text="Temperature:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
            temp_var = tk.DoubleVar(value=0.7)
            temp_scale = ttk.Scale(llm_frame, from_=0.0, to=2.0, variable=temp_var, orient=tk.HORIZONTAL)
            temp_scale.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=5)
            ttk.Label(llm_frame, textvariable=temp_var).grid(row=0, column=2, padx=10)
            
            # Max Tokens設定
            ttk.Label(llm_frame, text="Max Tokens:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
            tokens_var = tk.IntVar(value=2048)
            tokens_entry = ttk.Entry(llm_frame, textvariable=tokens_var)
            tokens_entry.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=5)
            
            # 保存ボタン
            def save_settings():
                # 設定保存処理（簡易版）
                messagebox.showinfo("情報", "設定を保存しました")
                settings_window.destroy()
            
            ttk.Button(settings_window, text="保存", command=save_settings).pack(pady=10)
            
        except Exception as e:
            self.logger.error(f"設定ダイアログエラー: {e}")
            messagebox.showerror("エラー", f"設定ダイアログの表示に失敗しました: {e}")
    
    def show_statistics(self):
        """統計情報を表示"""
        try:
            stats_window = tk.Toplevel(self.root)
            stats_window.title("統計情報")
            stats_window.geometry("600x500")
            
            # 統計情報を取得
            service_stats = self.llm_service.get_service_stats()
            factory_stats = self.llm_factory.get_factory_stats()
            
            # 統計表示
            stats_text = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD, state=tk.DISABLED)
            stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            stats_text.config(state=tk.NORMAL)
            stats_text.insert(tk.END, "=== LLM サービス統計 ===\n\n")
            
            for key, value in service_stats.items():
                stats_text.insert(tk.END, f"{key}: {value}\n")
            
            stats_text.insert(tk.END, "\n=== LLM ファクトリー統計 ===\n\n")
            
            for key, value in factory_stats.items():
                stats_text.insert(tk.END, f"{key}: {value}\n")
            
            stats_text.config(state=tk.DISABLED)
            
        except Exception as e:
            self.logger.error(f"統計表示エラー: {e}")
            messagebox.showerror("エラー", f"統計情報の表示に失敗しました: {e}")
    
    def update_status(self, message: str):
        """ステータスを更新"""
        try:
            self.status_var.set(message)
            self.root.update_idletasks()
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"ステータス更新エラー: {e}")
    
    def start_progress(self):
        """プログレスバーを開始"""
        try:
            self.progress_bar.start(10)
        except Exception as e:
            self.logger.error(f"プログレスバー開始エラー: {e}")
    
    def stop_progress(self):
        """プログレスバーを停止"""
        try:
            self.progress_bar.stop()
        except Exception as e:
            self.logger.error(f"プログレスバー停止エラー: {e}")
    
    # イベントハンドラー
    def on_task_started(self, event):
        """タスク開始イベント"""
        try:
            self.root.after(0, lambda: self.update_status("処理中..."))
            self.root.after(0, self.start_progress)
        except Exception as e:
            self.logger.error(f"タスク開始イベントエラー: {e}")
    
    def on_task_completed(self, event):
        """タスク完了イベント"""
        try:
            self.root.after(0, lambda: self.update_status("完了"))
            self.root.after(0, self.stop_progress)
        except Exception as e:
            self.logger.error(f"タスク完了イベントエラー: {e}")
    
    def on_task_failed(self, event):
        """タスク失敗イベント"""
        try:
            error_msg = event.data.get('error', '不明なエラー')
            self.root.after(0, lambda: self.update_status(f"エラー: {error_msg}"))
            self.root.after(0, self.stop_progress)
        except Exception as e:
            self.logger.error(f"タスク失敗イベントエラー: {e}")
    
    def save_conversation(self):
        """会話を保存"""
        try:
            if not self.current_conversation:
                messagebox.showinfo("情報", "保存する会話がありません")
                return
            
            file_path = filedialog.asksaveasfilename(
                title="会話を保存",
                defaultextension=".json",
                filetypes=[
                    ("JSONファイル", "*.json"),
                    ("テキストファイル", "*.txt"),
                    ("すべてのファイル", "*.*")
                ]
            )
            
            if file_path:
                if file_path.endswith('.json'):
                    # JSON形式で保存
                    conversation_data = {
                        'timestamp': datetime.now().isoformat(),
                        'provider': self.current_provider,
                        'model': self.current_model,
                        'conversation': self.current_conversation
                    }
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(conversation_data, f, ensure_ascii=False, indent=2)
                else:
                    # テキスト形式で保存
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(f"会話ログ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"プロバイダー: {self.current_provider}\n")
                        f.write(f"モデル: {self.current_model}\n")
                        f.write("=" * 50 + "\n\n")
                        
                        for msg in self.current_conversation:
                            role = "あなた" if msg['role'] == 'user' else "AI"
                            f.write(f"{role}:\n{msg['content']}\n\n")
                
                messagebox.showinfo("成功", "会話を保存しました")
                
        except Exception as e:
            self.logger.error(f"会話保存エラー: {e}")
            messagebox.showerror("エラー", f"会話の保存に失敗しました: {e}")
    
    def load_conversation(self):
        """会話を読み込み"""
        try:
            file_path = filedialog.askopenfilename(
                title="会話を読み込み",
                filetypes=[
                    ("JSONファイル", "*.json"),
                    ("すべてのファイル", "*.*")
                ]
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    conversation_data = json.load(f)
                
                # 会話を復元
                self.current_conversation = conversation_data.get('conversation', [])
                
                # チャット表示をクリアして再表示
                self.clear_chat()
                
                for msg in self.current_conversation:
                    role = "user" if msg['role'] == 'user' else "assistant"
                    self.add_message_to_chat(role, msg['content'])
                
                # プロバイダーとモデルを復元
                if 'provider' in conversation_data:
                    self.provider_var.set(conversation_data['provider'])
                    self.on_provider_changed()
                
                if 'model' in conversation_data:
                    self.model_var.set(conversation_data['model'])
                
                messagebox.showinfo("成功", "会話を読み込みました")
                
        except Exception as e:
            self.logger.error(f"会話読み込みエラー: {e}")
            messagebox.showerror("エラー", f"会話の読み込みに失敗しました: {e}")
    
    def export_code(self):
        """コードをエクスポート"""
        try:
            # チャットからコードブロックを抽出
            chat_content = self.chat_display.get(1.0, tk.END)
            
            # レスポンスパーサーを使用してコードを抽出
            code_blocks = self.response_parser.extract_code_from_response(chat_content)
            
            if not code_blocks:
                messagebox.showinfo("情報", "エクスポートするコードが見つかりません")
                return
            
            # コードを統合
            combined_code = "\n\n".join(f"# コードブロック {i+1}\n{code}" for i, code in enumerate(code_blocks))
            
            file_path = filedialog.asksaveasfilename(
                title="コードをエクスポート",
                defaultextension=".py",
                filetypes=[
                    ("Pythonファイル", "*.py"),
                    ("JavaScriptファイル", "*.js"),
                    ("テキストファイル", "*.txt"),
                    ("すべてのファイル", "*.*")
                ]
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(combined_code)
                
                messagebox.showinfo("成功", "コードをエクスポートしました")
                
        except Exception as e:
            self.logger.error(f"コードエクスポートエラー: {e}")
            messagebox.showerror("エラー", f"コードのエクスポートに失敗しました: {e}")
    
    def setup_menu(self):
        """メニューバーをセットアップ"""
        try:
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # ファイルメニュー
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="ファイル", menu=file_menu)
            file_menu.add_command(label="会話を保存", command=self.save_conversation)
            file_menu.add_command(label="会話を読み込み", command=self.load_conversation)
            file_menu.add_separator()
            file_menu.add_command(label="コードをエクスポート", command=self.export_code)
            file_menu.add_separator()
            file_menu.add_command(label="終了", command=self.root.quit)
            
            # 編集メニュー
            edit_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="編集", menu=edit_menu)
            edit_menu.add_command(label="チャットをクリア", command=self.clear_chat)
            edit_menu.add_command(label="入力をクリア", command=self.clear_input)
            
            # 表示メニュー
            view_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="表示", menu=view_menu)
            view_menu.add_command(label="統計情報", command=self.show_statistics)
            view_menu.add_command(label="設定", command=self.open_settings_dialog)
            
            # ヘルプメニュー
            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="ヘルプ", menu=help_menu)
            help_menu.add_command(label="使い方", command=self.show_help)
            help_menu.add_command(label="バージョン情報", command=self.show_about)
            
        except Exception as e:
            self.logger.error(f"メニューセットアップエラー: {e}")
    
    def show_help(self):
        """ヘルプを表示"""
        help_text = """
LLM Chat Assistant - 使い方

1. プロバイダーとモデルを選択してください
2. タスクタイプを選択してください
3. 下部の入力エリアにメッセージを入力してください
4. 「送信」ボタンまたはCtrl+Enterで送信してください

機能:
- ファイル読み込み: テキストファイルを読み込んで入力に追加
- テンプレート: 定型的なプロンプトテンプレートを使用
- ストリーミング: リアルタイムでレスポンスを受信
- 会話保存/読み込み: 会話履歴の保存と復元
- コードエクスポート: 生成されたコードの抽出と保存

ショートカットキー:
- Ctrl+Enter: メッセージ送信
- Ctrl+L: 入力クリア
        """
        
        messagebox.showinfo("使い方", help_text)
    
    def show_about(self):
        """バージョン情報を表示"""
        about_text = """
LLM Chat Assistant
Version 1.0.0

多機能LLMチャットアプリケーション

対応プロバイダー:
- OpenAI GPT
- Anthropic Claude
- ローカルLLM (Ollama)

開発: Python 3.11.9
GUI: Tkinter
        """
        
        messagebox.showinfo("バージョン情報", about_text)
    
    def on_closing(self):
        """アプリケーション終了時の処理"""
        try:
            # 設定を保存
            self.save_window_settings()
            
            # サービスをクリーンアップ
            self.llm_service.cleanup()
            
            # ウィンドウを閉じる
            self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"終了処理エラー: {e}")
            self.root.destroy()
    
    def save_window_settings(self):
        """ウィンドウ設定を保存"""
        try:
            # ウィンドウサイズを保存
            geometry = self.root.geometry()
            width, height = geometry.split('+')[0].split('x')
            
            settings = {
                'window_size': {
                    'width': int(width),
                    'height': int(height)
                },
                'streaming': self.streaming_var.get(),
                'last_provider': self.current_provider,
                'last_model': self.current_model
            }
            
            # 設定ファイルに保存（簡易版）
            config_path = "config/gui_settings.json"
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")

def create_gui(root):
    """
    GUIを作成
    
    Args:
        root: Tkinterルートウィンドウ
        
    Returns:
        ChatGUI: GUIインスタンス
    """
    try:
        gui = ChatGUI(root)
        
        # メニューバーをセットアップ
        gui.setup_menu()
        
        # 終了時の処理を設定
        root.protocol("WM_DELETE_WINDOW", gui.on_closing)
        
        return gui
        
    except Exception as e:
        logger.error(f"GUI作成エラー: {e}")
        messagebox.showerror("エラー", f"GUIの作成に失敗しました: {e}")
        raise

if __name__ == "__main__":
    # テスト用のメイン関数
    root = tk.Tk()
    gui = create_gui(root)
    root.mainloop()

