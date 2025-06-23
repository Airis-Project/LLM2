# src/ui/chat_panel.py
"""
チャットパネルコンポーネント
LLMとの対話インターフェースを提供
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QSplitter, QScrollArea, QFrame, QLabel,
    QComboBox, QSpinBox, QSlider, QCheckBox, QGroupBox,
    QTabWidget, QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar, QToolButton, QMenu, QTextBrowser,
    QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QThread, QObject, QSettings,
    QSize, QPropertyAnimation, QEasingCurve, QRect
)
from PyQt6.QtGui import (
    QFont, QTextCursor, QTextCharFormat, QColor, QPalette,
    QPixmap, QIcon, QAction, QKeySequence, QShortcut,
    QTextDocument, QSyntaxHighlighter
)

from ..core.logger import get_logger
from ..llm.llm_factory import LLMFactory
from ..llm.base_llm import BaseLLM
from ..utils.text_utils import format_code_block, extract_code_blocks
from .components.syntax_highlighter import PythonHighlighter


class MessageType(Enum):
    """メッセージタイプ"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"
    INFO = "info"


class ChatMessage:
    """チャットメッセージクラス"""
    
    def __init__(self, content: str, message_type: MessageType, 
                 timestamp: Optional[datetime] = None, metadata: Optional[Dict] = None):
        self.content = content
        self.message_type = message_type
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
        self.id = f"{self.timestamp.timestamp()}_{id(self)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'content': self.content,
            'type': self.message_type.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """辞書から復元"""
        return cls(
            content=data['content'],
            message_type=MessageType(data['type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )


class LLMWorker(QObject):
    """LLM処理ワーカー"""
    
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, llm_client: BaseLLM, messages: List[Dict[str, str]]):
        super().__init__()
        self.llm_client = llm_client
        self.messages = messages
        self.logger = get_logger(__name__)
    
    def process(self):
        """LLM処理を実行"""
        try:
            response = self.llm_client.generate_response(self.messages)
            self.response_received.emit(response)
            
        except Exception as e:
            self.logger.error(f"LLM処理エラー: {e}")
            self.error_occurred.emit(str(e))
        
        finally:
            self.finished.emit()


class MessageWidget(QFrame):
    """メッセージ表示ウィジェット"""
    
    code_execution_requested = pyqtSignal(str, str)  # code, language
    
    def __init__(self, message: ChatMessage, parent=None):
        super().__init__(parent)
        self.message = message
        self.logger = get_logger(__name__)
        
        self._init_ui()
        self._apply_style()
    
    def _init_ui(self):
        """UI初期化"""
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(5)
            
            # ヘッダー部分
            header_layout = QHBoxLayout()
            
            # アイコン
            icon_label = QLabel()
            if self.message.message_type == MessageType.USER:
                icon_label.setText("👤")
            elif self.message.message_type == MessageType.ASSISTANT:
                icon_label.setText("🤖")
            elif self.message.message_type == MessageType.SYSTEM:
                icon_label.setText("⚙️")
            elif self.message.message_type == MessageType.ERROR:
                icon_label.setText("❌")
            else:
                icon_label.setText("ℹ️")
            
            icon_label.setFont(QFont("Arial", 12))
            header_layout.addWidget(icon_label)
            
            # 送信者名
            sender_label = QLabel()
            if self.message.message_type == MessageType.USER:
                sender_label.setText("あなた")
            elif self.message.message_type == MessageType.ASSISTANT:
                sender_label.setText("アシスタント")
            elif self.message.message_type == MessageType.SYSTEM:
                sender_label.setText("システム")
            elif self.message.message_type == MessageType.ERROR:
                sender_label.setText("エラー")
            else:
                sender_label.setText("情報")
            
            sender_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            header_layout.addWidget(sender_label)
            
            # 時刻
            time_label = QLabel(self.message.timestamp.strftime("%H:%M:%S"))
            time_label.setFont(QFont("Arial", 9))
            time_label.setStyleSheet("color: #666666;")
            header_layout.addWidget(time_label)
            
            header_layout.addStretch()
            layout.addLayout(header_layout)
            
            # メッセージ内容
            content_widget = self._create_content_widget()
            layout.addWidget(content_widget)
            
        except Exception as e:
            self.logger.error(f"メッセージウィジェット初期化エラー: {e}")
    
    def _create_content_widget(self) -> QWidget:
        """コンテンツウィジェットを作成"""
        try:
            # コードブロックを検出
            code_blocks = extract_code_blocks(self.message.content)
            
            if code_blocks:
                return self._create_rich_content_widget(code_blocks)
            else:
                return self._create_simple_content_widget()
            
        except Exception as e:
            self.logger.error(f"コンテンツウィジェット作成エラー: {e}")
            return self._create_simple_content_widget()
    
    def _create_simple_content_widget(self) -> QWidget:
        """シンプルなコンテンツウィジェットを作成"""
        try:
            text_browser = QTextBrowser()
            text_browser.setPlainText(self.message.content)
            text_browser.setMaximumHeight(200)
            text_browser.setOpenExternalLinks(True)
            
            # フォント設定
            font = QFont("Consolas", 10)
            text_browser.setFont(font)
            
            return text_browser
            
        except Exception as e:
            self.logger.error(f"シンプルコンテンツ作成エラー: {e}")
            label = QLabel(self.message.content)
            label.setWordWrap(True)
            return label
    
    def _create_rich_content_widget(self, code_blocks: List[Dict[str, str]]) -> QWidget:
        """リッチなコンテンツウィジェットを作成（コードブロック付き）"""
        try:
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)
            
            content = self.message.content
            last_end = 0
            
            for code_block in code_blocks:
                # コードブロック前のテキスト
                if code_block['start'] > last_end:
                    text_part = content[last_end:code_block['start']]
                    if text_part.strip():
                        text_widget = QTextBrowser()
                        text_widget.setPlainText(text_part.strip())
                        text_widget.setMaximumHeight(100)
                        layout.addWidget(text_widget)
                
                # コードブロック
                code_widget = self._create_code_widget(
                    code_block['code'], 
                    code_block['language']
                )
                layout.addWidget(code_widget)
                
                last_end = code_block['end']
            
            # 残りのテキスト
            if last_end < len(content):
                remaining_text = content[last_end:].strip()
                if remaining_text:
                    text_widget = QTextBrowser()
                    text_widget.setPlainText(remaining_text)
                    text_widget.setMaximumHeight(100)
                    layout.addWidget(text_widget)
            
            return container
            
        except Exception as e:
            self.logger.error(f"リッチコンテンツ作成エラー: {e}")
            return self._create_simple_content_widget()
    
    def _create_code_widget(self, code: str, language: str) -> QWidget:
        """コードウィジェットを作成"""
        try:
            container = QFrame()
            container.setFrameStyle(QFrame.Shape.Box)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(3)
            
            # ヘッダー
            header_layout = QHBoxLayout()
            
            # 言語ラベル
            lang_label = QLabel(f"言語: {language or '不明'}")
            lang_label.setFont(QFont("Arial", 9))
            lang_label.setStyleSheet("color: #666666;")
            header_layout.addWidget(lang_label)
            
            header_layout.addStretch()
            
            # コピーボタン
            copy_button = QPushButton("コピー")
            copy_button.setMaximumSize(60, 25)
            copy_button.clicked.connect(lambda: self._copy_code(code))
            header_layout.addWidget(copy_button)
            
            # 実行ボタン（Pythonの場合）
            if language and language.lower() in ['python', 'py']:
                run_button = QPushButton("実行")
                run_button.setMaximumSize(60, 25)
                run_button.clicked.connect(lambda: self.code_execution_requested.emit(code, language))
                header_layout.addWidget(run_button)
            
            layout.addLayout(header_layout)
            
            # コード表示
            code_editor = QTextEdit()
            code_editor.setPlainText(code)
            code_editor.setReadOnly(True)
            code_editor.setMaximumHeight(300)
            
            # フォント設定
            font = QFont("Consolas", 10)
            code_editor.setFont(font)
            
            # シンタックスハイライト
            if language and language.lower() in ['python', 'py']:
                highlighter = PythonHighlighter(code_editor.document())
            
            layout.addWidget(code_editor)
            
            return container
            
        except Exception as e:
            self.logger.error(f"コードウィジェット作成エラー: {e}")
            # フォールバック
            text_edit = QTextEdit()
            text_edit.setPlainText(code)
            text_edit.setReadOnly(True)
            text_edit.setMaximumHeight(200)
            return text_edit
    
    def _copy_code(self, code: str):
        """コードをクリップボードにコピー"""
        try:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(code)
            
            # 一時的な視覚フィードバック
            # TODO: トーストメッセージを表示
            
        except Exception as e:
            self.logger.error(f"コードコピーエラー: {e}")
    
    def _apply_style(self):
        """スタイルを適用"""
        try:
            if self.message.message_type == MessageType.USER:
                self.setStyleSheet("""
                    MessageWidget {
                        background-color: #e3f2fd;
                        border: 1px solid #bbdefb;
                        border-radius: 8px;
                        margin: 2px;
                    }
                """)
            elif self.message.message_type == MessageType.ASSISTANT:
                self.setStyleSheet("""
                    MessageWidget {
                        background-color: #f3e5f5;
                        border: 1px solid #e1bee7;
                        border-radius: 8px;
                        margin: 2px;
                    }
                """)
            elif self.message.message_type == MessageType.ERROR:
                self.setStyleSheet("""
                    MessageWidget {
                        background-color: #ffebee;
                        border: 1px solid #ffcdd2;
                        border-radius: 8px;
                        margin: 2px;
                    }
                """)
            else:
                self.setStyleSheet("""
                    MessageWidget {
                        background-color: #f5f5f5;
                        border: 1px solid #e0e0e0;
                        border-radius: 8px;
                        margin: 2px;
                    }
                """)
            
        except Exception as e:
            self.logger.error(f"スタイル適用エラー: {e}")


class ChatPanel(QWidget):
    """チャットパネルメインクラス"""
    
    # シグナル定義
    message_sent = pyqtSignal(str)  # メッセージが送信された
    code_execution_requested = pyqtSignal(str, str)  # コード実行が要求された
    file_analysis_requested = pyqtSignal(str)  # ファイル解析が要求された
    project_analysis_requested = pyqtSignal(str)  # プロジェクト解析が要求された
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.settings = QSettings()
        
        # チャット履歴
        self.chat_history: List[ChatMessage] = []
        self.current_session_id: Optional[str] = None
        
        # LLM関連
        self.llm_factory = LLMFactory()
        self.current_llm: Optional[BaseLLM] = None
        self.llm_worker: Optional[LLMWorker] = None
        self.llm_thread: Optional[QThread] = None
        
        # UI状態
        self.is_processing = False
        self.auto_scroll = True
        
        self._init_ui()
        self._setup_connections()
        self._load_settings()
        self._load_chat_history()
    
    def _init_ui(self):
        """UI初期化"""
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)
            
            # ツールバー
            toolbar_layout = self._create_toolbar()
            layout.addLayout(toolbar_layout)
            
            # メインエリア
            main_splitter = QSplitter(Qt.Orientation.Vertical)
            
            # チャット表示エリア
            self.chat_display = self._create_chat_display()
            main_splitter.addWidget(self.chat_display)
            
            # 入力エリア
            input_widget = self._create_input_area()
            main_splitter.addWidget(input_widget)
            
            # スプリッターの比率設定
            main_splitter.setSizes([400, 150])
            main_splitter.setCollapsible(0, False)
            main_splitter.setCollapsible(1, False)
            
            layout.addWidget(main_splitter)
            
            # ステータスバー
            status_layout = self._create_status_bar()
            layout.addLayout(status_layout)
            
        except Exception as e:
            self.logger.error(f"UI初期化エラー: {e}")
    
    def _create_toolbar(self) -> QHBoxLayout:
        """ツールバーを作成"""
        try:
            layout = QHBoxLayout()
            
            # LLMモデル選択
            model_label = QLabel("モデル:")
            layout.addWidget(model_label)
            
            self.model_combo = QComboBox()
            self.model_combo.addItems(self.llm_factory.get_available_models())
            self.model_combo.currentTextChanged.connect(self._on_model_changed)
            layout.addWidget(self.model_combo)
            
            layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding))
            
            # 新しいチャット
            new_chat_button = QPushButton("新しいチャット")
            new_chat_button.clicked.connect(self._start_new_chat)
            layout.addWidget(new_chat_button)
            
            # 履歴クリア
            clear_button = QPushButton("履歴クリア")
            clear_button.clicked.connect(self._clear_history)
            layout.addWidget(clear_button)
            
            # 設定
            settings_button = QPushButton("設定")
            settings_button.clicked.connect(self._show_settings)
            layout.addWidget(settings_button)
            
            return layout
            
        except Exception as e:
            self.logger.error(f"ツールバー作成エラー: {e}")
            return QHBoxLayout()
    
    def _create_chat_display(self) -> QWidget:
        """チャット表示エリアを作成"""
        try:
            # スクロールエリア
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            
            # コンテナウィジェット
            self.chat_container = QWidget()
            self.chat_layout = QVBoxLayout(self.chat_container)
            self.chat_layout.setContentsMargins(5, 5, 5, 5)
            self.chat_layout.setSpacing(5)
            self.chat_layout.addStretch()
            
            scroll_area.setWidget(self.chat_container)
            
            return scroll_area
            
        except Exception as e:
            self.logger.error(f"チャット表示エリア作成エラー: {e}")
            return QWidget()
    
    def _create_input_area(self) -> QWidget:
        """入力エリアを作成"""
        try:
            container = QFrame()
            container.setFrameStyle(QFrame.Shape.Box)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)
            
            # 入力フィールド
            self.input_text = QTextEdit()
            self.input_text.setMaximumHeight(100)
            self.input_text.setPlaceholderText("メッセージを入力してください... (Ctrl+Enter で送信)")
            
            # フォント設定
            font = QFont("Arial", 10)
            self.input_text.setFont(font)
            
            layout.addWidget(self.input_text)
            
            # ボタンエリア
            button_layout = QHBoxLayout()
            
            # ファイル添付ボタン
            attach_button = QPushButton("📎")
            attach_button.setMaximumSize(30, 30)
            attach_button.setToolTip("ファイルを添付")
            attach_button.clicked.connect(self._attach_file)
            button_layout.addWidget(attach_button)
            
            button_layout.addStretch()
            
            # 送信ボタン
            self.send_button = QPushButton("送信")
            self.send_button.setMinimumSize(80, 30)
            self.send_button.clicked.connect(self._send_message)
            button_layout.addWidget(self.send_button)
            
            layout.addLayout(button_layout)
            
            return container
            
        except Exception as e:
            self.logger.error(f"入力エリア作成エラー: {e}")
            return QWidget()
    
    def _create_status_bar(self) -> QHBoxLayout:
        """ステータスバーを作成"""
        try:
            layout = QHBoxLayout()
            
            # ステータスラベル
            self.status_label = QLabel("準備完了")
            layout.addWidget(self.status_label)
            
            layout.addStretch()
            
            # プログレスバー
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            self.progress_bar.setMaximumWidth(200)
            layout.addWidget(self.progress_bar)
            
            # メッセージ数
            self.message_count_label = QLabel("メッセージ: 0")
            layout.addWidget(self.message_count_label)
            
            return layout
            
        except Exception as e:
            self.logger.error(f"ステータスバー作成エラー: {e}")
            return QHBoxLayout()
    
    def _setup_connections(self):
        """シグナル接続"""
        try:
            # キーボードショートカット
            send_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.input_text)
            send_shortcut.activated.connect(self._send_message)
            
            # テキスト変更
            self.input_text.textChanged.connect(self._on_input_changed)
            
        except Exception as e:
            self.logger.error(f"シグナル接続エラー: {e}")
    def _load_settings(self):
        """設定を読み込み"""
        try:
            # デフォルトモデルを設定
            default_model = self.settings.value("chat/default_model", "gpt-3.5-turbo")
            index = self.model_combo.findText(default_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            
            # 自動スクロール設定
            self.auto_scroll = self.settings.value("chat/auto_scroll", True, type=bool)
            
            # その他の設定
            self._initialize_llm()
            
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {e}")
    
    def _save_settings(self):
        """設定を保存"""
        try:
            self.settings.setValue("chat/default_model", self.model_combo.currentText())
            self.settings.setValue("chat/auto_scroll", self.auto_scroll)
            
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
    
    def _initialize_llm(self):
        """LLMを初期化"""
        try:
            model_name = self.model_combo.currentText()
            if model_name:
                self.current_llm = self.llm_factory.create_llm(model_name)
                self.status_label.setText(f"モデル: {model_name}")
                self.logger.info(f"LLMを初期化しました: {model_name}")
            
        except Exception as e:
            self.logger.error(f"LLM初期化エラー: {e}")
            self.status_label.setText("LLM初期化エラー")
    
    def _load_chat_history(self):
        """チャット履歴を読み込み"""
        try:
            # 履歴ファイルパス
            history_dir = os.path.join(os.path.expanduser("~"), ".llm_code_assistant", "chat_history")
            os.makedirs(history_dir, exist_ok=True)
            
            # 最新のセッションファイルを探す
            session_files = [f for f in os.listdir(history_dir) if f.endswith('.json')]
            if session_files:
                latest_file = max(session_files, key=lambda x: os.path.getctime(os.path.join(history_dir, x)))
                history_file = os.path.join(history_dir, latest_file)
                
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                # メッセージを復元
                for msg_data in history_data.get('messages', []):
                    message = ChatMessage.from_dict(msg_data)
                    self.chat_history.append(message)
                    self._add_message_to_display(message)
                
                self.current_session_id = history_data.get('session_id')
                self.logger.info(f"チャット履歴を読み込みました: {len(self.chat_history)}件")
            
            self._update_message_count()
            
        except Exception as e:
            self.logger.error(f"チャット履歴読み込みエラー: {e}")
    
    def _save_chat_history(self):
        """チャット履歴を保存"""
        try:
            if not self.chat_history:
                return
            
            # 履歴ディレクトリ
            history_dir = os.path.join(os.path.expanduser("~"), ".llm_code_assistant", "chat_history")
            os.makedirs(history_dir, exist_ok=True)
            
            # セッションIDが未設定の場合は生成
            if not self.current_session_id:
                self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 履歴ファイル
            history_file = os.path.join(history_dir, f"{self.current_session_id}.json")
            
            # データ構造
            history_data = {
                'session_id': self.current_session_id,
                'created_at': datetime.now().isoformat(),
                'model': self.model_combo.currentText(),
                'messages': [msg.to_dict() for msg in self.chat_history]
            }
            
            # 保存
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"チャット履歴を保存しました: {history_file}")
            
        except Exception as e:
            self.logger.error(f"チャット履歴保存エラー: {e}")
    
    def _on_model_changed(self, model_name: str):
        """モデル変更時の処理"""
        try:
            if model_name:
                self._initialize_llm()
                self._save_settings()
            
        except Exception as e:
            self.logger.error(f"モデル変更エラー: {e}")
    
    def _on_input_changed(self):
        """入力テキスト変更時の処理"""
        try:
            # 送信ボタンの有効/無効制御
            has_text = bool(self.input_text.toPlainText().strip())
            self.send_button.setEnabled(has_text and not self.is_processing)
            
        except Exception as e:
            self.logger.error(f"入力変更処理エラー: {e}")
    
    def _send_message(self):
        """メッセージを送信"""
        try:
            if self.is_processing:
                return
            
            message_text = self.input_text.toPlainText().strip()
            if not message_text:
                return
            
            # ユーザーメッセージを追加
            user_message = ChatMessage(message_text, MessageType.USER)
            self._add_message(user_message)
            
            # 入力フィールドをクリア
            self.input_text.clear()
            
            # LLM処理を開始
            self._process_llm_request()
            
        except Exception as e:
            self.logger.error(f"メッセージ送信エラー: {e}")
            self._show_error_message(f"メッセージ送信エラー: {e}")
    
    def _process_llm_request(self):
        """LLM処理を実行"""
        try:
            if not self.current_llm:
                self._show_error_message("LLMが初期化されていません")
                return
            
            # 処理状態を設定
            self._set_processing_state(True)
            
            # メッセージ履歴を準備
            messages = []
            for msg in self.chat_history[-10:]:  # 最新10件のみ
                if msg.message_type == MessageType.USER:
                    messages.append({"role": "user", "content": msg.content})
                elif msg.message_type == MessageType.ASSISTANT:
                    messages.append({"role": "assistant", "content": msg.content})
            
            # ワーカースレッドで処理
            self.llm_thread = QThread()
            self.llm_worker = LLMWorker(self.current_llm, messages)
            self.llm_worker.moveToThread(self.llm_thread)
            
            # シグナル接続
            self.llm_thread.started.connect(self.llm_worker.process)
            self.llm_worker.response_received.connect(self._on_llm_response)
            self.llm_worker.error_occurred.connect(self._on_llm_error)
            self.llm_worker.finished.connect(self._on_llm_finished)
            self.llm_worker.finished.connect(self.llm_thread.quit)
            self.llm_worker.finished.connect(self.llm_worker.deleteLater)
            self.llm_thread.finished.connect(self.llm_thread.deleteLater)
            
            # スレッド開始
            self.llm_thread.start()
            
        except Exception as e:
            self.logger.error(f"LLM処理エラー: {e}")
            self._set_processing_state(False)
            self._show_error_message(f"LLM処理エラー: {e}")
    
    def _on_llm_response(self, response: str):
        """LLM応答受信時の処理"""
        try:
            # アシスタントメッセージを追加
            assistant_message = ChatMessage(response, MessageType.ASSISTANT)
            self._add_message(assistant_message)
            
        except Exception as e:
            self.logger.error(f"LLM応答処理エラー: {e}")
    
    def _on_llm_error(self, error_message: str):
        """LLMエラー時の処理"""
        try:
            self._show_error_message(f"LLMエラー: {error_message}")
            
        except Exception as e:
            self.logger.error(f"LLMエラー処理エラー: {e}")
    
    def _on_llm_finished(self):
        """LLM処理完了時の処理"""
        try:
            self._set_processing_state(False)
            
        except Exception as e:
            self.logger.error(f"LLM完了処理エラー: {e}")
    
    def _set_processing_state(self, processing: bool):
        """処理状態を設定"""
        try:
            self.is_processing = processing
            
            # UI状態を更新
            self.send_button.setEnabled(not processing and bool(self.input_text.toPlainText().strip()))
            self.input_text.setEnabled(not processing)
            self.model_combo.setEnabled(not processing)
            
            # プログレスバー
            self.progress_bar.setVisible(processing)
            if processing:
                self.progress_bar.setRange(0, 0)  # 不定プログレス
                self.status_label.setText("処理中...")
            else:
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(100)
                self.status_label.setText("準備完了")
            
        except Exception as e:
            self.logger.error(f"処理状態設定エラー: {e}")
    
    def _add_message(self, message: ChatMessage):
        """メッセージを追加"""
        try:
            # 履歴に追加
            self.chat_history.append(message)
            
            # 表示に追加
            self._add_message_to_display(message)
            
            # カウント更新
            self._update_message_count()
            
            # 履歴保存
            self._save_chat_history()
            
            # シグナル発信
            if message.message_type == MessageType.USER:
                self.message_sent.emit(message.content)
            
        except Exception as e:
            self.logger.error(f"メッセージ追加エラー: {e}")
    
    def _add_message_to_display(self, message: ChatMessage):
        """メッセージを表示に追加"""
        try:
            # メッセージウィジェットを作成
            message_widget = MessageWidget(message)
            message_widget.code_execution_requested.connect(self.code_execution_requested)
            
            # レイアウトに追加（ストレッチの前に挿入）
            self.chat_layout.insertWidget(self.chat_layout.count() - 1, message_widget)
            
            # 自動スクロール
            if self.auto_scroll:
                QTimer.singleShot(100, self._scroll_to_bottom)
            
        except Exception as e:
            self.logger.error(f"メッセージ表示追加エラー: {e}")
    
    def _scroll_to_bottom(self):
        """最下部にスクロール"""
        try:
            scroll_area = self.chat_display
            if isinstance(scroll_area, QScrollArea):
                scrollbar = scroll_area.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            self.logger.error(f"スクロールエラー: {e}")
    
    def _update_message_count(self):
        """メッセージ数を更新"""
        try:
            count = len(self.chat_history)
            self.message_count_label.setText(f"メッセージ: {count}")
            
        except Exception as e:
            self.logger.error(f"メッセージ数更新エラー: {e}")
    
    def _show_error_message(self, error_text: str):
        """エラーメッセージを表示"""
        try:
            error_message = ChatMessage(error_text, MessageType.ERROR)
            self._add_message_to_display(error_message)
            
        except Exception as e:
            self.logger.error(f"エラーメッセージ表示エラー: {e}")
    
    def _start_new_chat(self):
        """新しいチャットを開始"""
        try:
            if self.chat_history:
                reply = QMessageBox.question(
                    self, "新しいチャット",
                    "現在のチャット履歴をクリアして新しいチャットを開始しますか？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # 履歴をクリア
            self._clear_history()
            
            # 新しいセッションID
            self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # ウェルカムメッセージ
            welcome_message = ChatMessage(
                "新しいチャットを開始しました。何かお手伝いできることはありますか？",
                MessageType.SYSTEM
            )
            self._add_message_to_display(welcome_message)
            
            self.logger.info("新しいチャットを開始しました")
            
        except Exception as e:
            self.logger.error(f"新しいチャット開始エラー: {e}")
    
    def _clear_history(self):
        """履歴をクリア"""
        try:
            # 確認ダイアログ
            if self.chat_history:
                reply = QMessageBox.question(
                    self, "履歴クリア",
                    "チャット履歴をクリアしますか？この操作は元に戻せません。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # 履歴をクリア
            self.chat_history.clear()
            
            # 表示をクリア
            while self.chat_layout.count() > 1:  # ストレッチを残す
                child = self.chat_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # カウント更新
            self._update_message_count()
            
            self.logger.info("チャット履歴をクリアしました")
            
        except Exception as e:
            self.logger.error(f"履歴クリアエラー: {e}")
    
    def _attach_file(self):
        """ファイルを添付"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getOpenFileName(
                self, "ファイルを選択",
                "", "すべてのファイル (*.*)"
            )
            
            if file_path:
                # ファイル解析を要求
                self.file_analysis_requested.emit(file_path)
                
                # ファイル情報をメッセージに追加
                file_info = f"📎 ファイルを添付しました: {os.path.basename(file_path)}"
                info_message = ChatMessage(file_info, MessageType.INFO)
                self._add_message_to_display(info_message)
            
        except Exception as e:
            self.logger.error(f"ファイル添付エラー: {e}")
            self._show_error_message(f"ファイル添付エラー: {e}")
    
    def _show_settings(self):
        """設定ダイアログを表示"""
        try:
            from .settings_dialog import ChatSettingsDialog
            
            dialog = ChatSettingsDialog(self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                # 設定を適用
                self._load_settings()
            
        except Exception as e:
            self.logger.error(f"設定表示エラー: {e}")
    
    # 公開メソッド
    def add_system_message(self, message: str):
        """システムメッセージを追加"""
        try:
            system_message = ChatMessage(message, MessageType.SYSTEM)
            self._add_message(system_message)
            
        except Exception as e:
            self.logger.error(f"システムメッセージ追加エラー: {e}")
    
    def add_info_message(self, message: str):
        """情報メッセージを追加"""
        try:
            info_message = ChatMessage(message, MessageType.INFO)
            self._add_message(info_message)
            
        except Exception as e:
            self.logger.error(f"情報メッセージ追加エラー: {e}")
    
    def set_context(self, context: str):
        """コンテキストを設定"""
        try:
            if context:
                context_message = f"コンテキスト情報:\n{context}"
                self.add_system_message(context_message)
            
        except Exception as e:
            self.logger.error(f"コンテキスト設定エラー: {e}")
    
    def get_chat_history(self) -> List[ChatMessage]:
        """チャット履歴を取得"""
        return self.chat_history.copy()
    
    def export_chat_history(self, file_path: str):
        """チャット履歴をエクスポート"""
        try:
            export_data = {
                'session_id': self.current_session_id,
                'exported_at': datetime.now().isoformat(),
                'model': self.model_combo.currentText(),
                'messages': [msg.to_dict() for msg in self.chat_history]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"チャット履歴をエクスポートしました: {file_path}")
            
        except Exception as e:
            self.logger.error(f"チャット履歴エクスポートエラー: {e}")
            raise
    
    def import_chat_history(self, file_path: str):
        """チャット履歴をインポート"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 現在の履歴をクリア
            self._clear_history()
            
            # メッセージを復元
            for msg_data in import_data.get('messages', []):
                message = ChatMessage.from_dict(msg_data)
                self.chat_history.append(message)
                self._add_message_to_display(message)
            
            self.current_session_id = import_data.get('session_id')
            self._update_message_count()
            
            self.logger.info(f"チャット履歴をインポートしました: {file_path}")
            
        except Exception as e:
            self.logger.error(f"チャット履歴インポートエラー: {e}")
            raise
    
    # クリーンアップ
    def cleanup(self):
        """クリーンアップ"""
        try:
            # 設定を保存
            self._save_settings()
            
            # チャット履歴を保存
            self._save_chat_history()
            
            # LLMスレッドを停止
            if self.llm_thread and self.llm_thread.isRunning():
                self.llm_thread.quit()
                self.llm_thread.wait()
            
            self.logger.info("ChatPanel をクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")
