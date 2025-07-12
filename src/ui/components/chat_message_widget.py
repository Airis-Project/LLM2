"""
チャットメッセージウィジェットモジュール
PyQt6を使用したチャットメッセージ表示コンポーネント
"""

import sys
from typing import Dict, Optional, Any, List
from datetime import datetime
import json

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
        QFrame, QPushButton, QScrollArea, QSizePolicy, QMenu,
        QApplication, QToolTip
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QSize
    from PyQt6.QtGui import (
        QFont, QColor, QPalette, QTextCursor, QTextCharFormat,
        QAction, QIcon, QPainter, QPixmap
    )
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

from ...core.logger import get_logger
from ...core.config_manager import get_config

class ChatMessage(QWidget):
    """チャットメッセージウィジェット"""
    
    # シグナル定義
    message_copied = pyqtSignal(str)  # メッセージがコピーされた時
    message_edited = pyqtSignal(str, str)  # メッセージが編集された時 (old, new)
    message_deleted = pyqtSignal(str)  # メッセージが削除された時
    
    def __init__(self, role: str, content: str, metadata: Optional[Dict] = None, parent=None):
        """
        初期化
        
        Args:
            role: メッセージの役割 ('user', 'assistant', 'system')
            content: メッセージ内容
            metadata: メタデータ（タイムスタンプ、モデル情報など）
            parent: 親ウィジェット
        """
        if not PYQT6_AVAILABLE:
            raise ImportError("PyQt6が利用できません")
        
        super().__init__(parent)
        
        self.role = role
        self.content = content
        self.metadata = metadata or {}
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        
        # 編集モード
        self.is_editing = False
        self.original_content = content
        
        # UI要素
        self.content_label = None
        self.content_edit = None
        self.timestamp_label = None
        self.role_label = None
        self.metadata_label = None
        
        self._setup_ui()
        self._setup_style()
        self._setup_context_menu()
        
        self.logger.debug(f"ChatMessage作成: role={role}, content_length={len(content)}")
    
    def _setup_ui(self):
        """UIを設定"""
        try:
            # メインレイアウト
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(10, 8, 10, 8)
            main_layout.setSpacing(4)
            
            # ヘッダー部分
            header_layout = QHBoxLayout()
            header_layout.setSpacing(8)
            
            # 役割ラベル
            self.role_label = QLabel(self._get_role_display_name())
            self.role_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            header_layout.addWidget(self.role_label)
            
            # タイムスタンプ
            timestamp = self.metadata.get('timestamp', datetime.now().isoformat())
            if isinstance(timestamp, str):
                try:
                    timestamp_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp_str = timestamp_dt.strftime('%H:%M:%S')
                except:
                    timestamp_str = timestamp[:8] if len(timestamp) >= 8 else timestamp
            else:
                timestamp_str = datetime.now().strftime('%H:%M:%S')
            
            self.timestamp_label = QLabel(timestamp_str)
            self.timestamp_label.setFont(QFont("Arial", 8))
            header_layout.addWidget(self.timestamp_label)
            
            # スペーサー
            header_layout.addStretch()
            
            # メタデータ情報
            if self.metadata.get('model'):
                self.metadata_label = QLabel(f"Model: {self.metadata['model']}")
                self.metadata_label.setFont(QFont("Arial", 8))
                header_layout.addWidget(self.metadata_label)
            
            main_layout.addLayout(header_layout)
            
            # コンテンツ部分
            self.content_label = QLabel()
            self.content_label.setWordWrap(True)
            self.content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.content_label.setFont(QFont("Arial", 10))
            self.content_label.setText(self.content)
            
            # 長いコンテンツの場合はスクロール可能にする
            if len(self.content) > 500:
                scroll_area = QScrollArea()
                scroll_area.setWidget(self.content_label)
                scroll_area.setWidgetResizable(True)
                scroll_area.setMaximumHeight(200)
                scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                main_layout.addWidget(scroll_area)
            else:
                main_layout.addWidget(self.content_label)
            
            # 編集用テキストエディット（初期は非表示）
            self.content_edit = QTextEdit()
            self.content_edit.setFont(QFont("Arial", 10))
            self.content_edit.setMaximumHeight(150)
            self.content_edit.hide()
            main_layout.addWidget(self.content_edit)
            
            # サイズポリシー設定
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            
        except Exception as e:
            self.logger.error(f"UI設定エラー: {e}")
            raise
    
    def _setup_style(self):
        """スタイルを設定"""
        try:
            # 役割に応じた色設定
            if self.role == 'user':
                bg_color = self.config.get('ui.chat.user_bg_color', '#E3F2FD')
                border_color = self.config.get('ui.chat.user_border_color', '#2196F3')
                role_color = '#1976D2'
            elif self.role == 'assistant':
                bg_color = self.config.get('ui.chat.assistant_bg_color', '#F3E5F5')
                border_color = self.config.get('ui.chat.assistant_border_color', '#9C27B0')
                role_color = '#7B1FA2'
            elif self.role == 'system':
                bg_color = self.config.get('ui.chat.system_bg_color', '#FFF3E0')
                border_color = self.config.get('ui.chat.system_border_color', '#FF9800')
                role_color = '#F57C00'
            else:
                bg_color = '#F5F5F5'
                border_color = '#BDBDBD'
                role_color = '#757575'
            
            # ウィジェットスタイル
            self.setStyleSheet(f"""
                ChatMessage {{
                    background-color: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: 8px;
                    margin: 2px;
                }}
                ChatMessage:hover {{
                    border-color: {self._darken_color(border_color)};
                }}
            """)
            
            # 役割ラベルの色
            if self.role_label:
                self.role_label.setStyleSheet(f"color: {role_color};")
            
            # タイムスタンプラベルの色
            if self.timestamp_label:
                self.timestamp_label.setStyleSheet("color: #666666;")
            
            # メタデータラベルの色
            if self.metadata_label:
                self.metadata_label.setStyleSheet("color: #888888;")
            
        except Exception as e:
            self.logger.error(f"スタイル設定エラー: {e}")
    
    def _setup_context_menu(self):
        """コンテキストメニューを設定"""
        try:
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.customContextMenuRequested.connect(self._show_context_menu)
            
        except Exception as e:
            self.logger.error(f"コンテキストメニュー設定エラー: {e}")
    
    def _show_context_menu(self, position: QPoint):
        """コンテキストメニューを表示"""
        try:
            menu = QMenu(self)
            
            # コピーアクション
            copy_action = QAction("コピー", self)
            copy_action.triggered.connect(self._copy_content)
            menu.addAction(copy_action)
            
            # 編集アクション（ユーザーメッセージのみ）
            if self.role == 'user':
                edit_action = QAction("編集", self)
                edit_action.triggered.connect(self._start_edit)
                menu.addAction(edit_action)
            
            # 削除アクション
            delete_action = QAction("削除", self)
            delete_action.triggered.connect(self._delete_message)
            menu.addAction(delete_action)
            
            menu.addSeparator()
            
            # 詳細情報アクション
            info_action = QAction("詳細情報", self)
            info_action.triggered.connect(self._show_info)
            menu.addAction(info_action)
            
            # メニューを表示
            menu.exec(self.mapToGlobal(position))
            
        except Exception as e:
            self.logger.error(f"コンテキストメニュー表示エラー: {e}")
    
    def _copy_content(self):
        """コンテンツをクリップボードにコピー"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.content)
            self.message_copied.emit(self.content)
            
            # ツールチップで通知
            QToolTip.showText(self.mapToGlobal(QPoint(0, 0)), "コピーしました", self)
            
        except Exception as e:
            self.logger.error(f"コピーエラー: {e}")
    
    def _start_edit(self):
        """編集モードを開始"""
        try:
            if self.role != 'user':
                return
            
            self.is_editing = True
            self.original_content = self.content
            
            # ラベルを隠してエディットを表示
            self.content_label.hide()
            self.content_edit.setPlainText(self.content)
            self.content_edit.show()
            self.content_edit.setFocus()
            
            # 編集完了のショートカット
            self.content_edit.keyPressEvent = self._edit_key_press_event
            
        except Exception as e:
            self.logger.error(f"編集開始エラー: {e}")
    
    def _edit_key_press_event(self, event):
        """編集中のキーイベント処理"""
        try:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self._finish_edit()
            elif event.key() == Qt.Key.Key_Escape:
                self._cancel_edit()
            else:
                QTextEdit.keyPressEvent(self.content_edit, event)
                
        except Exception as e:
            self.logger.error(f"編集キーイベントエラー: {e}")
    
    def _finish_edit(self):
        """編集を完了"""
        try:
            new_content = self.content_edit.toPlainText().strip()
            
            if new_content != self.original_content:
                old_content = self.content
                self.content = new_content
                self.content_label.setText(new_content)
                self.message_edited.emit(old_content, new_content)
            
            self._exit_edit_mode()
            
        except Exception as e:
            self.logger.error(f"編集完了エラー: {e}")
    
    def _cancel_edit(self):
        """編集をキャンセル"""
        try:
            self._exit_edit_mode()
            
        except Exception as e:
            self.logger.error(f"編集キャンセルエラー: {e}")
    
    def _exit_edit_mode(self):
        """編集モードを終了"""
        try:
            self.is_editing = False
            self.content_edit.hide()
            self.content_label.show()
            
        except Exception as e:
            self.logger.error(f"編集モード終了エラー: {e}")
    
    def _delete_message(self):
        """メッセージを削除"""
        try:
            self.message_deleted.emit(self.content)
            self.deleteLater()
            
        except Exception as e:
            self.logger.error(f"メッセージ削除エラー: {e}")
    
    def _show_info(self):
        """詳細情報を表示"""
        try:
            info_text = f"""
