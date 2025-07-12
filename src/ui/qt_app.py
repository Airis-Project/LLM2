# src/ui/qt_app.py
"""
Qt アプリケーション管理システム
PyQt6ベースのGUIアプリケーション統合管理
"""

import sys
import os
import signal
import threading
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from contextlib import contextmanager
from enum import Enum, auto
import traceback
import webbrowser
from concurrent.futures import ThreadPoolExecutor

# PyQt6 imports
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QTextEdit, QLabel, QPushButton, QProgressBar,
        QStatusBar, QMenuBar, QMenu, QAction, QSystemTrayIcon,
        QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
        QLineEdit, QSpinBox, QCheckBox, QComboBox, QGroupBox,
        QSplitter, QTreeWidget, QTreeWidgetItem, QTableWidget,
        QTableWidgetItem, QHeaderView, QFrame, QScrollArea,
        QToolBar, QFileDialog, QInputDialog
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QThread, pyqtSignal, QObject, QSize,
        QSettings, QStandardPaths, QUrl, QMimeData, QEvent
    )
    from PyQt6.QtGui import (
        QIcon, QPixmap, QFont, QColor, QPalette, QAction,
        QKeySequence, QClipboard, QDesktopServices, QPainter,
        QBrush, QPen, QPolygon, QLinearGradient
    )
    PYQT_AVAILABLE = True
except ImportError as e:
    PYQT_AVAILABLE = False
    PyQt6_import_error = str(e)

from src.core.logger import get_logger
from src.core.config_manager import get_config_manager
from src.core.exceptions import UIError, ConfigurationError, SystemError
from src.core.event_system import get_event_system, Event
from src.utils.system_utils import get_system_utils
from src.utils.performance_monitor import get_performance_monitor
from src.ui.chat_interface import get_chat_interface

logger = get_logger(__name__)


