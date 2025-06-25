#src/ui/main_window.py
"""
メインウィンドウクラス
LLM Code Assistant のメインUI
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QTabWidget, QMenuBar, QStatusBar,
    QTextEdit, QPushButton, QComboBox, QLabel,
    QProgressBar, QMessageBox, QToolBar, QAction
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

from .llm_chat_panel import LLMChatPanel  # ⭐ 新規パネル
from .code_editor import CodeEditor
from .project_tree import ProjectTree
#from .status_panel import StatusPanel

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """メインウィンドウクラス"""
    
    def __init__(self, app_components):
        super().__init__()
        
        # アプリケーションコンポーネント
        self.config_manager = app_components['config_manager']
        self.event_bus = app_components['event_bus']
        self.plugin_manager = app_components['plugin_manager']
        self.llm_client = app_components['llm_client']  # ⭐ LLMクライアント
        
        # UI初期化
        self.init_ui()
        self.setup_menus()
        self.setup_toolbars()
        self.setup_status_bar()
        self.setup_connections()
        
        # ⭐ LLM関連の初期化
        self.setup_llm_features()
        
        logger.info("メインウィンドウが初期化されました")
    
    def init_ui(self):
        """UI初期化"""
        self.setWindowTitle("LLM Code Assistant")
        self.setMinimumSize(1000, 700)
        
        # 設定から初期サイズを取得
        config = self.config_manager.config
        ui_config = config.get('ui', {}).get('window', {})
        
        width = ui_config.get('default_width', 1200)
        height = ui_config.get('default_height', 800)
        self.resize(width, height)
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QHBoxLayout(central_widget)
        
        # スプリッター（左右分割）
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # 左パネル（プロジェクトツリー）
        self.project_tree = ProjectTree()
        main_splitter.addWidget(self.project_tree)
        
        # 右パネル（エディタ + LLMパネル）
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(right_splitter)
        
        # エディタタブ
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.tabCloseRequested.connect(self.close_tab)
        right_splitter.addWidget(self.editor_tabs)
        
        # ⭐ LLMチャットパネル
        self.llm_chat_panel = LLMChatPanel(self.llm_client)
        right_splitter.addWidget(self.llm_chat_panel)
        
        # スプリッター比率設定
        main_splitter.setSizes([250, 950])
        right_splitter.setSizes([600, 400])
    
    def setup_llm_features(self):
        """LLM機能の初期化"""
        try:
            # LLMクライアントの状態監視
            self.llm_status_timer = QTimer()
            self.llm_status_timer.timeout.connect(self.update_llm_status)
            self.llm_status_timer.start(5000)  # 5秒間隔
            
            # 初期状態更新
            self.update_llm_status()
            
            logger.info("LLM機能が初期化されました")
            
        except Exception as e:
            logger.error(f"LLM機能の初期化に失敗しました: {e}")
    
    def update_llm_status(self):
        """LLMサービスの状態を更新"""
        try:
            if hasattr(self, 'llm_status_label'):
                if self.llm_client.is_available():
                    self.llm_status_label.setText("🟢 LLM: 利用可能")
                    self.llm_status_label.setStyleSheet("color: green;")
                else:
                    self.llm_status_label.setText("🔴 LLM: 利用不可")
                    self.llm_status_label.setStyleSheet("color: red;")
        except Exception as e:
            logger.error(f"LLM状態更新エラー: {e}")
    
    def setup_menus(self):
        """メニューバー設定"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu('ファイル(&F)')
        
        new_action = QAction('新規作成(&N)', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction('開く(&O)', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction('保存(&S)', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        # ⭐ LLMメニュー
        llm_menu = menubar.addMenu('LLM(&L)')
        
        generate_code_action = QAction('コード生成(&G)', self)
        generate_code_action.setShortcut('Ctrl+G')
        generate_code_action.triggered.connect(self.generate_code)
        llm_menu.addAction(generate_code_action)
        
        explain_code_action = QAction('コード説明(&E)', self)
        explain_code_action.setShortcut('Ctrl+E')
        explain_code_action.triggered.connect(self.explain_code)
        llm_menu.addAction(explain_code_action)
        
        refactor_code_action = QAction('リファクタリング(&R)', self)
        refactor_code_action.setShortcut('Ctrl+R')
        refactor_code_action.triggered.connect(self.refactor_code)
        llm_menu.addAction(refactor_code_action)
        
        llm_menu.addSeparator()
        
        chat_panel_action = QAction('チャットパネル(&T)', self)
        chat_panel_action.setShortcut('Ctrl+T')
        chat_panel_action.triggered.connect(self.toggle_chat_panel)
        llm_menu.addAction(chat_panel_action)
    
    def setup_toolbars(self):
        """ツールバー設定"""
        # メインツールバー
        main_toolbar = self.addToolBar('メイン')
        
        # ファイル操作
        new_action = QAction('新規', self)
        new_action.triggered.connect(self.new_file)
        main_toolbar.addAction(new_action)
        
        open_action = QAction('開く', self)
        open_action.triggered.connect(self.open_file)
        main_toolbar.addAction(open_action)
        
        save_action = QAction('保存', self)
        save_action.triggered.connect(self.save_file)
        main_toolbar.addAction(save_action)
        
        main_toolbar.addSeparator()
        
        # ⭐ LLM操作
        generate_action = QAction('生成', self)
        generate_action.triggered.connect(self.generate_code)
        main_toolbar.addAction(generate_action)
        
        explain_action = QAction('説明', self)
        explain_action.triggered.connect(self.explain_code)
        main_toolbar.addAction(explain_action)
    
    def setup_status_bar(self):
        """ステータスバー設定"""
        status_bar = self.statusBar()
        
        # 基本情報
        self.status_label = QLabel("準備完了")
        status_bar.addWidget(self.status_label)
        
        status_bar.addPermanentWidget(QLabel("|"))
        
        # ⭐ LLM状態表示
        self.llm_status_label = QLabel("🔄 LLM: 確認中")
        status_bar.addPermanentWidget(self.llm_status_label)
        
        status_bar.addPermanentWidget(QLabel("|"))
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_bar.addPermanentWidget(self.progress_bar)
    
    def setup_connections(self):
        """シグナル・スロット接続"""
        # プロジェクトツリーからのファイル選択
        self.project_tree.file_selected.connect(self.open_file_from_tree)
        
        # ⭐ LLMチャットパネルからの操作
        if hasattr(self.llm_chat_panel, 'code_generated'):
            self.llm_chat_panel.code_generated.connect(self.insert_generated_code)
    
    # ⭐ LLM関連メソッド
    def generate_code(self):
        """コード生成"""
        current_editor = self.get_current_editor()
        if current_editor:
            selected_text = current_editor.textCursor().selectedText()
            if selected_text:
                prompt = f"Generate code based on: {selected_text}"
            else:
                prompt = "Generate a code example"
            
            self.llm_chat_panel.send_request(prompt, task_type='code_generation')
    
    def explain_code(self):
        """コード説明"""
        current_editor = self.get_current_editor()
        if current_editor:
            selected_text = current_editor.textCursor().selectedText()
            if selected_text:
                prompt = f"Explain this code: {selected_text}"
                self.llm_chat_panel.send_request(prompt, task_type='code_explanation')
            else:
                QMessageBox.information(self, "情報", "説明するコードを選択してください。")
    
    def refactor_code(self):
        """コードリファクタリング"""
        current_editor = self.get_current_editor()
        if current_editor:
            selected_text = current_editor.textCursor().selectedText()
            if selected_text:
                prompt = f"Refactor this code: {selected_text}"
                self.llm_chat_panel.send_request(prompt, task_type='refactoring')
            else:
                QMessageBox.information(self, "情報", "リファクタリングするコードを選択してください。")
    
    def toggle_chat_panel(self):
        """チャットパネルの表示切り替え"""
        if self.llm_chat_panel.isVisible():
            self.llm_chat_panel.hide()
        else:
            self.llm_chat_panel.show()
    
    def insert_generated_code(self, code):
        """生成されたコードを挿入"""
        current_editor = self.get_current_editor()
        if current_editor:
            cursor = current_editor.textCursor()
            cursor.insertText(code)
    
    def get_current_editor(self):
        """現在のエディタを取得"""
        current_tab = self.editor_tabs.currentWidget()
        if isinstance(current_tab, CodeEditor):
            return current_tab
        return None
    
    # 既存のメソッド（簡略化）
    def new_file(self):
        """新規ファイル作成"""
        editor = CodeEditor()
        index = self.editor_tabs.addTab(editor, "新規ファイル")
        self.editor_tabs.setCurrentIndex(index)
    
    def open_file(self):
        """ファイルを開く"""
        # ファイルダイアログの実装
        pass
    
    def open_file_from_tree(self, file_path):
        """プロジェクトツリーからファイルを開く"""
        # ファイル読み込みの実装
        pass
    
    def save_file(self):
        """ファイル保存"""
        # ファイル保存の実装
        pass
    
    def close_tab(self, index):
        """タブを閉じる"""
        self.editor_tabs.removeTab(index)
