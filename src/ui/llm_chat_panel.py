#!/usr/bin/env python3
"""
LLMチャットパネル - 新LLMシステム対応版
ユーザーとLLMの対話インターフェースを提供
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QLabel, QSplitter, QGroupBox,
    QScrollArea, QFrame, QProgressBar, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTabWidget, QListWidget, QListWidgetItem,
    QMessageBox, QFileDialog, QToolButton, QMenu, QAction,
    QInputDialog
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize,
    QPropertyAnimation, QEasingCurve, QRect
)
from PyQt6.QtGui import (
    QFont, QTextCursor, QPixmap, QIcon,
    QTextCharFormat, QColor, QPalette
)

# 新LLMシステムインポート
from src.llm import (
    get_llm_factory,
    LLMMessage,
    LLMRole,
    LLMProvider,
    LLMConfig,
    create_llm_client,
    get_available_providers,
    LLMResponse
)

# コアシステムインポート
from src.core.logger import get_logger
from src.core.config_manager import get_config
from src.core.event_system import get_event_system, Event

# UIコンポーネント
from src.ui.components.chat_message_widget import ChatMessage
from src.ui.components.model_selector_widget import ModelSelector
from src.ui.components.prompt_template_widget import PromptTemplate

# ユーティリティ
from src.utils.text_utils import TextUtils
from src.utils.file_utils import FileUtils

logger = get_logger(__name__)

class LLMRequestThread(QThread):
    """LLMリクエスト処理スレッド"""
    
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, llm_client, messages: List[LLMMessage], config: Dict[str, Any]):
        super().__init__()
        self.llm_client = llm_client
        self.messages = messages
        self.config = config
        self.is_cancelled = False
    
    def run(self):
        """リクエスト実行"""
        try:
            if not self.llm_client or not self.llm_client.is_available():
                self.error_occurred.emit("LLMクライアントが利用できません")
                return
            
            # プログレス更新
            self.progress_updated.emit(25)
            
            # 非同期リクエスト実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # プログレス更新
                self.progress_updated.emit(50)
                
                # LLM呼び出し
                response = loop.run_until_complete(
                    self.llm_client.generate_async(
                        messages=self.messages,
                        **self.config
                    )
                )
                
                # プログレス更新
                self.progress_updated.emit(75)
                
                if not self.is_cancelled and response:
                    self.response_received.emit(response.content)
                
                # プログレス完了
                self.progress_updated.emit(100)
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"LLMリクエストエラー: {e}")
            self.error_occurred.emit(str(e))
    
    def cancel(self):
        """リクエストキャンセル"""
        self.is_cancelled = True

class LLMChatPanel(QWidget):
    """LLMチャットパネル - 新システム対応"""
    
    # シグナル定義
    message_sent = pyqtSignal(str)
    response_received = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    config_changed = pyqtSignal(dict)
    
    def __init__(self, llm_client=None, parent=None):
        """初期化"""
        super().__init__(parent)
        
        # 新LLMシステム初期化
        self.llm_factory = get_llm_factory()
        self.llm_client = llm_client
        self.available_providers = get_available_providers()
        
        # 設定管理
        self.config_manager = get_config()
        self.chat_config = self.config_manager.get_section('chat', {})
        
        # イベントシステム
        self.event_system = get_event_system()
        
        # 状態管理
        self.conversation_history: List[LLMMessage] = []
        self.current_request_thread: Optional[LLMRequestThread] = None
        self.is_processing = False
        
        # UI初期化
        self.setup_ui()
        self.setup_connections()
        self.setup_event_handlers()
        self.load_chat_settings()
        
        # 初期状態更新
        self.update_ui_state()
        
        logger.info("LLMチャットパネル初期化完了")
    
    def setup_ui(self):
        """UI構築"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # === 上部: モデル選択・設定エリア ===
        self.setup_header_area(layout)
        
        # === 中央: チャット表示エリア ===
        self.setup_chat_area(layout)
        
        # === 下部: 入力エリア ===
        self.setup_input_area(layout)
        
        # === 右側: 設定パネル ===
        self.setup_settings_panel()
    
    def setup_header_area(self, layout):
        """ヘッダーエリア構築"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        # モデル選択
        model_group = QGroupBox("モデル選択")
        model_layout = QHBoxLayout(model_group)
        
        # プロバイダー選択
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([p.value for p in self.available_providers])
        self.provider_combo.setMinimumWidth(120)
        model_layout.addWidget(QLabel("プロバイダー:"))
        model_layout.addWidget(self.provider_combo)
        
        # モデル選択
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        model_layout.addWidget(QLabel("モデル:"))
        model_layout.addWidget(self.model_combo)
        
        # 更新ボタン
        self.refresh_models_btn = QPushButton("更新")
        self.refresh_models_btn.setMaximumWidth(60)
        model_layout.addWidget(self.refresh_models_btn)
        
        header_layout.addWidget(model_group)
        
        # 接続状態表示
        status_group = QGroupBox("接続状態")
        status_layout = QHBoxLayout(status_group)
        
        self.status_label = QLabel("未接続")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        self.connect_btn = QPushButton("接続")
        self.connect_btn.setMaximumWidth(60)
        status_layout.addWidget(self.connect_btn)
        
        header_layout.addWidget(status_group)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        header_layout.addWidget(self.progress_bar)
        
        header_layout.addStretch()
        layout.addWidget(header_frame)
    
    def setup_chat_area(self, layout):
        """チャット表示エリア構築"""
        # スプリッター作成
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === 左側: チャット表示 ===
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        
        # チャット履歴表示
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        self.chat_display.setMinimumHeight(400)
        
        # チャット表示のスタイル設定
        self.setup_chat_display_style()
        
        chat_layout.addWidget(QLabel("チャット履歴"))
        chat_layout.addWidget(self.chat_display)
        
        # === 右側: 設定パネル ===
        settings_widget = self.create_settings_widget()
        
        # スプリッターに追加
        splitter.addWidget(chat_widget)
        splitter.addWidget(settings_widget)
        splitter.setSizes([700, 300])  # 7:3の比率
        
        layout.addWidget(splitter)
    
    def setup_input_area(self, layout):
        """入力エリア構築"""
        input_frame = QFrame()
        input_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        input_layout = QVBoxLayout(input_frame)
        
        # 入力フィールド
        input_row = QHBoxLayout()
        
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(100)
        self.input_field.setPlaceholderText("メッセージを入力してください... (Ctrl+Enter で送信)")
        self.input_field.setFont(QFont("Consolas", 10))
        
        input_row.addWidget(self.input_field)
        
        # ボタン群
        button_layout = QVBoxLayout()
        
        self.send_btn = QPushButton("送信")
        self.send_btn.setMinimumHeight(40)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.setMinimumHeight(30)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        self.clear_btn = QPushButton("クリア")
        self.clear_btn.setMinimumHeight(30)
        
        button_layout.addWidget(self.send_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        input_row.addLayout(button_layout)
        input_layout.addLayout(input_row)
        
        # ツールバー
        toolbar_layout = QHBoxLayout()
        
        # ファイル添付ボタン
        self.attach_file_btn = QToolButton()
        self.attach_file_btn.setText("📎")
        self.attach_file_btn.setToolTip("ファイル添付")
        
        # プロンプトテンプレートボタン
        self.template_btn = QToolButton()
        self.template_btn.setText("📝")
        self.template_btn.setToolTip("プロンプトテンプレート")
        
        # 履歴保存ボタン
        self.save_history_btn = QToolButton()
        self.save_history_btn.setText("💾")
        self.save_history_btn.setToolTip("履歴保存")
        
        toolbar_layout.addWidget(self.attach_file_btn)
        toolbar_layout.addWidget(self.template_btn)
        toolbar_layout.addWidget(self.save_history_btn)
        toolbar_layout.addStretch()
        
        # 統計情報
        self.stats_label = QLabel("メッセージ: 0 | トークン: 0")
        self.stats_label.setStyleSheet("color: gray; font-size: 10px;")
        toolbar_layout.addWidget(self.stats_label)
        
        input_layout.addLayout(toolbar_layout)
        layout.addWidget(input_frame)
    
    def create_settings_widget(self) -> QWidget:
        """設定ウィジェット作成"""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # タブウィジェット
        tab_widget = QTabWidget()
        
        # === パラメータータブ ===
        params_tab = QWidget()
        params_layout = QVBoxLayout(params_tab)
        
        # Temperature
        temp_group = QGroupBox("Temperature")
        temp_layout = QHBoxLayout(temp_group)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        self.temperature_spin.setDecimals(1)
        temp_layout.addWidget(self.temperature_spin)
        params_layout.addWidget(temp_group)
        
        # Max Tokens
        tokens_group = QGroupBox("Max Tokens")
        tokens_layout = QHBoxLayout(tokens_group)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 8192)
        self.max_tokens_spin.setValue(2048)
        tokens_layout.addWidget(self.max_tokens_spin)
        params_layout.addWidget(tokens_group)
        
        # Top P
        top_p_group = QGroupBox("Top P")
        top_p_layout = QHBoxLayout(top_p_group)
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.1)
        self.top_p_spin.setValue(1.0)
        self.top_p_spin.setDecimals(1)
        top_p_layout.addWidget(self.top_p_spin)
        params_layout.addWidget(top_p_group)
        
        # システムプロンプト
        system_group = QGroupBox("システムプロンプト")
        system_layout = QVBoxLayout(system_group)
        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setMaximumHeight(100)
        self.system_prompt_edit.setPlaceholderText("システムプロンプトを入力...")
        system_layout.addWidget(self.system_prompt_edit)
        params_layout.addWidget(system_group)
        
        params_layout.addStretch()
        tab_widget.addTab(params_tab, "パラメータ")
        
        # === 履歴タブ ===
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        
        self.history_list = QListWidget()
        history_layout.addWidget(QLabel("会話履歴"))
        history_layout.addWidget(self.history_list)
        
        history_btn_layout = QHBoxLayout()
        self.load_history_btn = QPushButton("読込")
        self.export_history_btn = QPushButton("エクスポート")
        history_btn_layout.addWidget(self.load_history_btn)
        history_btn_layout.addWidget(self.export_history_btn)
        history_layout.addLayout(history_btn_layout)
        
        tab_widget.addTab(history_tab, "履歴")
        
        settings_layout.addWidget(tab_widget)
        return settings_widget
    
    def setup_chat_display_style(self):
        """チャット表示のスタイル設定"""
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                line-height: 1.4;
            }
        """)
    
    def setup_connections(self):
        """シグナル・スロット接続"""
        # ボタン接続
        self.send_btn.clicked.connect(self.send_message)
        self.cancel_btn.clicked.connect(self.cancel_request)
        self.clear_btn.clicked.connect(self.clear_chat)
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.refresh_models_btn.clicked.connect(self.refresh_models)
        
        # コンボボックス接続
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        
        # 入力フィールド接続
        self.input_field.textChanged.connect(self.on_input_changed)
        
        # パラメータ変更接続
        self.temperature_spin.valueChanged.connect(self.on_config_changed)
        self.max_tokens_spin.valueChanged.connect(self.on_config_changed)
        self.top_p_spin.valueChanged.connect(self.on_config_changed)
        self.system_prompt_edit.textChanged.connect(self.on_config_changed)
        
        # ツールボタン接続
        self.attach_file_btn.clicked.connect(self.attach_file)
        self.template_btn.clicked.connect(self.show_templates)
        self.save_history_btn.clicked.connect(self.save_history)
        
        # 履歴関連
        self.load_history_btn.clicked.connect(self.load_history)
        self.export_history_btn.clicked.connect(self.export_history)
        
        # キーボードショートカット
        self.input_field.installEventFilter(self)
    
    def setup_event_handlers(self):
        """イベントハンドラー設定"""
        self.event_system.subscribe('llm_status_changed', self.on_llm_status_changed)
        self.event_system.subscribe('llm_model_changed', self.on_llm_model_changed)
        self.event_system.subscribe('llm_request_completed', self.on_llm_request_completed)
    
    def load_chat_settings(self):
        """チャット設定読み込み"""
        try:
            # パラメータ設定
            self.temperature_spin.setValue(self.chat_config.get('temperature', 0.7))
            self.max_tokens_spin.setValue(self.chat_config.get('max_tokens', 2048))
            self.top_p_spin.setValue(self.chat_config.get('top_p', 1.0))
            
            # システムプロンプト
            system_prompt = self.chat_config.get('system_prompt', '')
            self.system_prompt_edit.setPlainText(system_prompt)
            
            # モデル選択
            preferred_provider = self.chat_config.get('preferred_provider', '')
            if preferred_provider:
                index = self.provider_combo.findText(preferred_provider)
                if index >= 0:
                    self.provider_combo.setCurrentIndex(index)
            
            logger.info("チャット設定読み込み完了")
            
        except Exception as e:
            logger.error(f"チャット設定読み込みエラー: {e}")
    
    def update_ui_state(self):
        """UI状態更新"""
        try:
            # 接続状態確認
            is_connected = (self.llm_client and 
                          self.llm_client.is_available())
            
            # 状態表示更新
            if is_connected:
                self.status_label.setText("接続済み")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.connect_btn.setText("切断")
            else:
                self.status_label.setText("未接続")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
                self.connect_btn.setText("接続")
            
            # ボタン状態更新
            self.send_btn.setEnabled(is_connected and not self.is_processing)
            self.cancel_btn.setVisible(self.is_processing)
            
            # モデル情報更新
            if is_connected and self.llm_client:
                model_info = self.llm_client.get_model_info()
                current_model = model_info.get('model', 'Unknown')
                
                # モデルコンボボックス更新
                current_index = self.model_combo.findText(current_model)
                if current_index >= 0:
                    self.model_combo.setCurrentIndex(current_index)
            
            # 統計情報更新
            self.update_stats()
            
        except Exception as e:
            logger.error(f"UI状態更新エラー: {e}")
    
    def update_stats(self):
        """統計情報更新"""
        try:
            message_count = len(self.conversation_history)
            
            # トークン数概算
            total_tokens = 0
            for msg in self.conversation_history:
                # 簡易トークン計算 (実際の計算はより複雑)
                total_tokens += len(msg.content.split()) * 1.3
            
            self.stats_label.setText(
                f"メッセージ: {message_count} | トークン: {int(total_tokens)}"
            )
            
        except Exception as e:
            logger.error(f"統計更新エラー: {e}")
    
    def refresh_models(self):
        """モデル一覧更新"""
        try:
            current_provider = self.provider_combo.currentText()
            if not current_provider:
                return
            
            self.model_combo.clear()
            
            if self.llm_client:
                try:
                    # プロバイダー固有のモデル取得
                    available_models = self.llm_client.get_available_models()
                    self.model_combo.addItems(available_models)
                    logger.info(f"{current_provider} モデル一覧更新完了: {len(available_models)}個")
                except Exception as e:
                    logger.warning(f"モデル一覧取得失敗: {e}")
                    # デフォルトモデル追加
                    default_models = self.get_default_models(current_provider)
                    self.model_combo.addItems(default_models)
            
        except Exception as e:
            logger.error(f"モデル更新エラー: {e}")
    
    def get_default_models(self, provider: str) -> List[str]:
        """デフォルトモデル一覧取得"""
        defaults = {
            'openai': ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo'],
            'claude': ['claude-3-sonnet', 'claude-3-haiku', 'claude-3-opus'],
            'local': ['llama2', 'codellama', 'mistral']
        }
        return defaults.get(provider, ['default'])
    
    def send_message(self):
        """メッセージ送信"""
        try:
            if self.is_processing:
                return
            
            message_text = self.input_field.toPlainText().strip()
            if not message_text:
                return
            
            if not self.llm_client or not self.llm_client.is_available():
                QMessageBox.warning(self, "警告", "LLMクライアントが接続されていません")
                return
            
            # ユーザーメッセージ追加
            user_message = LLMMessage(role=LLMRole.USER, content=message_text)
            self.conversation_history.append(user_message)
            
            # チャット表示更新
            self.append_message("User", message_text, "#007bff")
            
            # 入力フィールドクリア
            self.input_field.clear()
            
            # リクエスト実行
            self.execute_llm_request()
            
            # シグナル発火
            self.message_sent.emit(message_text)
            
        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            QMessageBox.critical(self, "エラー", f"メッセージ送信に失敗しました: {e}")
    
    def execute_llm_request(self):
        """LLMリクエスト実行"""
        try:
            # 処理状態設定
            self.is_processing = True
            self.update_ui_state()
            
            # プログレスバー表示
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # システムプロンプト追加
            messages = []
            system_prompt = self.system_prompt_edit.toPlainText().strip()
            if system_prompt:
                messages.append(LLMMessage(role=LLMRole.SYSTEM, content=system_prompt))
            
            # 会話履歴追加
            messages.extend(self.conversation_history)
            
            # リクエスト設定
            config = {
                'temperature': self.temperature_spin.value(),
                'max_tokens': self.max_tokens_spin.value(),
                'top_p': self.top_p_spin.value()
            }
            
            # リクエストスレッド作成・実行
            self.current_request_thread = LLMRequestThread(
                self.llm_client, messages, config
            )
            
            # スレッドシグナル接続
            self.current_request_thread.response_received.connect(self.on_response_received)
            self.current_request_thread.error_occurred.connect(self.on_request_error)
            self.current_request_thread.progress_updated.connect(self.progress_bar.setValue)
            self.current_request_thread.finished.connect(self.on_request_finished)
            
            # スレッド開始
            self.current_request_thread.start()
            
            logger.info("LLMリクエスト開始")
            
        except Exception as e:
            logger.error(f"LLMリクエスト実行エラー: {e}")
            self.on_request_error(str(e))
    
    def on_response_received(self, response: str):
        """レスポンス受信処理"""
        try:
            # アシスタントメッセージ追加
            assistant_message = LLMMessage(role=LLMRole.ASSISTANT, content=response)
            self.conversation_history.append(assistant_message)
            
            # チャット表示更新
            self.append_message("Assistant", response, "#28a745")
            
            # シグナル発火
            self.response_received.emit(response)
            
            logger.info(f"レスポンス受信完了: {len(response)}文字")
            
        except Exception as e:
            logger.error(f"レスポンス処理エラー: {e}")
    
    def on_request_error(self, error: str):
        """リクエストエラー処理"""
        self.append_message("System", f"エラー: {error}", "#dc3545")
        QMessageBox.critical(self, "LLMエラー", f"リクエストでエラーが発生しました:\n{error}")
        logger.error(f"LLMリクエストエラー: {error}")
    
    def on_request_finished(self):
        """リクエスト完了処理"""
        try:
            # 処理状態リセット
            self.is_processing = False
            self.current_request_thread = None
            
            # UI状態更新
            self.update_ui_state()
            
            # プログレスバー非表示
            self.progress_bar.setVisible(False)
            
            # 統計情報更新
            self.update_stats()
            
            logger.info("LLMリクエスト完了")
            
        except Exception as e:
            logger.error(f"リクエスト完了処理エラー: {e}")
    
    def cancel_request(self):
        """リクエストキャンセル"""
        try:
            if self.current_request_thread and self.current_request_thread.isRunning():
                self.current_request_thread.cancel()
                self.current_request_thread.quit()
                self.current_request_thread.wait(3000)  # 3秒待機
                
                self.append_message("System", "リクエストがキャンセルされました", "#ffc107")
                logger.info("LLMリクエストキャンセル")
            
            self.on_request_finished()
            
        except Exception as e:
            logger.error(f"リクエストキャンセルエラー: {e}")
    
    def append_message(self, sender: str, message: str, color: str = "#000000"):
        """チャット表示にメッセージ追加"""
        try:
            cursor = self.chat_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            
            # タイムスタンプ
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # 送信者名フォーマット
            sender_format = QTextCharFormat()
            sender_format.setForeground(QColor(color))
            sender_format.setFontWeight(QFont.Weight.Bold)
            
            # メッセージフォーマット
            message_format = QTextCharFormat()
            message_format.setForeground(QColor("#333333"))
            
            # タイムスタンプフォーマット
            timestamp_format = QTextCharFormat()
            timestamp_format.setForeground(QColor("#888888"))
            timestamp_format.setFontPointSize(8)
            
            # メッセージ挿入
            cursor.insertText(f"\n[{timestamp}] ", timestamp_format)
            cursor.insertText(f"{sender}: ", sender_format)
            cursor.insertText(f"{message}\n", message_format)
            
            # スクロール
            self.chat_display.setTextCursor(cursor)
            self.chat_display.ensureCursorVisible()
            
        except Exception as e:
            logger.error(f"メッセージ追加エラー: {e}")
    
    def clear_chat(self):
        """チャットクリア"""
        try:
            reply = QMessageBox.question(
                self, "確認", 
                "チャット履歴をクリアしますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.chat_display.clear()
                self.conversation_history.clear()
                self.update_stats()
                logger.info("チャット履歴クリア")
        
        except Exception as e:
            logger.error(f"チャットクリアエラー: {e}")
    
    def toggle_connection(self):
        """接続切り替え"""
        try:
            if self.llm_client and self.llm_client.is_available():
                # 切断
                self.disconnect_llm()
            else:
                # 接続
                self.connect_llm()
            
        except Exception as e:
            logger.error(f"接続切り替えエラー: {e}")
            QMessageBox.critical(self, "エラー", f"接続処理でエラーが発生しました: {e}")
    
    def connect_llm(self):
        """LLM接続"""
        try:
            current_provider = self.provider_combo.currentText()
            current_model = self.model_combo.currentText()
            
            if not current_provider:
                QMessageBox.warning(self, "警告", "プロバイダーを選択してください")
                return
            
            # LLM設定作成
            llm_config = LLMConfig(
                model=current_model or 'default',
                temperature=self.temperature_spin.value(),
                max_tokens=self.max_tokens_spin.value(),
                timeout=30.0,
                retry_count=3
            )
            
            # クライアント作成
            self.llm_client = create_llm_client(current_provider, llm_config)
            
            if self.llm_client and self.llm_client.is_available():
                self.append_message("System", f"{current_provider} に接続しました", "#28a745")
                logger.info(f"LLM接続成功: {current_provider}")
                
                # モデル一覧更新
                self.refresh_models()
            else:
                raise Exception("クライアント作成に失敗しました")
            
            self.update_ui_state()
            
        except Exception as e:
            logger.error(f"LLM接続エラー: {e}")
            self.append_message("System", f"接続エラー: {e}", "#dc3545")
            QMessageBox.critical(self, "接続エラー", f"LLMへの接続に失敗しました:\n{e}")
    
    def disconnect_llm(self):
        """LLM切断"""
        try:
            if self.llm_client:
                # 実行中のリクエストキャンセル
                if self.is_processing:
                    self.cancel_request()
                
                # クライアント切断
                if hasattr(self.llm_client, '__exit__'):
                    self.llm_client.__exit__(None, None, None)
                
                self.llm_client = None
                self.append_message("System", "LLMから切断しました", "#ffc107")
                logger.info("LLM切断完了")
            
            self.update_ui_state()
            
        except Exception as e:
            logger.error(f"LLM切断エラー: {e}")
    
    def on_provider_changed(self, provider: str):
        """プロバイダー変更処理"""
        try:
            logger.info(f"プロバイダー変更: {provider}")
            
            # 現在の接続を切断
            if self.llm_client:
                self.disconnect_llm()
            
            # モデル一覧クリア
            self.model_combo.clear()
            
            # デフォルトモデル設定
            default_models = self.get_default_models(provider)
            self.model_combo.addItems(default_models)
            
            # 設定保存
            self.chat_config['preferred_provider'] = provider
            self.save_chat_settings()
            
        except Exception as e:
            logger.error(f"プロバイダー変更エラー: {e}")
    
    def on_model_changed(self, model: str):
        """モデル変更処理"""
        try:
            if model:
                logger.info(f"モデル変更: {model}")
                self.model_changed.emit(model)
                
                # 設定保存
                self.chat_config['preferred_model'] = model
                self.save_chat_settings()
        
        except Exception as e:
            logger.error(f"モデル変更エラー: {e}")
    
    def on_input_changed(self):
        """入力変更処理"""
        try:
            # 送信ボタン状態更新
            has_text = bool(self.input_field.toPlainText().strip())
            is_connected = self.llm_client and self.llm_client.is_available()
            self.send_btn.setEnabled(has_text and is_connected and not self.is_processing)
            
        except Exception as e:
            logger.error(f"入力変更処理エラー: {e}")
    
    def on_config_changed(self):
        """設定変更処理"""
        try:
            # 設定保存
            self.save_chat_settings()
            
            # 設定変更シグナル発火
            config = {
                'temperature': self.temperature_spin.value(),
                'max_tokens': self.max_tokens_spin.value(),
                'top_p': self.top_p_spin.value(),
                'system_prompt': self.system_prompt_edit.toPlainText()
            }
            self.config_changed.emit(config)
            
        except Exception as e:
            logger.error(f"設定変更処理エラー: {e}")
    
    def save_chat_settings(self):
        """チャット設定保存"""
        try:
            self.chat_config.update({
                'temperature': self.temperature_spin.value(),
                'max_tokens': self.max_tokens_spin.value(),
                'top_p': self.top_p_spin.value(),
                'system_prompt': self.system_prompt_edit.toPlainText(),
                'preferred_provider': self.provider_combo.currentText(),
                'preferred_model': self.model_combo.currentText()
            })
            
            self.config_manager.set_section('chat', self.chat_config)
            self.config_manager.save_config()
            
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def attach_file(self):
        """ファイル添付"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "ファイル選択", "",
                "テキストファイル (*.txt *.py *.js *.html *.css *.json *.xml);;すべてのファイル (*)"
            )
            
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # ファイル内容を入力フィールドに追加
                    current_text = self.input_field.toPlainText()
                    file_content = f"\n\n--- {Path(file_path).name} ---\n{content}\n--- ファイル終了 ---"
                    
                    self.input_field.setPlainText(current_text + file_content)
                    logger.info(f"ファイル添付完了: {file_path}")
                    
                except Exception as e:
                    QMessageBox.warning(self, "警告", f"ファイル読み込みエラー: {e}")
        
        except Exception as e:
            logger.error(f"ファイル添付エラー: {e}")
    
    def show_templates(self):
        """プロンプトテンプレート表示"""
        try:
            # テンプレートメニュー作成
            menu = QMenu(self)
            
            templates = {
                "コード解説": "以下のコードについて詳しく解説してください：\n\n",
                "バグ修正": "以下のコードのバグを見つけて修正してください：\n\n",
                "リファクタリング": "以下のコードをより良い形にリファクタリングしてください：\n\n",
                "テスト作成": "以下のコードのユニットテストを作成してください：\n\n",
                "ドキュメント作成": "以下のコードのドキュメントを作成してください：\n\n"
            }
            
            for name, template in templates.items():
                action = QAction(name, self)
                action.triggered.connect(lambda checked, t=template: self.apply_template(t))
                menu.addAction(action)
            
            # メニュー表示
            menu.exec(self.template_btn.mapToGlobal(self.template_btn.rect().bottomLeft()))
            
        except Exception as e:
            logger.error(f"テンプレート表示エラー: {e}")
    
    def apply_template(self, template: str):
        """テンプレート適用"""
        try:
            current_text = self.input_field.toPlainText()
            self.input_field.setPlainText(current_text + template)
            self.input_field.setFocus()
            
        except Exception as e:
            logger.error(f"テンプレート適用エラー: {e}")
    
    def save_history(self):
        """履歴保存"""
        try:
            if not self.conversation_history:
                QMessageBox.information(self, "情報", "保存する履歴がありません")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "履歴保存", 
                f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON (*.json);;テキスト (*.txt)"
            )
            
            if file_path:
                if file_path.endswith('.json'):
                    # JSON形式で保存
                    history_data = {
                        'timestamp': datetime.now().isoformat(),
                        'messages': [
                            {
                                'role': msg.role.value,
                                'content': msg.content,
                                'timestamp': getattr(msg, 'timestamp', None)
                            }
                            for msg in self.conversation_history
                        ]
                    }
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(history_data, f, ensure_ascii=False, indent=2)
                else:
                    # テキスト形式で保存
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(f"チャット履歴 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("=" * 50 + "\n\n")
                        
                        for msg in self.conversation_history:
                            f.write(f"[{msg.role.value.upper()}]\n")
                            f.write(f"{msg.content}\n\n")
                
                QMessageBox.information(self, "完了", f"履歴を保存しました:\n{file_path}")
                logger.info(f"履歴保存完了: {file_path}")
        
        except Exception as e:
            logger.error(f"履歴保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"履歴保存に失敗しました: {e}")
    
    def load_history(self):
        """履歴読み込み"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "履歴読み込み", "",
                "JSON (*.json);;すべてのファイル (*)"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                # 履歴クリア確認
                if self.conversation_history:
                    reply = QMessageBox.question(
                        self, "確認",
                        "現在の履歴をクリアして読み込みますか？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.clear_chat()
                
                # 履歴復元
                for msg_data in history_data.get('messages', []):
                    role = LLMRole(msg_data['role'])
                    content = msg_data['content']
                    
                    message = LLMMessage(role=role, content=content)
                    self.conversation_history.append(message)
                    
                    # チャット表示に追加
                    role_name = "User" if role == LLMRole.USER else "Assistant"
                    color = "#007bff" if role == LLMRole.USER else "#28a745"
                    self.append_message(role_name, content, color)
                
                self.update_stats()
                QMessageBox.information(self, "完了", "履歴を読み込みました")
                logger.info(f"履歴読み込み完了: {file_path}")
        
        except Exception as e:
            logger.error(f"履歴読み込みエラー: {e}")
            QMessageBox.critical(self, "エラー", f"履歴読み込みに失敗しました: {e}")
    
    def export_history(self):
        """履歴エクスポート"""
        try:
            if not self.conversation_history:
                QMessageBox.information(self, "情報", "エクスポートする履歴がありません")
                return
            
            # エクスポート形式選択
            formats = ["Markdown (*.md)", "HTML (*.html)", "CSV (*.csv)"]
            format_choice, ok = QInputDialog.getItem(
                self, "エクスポート形式", "形式を選択してください:", formats, 0, False
            )
            
            if not ok:
                return
            
            # ファイル保存ダイアログ
            file_path, _ = QFileDialog.getSaveFileName(
                self, "履歴エクスポート",
                f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                format_choice
            )
            
            if file_path:
                if format_choice.startswith("Markdown"):
                    self.export_as_markdown(file_path)
                elif format_choice.startswith("HTML"):
                    self.export_as_html(file_path)
                elif format_choice.startswith("CSV"):
                    self.export_as_csv(file_path)
                
                QMessageBox.information(self, "完了", f"履歴をエクスポートしました:\n{file_path}")
                logger.info(f"履歴エクスポート完了: {file_path}")
        
        except Exception as e:
            logger.error(f"履歴エクスポートエラー: {e}")
            QMessageBox.critical(self, "エラー", f"履歴エクスポートに失敗しました: {e}")
    
    def export_as_markdown(self, file_path: str):
        """Markdown形式でエクスポート"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# チャット履歴\n\n")
            f.write(f"**日時:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for i, msg in enumerate(self.conversation_history, 1):
                role_name = "👤 User" if msg.role == LLMRole.USER else "🤖 Assistant"
                f.write(f"## {i}. {role_name}\n\n")
                f.write(f"{msg.content}\n\n")
                f.write("---\n\n")
    
    def export_as_html(self, file_path: str):
        """HTML形式でエクスポート"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>チャット履歴</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .user { background-color: #e3f2fd; }
        .assistant { background-color: #f1f8e9; }
        .role { font-weight: bold; margin-bottom: 5px; }
    </style>
</head>
<body>
""")
            f.write(f"<h1>チャット履歴</h1>\n")
            f.write(f"<p><strong>日時:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
            
            for msg in self.conversation_history:
                css_class = "user" if msg.role == LLMRole.USER else "assistant"
                role_name = "👤 User" if msg.role == LLMRole.USER else "🤖 Assistant"
                
                f.write(f'<div class="message {css_class}">\n')
                f.write(f'<div class="role">{role_name}</div>\n')
                f.write(f'<div>{msg.content.replace(chr(10), "<br>")}</div>\n')
                f.write(f'</div>\n')
            
            f.write("</body></html>")
    
    def export_as_csv(self, file_path: str):
        """CSV形式でエクスポート"""
        import csv
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['No', 'Role', 'Content', 'Length'])
            
            for i, msg in enumerate(self.conversation_history, 1):
                writer.writerow([
                    i,
                    msg.role.value,
                    msg.content,
                    len(msg.content)
                ])
    
    # イベントハンドラー
    def on_llm_status_changed(self, event: Event):
        """LLM状態変更イベント処理"""
        try:
            data = event.data
            status = data.get('new_status', 'unknown')
            
            if status == 'connected':
                self.append_message("System", "LLM接続が確立されました", "#28a745")
            elif status == 'disconnected':
                self.append_message("System", "LLM接続が切断されました", "#ffc107")
            elif status == 'error':
                error_msg = data.get('error', '不明なエラー')
                self.append_message("System", f"LLMエラー: {error_msg}", "#dc3545")
            
            self.update_ui_state()
            
        except Exception as e:
            logger.error(f"LLM状態変更処理エラー: {e}")
    
    def on_llm_model_changed(self, event: Event):
        """LLMモデル変更イベント処理"""
        try:
            data = event.data
            new_model = data.get('new_model', 'unknown')
            
            # モデルコンボボックス更新
            index = self.model_combo.findText(new_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            
            self.append_message("System", f"モデルが変更されました: {new_model}", "#17a2b8")
            
        except Exception as e:
            logger.error(f"モデル変更処理エラー: {e}")
    
    def on_llm_request_completed(self, event: Event):
        """LLMリクエスト完了イベント処理"""
        try:
            data = event.data
            success = data.get('success', False)
            tokens = data.get('tokens', 0)
            response_time = data.get('response_time', 0)
            
            if success:
                logger.debug(f"リクエスト完了: {tokens}トークン, {response_time:.2f}秒")
            
        except Exception as e:
            logger.error(f"リクエスト完了処理エラー: {e}")
    
    def eventFilter(self, obj, event):
        """イベントフィルター (キーボードショートカット)"""
        if obj == self.input_field and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.send_message()
                return True
        
        return super().eventFilter(obj, event)
    
    def closeEvent(self, event):
        """ウィンドウクローズイベント"""
        try:
            # 実行中のリクエストキャンセル
            if self.is_processing:
                self.cancel_request()
            
            # 設定保存
            self.save_chat_settings()
            
            # LLM切断
            if self.llm_client:
                self.disconnect_llm()
            
            event.accept()
            
        except Exception as e:
            logger.error(f"クローズ処理エラー: {e}")
            event.accept()

# === 使用例とテスト ===
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    # テスト用アプリケーション
    app = QApplication(sys.argv)
    
    # テスト用LLMクライアント作成
    try:
        from src.llm import create_llm_client, LLMConfig
        
        config = LLMConfig(model="gpt-3.5-turbo", temperature=0.7)
        test_client = create_llm_client("openai", config)
        
        # チャットパネル作成
        chat_panel = LLMChatPanel(llm_client=test_client)
        chat_panel.show()
        
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        
        # LLMクライアントなしでテスト
        chat_panel = LLMChatPanel()
        chat_panel.show()
        
        sys.exit(app.exec())