class AppTheme(Enum):
    """アプリケーションテーマ"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class WindowState(Enum):
    """ウィンドウ状態"""
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"
    HIDDEN = "hidden"


@dataclass
class UIConfig:
    """UI設定"""
    theme: AppTheme = AppTheme.AUTO
    window_width: int = 1200
    window_height: int = 800
    window_x: int = 100
    window_y: int = 100
    window_state: WindowState = WindowState.NORMAL
    enable_system_tray: bool = True
    enable_notifications: bool = True
    auto_save_interval: int = 300  # 5分
    font_family: str = "Segoe UI"
    font_size: int = 10
    show_performance_monitor: bool = True
    show_debug_console: bool = False
    language: str = "ja"
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で返す"""
        return {
            'theme': self.theme.value,
            'window_width': self.window_width,
            'window_height': self.window_height,
            'window_x': self.window_x,
            'window_y': self.window_y,
            'window_state': self.window_state.value,
            'enable_system_tray': self.enable_system_tray,
            'enable_notifications': self.enable_notifications,
            'auto_save_interval': self.auto_save_interval,
            'font_family': self.font_family,
            'font_size': self.font_size,
            'show_performance_monitor': self.show_performance_monitor,
            'show_debug_console': self.show_debug_console,
            'language': self.language
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIConfig':
        """辞書からインスタンス作成"""
        return cls(
            theme=AppTheme(data.get('theme', AppTheme.AUTO.value)),
            window_width=data.get('window_width', 1200),
            window_height=data.get('window_height', 800),
            window_x=data.get('window_x', 100),
            window_y=data.get('window_y', 100),
            window_state=WindowState(data.get('window_state', WindowState.NORMAL.value)),
            enable_system_tray=data.get('enable_system_tray', True),
            enable_notifications=data.get('enable_notifications', True),
            auto_save_interval=data.get('auto_save_interval', 300),
            font_family=data.get('font_family', 'Segoe UI'),
            font_size=data.get('font_size', 10),
            show_performance_monitor=data.get('show_performance_monitor', True),
            show_debug_console=data.get('show_debug_console', False),
            language=data.get('language', 'ja')
        )


class PerformanceWidget(QWidget):
    """パフォーマンス監視ウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(self.__class__.__name__)
        self.performance_monitor = get_performance_monitor()
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # タイトル
        title = QLabel("システムパフォーマンス")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # CPU使用率
        self.cpu_label = QLabel("CPU: 0%")
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.cpu_progress)
        
        # メモリ使用率
        self.memory_label = QLabel("メモリ: 0%")
        self.memory_progress = QProgressBar()
        self.memory_progress.setRange(0, 100)
        layout.addWidget(self.memory_label)
        layout.addWidget(self.memory_progress)
        
        # ディスク使用率
        self.disk_label = QLabel("ディスク: 0%")
        self.disk_progress = QProgressBar()
        self.disk_progress.setRange(0, 100)
        layout.addWidget(self.disk_label)
        layout.addWidget(self.disk_progress)
        
        # アラート表示
        self.alert_label = QLabel("アラート: なし")
        self.alert_label.setStyleSheet("color: green;")
        layout.addWidget(self.alert_label)
        
        # 詳細ボタン
        self.detail_button = QPushButton("詳細表示")
        self.detail_button.clicked.connect(self.show_details)
        layout.addWidget(self.detail_button)
    
    def setup_timer(self):
        """タイマー設定"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_performance)
        self.timer.start(2000)  # 2秒間隔
    
    def update_performance(self):
        """パフォーマンス更新"""
        try:
            # 最新メトリクス取得
            cpu_metrics = self.performance_monitor.get_metrics("cpu_percent", limit=1)
            memory_metrics = self.performance_monitor.get_metrics("memory_percent", limit=1)
            disk_metrics = self.performance_monitor.get_metrics("disk_usage_percent", limit=1)
            
            # CPU更新
            if cpu_metrics:
                cpu_value = int(cpu_metrics[0].value)
                self.cpu_label.setText(f"CPU: {cpu_value}%")
                self.cpu_progress.setValue(cpu_value)
                self.cpu_progress.setStyleSheet(self._get_progress_style(cpu_value))
            
            # メモリ更新
            if memory_metrics:
                memory_value = int(memory_metrics[0].value)
                self.memory_label.setText(f"メモリ: {memory_value}%")
                self.memory_progress.setValue(memory_value)
                self.memory_progress.setStyleSheet(self._get_progress_style(memory_value))
            
            # ディスク更新
            if disk_metrics:
                disk_value = int(disk_metrics[0].value)
                self.disk_label.setText(f"ディスク: {disk_value}%")
                self.disk_progress.setValue(disk_value)
                self.disk_progress.setStyleSheet(self._get_progress_style(disk_value))
            
            # アラート更新
            active_alerts = self.performance_monitor.get_alerts(resolved=False)
            if active_alerts:
                critical_count = len([a for a in active_alerts if a.level.value in ['critical', 'emergency']])
                if critical_count > 0:
                    self.alert_label.setText(f"アラート: {critical_count}件の重要なアラート")
                    self.alert_label.setStyleSheet("color: red; font-weight: bold;")
                else:
                    self.alert_label.setText(f"アラート: {len(active_alerts)}件")
                    self.alert_label.setStyleSheet("color: orange;")
            else:
                self.alert_label.setText("アラート: なし")
                self.alert_label.setStyleSheet("color: green;")
                
        except Exception as e:
            self.logger.error(f"パフォーマンス更新エラー: {e}")
    
    def _get_progress_style(self, value: int) -> str:
        """プログレスバーのスタイル取得"""
        if value >= 90:
            return "QProgressBar::chunk { background-color: #ff4444; }"
        elif value >= 70:
            return "QProgressBar::chunk { background-color: #ffaa00; }"
        else:
            return "QProgressBar::chunk { background-color: #44ff44; }"
    
    def show_details(self):
        """詳細表示"""
        try:
            # 詳細ダイアログ作成
            dialog = QDialog(self)
            dialog.setWindowTitle("パフォーマンス詳細")
            dialog.setModal(True)
            dialog.resize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            # 詳細情報表示
            details_text = QTextEdit()
            details_text.setReadOnly(True)
            
            # ダッシュボードデータ取得
            dashboard_data = self.performance_monitor.create_dashboard_data()
            details_text.setPlainText(json.dumps(dashboard_data, ensure_ascii=False, indent=2))
            
            layout.addWidget(details_text)
            
            # 閉じるボタン
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.exec()
            
        except Exception as e:
            self.logger.error(f"詳細表示エラー: {e}")
            QMessageBox.warning(self, "エラー", f"詳細表示に失敗しました: {e}")


class LogWidget(QWidget):
    """ログ表示ウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(self.__class__.__name__)
        self.setup_ui()
        self.setup_log_handler()
    
    def setup_ui(self):
        """UI設定"""
        layout = QVBoxLayout(self)
        
        # コントロール
        control_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("クリア")
        self.clear_button.clicked.connect(self.clear_logs)
        control_layout.addWidget(self.clear_button)
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_logs)
        control_layout.addWidget(self.save_button)
        
        control_layout.addStretch()
        
        # ログレベルフィルタ
        self.level_combo = QComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.currentTextChanged.connect(self.filter_logs)
        control_layout.addWidget(QLabel("レベル:"))
        control_layout.addWidget(self.level_combo)
        
        layout.addLayout(control_layout)
        
        # ログ表示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)
        
        # ログ履歴
        self.log_entries = []
        self.max_entries = 1000
    
    def setup_log_handler(self):
        """ログハンドラー設定"""
        # カスタムログハンドラーを追加してGUIに表示
        # 実装は簡略化
        pass
    
    def add_log_entry(self, level: str, message: str, timestamp: datetime = None):
        """ログエントリ追加"""
        if timestamp is None:
            timestamp = datetime.now()
        
        entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message
        }
        
        self.log_entries.append(entry)
        
        # 最大エントリ数制限
        if len(self.log_entries) > self.max_entries:
            self.log_entries = self.log_entries[-self.max_entries:]
        
        self.update_display()
    
    def update_display(self):
        """表示更新"""
        current_level = self.level_combo.currentText()
        
        filtered_entries = self.log_entries
        if current_level != "ALL":
            filtered_entries = [e for e in self.log_entries if e['level'] == current_level]
        
        # 最新100件のみ表示
        display_entries = filtered_entries[-100:]
        
        text_lines = []
        for entry in display_entries:
            timestamp_str = entry['timestamp'].strftime("%H:%M:%S")
            level_str = entry['level'].ljust(8)
            text_lines.append(f"[{timestamp_str}] {level_str} {entry['message']}")
        
        self.log_text.setPlainText('\n'.join(text_lines))
        
        # 最下部にスクロール
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_logs(self):
        """ログクリア"""
        self.log_entries.clear()
        self.log_text.clear()
    
    def save_logs(self):
        """ログ保存"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "ログファイル保存", 
                f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Text Files (*.txt);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for entry in self.log_entries:
                        timestamp_str = entry['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"[{timestamp_str}] {entry['level']} {entry['message']}\n")
                
                QMessageBox.information(self, "保存完了", f"ログファイルを保存しました:\n{file_path}")
                
        except Exception as e:
            self.logger.error(f"ログ保存エラー: {e}")
            QMessageBox.warning(self, "エラー", f"ログ保存に失敗しました: {e}")
    
    def filter_logs(self):
        """ログフィルタ"""
        self.update_display()


class MainWindow(QMainWindow):
    """メインウィンドウ"""
    
    def __init__(self, qt_app_manager):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.qt_app_manager = qt_app_manager
        self.config = qt_app_manager.ui_config
        
        # コンポーネント参照
        self.config_manager = get_config_manager()
        self.event_system = get_event_system()
        self.system_utils = get_system_utils()
        self.performance_monitor = get_performance_monitor()
        
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.setup_system_tray()
        self.apply_theme()
        self.restore_window_state()
        
        # イベント接続
        self.setup_event_handlers()
        
        self.logger.info("メインウィンドウ初期化完了")
    
    def setup_ui(self):
        """UI設定"""
        self.setWindowTitle("LLM統合システム")
        self.setMinimumSize(800, 600)
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QHBoxLayout(central_widget)
        
        # スプリッター
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左パネル（チャット）
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右パネル（監視・ログ）
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # スプリッター比率設定
        splitter.setSizes([800, 400])
    
    def create_left_panel(self) -> QWidget:
        """左パネル作成"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # チャットインターフェース
        try:
            chat_interface = get_chat_interface()
            if hasattr(chat_interface, 'create_qt_widget'):
                chat_widget = chat_interface.create_qt_widget()
                layout.addWidget(chat_widget)
            else:
                # フォールバック: シンプルなチャット表示
                chat_placeholder = QTextEdit()
                chat_placeholder.setPlaceholderText("チャットインターフェースを読み込み中...")
                chat_placeholder.setReadOnly(True)
                layout.addWidget(chat_placeholder)
        except Exception as e:
            self.logger.error(f"チャットインターフェース作成エラー: {e}")
            error_label = QLabel(f"チャットインターフェースの読み込みに失敗しました: {e}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """右パネル作成"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # タブウィジェット
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # パフォーマンス監視タブ
        if self.config.show_performance_monitor:
            performance_widget = PerformanceWidget()
            tab_widget.addTab(performance_widget, "パフォーマンス")
        
        # ログタブ
        self.log_widget = LogWidget()
        tab_widget.addTab(self.log_widget, "ログ")
        
        # システム情報タブ
        system_info_widget = self.create_system_info_widget()
        tab_widget.addTab(system_info_widget, "システム情報")
        
        # 設定タブ
        settings_widget = self.create_settings_widget()
        tab_widget.addTab(settings_widget, "設定")
        
        return panel
    
    def create_system_info_widget(self) -> QWidget:
        """システム情報ウィジェット作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 更新ボタン
        refresh_button = QPushButton("情報更新")
        layout.addWidget(refresh_button)
        
        # システム情報表示
        self.system_info_text = QTextEdit()
        self.system_info_text.setReadOnly(True)
        self.system_info_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.system_info_text)
        
        # 初期情報表示
        refresh_button.clicked.connect(self.update_system_info)
        self.update_system_info()
        
        return widget
    
    def create_settings_widget(self) -> QWidget:
        """設定ウィジェット作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # スクロールエリア
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QFormLayout(scroll_widget)
        
        # テーマ設定
        theme_group = QGroupBox("外観設定")
        theme_layout = QFormLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["auto", "light", "dark"])
        self.theme_combo.setCurrentText(self.config.theme.value)
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addRow("テーマ:", self.theme_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 20)
        self.font_size_spin.setValue(self.config.font_size)
        self.font_size_spin.valueChanged.connect(self.change_font_size)
        theme_layout.addRow("フォントサイズ:", self.font_size_spin)
        
        scroll_layout.addWidget(theme_group)
        
        # 監視設定
        monitor_group = QGroupBox("監視設定")
        monitor_layout = QFormLayout(monitor_group)
        
        self.enable_performance_check = QCheckBox()
        self.enable_performance_check.setChecked(self.config.show_performance_monitor)
        self.enable_performance_check.toggled.connect(self.toggle_performance_monitor)
        monitor_layout.addRow("パフォーマンス監視:", self.enable_performance_check)
        
        self.enable_notifications_check = QCheckBox()
        self.enable_notifications_check.setChecked(self.config.enable_notifications)
        self.enable_notifications_check.toggled.connect(self.toggle_notifications)
        monitor_layout.addRow("通知:", self.enable_notifications_check)
        
        scroll_layout.addWidget(monitor_group)
        
        # 保存ボタン
        save_button = QPushButton("設定保存")
        save_button.clicked.connect(self.save_settings)
        scroll_layout.addWidget(save_button)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def setup_menu(self):
        """メニュー設定"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル(&F)")
        
        # 設定
        settings_action = QAction("設定(&S)", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # 終了
        exit_action = QAction("終了(&X)", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 表示メニュー
        view_menu = menubar.addMenu("表示(&V)")
        
        # パフォーマンス監視
        self.performance_action = QAction("パフォーマンス監視", self)
        self.performance_action.setCheckable(True)
        self.performance_action.setChecked(self.config.show_performance_monitor)
        self.performance_action.toggled.connect(self.toggle_performance_monitor)
        view_menu.addAction(self.performance_action)
        
        # デバッグコンソール
        self.debug_action = QAction("デバッグコンソール", self)
        self.debug_action.setCheckable(True)
        self.debug_action.setChecked(self.config.show_debug_console)
        self.debug_action.toggled.connect(self.toggle_debug_console)
        view_menu.addAction(self.debug_action)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu("ヘルプ(&H)")
        
        # バージョン情報
        about_action = QAction("バージョン情報(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_status_bar(self):
        """ステータスバー設定"""
        self.status_bar = self.statusBar()
        
        # ステータスラベル
        self.status_label = QLabel("準備完了")
        self.status_bar.addWidget(self.status_label)
        
        # パフォーマンス表示
        self.performance_label = QLabel("CPU: 0% | メモリ: 0%")
        self.status_bar.addPermanentWidget(self.performance_label)
        
        # 時刻表示
        self.time_label = QLabel()
        self.status_bar.addPermanentWidget(self.time_label)
        
        # ステータス更新タイマー
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # 5秒間隔
        
        self.update_status()
    
    def setup_system_tray(self):
        """システムトレイ設定"""
        if not self.config.enable_system_tray or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        try:
            self.tray_icon = QSystemTrayIcon(self)
            
            # アイコン設定（デフォルトアイコン使用）
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
            
            # コンテキストメニュー
            tray_menu = QMenu()
            
            show_action = QAction("表示", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)
            
            hide_action = QAction("非表示", self)
            hide_action.triggered.connect(self.hide)
            tray_menu.addAction(hide_action)
            
            tray_menu.addSeparator()
            
            quit_action = QAction("終了", self)
            quit_action.triggered.connect(self.close)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            
            # ダブルクリックで表示/非表示
            self.tray_icon.activated.connect(self.tray_icon_activated)
            
            self.tray_icon.show()
            
        except Exception as e:
            self.logger.error(f"システムトレイ設定エラー: {e}")
    
    def setup_event_handlers(self):
        """イベントハンドラー設定"""
        # パフォーマンスアラートイベント
        self.event_system.subscribe("performance_alert_created", self.on_performance_alert)
        
        # システムイベント
        self.event_system.subscribe("system_shutdown", self.on_system_shutdown)
        
        # 設定変更イベント
        self.event_system.subscribe("config_changed", self.on_config_changed)
    
    def apply_theme(self):
        """テーマ適用"""
        try:
            theme = self.config.theme
            
            if theme == AppTheme.DARK:
                self.setStyleSheet(self._get_dark_theme_style())
            elif theme == AppTheme.LIGHT:
                self.setStyleSheet(self._get_light_theme_style())
            else:  # AUTO
                # システムのダークモード設定に従う
                palette = QApplication.palette()
                if palette.color(QPalette.ColorRole.Window).lightness() < 128:
                    self.setStyleSheet(self._get_dark_theme_style())
                else:
                    self.setStyleSheet(self._get_light_theme_style())
            
            # フォント設定
            font = QFont(self.config.font_family, self.config.font_size)
            self.setFont(font)
            
        except Exception as e:
            self.logger.error(f"テーマ適用エラー: {e}")
    
    def _get_dark_theme_style(self) -> str:
        """ダークテーマスタイル"""
        return """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #3c3c3c;
        }
        QTabBar::tab {
            background-color: #555555;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #0078d4;
        }
        QPushButton {
            background-color: #0078d4;
            color: #ffffff;
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QTextEdit, QLineEdit {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 4px;
        }
        QProgressBar {
            border: 1px solid #555555;
            border-radius: 3px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 2px;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555555;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        """
    
    def _get_light_theme_style(self) -> str:
        """ライトテーマスタイル"""
        return """
        QMainWindow {
            background-color: #ffffff;
            color: #000000;
        }
        QWidget {
            background-color: #ffffff;
            color: #000000;
        }
        QTabWidget::pane {
            border: 1px solid #cccccc;
            background-color: #f8f8f8;
        }
        QTabBar::tab {
            background-color: #e1e1e1;
            color: #000000;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        QPushButton {
            background-color: #0078d4;
            color: #ffffff;
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QTextEdit, QLineEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 4px;
        }
        QProgressBar {
            border: 1px solid #cccccc;
            border-radius: 3px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 2px;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        """
    
    def restore_window_state(self):
        """ウィンドウ状態復元"""
        try:
            self.resize(self.config.window_width, self.config.window_height)
            self.move(self.config.window_x, self.config.window_y)
            
            if self.config.window_state == WindowState.MAXIMIZED:
                self.showMaximized()
            elif self.config.window_state == WindowState.MINIMIZED:
                self.showMinimized()
            elif self.config.window_state == WindowState.FULLSCREEN:
                self.showFullScreen()
            else:
                self.showNormal()
                
        except Exception as e:
            self.logger.error(f"ウィンドウ状態復元エラー: {e}")
    
    def save_window_state(self):
        """ウィンドウ状態保存"""
        try:
            if self.isMaximized():
                self.config.window_state = WindowState.MAXIMIZED
            elif self.isMinimized():
                self.config.window_state = WindowState.MINIMIZED
            elif self.isFullScreen():
                self.config.window_state = WindowState.FULLSCREEN
            else:
                self.config.window_state = WindowState.NORMAL
                self.config.window_width = self.width()
                self.config.window_height = self.height()
                self.config.window_x = self.x()
                self.config.window_y = self.y()
            
            # 設定保存
            self.qt_app_manager.save_ui_config()
            
        except Exception as e:
            self.logger.error(f"ウィンドウ状態保存エラー: {e}")
    
    def update_status(self):
        """ステータス更新"""
        try:
            # 時刻更新
            current_time = datetime.now().strftime("%H:%M:%S")
            self.time_label.setText(current_time)
            
            # パフォーマンス更新
            cpu_metrics = self.performance_monitor.get_metrics("cpu_percent", limit=1)
            memory_metrics = self.performance_monitor.get_metrics("memory_percent", limit=1)
            
            cpu_value = int(cpu_metrics[0].value) if cpu_metrics else 0
            memory_value = int(memory_metrics[0].value) if memory_metrics else 0
            
            self.performance_label.setText(f"CPU: {cpu_value}% | メモリ: {memory_value}%")
            
        except Exception as e:
            self.logger.debug(f"ステータス更新エラー: {e}")
    
    def update_system_info(self):
        """システム情報更新"""
        try:
            system_info = self.system_utils.get_system_info()
            resource_usage = self.system_utils.get_resource_usage()
            
            info_text = f"""
システム情報:
OS: {system_info.os_name} {system_info.os_version}
アーキテクチャ: {system_info.architecture}
プロセッサ: {system_info.processor}
物理コア数: {system_info.cpu_cores_physical}
論理コア数: {system_info.cpu_cores_logical}
総メモリ: {system_info.total_memory / (1024**3):.2f} GB
ディスク容量: {system_info.disk_total / (1024**3):.2f} GB

現在のリソース使用状況:
CPU使用率: {resource_usage.cpu_percent:.1f}%
メモリ使用率: {resource_usage.memory_percent:.1f}%
メモリ使用量: {resource_usage.memory_used / (1024**3):.2f} GB
メモリ利用可能: {resource_usage.memory_available / (1024**3):.2f} GB
ディスク使用率: {resource_usage.disk_usage_percent:.1f}%
ネットワーク送信: {resource_usage.network_sent_bytes / (1024**2):.2f} MB
ネットワーク受信: {resource_usage.network_recv_bytes / (1024**2):.2f} MB

更新時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            self.system_info_text.setPlainText(info_text.strip())
            
        except Exception as e:
            self.logger.error(f"システム情報更新エラー: {e}")
            self.system_info_text.setPlainText(f"システム情報の取得に失敗しました: {e}")
    
    def change_theme(self, theme_name: str):
        """テーマ変更"""
        try:
            self.config.theme = AppTheme(theme_name)
            self.apply_theme()
            self.qt_app_manager.save_ui_config()
        except Exception as e:
            self.logger.error(f"テーマ変更エラー: {e}")
    
    def change_font_size(self, size: int):
        """フォントサイズ変更"""
        try:
            self.config.font_size = size
            self.apply_theme()
            self.qt_app_manager.save_ui_config()
        except Exception as e:
            self.logger.error(f"フォントサイズ変更エラー: {e}")
    
    def toggle_performance_monitor(self, enabled: bool):
        """パフォーマンス監視切り替え"""
        self.config.show_performance_monitor = enabled
        self.qt_app_manager.save_ui_config()
        # UI再構築が必要な場合の処理
    
    def toggle_notifications(self, enabled: bool):
        """通知切り替え"""
        self.config.enable_notifications = enabled
        self.qt_app_manager.save_ui_config()
    
    def toggle_debug_console(self, enabled: bool):
        """デバッグコンソール切り替え"""
        self.config.show_debug_console = enabled
        self.qt_app_manager.save_ui_config()
    
    def save_settings(self):
        """設定保存"""
        try:
            self.qt_app_manager.save_ui_config()
            QMessageBox.information(self, "設定保存", "設定を保存しました。")
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
            QMessageBox.warning(self, "エラー", f"設定保存に失敗しました: {e}")
    
    def show_settings(self):
        """設定ダイアログ表示"""
        # 設定タブにフォーカス
        try:
            # 右パネルのタブウィジェットを取得して設定タブを選択
            central_widget = self.centralWidget()
            splitter = central_widget.findChild(QSplitter)
            if splitter:
                right_panel = splitter.widget(1)
                tab_widget = right_panel.findChild(QTabWidget)
                if tab_widget:
                    # 設定タブのインデックスを探す
                    for i in range(tab_widget.count()):
                        if tab_widget.tabText(i) == "設定":
                            tab_widget.setCurrentIndex(i)
                            break
        except Exception as e:
            self.logger.error(f"設定表示エラー: {e}")
    
    def show_about(self):
        """バージョン情報表示"""
        try:
            about_text = f"""
LLM統合システム

バージョン: 1.0.0
Python: {sys.version}
PyQt6: {getattr(sys.modules.get('PyQt6.QtCore'), 'PYQT_VERSION_STR', 'Unknown')}

開発者: AI Assistant
ライセンス: MIT License

このソフトウェアは、大規模言語モデルとの
統合インターフェースを提供します。
"""
            QMessageBox.about(self, "バージョン情報", about_text.strip())
            
        except Exception as e:
            self.logger.error(f"バージョン情報表示エラー: {e}")
    
    def tray_icon_activated(self, reason):
        """システムトレイアイコンクリック処理"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
    
    def on_performance_alert(self, event: Event):
        """パフォーマンスアラート処理"""
        try:
            if not self.config.enable_notifications:
                return
            
            alert_data = event.data
            level = alert_data.get('level', 'info')
            message = alert_data.get('message', 'パフォーマンスアラート')
            
            # システムトレイ通知
            if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
                if level in ['critical', 'emergency']:
                    icon = QSystemTrayIcon.MessageIcon.Critical
                elif level == 'warning':
                    icon = QSystemTrayIcon.MessageIcon.Warning
                else:
                    icon = QSystemTrayIcon.MessageIcon.Information
                
                self.tray_icon.showMessage("パフォーマンスアラート", message, icon, 5000)
            
            # ログウィジェットに追加
            if hasattr(self, 'log_widget'):
                self.log_widget.add_log_entry(level.upper(), message)
            
        except Exception as e:
            self.logger.error(f"パフォーマンスアラート処理エラー: {e}")
    
    def on_system_shutdown(self, event: Event):
        """システムシャットダウン処理"""
        self.close()
    
    def on_config_changed(self, event: Event):
        """設定変更処理"""
        try:
            # UI設定の再読み込み
            self.apply_theme()
        except Exception as e:
            self.logger.error(f"設定変更処理エラー: {e}")
    
    def closeEvent(self, event):
        """ウィンドウクローズイベント"""
        try:
            # システムトレイが有効で、まだ表示されている場合は非表示にする
            if (hasattr(self, 'tray_icon') and 
                self.tray_icon.isVisible() and 
                self.config.enable_system_tray):
                
                # 初回非表示時のみ通知
                if not hasattr(self, '_hide_notification_shown'):
                    self.tray_icon.showMessage(
                        "LLM統合システム",
                        "アプリケーションはシステムトレイで実行中です。",
                        QSystemTrayIcon.MessageIcon.Information,
                        3000
                    )
                    self._hide_notification_shown = True
                
                self.hide()
                event.ignore()
                return
            
            # ウィンドウ状態保存
            self.save_window_state()
            
            # アプリケーション終了
            self.qt_app_manager.shutdown()
            event.accept()
            
        except Exception as e:
            self.logger.error(f"ウィンドウクローズエラー: {e}")
            event.accept()


class QtAppManager:
    """Qt アプリケーション管理クラス"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        
        # PyQt6 可用性チェック
        if not PYQT_AVAILABLE:
            raise UIError(f"PyQt6が利用できません: {PyQt6_import_error}")
        
        # 設定管理
        self.config_manager = get_config_manager()
        self.event_system = get_event_system()
        
        # UI設定
        self.ui_config = self._load_ui_config()
        
        # Qt アプリケーション
        self.app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None
        
        # 状態管理
        self.is_running = False
        self.shutdown_requested = False
        
        # スレッド管理
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="QtApp")
        
        self.logger.info("QtAppManager初期化完了")
    
    def _load_ui_config(self) -> UIConfig:
        """UI設定読み込み"""
        try:
            config_data = self.config_manager.get_config("ui", {})
            return UIConfig.from_dict(config_data)
        except Exception as e:
            self.logger.warning(f"UI設定読み込みエラー: {e}")
            return UIConfig()
    
    def save_ui_config(self):
        """UI設定保存"""
        try:
            self.config_manager.set_config("ui", self.ui_config.to_dict())
            self.config_manager.save_config()
            self.logger.debug("UI設定保存完了")
        except Exception as e:
            self.logger.error(f"UI設定保存エラー: {e}")
    
    def initialize(self) -> bool:
        """初期化"""
        try:
            self.logger.info("Qt アプリケーション初期化開始")
            
            # Qt アプリケーション作成
            if QApplication.instance() is None:
                self.app = QApplication(sys.argv)
            else:
                self.app = QApplication.instance()
            
            # アプリケーション設定
            self.app.setApplicationName("LLM統合システム")
            self.app.setApplicationVersion("1.0.0")
            self.app.setOrganizationName("AI Assistant")
            
            # 高DPI対応
            self.app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            self.app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
            
            # システム終了シグナル処理
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # メインウィンドウ作成
            self.main_window = MainWindow(self)
            
            self.logger.info("Qt アプリケーション初期化完了")
            return True
            
        except Exception as e:
            self.logger.error(f"Qt アプリケーション初期化エラー: {e}")
            return False
    
    def run(self) -> int:
        """アプリケーション実行"""
        try:
            if not self.app or not self.main_window:
                raise UIError("アプリケーションが初期化されていません")
            
            self.logger.info("Qt アプリケーション開始")
            self.is_running = True
            
            # メインウィンドウ表示
            self.main_window.show()
            
            # イベント発行
            self.event_system.emit(Event(
                name="qt_app_started",
                data={"config": self.ui_config.to_dict()}
            ))
            
            # アプリケーションループ実行
            exit_code = self.app.exec()
            
            self.logger.info(f"Qt アプリケーション終了 (終了コード: {exit_code})")
            return exit_code
            
        except Exception as e:
            self.logger.error(f"Qt アプリケーション実行エラー: {e}")
            return 1
        finally:
            self.is_running = False
    
    def shutdown(self):
        """アプリケーション終了"""
        try:
            if self.shutdown_requested:
                return
            
            self.shutdown_requested = True
            self.logger.info("Qt アプリケーション終了処理開始")
            
            # UI設定保存
            self.save_ui_config()
            
            # イベント発行
            self.event_system.emit(Event(
                name="qt_app_shutdown",
                data={}
            ))
            
            # メインウィンドウ終了
            if self.main_window:
                self.main_window.close()
            
            # アプリケーション終了
            if self.app:
                self.app.quit()
            
            # スレッドプール終了
            self.executor.shutdown(wait=True)
            
            self.logger.info("Qt アプリケーション終了処理完了")
            
        except Exception as e:
            self.logger.error(f"Qt アプリケーション終了処理エラー: {e}")
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        self.logger.info(f"終了シグナル受信: {signum}")
        if self.app:
            self.app.quit()
    
    def show_message(self, title: str, message: str, message_type: str = "info"):
        """メッセージ表示"""
        try:
            if not self.main_window:
                return
            
            if message_type == "error":
                QMessageBox.critical(self.main_window, title, message)
            elif message_type == "warning":
                QMessageBox.warning(self.main_window, title, message)
            else:
                QMessageBox.information(self.main_window, title, message)
                
        except Exception as e:
            self.logger.error(f"メッセージ表示エラー: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """ステータス取得"""
        return {
            'is_running': self.is_running,
            'shutdown_requested': self.shutdown_requested,
            'pyqt_available': PYQT_AVAILABLE,
            'main_window_visible': self.main_window.isVisible() if self.main_window else False,
            'ui_config': self.ui_config.to_dict()
        }


# グローバルインスタンス
_qt_app_manager_instance: Optional[QtAppManager] = None


def get_qt_app_manager() -> QtAppManager:
    """QtAppManagerのシングルトンインスタンスを取得"""
    global _qt_app_manager_instance
    if _qt_app_manager_instance is None:
        _qt_app_manager_instance = QtAppManager()
    return _qt_app_manager_instance


def create_qt_app_manager() -> QtAppManager:
    """新しいQtAppManagerインスタンスを作成"""
    return QtAppManager()


# 便利関数
def is_qt_available() -> bool:
    """Qt の利用可能性チェック"""
    return PYQT_AVAILABLE


def run_qt_app() -> int:
    """Qt アプリケーション実行"""
    try:
        app_manager = get_qt_app_manager()
        if app_manager.initialize():
            return app_manager.run()
        else:
            return 1
    except Exception as e:
        logger.error(f"Qt アプリケーション実行エラー: {e}")
        return 1


def show_error_dialog(title: str, message: str):
    """エラーダイアログ表示"""
    try:
        app_manager = get_qt_app_manager()
        app_manager.show_message(title, message, "error")
    except Exception as e:
        logger.error(f"エラーダイアログ表示エラー: {e}")


# 使用例とテスト
if __name__ == "__main__":
    def test_qt_app():
        """テスト関数"""
        print("=== QtAppManager テスト ===")
        
        if not is_qt_available():
            print("PyQt6が利用できません")
            return 1
        
        try:
            # アプリケーション実行
            exit_code = run_qt_app()
            print(f"アプリケーション終了: {exit_code}")
            return exit_code
            
        except Exception as e:
            print(f"テストエラー: {e}")
            return 1
    
    # テスト実行
    sys.exit(test_qt_app())

