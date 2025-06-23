# src/ui/components/custom_widgets.py
"""
Custom Widgets - カスタムウィジェット

このモジュールは、LLM Code Assistantで使用するカスタムUIウィジェットを提供します。
再利用可能で一貫性のあるUIコンポーネントを実装し、アプリケーション全体の
ユーザーエクスペリエンスを向上させます。
"""

import os
from typing import Optional, List, Dict, Any, Callable, Union
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QProgressBar, QSlider, QSpinBox, QDoubleSpinBox, QFrame,
    QScrollArea, QSplitter, QTabWidget, QGroupBox, QButtonGroup,
    QRadioButton, QListWidget, QTreeWidget, QTableWidget,
    QFileDialog, QColorDialog, QFontDialog, QMessageBox,
    QToolButton, QMenu, QAction, QSizePolicy, QApplication
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
    QRect, QSize, QPoint, QThread, QMutex, QWaitCondition
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPainter, QPen, QBrush, QPixmap,
    QIcon, QCursor, QMovie, QFontMetrics, QPainterPath,
    QLinearGradient, QRadialGradient
)

from ...core.logger import get_logger

logger = get_logger(__name__)


class AnimatedButton(QPushButton):
    """
    アニメーション付きボタン
    
    ホバー時やクリック時にアニメーション効果を提供するカスタムボタン
    """
    
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        """
        AnimatedButtonを初期化
        
        Args:
            text: ボタンテキスト
            parent: 親ウィジェット
        """
        super().__init__(text, parent)
        
        self.animation_duration = 200
        self.hover_color = QColor(70, 130, 180)
        self.normal_color = QColor(50, 50, 50)
        self.pressed_color = QColor(30, 80, 120)
        
        self._setup_animation()
        self._setup_style()
        
        logger.debug(f"AnimatedButton created: {text}")
    
    def _setup_animation(self) -> None:
        """アニメーションのセットアップ"""
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(self.animation_duration)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def _setup_style(self) -> None:
        """スタイルのセットアップ"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.normal_color.name()};
                border: 2px solid {self.normal_color.name()};
                border-radius: 8px;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: {self.hover_color.name()};
                border-color: {self.hover_color.name()};
            }}
            QPushButton:pressed {{
                background-color: {self.pressed_color.name()};
                border-color: {self.pressed_color.name()};
            }}
            QPushButton:disabled {{
                background-color: #666666;
                border-color: #666666;
                color: #999999;
            }}
        """)
    
    def enterEvent(self, event) -> None:
        """マウスエンターイベント"""
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        super().enterEvent(event)
    
    def leaveEvent(self, event) -> None:
        """マウスリーブイベント"""
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().leaveEvent(event)


