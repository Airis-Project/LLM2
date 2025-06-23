# src/ui/chat_interface.py
"""
チャットインターフェース - ユーザーとAIの会話UI
"""

import logging
from os import name
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Callable, Optional, List, Dict, Any
from datetime import datetime
import re
import threading
import time
from pathlib import Path

class MessageBubble:
    """メッセージバブルクラス"""
    
    def __init__(self, parent_text: tk.Text, message: str, is_user: bool, timestamp: datetime = None):
        self.parent_text = parent_text
        self.message = message
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now()
        self.start_index = None
        self.end_index = None
        
        # スタイル設定
        self.user_bg = "#007AFF"
        self.user_fg = "white"
        self.assistant_bg = "#E5E5EA"
        self.assistant_fg = "black"
        self.code_bg = "#F6F8FA"
        self.code_fg = "#24292E"
        
    def insert(self):
        """メッセージをテキストウィジェットに挿入"""
        # 現在の位置を記録
        self.start_index = self.parent_text.index(tk.INSERT)
        
        # タイムスタンプ
        timestamp_str = self.timestamp.strftime("%H:%M")
        
        # メッセージヘッダー
        header = f"{'You' if self.is_user else 'AI'} ({timestamp_str})\n"
        self.parent_text.insert(tk.INSERT, header, "header")
        
        # メッセージ本文
        self._insert_formatted_message()
        
        # 改行
        self.parent_text.insert(tk.INSERT, "\n\n")
        
        # 終了位置を記録
        self.end_index = self.parent_text.index(tk.INSERT)
        
        # スタイルを適用
        self._apply_styles()
        
        # 最下部にスクロール
        self.parent_text.see(tk.END)
    
    def _insert_formatted_message(self):
        """フォーマットされたメッセージを挿入"""
        # コードブロックを検出して分割
        parts = self._split_message_with_code()
        
        for part in parts:
            if part['type'] == 'code':
                self._insert_code_block(part['content'], part.get('language', ''))
            else:
                self._insert_text_with_formatting(part['content'])
    
    def _split_message_with_code(self) -> List[Dict[str, str]]:
        """メッセージをコードブロックとテキストに分割"""
        parts = []
        current_pos = 0
        
        # コードブロックのパターン
        code_pattern = r'```(\w+)?\n(.*?)\n```'
        
        for match in re.finditer(code_pattern, self.message, re.DOTALL):
            # コードブロック前のテキスト
            if match.start() > current_pos:
                text_content = self.message[current_pos:match.start()]
                if text_content.strip():
                    parts.append({
                        'type': 'text',
                        'content': text_content
                    })
            
            # コードブロック
            language = match.group(1) or ''
            code_content = match.group(2)
            parts.append({
                'type': 'code',
                'content': code_content,
                'language': language
            })
            
            current_pos = match.end()
        
        # 残りのテキスト
        if current_pos < len(self.message):
            remaining_text = self.message[current_pos:]
            if remaining_text.strip():
                parts.append({
                    'type': 'text',
                    'content': remaining_text
                })
        
        # パターンが見つからない場合は全体をテキストとして扱う
        if not parts:
            parts.append({
                'type': 'text',
                'content': self.message
            })
        
        return parts
    
    def _insert_code_block(self, code: str, language: str):
        """コードブロックを挿入"""
        # 言語ラベル
        if language:
            self.parent_text.insert(tk.INSERT, f"[{language}]\n", "code_language")
        
        # コード内容
        self.parent_text.insert(tk.INSERT, code, "code_block")
        self.parent_text.insert(tk.INSERT, "\n")
    
    def _insert_text_with_formatting(self, text: str):
        """フォーマット付きテキストを挿入"""
        # インラインコードの処理
        parts = re.split(r'(`[^`]+`)', text)
        
        for part in parts:
            if part.startswith('`') and part.endswith('`'):
                # インラインコード
                code_text = part[1:-1]
                self.parent_text.insert(tk.INSERT, code_text, "inline_code")
            else:
                # 通常のテキスト
                self.parent_text.insert(tk.INSERT, part, "message_text")
    
    def _apply_styles(self):
        """スタイルを適用"""
        # メッセージ全体のスタイル
        message_tag = f"message_{self.is_user}_{id(self)}"
        self.parent_text.tag_add(message_tag, self.start_index, self.end_index)
        
        if self.is_user:
            self.parent_text.tag_config(message_tag, 
                                      background=self.user_bg,
                                      foreground=self.user_fg,
                                      relief="raised",
                                      borderwidth=1,
                                      lmargin1=50,
                                      lmargin2=50,
                                      rmargin=10)
        else:
            self.parent_text.tag_config(message_tag,
                                      background=self.assistant_bg,
                                      foreground=self.assistant_fg,
                                      relief="raised",
                                      borderwidth=1,
                                      lmargin1=10,
                                      lmargin2=10,
                                      rmargin=50)


