# src/ui/code_editor.py
"""
コードエディタウィジェット
LLM統合機能付きエディタ
"""

import logging
from PyQt6.QtWidgets import (
    QTextEdit, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QAction, QKeySequence

logger = logging.getLogger(__name__)

class CodeEditor(QTextEdit):
    """LLM統合コードエディタ"""
    
    # シグナル定義
    llm_request_triggered = pyqtSignal(str, str)  # prompt, task_type
    text_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_editor()
        self.setup_context_menu()
        
        # LLMクライアント参照（後で設定）
        self.llm_client = None
        
        logger.info("コードエディタが初期化されました")
    
    def setup_editor(self):
        """エディタ設定"""
        # フォント設定
        font = QFont("Consolas", 12)
        font.setFixedPitch(True)
        self.setFont(font)
        
        # エディタスタイル
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                selection-background-color: #264f78;
            }
        """)
        
        # タブ設定
        self.setTabStopDistance(40)  # 4スペース相当
    
    def setup_context_menu(self):
        """コンテキストメニュー設定"""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def show_context_menu(self, position):
        """コンテキストメニュー表示"""
        menu = QMenu(self)
        
        # 標準メニュー項目
        menu.addAction("切り取り", self.cut, QKeySequence.StandardKey.Cut)
        menu.addAction("コピー", self.copy, QKeySequence.StandardKey.Copy)
        menu.addAction("貼り付け", self.paste, QKeySequence.StandardKey.Paste)
        menu.addSeparator()
        
        # ⭐ LLM機能メニュー
        selected_text = self.textCursor().selectedText()
        
        if selected_text:
            llm_menu = menu.addMenu("🤖 LLM機能")
            
            llm_menu.addAction("コード説明", lambda: self.request_llm_action("explain", selected_text))
            llm_menu.addAction("コード修正", lambda: self.request_llm_action("debug", selected_text))
            llm_menu.addAction("リファクタリング", lambda: self.request_llm_action("refactor", selected_text))
            llm_menu.addAction("最適化", lambda: self.request_llm_action("optimize", selected_text))
            llm_menu.addSeparator()
            llm_menu.addAction("コメント追加", lambda: self.request_llm_action("comment", selected_text))
            llm_menu.addAction("テスト生成", lambda: self.request_llm_action("test", selected_text))
        else:
            menu.addAction("🤖 コード生成...", self.request_code_generation)
        
        menu.addSeparator()
        menu.addAction("全選択", self.selectAll, QKeySequence.StandardKey.SelectAll)
        
        menu.exec(self.mapToGlobal(position))
    
    def request_llm_action(self, action_type: str, selected_text: str):
        """LLMアクション要求"""
        try:
            prompts = {
                "explain": f"Explain this code:\n{selected_text}",
                "debug": f"Find and fix bugs in this code:\n{selected_text}",
                "refactor": f"Refactor this code for better readability:\n{selected_text}",
                "optimize": f"Optimize this code for performance:\n{selected_text}",
                "comment": f"Add appropriate comments to this code:\n{selected_text}",
                "test": f"Generate unit tests for this code:\n{selected_text}"
            }
            
            task_types = {
                "explain": "code_explanation",
                "debug": "debugging",
                "refactor": "refactoring",
                "optimize": "refactoring",
                "comment": "code_generation",
                "test": "code_generation"
            }
            
            prompt = prompts.get(action_type, selected_text)
            task_type = task_types.get(action_type, "general")
            
            self.llm_request_triggered.emit(prompt, task_type)
            
        except Exception as e:
            logger.error(f"LLMアクション要求エラー: {e}")
    
    def request_code_generation(self):
        """コード生成要求"""
        from PyQt6.QtWidgets import QInputDialog
        
        prompt, ok = QInputDialog.getText(
            self, "コード生成", 
            "生成したいコードの説明を入力してください:"
        )
        
        if ok and prompt.strip():
            self.llm_request_triggered.emit(prompt.strip(), "code_generation")
    
    def set_llm_client(self, llm_client):
        """LLMクライアントを設定"""
        self.llm_client = llm_client
    
    def insert_llm_response(self, response: str):
        """LLMレスポンスを挿入"""
        try:
            cursor = self.textCursor()
            
            # 選択テキストがある場合は置換、なければ挿入
            if cursor.hasSelection():
                cursor.insertText(response)
            else:
                cursor.insertText(f"\n{response}\n")
            
            # カーソル位置を調整
            self.setTextCursor(cursor)
            
        except Exception as e:
            logger.error(f"LLMレスポンス挿入エラー: {e}")
    
    def highlight_syntax(self):
        """シンタックスハイライト（簡易版）"""
        # 実装は省略（必要に応じて追加）
        pass
