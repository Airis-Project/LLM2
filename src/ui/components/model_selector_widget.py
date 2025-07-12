"""
モデル選択ウィジェットモジュール
PyQt6を使用したLLMモデル選択コンポーネント
"""

import sys
from typing import Dict, List, Optional, Any, Callable
import json

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
        QPushButton, QGroupBox, QSpinBox, QDoubleSpinBox,
        QSlider, QCheckBox, QTextEdit, QTabWidget, QFormLayout,
        QMessageBox, QProgressBar, QToolTip
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
    from PyQt6.QtGui import QFont, QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

from ...core.logger import get_logger
from ...core.config_manager import get_config
from ...llm.llm_factory import get_llm_factory

class ModelTestThread(QThread):
    """モデル接続テスト用スレッド"""
    
    test_completed = pyqtSignal(bool, str)  # 成功/失敗, メッセージ
    
    def __init__(self, model_config: Dict):
        super().__init__()
        self.model_config = model_config
        self.logger = get_logger(self.__class__.__name__)
    
    def run(self):
        """テストを実行"""
        try:
            factory = get_llm_factory()
            llm = factory.create_llm(self.model_config)
            
            # 簡単なテストメッセージを送信
            test_message = "Hello, this is a connection test."
            response = llm.generate_response(test_message)
            
            if response and len(response.strip()) > 0:
                self.test_completed.emit(True, "接続テスト成功")
            else:
                self.test_completed.emit(False, "レスポンスが空です")
                
        except Exception as e:
            self.test_completed.emit(False, f"接続エラー: {str(e)}")

