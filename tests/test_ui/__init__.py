# tests/test_ui/__init__.py
"""
UIコンポーネントのテストパッケージ
GUI関連のテストモジュールとユーティリティを提供
"""

import sys
import pytest
from pathlib import Path
from typing import Optional, Dict, Any, List
from unittest.mock import Mock, patch

# Qt関連のインポート（テスト環境での利用可能性をチェック）
try:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtTest import QTest
    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt5.QtWidgets import QApplication, QWidget
        from PyQt5.QtCore import QTimer, Qt
        from PyQt5.QtTest import QTest
        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False


class UITestBase:
    """UIテストの基底クラス"""
    
    @classmethod
    def setup_class(cls):
        """クラス全体のセットアップ"""
        if not QT_AVAILABLE:
            pytest.skip("Qt not available for UI testing")
        
        # QApplicationの初期化（既に存在する場合は再利用）
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
        
        # テスト用の設定
        cls.app.setQuitOnLastWindowClosed(False)
    
    @classmethod
    def teardown_class(cls):
        """クラス全体のクリーンアップ"""
        if hasattr(cls, 'app') and cls.app:
            # アプリケーションの終了処理
            cls.app.processEvents()
    
    def setup_method(self):
        """各テストメソッドのセットアップ"""
        self.widgets_to_cleanup = []
    
    def teardown_method(self):
        """各テストメソッドのクリーンアップ"""
        # 作成されたウィジェットをクリーンアップ
        for widget in self.widgets_to_cleanup:
            if widget and hasattr(widget, 'close'):
                widget.close()
                widget.deleteLater()
        
        # イベントループを処理
        if QT_AVAILABLE and QApplication.instance():
            QApplication.instance().processEvents()
    
    def create_widget(self, widget_class, *args, **kwargs):
        """テスト用ウィジェット作成ヘルパー"""
        widget = widget_class(*args, **kwargs)
        self.widgets_to_cleanup.append(widget)
        return widget


class MockQApplication:
    """QApplicationのモック"""
    
    def __init__(self):
        self.widgets = []
        self.quit_called = False
        self.events_processed = 0
    
    def processEvents(self):
        """イベント処理のモック"""
        self.events_processed += 1
    
    def quit(self):
        """アプリケーション終了のモック"""
        self.quit_called = True
    
    def setQuitOnLastWindowClosed(self, quit_on_close):
        """終了設定のモック"""
        self.quit_on_last_window_closed = quit_on_close
    
    @staticmethod
    def instance():
        """インスタンス取得のモック"""
        return None