class LoadingSpinner(QWidget):
    """
    ローディングスピナー
    
    処理中を示すアニメーション付きスピナーウィジェット
    """
    
    def __init__(self, parent: Optional[QWidget] = None, size: int = 32):
        """
        LoadingSpinnerを初期化
        
        Args:
            parent: 親ウィジェット
            size: スピナーのサイズ
        """
        super().__init__(parent)
        
        self.size = size
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._rotate)
        
        self.setFixedSize(size, size)
        self._setup_style()
        
        logger.debug(f"LoadingSpinner created with size: {size}")
    
    def _setup_style(self) -> None:
        """スタイルのセットアップ"""
        self.setStyleSheet("""
            LoadingSpinner {
                background-color: transparent;
            }
        """)
    
    def start(self) -> None:
        """スピナーを開始"""
        self.timer.start(50)  # 50ms間隔で回転
        self.show()
    
    def stop(self) -> None:
        """スピナーを停止"""
        self.timer.stop()
        self.hide()
    
    def _rotate(self) -> None:
        """回転処理"""
        self.angle = (self.angle + 10) % 360
        self.update()
    
    def paintEvent(self, event) -> None:
        """描画イベント"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 中心座標
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 2
        
        # 円弧を描画
        for i in range(8):
            alpha = 255 - (i * 30)
            if alpha < 0:
                alpha = 0
            
            color = QColor(70, 130, 180, alpha)
            painter.setPen(QPen(color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            
            start_angle = (self.angle + i * 45) % 360
            painter.drawArc(
                center_x - radius, center_y - radius,
                radius * 2, radius * 2,
                start_angle * 16, 30 * 16
            )


class CollapsibleGroupBox(QGroupBox):
    """
    折りたたみ可能なグループボックス
    
    タイトルクリックで内容の表示/非表示を切り替えられるグループボックス
    """
    
    toggled = pyqtSignal(bool)  # 展開/折りたたみ状態変更シグナル
    
    def __init__(self, title: str = "", parent: Optional[QWidget] = None):
        """
        CollapsibleGroupBoxを初期化
        
        Args:
            title: グループボックスのタイトル
            parent: 親ウィジェット
        """
        super().__init__(title, parent)
        
        self.is_collapsed = False
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
        self._setup_ui()
        self._setup_style()
        
        logger.debug(f"CollapsibleGroupBox created: {title}")
    
    def _setup_ui(self) -> None:
        """UIのセットアップ"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # タイトル部分
        self.title_frame = QFrame()
        self.title_frame.setFrameStyle(QFrame.Shape.Box)
        self.title_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        title_layout = QHBoxLayout(self.title_frame)
        title_layout.setContentsMargins(10, 5, 10, 5)
        
        # 展開/折りたたみアイコン
        self.toggle_icon = QLabel("▼")
        self.toggle_icon.setFixedWidth(20)
        title_layout.addWidget(self.toggle_icon)
        
        # タイトルラベル
        self.title_label = QLabel(self.title())
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        main_layout.addWidget(self.title_frame)
        main_layout.addWidget(self.content_widget)
        
        self.setLayout(main_layout)
        
        # クリックイベント
        self.title_frame.mousePressEvent = self._toggle_collapsed
    
    def _setup_style(self) -> None:
        """スタイルのセットアップ"""
        self.setStyleSheet("""
            CollapsibleGroupBox {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 0px;
            }
            QFrame {
                background-color: #f0f0f0;
                border: none;
                border-radius: 5px;
            }
            QFrame:hover {
                background-color: #e0e0e0;
            }
        """)
    
    def _toggle_collapsed(self, event) -> None:
        """折りたたみ状態を切り替え"""
        self.is_collapsed = not self.is_collapsed
        
        if self.is_collapsed:
            self.content_widget.hide()
            self.toggle_icon.setText("▶")
        else:
            self.content_widget.show()
            self.toggle_icon.setText("▼")
        
        self.toggled.emit(not self.is_collapsed)
        
        # アニメーション
        self.animation = QPropertyAnimation(self, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        if self.is_collapsed:
            self.animation.setEndValue(self.title_frame.height())
        else:
            self.animation.setEndValue(self.sizeHint().height())
        
        self.animation.start()
    
    def addWidget(self, widget: QWidget) -> None:
        """ウィジェットを追加"""
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout) -> None:
        """レイアウトを追加"""
        self.content_layout.addLayout(layout)