class ModelSelector(QWidget):
    """モデル選択ウィジェット"""
    
    # シグナル定義
    model_changed = pyqtSignal(dict)  # モデル設定が変更された時
    model_tested = pyqtSignal(bool, str)  # モデルテストが完了した時
    
    def __init__(self, parent=None):
        """
        初期化
        
        Args:
            parent: 親ウィジェット
        """
        if not PYQT6_AVAILABLE:
            raise ImportError("PyQt6が利用できません")
        
        super().__init__(parent)
        
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.llm_factory = get_llm_factory()
        
        # 現在の設定
        self.current_config = {}
        self.available_models = {}
        self.test_thread = None
        
        # UI要素
        self.provider_combo = None
        self.model_combo = None
        self.api_key_edit = None
        self.base_url_edit = None
        self.temperature_slider = None
        self.max_tokens_spin = None
        self.top_p_spin = None
        self.frequency_penalty_spin = None
        self.presence_penalty_spin = None
        self.test_button = None
        self.test_progress = None
        
        self._setup_ui()
        self._load_available_models()
        self._load_current_config()
        
        self.logger.debug("ModelSelector初期化完了")
    
    def _setup_ui(self):
        """UIを設定"""
        try:
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # タイトル
            title_label = QLabel("LLMモデル設定")
            title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            main_layout.addWidget(title_label)
            
            # タブウィジェット
            tab_widget = QTabWidget()
            main_layout.addWidget(tab_widget)
            
            # 基本設定タブ
            basic_tab = self._create_basic_tab()
            tab_widget.addTab(basic_tab, "基本設定")
            
            # 詳細設定タブ
            advanced_tab = self._create_advanced_tab()
            tab_widget.addTab(advanced_tab, "詳細設定")
            
            # テストボタンとプログレスバー
            test_layout = QHBoxLayout()
            
            self.test_button = QPushButton("接続テスト")
            self.test_button.clicked.connect(self._test_connection)
            test_layout.addWidget(self.test_button)
            
            self.test_progress = QProgressBar()
            self.test_progress.setVisible(False)
            test_layout.addWidget(self.test_progress)
            
            test_layout.addStretch()
            
            main_layout.addLayout(test_layout)
            
        except Exception as e:
            self.logger.error(f"UI設定エラー: {e}")
            raise
    
    def _create_basic_tab(self) -> QWidget:
        """基本設定タブを作成"""
        try:
            tab = QWidget()
            layout = QFormLayout(tab)
            layout.setSpacing(10)
            
            # プロバイダー選択
            self.provider_combo = QComboBox()
            self.provider_combo.addItems(["OpenAI", "Anthropic", "Google", "Local", "Other"])
            self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
            layout.addRow("プロバイダー:", self.provider_combo)
            
            # モデル選択
            self.model_combo = QComboBox()
            self.model_combo.setEditable(True)
            self.model_combo.currentTextChanged.connect(self._on_model_changed)
            layout.addRow("モデル:", self.model_combo)
            
            # APIキー
            self.api_key_edit = QTextEdit()
            self.api_key_edit.setMaximumHeight(60)
            self.api_key_edit.setPlaceholderText("APIキーを入力してください")
            self.api_key_edit.textChanged.connect(self._on_config_changed)
            layout.addRow("APIキー:", self.api_key_edit)
            
            # ベースURL
            self.base_url_edit = QTextEdit()
            self.base_url_edit.setMaximumHeight(40)
            self.base_url_edit.setPlaceholderText("ベースURL（オプション）")
            self.base_url_edit.textChanged.connect(self._on_config_changed)
            layout.addRow("ベースURL:", self.base_url_edit)
            
            return tab
            
        except Exception as e:
            self.logger.error(f"基本設定タブ作成エラー: {e}")
            raise
    
    def _create_advanced_tab(self) -> QWidget:
        """詳細設定タブを作成"""
        try:
            tab = QWidget()
            layout = QFormLayout(tab)
            layout.setSpacing(10)
            
            # Temperature
            temp_layout = QHBoxLayout()
            self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
            self.temperature_slider.setRange(0, 200)  # 0.0 - 2.0
            self.temperature_slider.setValue(70)  # 0.7
            self.temperature_slider.valueChanged.connect(self._on_temperature_changed)
            
            self.temperature_label = QLabel("0.70")
            self.temperature_label.setMinimumWidth(40)
            
            temp_layout.addWidget(self.temperature_slider)
            temp_layout.addWidget(self.temperature_label)
            layout.addRow("Temperature:", temp_layout)
            
            # Max Tokens
            self.max_tokens_spin = QSpinBox()
            self.max_tokens_spin.setRange(1, 32000)
            self.max_tokens_spin.setValue(2000)
            self.max_tokens_spin.valueChanged.connect(self._on_config_changed)
            layout.addRow("Max Tokens:", self.max_tokens_spin)
            
            # Top P
            self.top_p_spin = QDoubleSpinBox()
            self.top_p_spin.setRange(0.0, 1.0)
            self.top_p_spin.setSingleStep(0.1)
            self.top_p_spin.setValue(1.0)
            self.top_p_spin.valueChanged.connect(self._on_config_changed)
            layout.addRow("Top P:", self.top_p_spin)
            
            # Frequency Penalty
            self.frequency_penalty_spin = QDoubleSpinBox()
            self.frequency_penalty_spin.setRange(-2.0, 2.0)
            self.frequency_penalty_spin.setSingleStep(0.1)
            self.frequency_penalty_spin.setValue(0.0)
            self.frequency_penalty_spin.valueChanged.connect(self._on_config_changed)
            layout.addRow("Frequency Penalty:", self.frequency_penalty_spin)
            
            # Presence Penalty
            self.presence_penalty_spin = QDoubleSpinBox()
            self.presence_penalty_spin.setRange(-2.0, 2.0)
            self.presence_penalty_spin.setSingleStep(0.1)
            self.presence_penalty_spin.setValue(0.0)
            self.presence_penalty_spin.valueChanged.connect(self._on_config_changed)
            layout.addRow("Presence Penalty:", self.presence_penalty_spin)
            
            # ストリーミング
            self.streaming_checkbox = QCheckBox("ストリーミング有効")
            self.streaming_checkbox.setChecked(True)
            self.streaming_checkbox.toggled.connect(self._on_config_changed)
            layout.addRow("", self.streaming_checkbox)
            
            return tab
            
        except Exception as e:
            self.logger.error(f"詳細設定タブ作成エラー: {e}")
            raise
    
    def _load_available_models(self):
        """利用可能なモデルを読み込み"""
        try:
            self.available_models = {
                "OpenAI": [
                    "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
                    "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
                ],
                "Anthropic": [
                    "claude-3-opus-20240229", "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307", "claude-2.1", "claude-2.0"
                ],
                "Google": [
                    "gemini-pro", "gemini-pro-vision", "gemini-1.5-pro"
                ],
                "Local": [
                    "llama2-7b", "llama2-13b", "codellama-7b", "mistral-7b"
                ],
                "Other": []
            }
            
            self.logger.debug("利用可能なモデルを読み込みました")
            
        except Exception as e:
            self.logger.error(f"モデル読み込みエラー: {e}")
    
    def _load_current_config(self):
        """現在の設定を読み込み"""
        try:
            # 設定から現在のLLM設定を取得
            llm_config = self.config.get('llm', {})
            
            # プロバイダー設定
            provider = llm_config.get('provider', 'OpenAI')
            if provider in ["openai", "OpenAI"]:
                provider = "OpenAI"
            elif provider in ["anthropic", "Anthropic"]:
                provider = "Anthropic"
            elif provider in ["google", "Google"]:
                provider = "Google"
            
            provider_index = self.provider_combo.findText(provider)
            if provider_index >= 0:
                self.provider_combo.setCurrentIndex(provider_index)
            
            # モデル設定
            model = llm_config.get('model', '')
            if model:
                self.model_combo.setCurrentText(model)
            
            # APIキー
            api_key = llm_config.get('api_key', '')
            if api_key:
                self.api_key_edit.setPlainText(api_key)
            
            # ベースURL
            base_url = llm_config.get('base_url', '')
            if base_url:
                self.base_url_edit.setPlainText(base_url)
            
            # 詳細設定
            temperature = llm_config.get('temperature', 0.7)
            self.temperature_slider.setValue(int(temperature * 100))
            
            max_tokens = llm_config.get('max_tokens', 2000)
            self.max_tokens_spin.setValue(max_tokens)
            
            top_p = llm_config.get('top_p', 1.0)
            self.top_p_spin.setValue(top_p)
            
            frequency_penalty = llm_config.get('frequency_penalty', 0.0)
            self.frequency_penalty_spin.setValue(frequency_penalty)
            
            presence_penalty = llm_config.get('presence_penalty', 0.0)
            self.presence_penalty_spin.setValue(presence_penalty)
            
            streaming = llm_config.get('streaming', True)
            self.streaming_checkbox.setChecked(streaming)
            
            # 現在の設定を保存
            self.current_config = self._get_current_config()
            
            self.logger.debug("現在の設定を読み込みました")
            
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {e}")
    
    def _on_provider_changed(self, provider: str):
        """プロバイダー変更時の処理"""
        try:
            # モデル選択肢を更新
            self.model_combo.clear()
            if provider in self.available_models:
                self.model_combo.addItems(self.available_models[provider])
            
            # プロバイダーに応じたデフォルト設定
            if provider == "OpenAI":
                self.base_url_edit.setPlainText("https://api.openai.com/v1")
                if self.model_combo.count() > 0:
                    self.model_combo.setCurrentText("gpt-3.5-turbo")
            elif provider == "Anthropic":
                self.base_url_edit.setPlainText("https://api.anthropic.com")
                if self.model_combo.count() > 0:
                    self.model_combo.setCurrentText("claude-3-sonnet-20240229")
            elif provider == "Google":
                self.base_url_edit.setPlainText("")
                if self.model_combo.count() > 0:
                    self.model_combo.setCurrentText("gemini-pro")
            elif provider == "Local":
                self.base_url_edit.setPlainText("http://localhost:8080")
                self.api_key_edit.setPlainText("")
            
            self._on_config_changed()
            
        except Exception as e:
            self.logger.error(f"プロバイダー変更エラー: {e}")
    
    def _on_model_changed(self, model: str):
        """モデル変更時の処理"""
        try:
            # モデルに応じた推奨設定
            if "gpt-4" in model.lower():
                self.max_tokens_spin.setValue(4000)
            elif "claude-3" in model.lower():
                self.max_tokens_spin.setValue(4000)
            elif "gemini" in model.lower():
                self.max_tokens_spin.setValue(2048)
            
            self._on_config_changed()
            
        except Exception as e:
            self.logger.error(f"モデル変更エラー: {e}")
    
    def _on_temperature_changed(self, value: int):
        """Temperature変更時の処理"""
        try:
            temp_value = value / 100.0
            self.temperature_label.setText(f"{temp_value:.2f}")
            self._on_config_changed()
            
        except Exception as e:
            self.logger.error(f"Temperature変更エラー: {e}")
    
    def _on_config_changed(self):
        """設定変更時の処理"""
        try:
            new_config = self._get_current_config()
            
            # 設定が実際に変更された場合のみシグナルを発行
            if new_config != self.current_config:
                self.current_config = new_config
                self.model_changed.emit(new_config)
                
                # 設定を保存
                self._save_config(new_config)
                
        except Exception as e:
            self.logger.error(f"設定変更処理エラー: {e}")
    
    def _get_current_config(self) -> Dict[str, Any]:
        """現在の設定を取得"""
        try:
            return {
                'provider': self.provider_combo.currentText(),
                'model': self.model_combo.currentText(),
                'api_key': self.api_key_edit.toPlainText().strip(),
                'base_url': self.base_url_edit.toPlainText().strip(),
                'temperature': self.temperature_slider.value() / 100.0,
                'max_tokens': self.max_tokens_spin.value(),
                'top_p': self.top_p_spin.value(),
                'frequency_penalty': self.frequency_penalty_spin.value(),
                'presence_penalty': self.presence_penalty_spin.value(),
                'streaming': self.streaming_checkbox.isChecked()
            }
            
        except Exception as e:
            self.logger.error(f"設定取得エラー: {e}")
            return {}
    
    def _save_config(self, config: Dict[str, Any]):
        """設定を保存"""
        try:
            # 設定管理に保存
            self.config.set('llm', config)
            self.config.save()
            
            self.logger.debug("設定を保存しました")
            
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
    
    def _test_connection(self):
        """接続テストを実行"""
        try:
            if self.test_thread and self.test_thread.isRunning():
                return
            
            config = self._get_current_config()
            
            # 必須設定のチェック
            if not config.get('model'):
                QMessageBox.warning(self, "エラー", "モデルを選択してください")
                return
            
            if config.get('provider') != 'Local' and not config.get('api_key'):
                QMessageBox.warning(self, "エラー", "APIキーを入力してください")
                return
            
            # テスト開始
            self.test_button.setEnabled(False)
            self.test_progress.setVisible(True)
            self.test_progress.setRange(0, 0)  # 無限プログレスバー
            
            # テストスレッドを開始
            self.test_thread = ModelTestThread(config)
            self.test_thread.test_completed.connect(self._on_test_completed)
            self.test_thread.start()
            
            self.logger.debug("接続テストを開始しました")
            
        except Exception as e:
            self.logger.error(f"接続テストエラー: {e}")
            self._on_test_completed(False, f"テスト開始エラー: {e}")
    
    def _on_test_completed(self, success: bool, message: str):
        """テスト完了時の処理"""
        try:
            # UI状態を戻す
            self.test_button.setEnabled(True)
            self.test_progress.setVisible(False)
            
            # 結果を表示
            if success:
                QMessageBox.information(self, "テスト結果", f"✓ {message}")
                QToolTip.showText(
                    self.test_button.mapToGlobal(self.test_button.rect().center()),
                    "接続成功",
                    self.test_button
                )
            else:
                QMessageBox.warning(self, "テスト結果", f"✗ {message}")
            
            # シグナルを発行
            self.model_tested.emit(success, message)
            
            self.logger.debug(f"接続テスト完了: {success}, {message}")
            
        except Exception as e:
            self.logger.error(f"テスト完了処理エラー: {e}")
    
    def get_current_config(self) -> Dict[str, Any]:
        """現在の設定を取得（外部用）"""
        return self.current_config.copy()
    
    def set_config(self, config: Dict[str, Any]):
        """設定を適用（外部用）"""
        try:
            # プロバイダー
            if 'provider' in config:
                provider_index = self.provider_combo.findText(config['provider'])
                if provider_index >= 0:
                    self.provider_combo.setCurrentIndex(provider_index)
            
            # モデル
            if 'model' in config:
                self.model_combo.setCurrentText(config['model'])
            
            # APIキー
            if 'api_key' in config:
                self.api_key_edit.setPlainText(config['api_key'])
            
            # ベースURL
            if 'base_url' in config:
                self.base_url_edit.setPlainText(config['base_url'])
            
            # 詳細設定
            if 'temperature' in config:
                self.temperature_slider.setValue(int(config['temperature'] * 100))
            
            if 'max_tokens' in config:
                self.max_tokens_spin.setValue(config['max_tokens'])
            
            if 'top_p' in config:
                self.top_p_spin.setValue(config['top_p'])
            
            if 'frequency_penalty' in config:
                self.frequency_penalty_spin.setValue(config['frequency_penalty'])
            
            if 'presence_penalty' in config:
                self.presence_penalty_spin.setValue(config['presence_penalty'])
            
            if 'streaming' in config:
                self.streaming_checkbox.setChecked(config['streaming'])
            
            self.logger.debug("設定を適用しました")
            
        except Exception as e:
            self.logger.error(f"設定適用エラー: {e}")
    
    def reset_to_defaults(self):
        """デフォルト設定にリセット"""
        try:
            default_config = {
                'provider': 'OpenAI',
                'model': 'gpt-3.5-turbo',
                'api_key': '',
                'base_url': 'https://api.openai.com/v1',
                'temperature': 0.7,
                'max_tokens': 2000,
                'top_p': 1.0,
                'frequency_penalty': 0.0,
                'presence_penalty': 0.0,
                'streaming': True
            }
            
            self.set_config(default_config)
            self.logger.debug("デフォルト設定にリセットしました")
            
        except Exception as e:
            self.logger.error(f"デフォルトリセットエラー: {e}")
    
    def add_custom_model(self, provider: str, model: str):
        """カスタムモデルを追加"""
        try:
            if provider not in self.available_models:
                self.available_models[provider] = []
            
            if model not in self.available_models[provider]:
                self.available_models[provider].append(model)
                
                # 現在のプロバイダーと一致する場合はコンボボックスを更新
                if self.provider_combo.currentText() == provider:
                    self.model_combo.addItem(model)
            
            self.logger.debug(f"カスタムモデルを追加: {provider}/{model}")
            
        except Exception as e:
            self.logger.error(f"カスタムモデル追加エラー: {e}")