class MockQWidget:
    """QWidgetのモック"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.children = []
        self.is_visible = False
        self.is_closed = False
        self.geometry_rect = (0, 0, 100, 100)
        self.window_title = ""
        self.enabled = True
        
        if parent:
            parent.children.append(self)
    
    def show(self):
        """ウィジェット表示のモック"""
        self.is_visible = True
    
    def hide(self):
        """ウィジェット非表示のモック"""
        self.is_visible = False
    
    def close(self):
        """ウィジェット閉じるのモック"""
        self.is_closed = True
        self.is_visible = False
        return True
    
    def deleteLater(self):
        """ウィジェット削除のモック"""
        pass
    
    def setGeometry(self, x, y, width, height):
        """ジオメトリ設定のモック"""
        self.geometry_rect = (x, y, width, height)
    
    def geometry(self):
        """ジオメトリ取得のモック"""
        return type('Rect', (), {
            'x': lambda: self.geometry_rect[0],
            'y': lambda: self.geometry_rect[1],
            'width': lambda: self.geometry_rect[2],
            'height': lambda: self.geometry_rect[3]
        })()
    
    def setWindowTitle(self, title):
        """ウィンドウタイトル設定のモック"""
        self.window_title = title
    
    def windowTitle(self):
        """ウィンドウタイトル取得のモック"""
        return self.window_title
    
    def setEnabled(self, enabled):
        """有効/無効設定のモック"""
        self.enabled = enabled
    
    def isEnabled(self):
        """有効状態取得のモック"""
        return self.enabled


class MockQTimer:
    """QTimerのモック"""
    
    def __init__(self):
        self.interval_ms = 0
        self.is_active = False
        self.single_shot = False
        self.timeout_callback = None
    
    def setInterval(self, ms):
        """インターバル設定のモック"""
        self.interval_ms = ms
    
    def start(self, ms=None):
        """タイマー開始のモック"""
        if ms is not None:
            self.interval_ms = ms
        self.is_active = True
    
    def stop(self):
        """タイマー停止のモック"""
        self.is_active = False
    
    def setSingleShot(self, single_shot):
        """シングルショット設定のモック"""
        self.single_shot = single_shot
    
    def timeout(self):
        """タイムアウトシグナルのモック"""
        return type('Signal', (), {
            'connect': lambda callback: setattr(self, 'timeout_callback', callback),
            'disconnect': lambda: setattr(self, 'timeout_callback', None),
            'emit': lambda: self.timeout_callback() if self.timeout_callback else None
        })()


def create_mock_qt_environment():
    """モックQt環境を作成"""
    mock_env = {
        'QApplication': MockQApplication,
        'QWidget': MockQWidget,
        'QTimer': MockQTimer,
        'Qt': type('Qt', (), {
            'LeftButton': 1,
            'RightButton': 2,
            'MiddleButton': 4,
            'Key_Return': 16777220,
            'Key_Enter': 16777221,
            'Key_Escape': 16777216,
            'AlignCenter': 0x0004,
            'AlignLeft': 0x0001,
            'AlignRight': 0x0002
        })()
    }
    return mock_env


def requires_qt(func):
    """Qtが必要なテスト用デコレータ"""
    def wrapper(*args, **kwargs):
        if not QT_AVAILABLE:
            pytest.skip("Qt not available")
        return func(*args, **kwargs)
    return wrapper


def mock_qt_test(func):
    """QtテストをモックQt環境で実行するデコレータ"""
    def wrapper(*args, **kwargs):
        if QT_AVAILABLE:
            # 実際のQt環境で実行
            return func(*args, **kwargs)
        else:
            # モック環境で実行
            mock_env = create_mock_qt_environment()
            with patch.multiple('PyQt6.QtWidgets', **mock_env), \
                 patch.multiple('PyQt6.QtCore', **mock_env), \
                 patch.multiple('PyQt5.QtWidgets', **mock_env), \
                 patch.multiple('PyQt5.QtCore', **mock_env):
                return func(*args, **kwargs)
    return wrapper


class UITestHelper:
    """UIテスト用ヘルパークラス"""
    
    @staticmethod
    def click_button(button, delay_ms=100):
        """ボタンクリックのシミュレート"""
        if QT_AVAILABLE and hasattr(button, 'click'):
            button.click()
            QApplication.instance().processEvents()
            if delay_ms > 0:
                QTest.qWait(delay_ms)
        else:
            # モック環境での処理
            if hasattr(button, 'click'):
                button.click()
    
    @staticmethod
    def type_text(widget, text, delay_ms=10):
        """テキスト入力のシミュレート"""
        if QT_AVAILABLE and hasattr(QTest, 'keyClicks'):
            QTest.keyClicks(widget, text)
            if delay_ms > 0:
                QTest.qWait(delay_ms)
        else:
            # モック環境での処理
            if hasattr(widget, 'setText'):
                widget.setText(text)
            elif hasattr(widget, 'insertPlainText'):
                widget.insertPlainText(text)
    
    @staticmethod
    def wait_for_signal(signal, timeout_ms=5000):
        """シグナル待機"""
        if QT_AVAILABLE:
            import time
            start_time = time.time()
            while (time.time() - start_time) * 1000 < timeout_ms:
                QApplication.instance().processEvents()
                time.sleep(0.01)
        # モック環境では即座に完了
    
    @staticmethod
    def capture_screenshot(widget, filename=None):
        """スクリーンショット撮影（テスト用）"""
        if QT_AVAILABLE and hasattr(widget, 'grab'):
            pixmap = widget.grab()
            if filename:
                pixmap.save(filename)
            return pixmap
        else:
            # モック環境では何もしない
            return None


class UITestFixtures:
    """UIテスト用フィクスチャ"""
    
    @staticmethod
    def create_test_config():
        """テスト用UI設定を作成"""
        return {
            'ui': {
                'theme': 'light',
                'font_family': 'Consolas',
                'font_size': 12,
                'window_geometry': {
                    'width': 800,
                    'height': 600,
                    'x': 100,
                    'y': 100
                },
                'editor': {
                    'tab_size': 4,
                    'show_line_numbers': True,
                    'word_wrap': False,
                    'syntax_highlighting': True
                },
                'panels': {
                    'project_tree_visible': True,
                    'chat_panel_visible': True,
                    'output_panel_visible': True
                }
            }
        }
    
    @staticmethod
    def create_test_project_data():
        """テスト用プロジェクトデータを作成"""
        return {
            'name': 'Test Project',
            'path': '/test/project/path',
            'files': [
                {'name': 'main.py', 'type': 'python'},
                {'name': 'config.json', 'type': 'json'},
                {'name': 'README.md', 'type': 'markdown'}
            ],
            'settings': {
                'language': 'python',
                'version': '3.11.9'
            }
        }


# テストで使用する共通の設定とデータ
UI_TEST_CONFIG = UITestFixtures.create_test_config()
UI_TEST_PROJECT_DATA = UITestFixtures.create_test_project_data()

# エクスポートする主要なクラスと関数
__all__ = [
    'UITestBase',
    'MockQApplication',
    'MockQWidget', 
    'MockQTimer',
    'create_mock_qt_environment',
    'requires_qt',
    'mock_qt_test',
    'UITestHelper',
    'UITestFixtures',
    'UI_TEST_CONFIG',
    'UI_TEST_PROJECT_DATA',
    'QT_AVAILABLE'
]
