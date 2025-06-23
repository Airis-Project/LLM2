# src/ui/about_dialog.py
"""
About Dialog - アプリケーション情報ダイアログ

このモジュールは、アプリケーションの情報を表示するダイアログを提供します。
バージョン情報、ライセンス情報、開発者情報などを表示します。
"""

import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QTabWidget, QWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap, QFont, QDesktopServices

from ..core.logger import get_logger

logger = get_logger(__name__)


class AboutDialog(QDialog):
    """
    アプリケーション情報ダイアログクラス
    
    アプリケーションのバージョン情報、ライセンス、開発者情報、
    使用ライブラリなどの情報を表示します。
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        AboutDialogを初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.setWindowTitle("LLM Code Assistant について")
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # ダイアログの初期化
        self._setup_ui()
        
        logger.debug("AboutDialog initialized")
    
    def _setup_ui(self) -> None:
        """UIコンポーネントのセットアップ"""
        try:
            # メインレイアウト
            layout = QVBoxLayout()
            layout.setSpacing(10)
            layout.setContentsMargins(15, 15, 15, 15)
            
            # ヘッダー部分
            header_widget = self._create_header()
            layout.addWidget(header_widget)
            
            # タブウィジェット
            tab_widget = self._create_tab_widget()
            layout.addWidget(tab_widget)
            
            # ボタン部分
            button_layout = self._create_buttons()
            layout.addLayout(button_layout)
            
            self.setLayout(layout)
            
        except Exception as e:
            logger.error(f"UI setup failed: {e}")
            raise
    
    def _create_header(self) -> QWidget:
        """ヘッダー部分の作成"""
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        # アプリケーションアイコン
        icon_label = QLabel()
        try:
            # アイコンの読み込み（存在しない場合はスキップ）
            pixmap = QPixmap("assets/icons/app_icon.ico")
            if not pixmap.isNull():
                icon_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio))
            else:
                icon_label.setText("🤖")
                icon_label.setStyleSheet("font-size: 48px;")
        except Exception:
            icon_label.setText("🤖")
            icon_label.setStyleSheet("font-size: 48px;")
        
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)
        
        # アプリケーション情報
        info_layout = QVBoxLayout()
        
        # アプリケーション名
        app_name = QLabel("LLM Code Assistant")
        app_name.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        app_name.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(app_name)
        
        # バージョン情報
        version_label = QLabel("バージョン 1.0.0")
        version_label.setFont(QFont("Arial", 10))
        version_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(version_label)
        
        # 説明
        description = QLabel("AI支援によるコード生成・編集ツール")
        description.setFont(QFont("Arial", 9))
        description.setAlignment(Qt.AlignmentFlag.AlignLeft)
        description.setWordWrap(True)
        info_layout.addWidget(description)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        header_widget.setLayout(header_layout)
        return header_widget
    
    def _create_tab_widget(self) -> QTabWidget:
        """タブウィジェットの作成"""
        tab_widget = QTabWidget()
        
        # 一般情報タブ
        general_tab = self._create_general_tab()
        tab_widget.addTab(general_tab, "一般")
        
        # ライセンスタブ
        license_tab = self._create_license_tab()
        tab_widget.addTab(license_tab, "ライセンス")
        
        # 使用ライブラリタブ
        libraries_tab = self._create_libraries_tab()
        tab_widget.addTab(libraries_tab, "ライブラリ")
        
        # システム情報タブ
        system_tab = self._create_system_tab()
        tab_widget.addTab(system_tab, "システム")
        
        return tab_widget
    
    def _create_general_tab(self) -> QWidget:
        """一般情報タブの作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # スクロール可能なエリア
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # アプリケーション情報
        info_text = """
<h3>LLM Code Assistant</h3>
<p><strong>開発者:</strong> Development Team</p>
<p><strong>リリース日:</strong> 2024年1月</p>
<p><strong>サポート:</strong> support@example.com</p>

<h4>概要</h4>
<p>LLM Code Assistantは、大規模言語モデル（LLM）を活用した
コード生成・編集支援ツールです。プログラマーの生産性向上を
目的として開発されました。</p>

<h4>主な機能</h4>
<ul>
<li>AI支援によるコード生成</li>
<li>インテリジェントなコード補完</li>
<li>多言語対応のシンタックスハイライト</li>
<li>プロジェクト管理機能</li>
<li>プラグインシステム</li>
<li>カスタマイズ可能なテーマ</li>
</ul>

<h4>サポートする言語</h4>
<p>Python, JavaScript, HTML, CSS, Java, C++, Go, Rust など</p>
        """
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll_layout.addWidget(info_label)
        scroll_layout.addStretch()
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        layout.addWidget(scroll_area)
        widget.setLayout(layout)
        
        return widget
    
    def _create_license_tab(self) -> QWidget:
        """ライセンスタブの作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ライセンステキスト
        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setPlainText(self._get_license_text())
        license_text.setFont(QFont("Courier", 9))
        
        layout.addWidget(license_text)
        widget.setLayout(layout)
        
        return widget
    
    def _create_libraries_tab(self) -> QWidget:
        """使用ライブラリタブの作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # スクロール可能なエリア
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # ライブラリ情報
        libraries_info = """
<h3>使用ライブラリ</h3>

<h4>GUI フレームワーク</h4>
<ul>
<li><strong>PyQt6</strong> - クロスプラットフォームGUIツールキット</li>
<li><strong>QScintilla</strong> - コードエディタコンポーネント</li>
</ul>

<h4>AI・機械学習</h4>
<ul>
<li><strong>OpenAI</strong> - OpenAI API クライアント</li>
<li><strong>Anthropic</strong> - Claude API クライアント</li>
<li><strong>Transformers</strong> - ローカルLLMモデル</li>
<li><strong>Torch</strong> - 機械学習フレームワーク</li>
</ul>

<h4>データ処理</h4>
<ul>
<li><strong>Requests</strong> - HTTP ライブラリ</li>
<li><strong>PyYAML</strong> - YAML パーサー</li>
<li><strong>Jinja2</strong> - テンプレートエンジン</li>
</ul>

<h4>開発・テスト</h4>
<ul>
<li><strong>pytest</strong> - テストフレームワーク</li>
<li><strong>black</strong> - コードフォーマッター</li>
<li><strong>flake8</strong> - コード品質チェック</li>
</ul>

<h4>その他</h4>
<ul>
<li><strong>GitPython</strong> - Git 操作ライブラリ</li>
<li><strong>Pygments</strong> - シンタックスハイライト</li>
<li><strong>chardet</strong> - 文字エンコーディング検出</li>
</ul>
        """
        
        libraries_label = QLabel(libraries_info)
        libraries_label.setWordWrap(True)
        libraries_label.setTextFormat(Qt.TextFormat.RichText)
        libraries_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll_layout.addWidget(libraries_label)
        scroll_layout.addStretch()
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        layout.addWidget(scroll_area)
        widget.setLayout(layout)
        
        return widget
    
    def _create_system_tab(self) -> QWidget:
        """システム情報タブの作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # システム情報の取得と表示
        system_info = self._get_system_info()
        
        system_text = QTextEdit()
        system_text.setReadOnly(True)
        system_text.setPlainText(system_info)
        system_text.setFont(QFont("Courier", 9))
        
        layout.addWidget(system_text)
        widget.setLayout(layout)
        
        return widget
    
    def _create_buttons(self) -> QHBoxLayout:
        """ボタン部分の作成"""
        button_layout = QHBoxLayout()
        
        # ウェブサイトボタン
        website_button = QPushButton("ウェブサイト")
        website_button.clicked.connect(self._open_website)
        button_layout.addWidget(website_button)
        
        # GitHubボタン
        github_button = QPushButton("GitHub")
        github_button.clicked.connect(self._open_github)
        button_layout.addWidget(github_button)
        
        button_layout.addStretch()
        
        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_layout.addWidget(close_button)
        
        return button_layout
    
    def _get_license_text(self) -> str:
        """ライセンステキストの取得"""
        return """MIT License