class SearchableComboBox(QComboBox):
    """
    検索可能なコンボボックス
    
    入力に基づいてアイテムをフィルタリングできるコンボボックス
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        SearchableComboBoxを初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        self.all_items: List[str] = []
        self.filtered_items: List[str] = []
        
        self._setup_signals()
        
        logger.debug("SearchableComboBox created")
    
    def _setup_signals(self) -> None:
        """シグナルのセットアップ"""
        self.lineEdit().textChanged.connect(self._filter_items)
    
    def addItem(self, text: str, userData: Any = None) -> None:
        """アイテムを追加"""
        super().addItem(text, userData)
        self.all_items.append(text)
    
    def addItems(self, texts: List[str]) -> None:
        """複数のアイテムを追加"""
        super().addItems(texts)
        self.all_items.extend(texts)
    
    def _filter_items(self, text: str) -> None:
        """アイテムをフィルタリング"""
        self.clear()
        
        if not text:
            # テキストが空の場合、すべてのアイテムを表示
            super().addItems(self.all_items)
            self.filtered_items = self.all_items.copy()
        else:
            # テキストに基づいてフィルタリング
            filtered = [item for item in self.all_items 
                       if text.lower() in item.lower()]
            super().addItems(filtered)
            self.filtered_items = filtered
        
        # ドロップダウンを表示
        if self.filtered_items:
            self.showPopup()


class StatusBar(QWidget):
    """
    カスタムステータスバー
    
    アプリケーションの状態情報を表示するステータスバー
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        StatusBarを初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self._setup_ui()
        self._setup_style()
        
        # デフォルトメッセージ
        self.show_message("準備完了")
        
        logger.debug("StatusBar created")
    
    def _setup_ui(self) -> None:
        """UIのセットアップ"""
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(10)
        
        # メインメッセージ
        self.message_label = QLabel("準備完了")
        layout.addWidget(self.message_label)
        
        layout.addStretch()
        
        # プログレスバー（通常は非表示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        layout.addWidget(self.progress_bar)
        
        # 右側の情報
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
        # 接続状態インジケーター
        self.connection_indicator = QLabel("●")
        self.connection_indicator.setStyleSheet("color: green;")
        self.connection_indicator.setToolTip("接続状態: オンライン")
        layout.addWidget(self.connection_indicator)
        
        self.setLayout(layout)
    
    def _setup_style(self) -> None:
        """スタイルのセットアップ"""
        self.setStyleSheet("""
            StatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #cccccc;
            }
            QLabel {
                color: #333333;
                font-size: 12px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
    
    def show_message(self, message: str, timeout: int = 0) -> None:
        """
        メッセージを表示
        
        Args:
            message: 表示するメッセージ
            timeout: タイムアウト（ミリ秒、0で永続表示）
        """
        self.message_label.setText(message)
        
        if timeout > 0:
            QTimer.singleShot(timeout, lambda: self.message_label.setText("準備完了"))
    
    def show_progress(self, visible: bool = True) -> None:
        """プログレスバーの表示/非表示"""
        self.progress_bar.setVisible(visible)
    
    def set_progress(self, value: int, maximum: int = 100) -> None:
        """プログレス値を設定"""
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
    
    def set_connection_status(self, connected: bool) -> None:
        """接続状態を設定"""
        if connected:
            self.connection_indicator.setStyleSheet("color: green;")
            self.connection_indicator.setToolTip("接続状態: オンライン")
        else:
            self.connection_indicator.setStyleSheet("color: red;")
            self.connection_indicator.setToolTip("接続状態: オフライン")
    
    def set_info(self, info: str) -> None:
        """右側の情報を設定"""
        self.info_label.setText(info)


class CodeSnippetWidget(QWidget):
    """
    コードスニペット表示ウィジェット
    
    コードスニペットを見やすく表示し、コピー機能を提供
    """
    
    def __init__(self, code: str = "", language: str = "python", parent: Optional[QWidget] = None):
        """
        CodeSnippetWidgetを初期化
        
        Args:
            code: コード内容
            language: プログラミング言語
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.code = code
        self.language = language
        
        self._setup_ui()
        self._setup_style()
        
        logger.debug(f"CodeSnippetWidget created for {language}")
    
    def _setup_ui(self) -> None:
        """UIのセットアップ"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ヘッダー
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.Box)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # 言語ラベル
        self.language_label = QLabel(self.language.upper())
        self.language_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        header_layout.addWidget(self.language_label)
        
        header_layout.addStretch()
        
        # コピーボタン
        self.copy_button = QPushButton("コピー")
        self.copy_button.setMaximumWidth(60)
        self.copy_button.clicked.connect(self._copy_code)
        header_layout.addWidget(self.copy_button)
        
        layout.addWidget(header_frame)
        
        # コード表示エリア
        self.code_text = QTextEdit()
        self.code_text.setPlainText(self.code)
        self.code_text.setReadOnly(True)
        self.code_text.setFont(QFont("Courier New", 10))
        layout.addWidget(self.code_text)
        
        self.setLayout(layout)
    
    def _setup_style(self) -> None:
        """スタイルのセットアップ"""
        self.setStyleSheet("""
            CodeSnippetWidget {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QFrame {
                background-color: #f8f8f8;
                border: none;
                border-bottom: 1px solid #cccccc;
            }
            QTextEdit {
                background-color: #fafafa;
                border: none;
                font-family: 'Courier New', monospace;
                line-height: 1.4;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)
    
    def _copy_code(self) -> None:
        """コードをクリップボードにコピー"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.code)
        
        # 一時的にボタンテキストを変更
        original_text = self.copy_button.text()
        self.copy_button.setText("コピー済み")
        QTimer.singleShot(1000, lambda: self.copy_button.setText(original_text))
    
    def set_code(self, code: str, language: str = None) -> None:
        """コードを設定"""
        self.code = code
        self.code_text.setPlainText(code)
        
        if language:
            self.language = language
            self.language_label.setText(language.upper())


class TabBar(QTabWidget):
    """
    カスタムタブバー
    
    閉じるボタン付きのタブバー
    """
    
    tab_close_requested = pyqtSignal(int)  # タブクローズ要求シグナル
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        TabBarを初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.setTabsClosable(True)
        self.setMovable(True)
        
        self._setup_style()
        self._setup_signals()
        
        logger.debug("TabBar created")
    
    def _setup_style(self) -> None:
        """スタイルのセットアップ"""
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-bottom: none;
                border-radius: 3px 3px 0px 0px;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #e0e0e0;
            }
            QTabBar::close-button {
                image: url(assets/icons/close.png);
                subcontrol-position: right;
            }
            QTabBar::close-button:hover {
                background-color: #ff6b6b;
                border-radius: 2px;
            }
        """)
    
    def _setup_signals(self) -> None:
        """シグナルのセットアップ"""
        self.tabCloseRequested.connect(self.tab_close_requested.emit)
    
    def add_tab(self, widget: QWidget, title: str, closable: bool = True) -> int:
        """
        タブを追加
        
        Args:
            widget: タブのウィジェット
            title: タブのタイトル
            closable: 閉じるボタンの表示有無
            
        Returns:
            追加されたタブのインデックス
        """
        index = self.addTab(widget, title)
        
        if not closable:
            # 閉じるボタンを無効化
            self.tabBar().setTabButton(index, self.tabBar().RightSide, None)
        
        return index


if __name__ == "__main__":
    """テスト用のメイン関数"""
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Custom Widgets Test")
            self.setGeometry(100, 100, 800, 600)
            
            # 中央ウィジェット
            central_widget = QWidget()
            layout = QVBoxLayout()
            
            # アニメーションボタンのテスト
            animated_btn = AnimatedButton("アニメーションボタン")
            layout.addWidget(animated_btn)
            
            # ローディングスピナーのテスト
            spinner = LoadingSpinner(size=48)
            spinner.start()
            layout.addWidget(spinner)
            
            # 折りたたみグループボックスのテスト
            collapsible = CollapsibleGroupBox("折りたたみ可能グループ")
            collapsible.addWidget(QLabel("これは折りたたみ可能なコンテンツです"))
            collapsible.addWidget(QPushButton("テストボタン"))
            layout.addWidget(collapsible)
            
            # 検索可能コンボボックスのテスト
            searchable_combo = SearchableComboBox()
            searchable_combo.addItems(["Python", "JavaScript", "Java", "C++", "Go", "Rust"])
            layout.addWidget(searchable_combo)
            
            # コードスニペットのテスト
            code_snippet = CodeSnippetWidget(
                code="def hello_world():\n    print('Hello, World!')\n    return True",
                language="python"
            )
            layout.addWidget(code_snippet)
            
            # ステータスバーのテスト
            status_bar = StatusBar()
            status_bar.show_message("カスタムウィジェットのテスト中...")
            status_bar.set_info("ファイル: test.py")
            layout.addWidget(status_bar)
            
            central_widget.setLayout(layout)
            self.setCentralWidget(central_widget)
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