役割: {self._get_role_display_name()}
文字数: {len(self.content)}
タイムスタンプ: {self.metadata.get('timestamp', 'N/A')}
"""
            
            if self.metadata.get('model'):
                info_text += f"モデル: {self.metadata['model']}\n"
            
            if self.metadata.get('tokens'):
                info_text += f"トークン数: {self.metadata['tokens']}\n"
            
            if self.metadata.get('processing_time'):
                info_text += f"処理時間: {self.metadata['processing_time']:.2f}秒\n"
            
            QToolTip.showText(self.mapToGlobal(QPoint(0, 0)), info_text.strip(), self)
            
        except Exception as e:
            self.logger.error(f"詳細情報表示エラー: {e}")
    
    def _get_role_display_name(self) -> str:
        """役割の表示名を取得"""
        role_names = {
            'user': 'ユーザー',
            'assistant': 'アシスタント',
            'system': 'システム'
        }
        return role_names.get(self.role, self.role.capitalize())
    
    def _darken_color(self, color: str) -> str:
        """色を暗くする"""
        try:
            if color.startswith('#'):
                color = color[1:]
            
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            
            # 20%暗くする
            r = max(0, int(r * 0.8))
            g = max(0, int(g * 0.8))
            b = max(0, int(b * 0.8))
            
            return f"#{r:02x}{g:02x}{b:02x}"
            
        except:
            return color
    
    def get_content(self) -> str:
        """コンテンツを取得"""
        return self.content
    
    def get_role(self) -> str:
        """役割を取得"""
        return self.role
    
    def get_metadata(self) -> Dict:
        """メタデータを取得"""
        return self.metadata.copy()
    
    def update_content(self, content: str):
        """コンテンツを更新"""
        try:
            old_content = self.content
            self.content = content
            self.content_label.setText(content)
            
            if old_content != content:
                self.message_edited.emit(old_content, content)
                
        except Exception as e:
            self.logger.error(f"コンテンツ更新エラー: {e}")
    
    def update_metadata(self, metadata: Dict):
        """メタデータを更新"""
        try:
            self.metadata.update(metadata)
            
            # メタデータラベルを更新
            if self.metadata_label and self.metadata.get('model'):
                self.metadata_label.setText(f"Model: {self.metadata['model']}")
                
        except Exception as e:
            self.logger.error(f"メタデータ更新エラー: {e}")
    
    def set_highlight(self, highlight: bool):
        """ハイライト表示を設定"""
        try:
            if highlight:
                self.setStyleSheet(self.styleSheet() + """
                    ChatMessage {
                        border-width: 3px;
                        box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
                    }
                """)
            else:
                # 元のスタイルに戻す
                self._setup_style()
                
        except Exception as e:
            self.logger.error(f"ハイライト設定エラー: {e}")
    
    def sizeHint(self) -> QSize:
        """推奨サイズを返す"""
        try:
            # コンテンツの長さに基づいて高さを調整
            base_height = 80
            content_height = len(self.content) // 50 * 20  # 50文字ごとに20px追加
            return QSize(400, min(base_height + content_height, 300))
            
        except:
            return QSize(400, 80)