class ChatInterface(ttk.Frame):
    """
    チャットインターフェースクラス
    ユーザーとAIの会話を管理
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # コールバック関数
        self.on_message_send: Optional[Callable[[str], None]] = None
        self.on_code_select: Optional[Callable[[str], None]] = None
        
        # 状態管理
        self.messages = []
        self.is_streaming = False
        self.current_stream_message = None
        self.input_enabled = True
        
        # UI作成
        self._create_widgets()
        self._setup_styles()
        self._setup_bindings()
        
        self.logger.info("チャットインターフェース初期化完了")
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # チャット表示エリア
        self._create_chat_display()
        
        # 入力エリア
        self._create_input_area()
        
        # ツールバー
        self._create_toolbar()
    
    def _create_chat_display(self):
        """チャット表示エリアを作成"""
        # チャット表示フレーム
        chat_frame = ttk.Frame(self.main_frame)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # スクロール可能なテキストエリア
        self.chat_text = tk.Text(
            chat_frame,
            wrap=tk.WORD,
            font=('Arial', 10),
            bg='white',
            fg='black',
            padx=10,
            pady=10,
            state=tk.DISABLED,
            cursor='arrow'
        )
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=scrollbar.set)
        
        # 配置
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # コンテキストメニュー
        self._create_context_menu()
    
    def _create_input_area(self):
        """入力エリアを作成"""
        # 入力フレーム
        input_frame = ttk.Frame(self.main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 入力テキストエリア
        self.input_text = tk.Text(
            input_frame,
            height=3,
            wrap=tk.WORD,
            font=('Arial', 10),
            bg='white',
            fg='black',
            padx=5,
            pady=5
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 送信ボタン
        self.send_button = ttk.Button(
            input_frame,
            text="送信",
            command=self._send_message,
            width=8
        )
        self.send_button.pack(side=tk.RIGHT, fill=tk.Y)
        
        # プレースホルダー
        self._setup_placeholder()
    
    def _create_toolbar(self):
        """ツールバーを作成"""
        toolbar_frame = ttk.Frame(self.main_frame)
        toolbar_frame.pack(fill=tk.X)
        
        # クリアボタン
        self.clear_button = ttk.Button(
            toolbar_frame,
            text="クリア",
            command=self.clear,
            width=8
        )
        self.clear_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # エクスポートボタン
        self.export_button = ttk.Button(
            toolbar_frame,
            text="エクスポート",
            command=self._export_chat,
            width=10
        )
        self.export_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 設定ボタン
        self.settings_button = ttk.Button(
            toolbar_frame,
            text="設定",
            command=self._show_chat_settings,
            width=8
        )
        self.settings_button.pack(side=tk.RIGHT)
        
        # ストリーミング停止ボタン（初期は非表示）
        self.stop_button = ttk.Button(
            toolbar_frame,
            text="停止",
            command=self._stop_streaming,
            width=8
        )
    
    def _create_context_menu(self):
        """コンテキストメニューを作成"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="コピー", command=self._copy_selection)
        self.context_menu.add_command(label="全て選択", command=self._select_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="コードを抽出", command=self._extract_code)
        self.context_menu.add_command(label="ファイルに保存", command=self._save_selection)
    
    def _setup_styles(self):
        """スタイルを設定"""
        # テキストタグの設定
        self.chat_text.tag_configure("header", 
                                   font=('Arial', 9, 'bold'),
                                   foreground='#666666')
        
        self.chat_text.tag_configure("message_text",
                                   font=('Arial', 10),
                                   foreground='black')
        
        self.chat_text.tag_configure("code_block",
                                   font=('Courier', 9),
                                   background='#F6F8FA',
                                   foreground='#24292E',
                                   relief='sunken',
                                   borderwidth=1,
                                   lmargin1=20,
                                   lmargin2=20,
                                   rmargin=20)
        
        self.chat_text.tag_configure("code_language",
                                   font=('Arial', 8, 'bold'),
                                   foreground='#586069',
                                   background='#F1F3F4')
        
        self.chat_text.tag_configure("inline_code",
                                   font=('Courier', 9),
                                   background='#F3F4F6',
                                   foreground='#E83E8C')
        
        self.chat_text.tag_configure("error",
                                   foreground='red',
                                   font=('Arial', 10, 'bold'))
        
        self.chat_text.tag_configure("system",
                                   foreground='#666666',
                                   font=('Arial', 9, 'italic'))
    
    def _setup_placeholder(self):
        """プレースホルダーを設定"""
        self.placeholder_text = "メッセージを入力してください..."
        self._show_placeholder()
        
        # フォーカスイベント
        self.input_text.bind('<FocusIn>', self._on_input_focus_in)
        self.input_text.bind('<FocusOut>', self._on_input_focus_out)
    
    def _show_placeholder(self):
        """プレースホルダーを表示"""
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(1.0, self.placeholder_text)
        self.input_text.config(fg='gray')
    
    def _hide_placeholder(self):
        """プレースホルダーを非表示"""
        if self.input_text.get(1.0, tk.END).strip() == self.placeholder_text:
            self.input_text.delete(1.0, tk.END)
            self.input_text.config(fg='black')
    
    def _on_input_focus_in(self, event):
        """入力フィールドフォーカス時"""
        self._hide_placeholder()
    
    def _on_input_focus_out(self, event):
        """入力フィールドフォーカス外し時"""
        if not self.input_text.get(1.0, tk.END).strip():
            self._show_placeholder()
    
    def _setup_bindings(self):
        """キーバインドを設定"""
        # 送信（Ctrl+Enter）
        self.input_text.bind('<Control-Return>', lambda e: self._send_message())
        
        # 改行（Shift+Enter）
        self.input_text.bind('<Shift-Return>', lambda e: self.input_text.insert(tk.INSERT, '\n'))
        
        # コンテキストメニュー
        self.chat_text.bind('<Button-3>', self._show_context_menu)
        
        # コードブロックのダブルクリック
        self.chat_text.bind('<Double-Button-1>', self._on_double_click)
        
        # テキスト選択
        self.chat_text.bind('<ButtonRelease-1>', self._on_text_select)
    
    def _show_context_menu(self, event):
        """コンテキストメニューを表示"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def _on_double_click(self, event):
        """ダブルクリック時の処理"""
        # クリック位置のタグを取得
        index = self.chat_text.index(f"@{event.x},{event.y}")
        tags = self.chat_text.tag_names(index)
        
        if "code_block" in tags:
            # コードブロックの範囲を取得
            code_text = self._get_code_block_at_index(index)
            if code_text and self.on_code_select:
                self.on_code_select(code_text)
    
    def _on_text_select(self, event):
        """テキスト選択時の処理"""
        try:
            selected_text = self.chat_text.selection_get()
            if selected_text and len(selected_text) > 10:
                # 長いテキストが選択された場合の処理
                pass
        except tk.TclError:
            # 選択されていない場合
            pass
    
    def _get_code_block_at_index(self, index: str) -> str:
        """指定位置のコードブロックを取得"""
        try:
            # code_blockタグの範囲を取得
            ranges = self.chat_text.tag_ranges("code_block")
            
            for i in range(0, len(ranges), 2):
                start, end = ranges[i], ranges[i + 1]
                if self.chat_text.compare(start, "<=", index) and self.chat_text.compare(index, "<", end):
                    return self.chat_text.get(start, end)
            
            return ""
        except Exception as e:
            self.logger.error(f"コードブロック取得エラー: {e}")
            return ""
    
    # ===== 公開メソッド =====
    
    def add_user_message(self, message: str):
        """ユーザーメッセージを追加"""
        self._add_message(message, is_user=True)
    
    def add_assistant_message(self, message: str):
        """アシスタントメッセージを追加"""
        self._add_message(message, is_user=False)
    
    def add_system_message(self, message: str):
        """システムメッセージを追加"""
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"[System] {message}\n", "system")
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)
    
    def add_error_message(self, message: str):
        """エラーメッセージを追加"""
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"[Error] {message}\n", "error")
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)
    
    def _add_message(self, message: str, is_user: bool):
        """メッセージを追加"""
        self.chat_text.config(state=tk.NORMAL)
        
        # メッセージバブルを作成して挿入
        bubble = MessageBubble(self.chat_text, message, is_user)
        bubble.insert()
        
        # メッセージを記録
        self.messages.append({
            'message': message,
            'is_user': is_user,
            'timestamp': datetime.now(),
            'bubble': bubble
        })
        
        self.chat_text.config(state=tk.DISABLED)
    
    def start_streaming_message(self):
        """ストリーミングメッセージを開始"""
        self.is_streaming = True
        self.stop_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 空のアシスタントメッセージを作成
        self.chat_text.config(state=tk.NORMAL)
        self.current_stream_message = {
            'start_index': self.chat_text.index(tk.INSERT),
            'content': ""
        }
        
        # ヘッダーを追加
        timestamp_str = datetime.now().strftime("%H:%M")
        header = f"AI ({timestamp_str})\n"
        self.chat_text.insert(tk.INSERT, header, "header")
        
        self.chat_text.config(state=tk.DISABLED)
    
    def append_to_stream(self, chunk: str):
        """ストリーミングメッセージにチャンクを追加"""
        if not self.is_streaming or not self.current_stream_message:
            return
        
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, chunk, "message_text")
        self.current_stream_message['content'] += chunk
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)
    
    def finish_streaming_message(self):
        """ストリーミングメッセージを完了"""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        self.stop_button.pack_forget()
        
        if self.current_stream_message:
            # 完了したメッセージを記録
            self.messages.append({
                'message': self.current_stream_message['content'],
                'is_user': False,
                'timestamp': datetime.now(),
                'bubble': None
            })
            
            self.current_stream_message = None
        
        # 最終的なフォーマットを適用
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, "\n\n")
        self.chat_text.config(state=tk.DISABLED)
    
    def append_to_last_message(self, text: str):
        """最後のメッセージにテキストを追加（ストリーミング用）"""
        if self.is_streaming:
            self.append_to_stream(text)
    
    def clear(self):
        """チャット履歴をクリア"""
        if messagebox.askyesno("確認", "チャット履歴をクリアしますか？"):
            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.delete(1.0, tk.END)
            self.chat_text.config(state=tk.DISABLED)
            self.messages.clear()
            self.add_system_message("チャット履歴をクリアしました")
    
    def set_input_enabled(self, enabled: bool):
        """入力の有効/無効を設定"""
        self.input_enabled = enabled
        state = tk.NORMAL if enabled else tk.DISABLED
        self.input_text.config(state=state)
        self.send_button.config(state=state)
        
        if not enabled:
            self.input_text.config(bg='#F0F0F0')
        else:
            self.input_text.config(bg='white')
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """メッセージ履歴を取得"""
        return self.messages.copy()
    
    def load_messages(self, messages: List[Dict[str, Any]]):
        """メッセージ履歴を読み込み"""
        self.clear()
        for msg in messages:
            if msg.get('is_user', False):
                self.add_user_message(msg['message'])
            else:
                self.add_assistant_message(msg['message'])
    
    # ===== プライベートメソッド =====
    
    def _send_message(self):
        """メッセージを送信"""
        if not self.input_enabled:
            return
        
        # 入力内容を取得
        message = self.input_text.get(1.0, tk.END).strip()
        
        # プレースホルダーチェック
        if message == self.placeholder_text or not message:
            return
        
        # 入力をクリア
        self.input_text.delete(1.0, tk.END)
        self._show_placeholder()
        
        # コールバック実行
        if self.on_message_send:
            self.on_message_send(message)
    
    def _stop_streaming(self):
        """ストリーミングを停止"""
        if self.is_streaming:
            self.finish_streaming_message()
            self.add_system_message("ストリーミングを停止しました")
    
    def _copy_selection(self):
        """選択範囲をコピー"""
        try:
            selected_text = self.chat_text.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            messagebox.showwarning("警告", "コピーするテキストを選択してください")
    
    def _select_all(self):
        """全て選択"""
        self.chat_text.tag_add(tk.SEL, "1.0", tk.END)
    
    def _extract_code(self):
        """コードを抽出"""
        try:
            selected_text = self.chat_text.selection_get()
            # コードブロックを抽出
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', selected_text, re.DOTALL)
            
            if code_blocks:
                extracted_code = '\n\n'.join(code_blocks)
                if self.on_code_select:
                    self.on_code_select(extracted_code)
            else:
                messagebox.showinfo("情報", "選択範囲にコードブロックが見つかりません")
                
        except tk.TclError:
            messagebox.showwarning("警告", "コードを抽出するテキストを選択してください")
    
    def _save_selection(self):
        """選択範囲をファイルに保存"""
        try:
            selected_text = self.chat_text.selection_get()
            
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(
                title="テキストを保存",
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("Markdown files", "*.md"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(selected_text)
                messagebox.showinfo("成功", f"テキストを保存しました: {Path(file_path).name}")
                
        except tk.TclError:
            messagebox.showwarning("警告", "保存するテキストを選択してください")
        except Exception as e:
            messagebox.showerror("エラー", f"保存に失敗しました: {e}")
    
    def _export_chat(self):
        """チャット履歴をエクスポート"""
        if not self.messages:
            messagebox.showwarning("警告", "エクスポートするメッセージがありません")
            return
        
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title="チャット履歴をエクスポート",
            defaultextension=".md",
            filetypes=[
                ("Markdown files", "*.md"),
                ("Text files", "*.txt"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                self._export_to_file(file_path)
                messagebox.showinfo("成功", f"チャット履歴をエクスポートしました: {Path(file_path).name}")
            except Exception as e:
                messagebox.showerror("エラー", f"エクスポートに失敗しました: {e}")
    
    def _export_to_file(self, file_path: str):
        """ファイルにエクスポート"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.json':
            self._export_to_json(file_path)
        elif file_ext == '.md':
            self._export_to_markdown(file_path)
        else:
            self._export_to_text(file_path)
    
    def _export_to_json(self, file_path: str):
        """JSON形式でエクスポート"""
        import json
        
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'messages': [
                {
                    'message': msg['message'],
                    'is_user': msg['is_user'],
                    'timestamp': msg['timestamp'].isoformat()
                }
                for msg in self.messages
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def _export_to_markdown(self, file_path: str):
        """Markdown形式でエクスポート"""
        lines = [
            "# AI Chat Export",
            f"Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ]
        
        for msg in self.messages:
            timestamp = msg['timestamp'].strftime('%H:%M:%S')
            sender = "**You**" if msg['is_user'] else "**AI**"
            
            lines.append(f"## {sender} ({timestamp})")
            lines.append("")
            lines.append(msg['message'])
            lines.append("")
            lines.append("---")
            lines.append("")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _export_to_text(self, file_path: str):
        """テキスト形式でエクスポート"""
        lines = [
            "AI Chat Export",
            f"Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 50,
            ""
        ]
        
        for msg in self.messages:
            timestamp = msg['timestamp'].strftime('%H:%M:%S')
            sender = "You" if msg['is_user'] else "AI"
            
            lines.append(f"[{timestamp}] {sender}:")
            lines.append(msg['message'])
            lines.append("-" * 30)
            lines.append("")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _show_chat_settings(self):
        """チャット設定を表示"""
        settings_dialog = ChatSettingsDialog(self, self._get_chat_settings())
        if settings_dialog.result:
            self._apply_chat_settings(settings_dialog.result)
    
    def _get_chat_settings(self) -> Dict[str, Any]:
        """現在のチャット設定を取得"""
        return {
            'font_size': 10,
            'font_family': 'Arial',
            'theme': 'light',
            'auto_scroll': True,
            'show_timestamps': True,
            'word_wrap': True,
            'code_highlighting': True
        }
    
    def _apply_chat_settings(self, settings: Dict[str, Any]):
        """チャット設定を適用"""
        try:
            # フォント設定
            font_family = settings.get('font_family', 'Arial')
            font_size = settings.get('font_size', 10)
            
            self.chat_text.config(font=(font_family, font_size))
            self.input_text.config(font=(font_family, font_size))
            
            # テーマ設定
            theme = settings.get('theme', 'light')
            if theme == 'dark':
                self.chat_text.config(bg='#2b2b2b', fg='white')
                self.input_text.config(bg='#3b3b3b', fg='white')
            else:
                self.chat_text.config(bg='white', fg='black')
                self.input_text.config(bg='white', fg='black')
            
            # 折り返し設定
            wrap_mode = tk.WORD if settings.get('word_wrap', True) else tk.NONE
            self.chat_text.config(wrap=wrap_mode)
            
            self.logger.info("チャット設定を適用しました")
            
        except Exception as e:
            self.logger.error(f"チャット設定適用エラー: {e}")


class ChatSettingsDialog:
    """チャット設定ダイアログ"""
    
    def __init__(self, parent, current_settings: Dict[str, Any]):
        self.parent = parent
        self.current_settings = current_settings
        self.result = None
        
        self._create_dialog()
    
    def _create_dialog(self):
        """ダイアログを作成"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("チャット設定")
        self.dialog.geometry("400x300")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 設定項目
        self._create_font_settings(main_frame)
        self._create_theme_settings(main_frame)
        self._create_behavior_settings(main_frame)
        self._create_buttons(main_frame)
        
        # ダイアログを中央に配置
        self._center_dialog()
    
    def _create_font_settings(self, parent):
        """フォント設定"""
        font_frame = ttk.LabelFrame(parent, text="フォント", padding=5)
        font_frame.pack(fill=tk.X, pady=(0, 10))
        
        # フォントファミリー
        ttk.Label(font_frame, text="フォント:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.font_var = tk.StringVar(value=self.current_settings.get('font_family', 'Arial'))
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_var, 
                                 values=['Arial', 'Helvetica', 'Times', 'Courier', 'Verdana'])
        font_combo.grid(row=0, column=1, sticky=tk.EW, padx=(0, 10))
        
        # フォントサイズ
        ttk.Label(font_frame, text="サイズ:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.size_var = tk.IntVar(value=self.current_settings.get('font_size', 10))
        size_spin = ttk.Spinbox(font_frame, from_=8, to=20, textvariable=self.size_var, width=5)
        size_spin.grid(row=0, column=3, sticky=tk.W)
        
        font_frame.columnconfigure(1, weight=1)
    
    def _create_theme_settings(self, parent):
        """テーマ設定"""
        theme_frame = ttk.LabelFrame(parent, text="テーマ", padding=5)
        theme_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.theme_var = tk.StringVar(value=self.current_settings.get('theme', 'light'))
        
        ttk.Radiobutton(theme_frame, text="ライトテーマ", variable=self.theme_var, 
                       value='light').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(theme_frame, text="ダークテーマ", variable=self.theme_var, 
                       value='dark').pack(side=tk.LEFT)
    
    def _create_behavior_settings(self, parent):
        """動作設定"""
        behavior_frame = ttk.LabelFrame(parent, text="動作", padding=5)
        behavior_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.auto_scroll_var = tk.BooleanVar(value=self.current_settings.get('auto_scroll', True))
        ttk.Checkbutton(behavior_frame, text="自動スクロール", 
                       variable=self.auto_scroll_var).pack(anchor=tk.W)
        
        self.show_timestamps_var = tk.BooleanVar(value=self.current_settings.get('show_timestamps', True))
        ttk.Checkbutton(behavior_frame, text="タイムスタンプ表示", 
                       variable=self.show_timestamps_var).pack(anchor=tk.W)
        
        self.word_wrap_var = tk.BooleanVar(value=self.current_settings.get('word_wrap', True))
        ttk.Checkbutton(behavior_frame, text="行の折り返し", 
                       variable=self.word_wrap_var).pack(anchor=tk.W)
        
        self.code_highlighting_var = tk.BooleanVar(value=self.current_settings.get('code_highlighting', True))
        ttk.Checkbutton(behavior_frame, text="コードハイライト", 
                       variable=self.code_highlighting_var).pack(anchor=tk.W)
    
    def _create_buttons(self, parent):
        """ボタン"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="キャンセル", 
                  command=self._cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="OK", 
                  command=self._ok).pack(side=tk.RIGHT)
    
    def _center_dialog(self):
        """ダイアログを中央に配置"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _ok(self):
        """OK処理"""
        self.result = {
            'font_family': self.font_var.get(),
            'font_size': self.size_var.get(),
            'theme': self.theme_var.get(),
            'auto_scroll': self.auto_scroll_var.get(),
            'show_timestamps': self.show_timestamps_var.get(),
            'word_wrap': self.word_wrap_var.get(),
            'code_highlighting': self.code_highlighting_var.get()
        }
        self.dialog.destroy()
    
    def _cancel(self):
        """キャンセル処理"""
        self.result = None
        self.dialog.destroy()


class StreamingTextHandler:
    """ストリーミングテキスト処理クラス"""
    
    def __init__(self, chat_interface: ChatInterface):
        self.chat_interface = chat_interface
        self.buffer = ""
        self.is_active = False
        self.update_interval = 50  # ms
        
    def start_streaming(self):
        """ストリーミング開始"""
        self.is_active = True
        self.buffer = ""
        self.chat_interface.start_streaming_message()
    
    def add_chunk(self, chunk: str):
        """チャンクを追加"""
        if self.is_active:
            self.buffer += chunk
            self._schedule_update()
    
    def _schedule_update(self):
        """更新をスケジュール"""
        if self.buffer:
            # バッファの内容を表示
            self.chat_interface.append_to_stream(self.buffer)
            self.buffer = ""
        
        # 次の更新をスケジュール
        if self.is_active:
            self.chat_interface.after(self.update_interval, self._schedule_update)
    
    def finish_streaming(self):
        """ストリーミング終了"""
        self.is_active = False
        if self.buffer:
            self.chat_interface.append_to_stream(self.buffer)
            self.buffer = ""
        self.chat_interface.finish_streaming_message()


# 使用例とテスト関数
def test_chat_interface():
    """チャットインターフェースのテスト"""
    import tkinter as tk
    
    root = tk.Tk()
    root.title("Chat Interface Test")
    root.geometry("800x600")
    
    # チャットインターフェースを作成
    chat = ChatInterface(root)
    chat.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # テストメッセージを追加
    def add_test_messages():
        chat.add_user_message("Hello! Can you help me with Python?")
        
        assistant_response = """Sure! I'd be happy to help you with Python. Here's a simple example:

    ```python
    def hello_world():
        print("Hello, World!")
        return "Success"

    # Call the function
    result = hello_world()
    print(f"Result: {result}")

    This function demonstrates:

    Function definition
    Print statement
    Return value
    Function call
    What specific Python topic would you like to learn about?"""

        chat.add_assistant_message(assistant_response)
        
        chat.add_user_message("Can you explain list comprehensions?")
        
        list_response = """List comprehensions are a concise way to create lists in Python. Here are some examples:
    # Basic list comprehension
    numbers = [1, 2, 3, 4, 5]
    squares = [x**2 for x in numbers]
    print(squares)  # [1, 4, 9, 16, 25]

    # With condition
    even_squares = [x**2 for x in numbers if x % 2 == 0]
    print(even_squares)  # [4, 16]

    # String processing
    words = ['hello', 'world', 'python']
    capitalized = [word.upper() for word in words]
    print(capitalized)  # ['HELLO', 'WORLD', 'PYTHON']
    The syntax is: [expression for item in iterable if condition]

    The if condition part is optional."""
        chat.add_assistant_message(list_response)

    # テストボタン
    test_frame = tk.Frame(root)
    test_frame.pack(fill=tk.X, padx=10, pady=5)

    tk.Button(test_frame, text="Add Test Messages", 
            command=add_test_messages).pack(side=tk.LEFT, padx=5)

    tk.Button(test_frame, text="Clear Chat", 
            command=chat.clear).pack(side=tk.LEFT, padx=5)

    # ストリーミングテスト
    def test_streaming():
        streaming_handler = StreamingTextHandler(chat)
        streaming_handler.start_streaming()
        
        test_chunks = [
            "This is a streaming response. ",
            "It comes in chunks ",
            "to simulate real-time generation.\n\n",
            "```python\n",
            "def streaming_example():\n",
            "    for i in range(5):\n",
            "        print(f'Chunk {i}')\n",
            "```\n\n",
            "The streaming is now complete!"
        ]
        
        def send_chunk(index=0):
            if index < len(test_chunks):
                streaming_handler.add_chunk(test_chunks[index])
                root.after(200, lambda: send_chunk(index + 1))
            else:
                streaming_handler.finish_streaming()
        
        send_chunk()

        tk.Button(test_frame, text="Test Streaming", 
                command=test_streaming).pack(side=tk.LEFT, padx=5)

        # コールバック設定
        def on_message_send(message):
            print(f"Message sent: {message}")
            # エコー応答
            chat.add_assistant_message(f"You said: {message}")

        def on_code_select(code):
            print(f"Code selected: {code[:50]}...")

        chat.on_message_send = on_message_send
        chat.on_code_select = on_code_select

        root.mainloop()

if name == "main":
    test_chat_interface()