Copyright (c) 2024 LLM Code Assistant

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
    
    def _get_system_info(self) -> str:
        """システム情報の取得"""
        try:
            import platform
            import os
            
            info_lines = [
                f"Python バージョン: {sys.version}",
                f"プラットフォーム: {platform.platform()}",
                f"アーキテクチャ: {platform.architecture()[0]}",
                f"プロセッサ: {platform.processor()}",
                f"OS: {platform.system()} {platform.release()}",
                f"ホスト名: {platform.node()}",
                f"ユーザー: {os.getenv('USER', os.getenv('USERNAME', 'Unknown'))}",
                "",
                "環境変数:",
                f"  PATH: {os.getenv('PATH', 'Not set')[:100]}...",
                f"  PYTHONPATH: {os.getenv('PYTHONPATH', 'Not set')}",
                "",
                "PyQt6 情報:",
            ]
            
            # PyQt6のバージョン情報
            try:
                from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
                info_lines.extend([
                    f"  PyQt6 バージョン: {PYQT_VERSION_STR}",
                    f"  Qt バージョン: {QT_VERSION_STR}",
                ])
            except ImportError:
                info_lines.append("  PyQt6: インストールされていません")
            
            return "\n".join(info_lines)
            
        except Exception as e:
            return f"システム情報の取得に失敗しました: {e}"
    
    def _open_website(self) -> None:
        """ウェブサイトを開く"""
        try:
            url = QUrl("https://example.com")
            QDesktopServices.openUrl(url)
            logger.info("Website opened")
        except Exception as e:
            logger.error(f"Failed to open website: {e}")
    
    def _open_github(self) -> None:
        """GitHubページを開く"""
        try:
            url = QUrl("https://github.com/example/llm-code-assistant")
            QDesktopServices.openUrl(url)
            logger.info("GitHub page opened")
        except Exception as e:
            logger.error(f"Failed to open GitHub page: {e}")


if __name__ == "__main__":
    """テスト用のメイン関数"""
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = AboutDialog()
    dialog.show()
    sys.exit(app.exec())
