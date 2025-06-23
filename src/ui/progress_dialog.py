# src/ui/progress_dialog.py
"""
Progress Dialog - 進捗表示ダイアログ

このモジュールは、長時間実行される処理の進捗を表示するダイアログを提供します。
プログレスバー、キャンセル機能、詳細情報表示などの機能を含みます。
"""

import time
from typing import Optional, Callable, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QIcon

from ..core.logger import get_logger

logger = get_logger(__name__)


class WorkerThread(QThread):
    """
    バックグラウンド処理を実行するワーカースレッド
    """
    
    # シグナル定義
    progress_updated = pyqtSignal(int)  # 進捗更新
    status_updated = pyqtSignal(str)    # ステータス更新
    detail_updated = pyqtSignal(str)    # 詳細情報更新
    finished_with_result = pyqtSignal(object)  # 完了（結果付き）
    error_occurred = pyqtSignal(str)    # エラー発生
    
    def __init__(self, task_func: Callable, *args, **kwargs):
        """
        ワーカースレッドを初期化
        
        Args:
            task_func: 実行するタスク関数
            *args: タスク関数の引数
            **kwargs: タスク関数のキーワード引数
        """
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False
        
    def run(self) -> None:
        """スレッドの実行"""
        try:
            # タスク実行
            result = self.task_func(
                progress_callback=self._progress_callback,
                status_callback=self._status_callback,
                detail_callback=self._detail_callback,
                is_cancelled_callback=self._is_cancelled_callback,
                *self.args,
                **self.kwargs
            )
            
            if not self._is_cancelled:
                self.finished_with_result.emit(result)
                
        except Exception as e:
            logger.error(f"Worker thread error: {e}")
            self.error_occurred.emit(str(e))
    
    def cancel(self) -> None:
        """処理をキャンセル"""
        self._is_cancelled = True
        logger.info("Worker thread cancellation requested")
    
    def _progress_callback(self, value: int) -> None:
        """進捗コールバック"""
        if not self._is_cancelled:
            self.progress_updated.emit(value)
    
    def _status_callback(self, status: str) -> None:
        """ステータスコールバック"""
        if not self._is_cancelled:
            self.status_updated.emit(status)
    
    def _detail_callback(self, detail: str) -> None:
        """詳細情報コールバック"""
        if not self._is_cancelled:
            self.detail_updated.emit(detail)
    
    def _is_cancelled_callback(self) -> bool:
        """キャンセル状態確認コールバック"""
        return self._is_cancelled


class ProgressDialog(QDialog):
    """
    進捗表示ダイアログクラス
    
    長時間実行される処理の進捗を表示し、ユーザーにフィードバックを提供します。
    キャンセル機能、詳細情報表示、自動クローズ機能などを含みます。
    """
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "処理中...",
        description: str = "処理を実行しています。しばらくお待ちください。",
        show_details: bool = True,
        cancelable: bool = True,
        auto_close: bool = True
    ):
        """
        ProgressDialogを初期化
        
        Args:
            parent: 親ウィジェット
            title: ダイアログタイトル
            description: 処理の説明
            show_details: 詳細情報表示の有無
            cancelable: キャンセル可能かどうか
            auto_close: 完了時の自動クローズ
        """
        super().__init__(parent)
        
        # 設定保存
        self.title = title
        self.description = description
        self.show_details = show_details
        self.cancelable = cancelable
        self.auto_close = auto_close
        
        # 状態管理
        self.worker_thread: Optional[WorkerThread] = None
        self.result: Any = None
        self.error_message: Optional[str] = None
        self.is_completed = False
        self.is_cancelled = False
        
        # UI初期化
        self._setup_ui()
        self._setup_timer()
        
        logger.debug(f"ProgressDialog initialized: {title}")
    
    def _setup_ui(self) -> None:
        """UIコンポーネントのセットアップ"""
        try:
            self.setWindowTitle(self.title)
            self.setFixedSize(450, 300 if self.show_details else 150)
            self.setWindowFlags(
                Qt.WindowType.Dialog | 
                Qt.WindowType.WindowTitleHint |
                (Qt.WindowType.WindowCloseButtonHint if self.cancelable else Qt.WindowType.CustomizeWindowHint)
            )
            
            # メインレイアウト
            layout = QVBoxLayout()
            layout.setSpacing(15)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # 説明ラベル
            self.description_label = QLabel(self.description)
            self.description_label.setWordWrap(True)
            self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.description_label)
            
            # プログレスバー
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(True)
            layout.addWidget(self.progress_bar)
            
            # ステータスラベル
            self.status_label = QLabel("準備中...")
            self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.status_label.setFont(QFont("Arial", 9))
            layout.addWidget(self.status_label)
            
            # 詳細情報（オプション）
            if self.show_details:
                # 区切り線
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setFrameShadow(QFrame.Shadow.Sunken)
                layout.addWidget(separator)
                
                # 詳細ラベル
                details_label = QLabel("詳細情報:")
                details_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                layout.addWidget(details_label)
                
                # 詳細テキスト
                self.details_text = QTextEdit()
                self.details_text.setReadOnly(True)
                self.details_text.setMaximumHeight(80)
                self.details_text.setFont(QFont("Courier", 8))
                layout.addWidget(self.details_text)
            
            # ボタンレイアウト
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            # キャンセルボタン
            if self.cancelable:
                self.cancel_button = QPushButton("キャンセル")
                self.cancel_button.clicked.connect(self._cancel_operation)
                button_layout.addWidget(self.cancel_button)
            
            # 閉じるボタン（初期は非表示）
            self.close_button = QPushButton("閉じる")
            self.close_button.clicked.connect(self.accept)
            self.close_button.setVisible(False)
            button_layout.addWidget(self.close_button)
            
            layout.addLayout(button_layout)
            self.setLayout(layout)
            
        except Exception as e:
            logger.error(f"UI setup failed: {e}")
            raise
    
    def _setup_timer(self) -> None:
        """タイマーのセットアップ"""
        # 経過時間表示用タイマー
        self.elapsed_timer = QTimer()
        self.elapsed_timer.timeout.connect(self._update_elapsed_time)
        self.start_time = time.time()
    
    def start_task(self, task_func: Callable, *args, **kwargs) -> None:
        """
        タスクを開始
        
        Args:
            task_func: 実行するタスク関数
            *args: タスク関数の引数
            **kwargs: タスク関数のキーワード引数
        """
        try:
            # ワーカースレッド作成
            self.worker_thread = WorkerThread(task_func, *args, **kwargs)
            
            # シグナル接続
            self.worker_thread.progress_updated.connect(self._update_progress)
            self.worker_thread.status_updated.connect(self._update_status)
            if self.show_details:
                self.worker_thread.detail_updated.connect(self._update_details)
            self.worker_thread.finished_with_result.connect(self._task_completed)
            self.worker_thread.error_occurred.connect(self._task_error)
            
            # タスク開始
            self.start_time = time.time()
            self.elapsed_timer.start(1000)  # 1秒間隔
            self.worker_thread.start()
            
            logger.info("Task started")
            
        except Exception as e:
            logger.error(f"Failed to start task: {e}")
            self.error_message = str(e)
            self._show_error()
    
    @pyqtSlot(int)
    def _update_progress(self, value: int) -> None:
        """進捗更新"""
        self.progress_bar.setValue(max(0, min(100, value)))
        QApplication.processEvents()
    
    @pyqtSlot(str)
    def _update_status(self, status: str) -> None:
        """ステータス更新"""
        self.status_label.setText(status)
        QApplication.processEvents()
    
    @pyqtSlot(str)
    def _update_details(self, detail: str) -> None:
        """詳細情報更新"""
        if self.show_details:
            self.details_text.append(f"[{time.strftime('%H:%M:%S')}] {detail}")
            # 自動スクロール
            scrollbar = self.details_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        QApplication.processEvents()
    
    @pyqtSlot(object)
    def _task_completed(self, result: Any) -> None:
        """タスク完了処理"""
        self.result = result
        self.is_completed = True
        
        # UI更新
        self.progress_bar.setValue(100)
        self.status_label.setText("完了")
        self.elapsed_timer.stop()
        
        if self.show_details:
            self.details_text.append(f"[{time.strftime('%H:%M:%S')}] 処理が完了しました")
        
        # ボタン切り替え
        if self.cancelable:
            self.cancel_button.setVisible(False)
        self.close_button.setVisible(True)
        
        logger.info("Task completed successfully")
        
        # 自動クローズ
        if self.auto_close:
            QTimer.singleShot(2000, self.accept)  # 2秒後に自動クローズ
    
    @pyqtSlot(str)
    def _task_error(self, error_message: str) -> None:
        """タスクエラー処理"""
        self.error_message = error_message
        self.elapsed_timer.stop()
        
        # UI更新
        self.status_label.setText("エラーが発生しました")
        if self.show_details:
            self.details_text.append(f"[{time.strftime('%H:%M:%S')}] エラー: {error_message}")
        
        # ボタン切り替え
        if self.cancelable:
            self.cancel_button.setText("閉じる")
        else:
            self.close_button.setVisible(True)
        
        logger.error(f"Task error: {error_message}")
        self._show_error()
    
    def _cancel_operation(self) -> None:
        """操作のキャンセル"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.cancel()
            self.is_cancelled = True
            
            self.status_label.setText("キャンセル中...")
            if self.show_details:
                self.details_text.append(f"[{time.strftime('%H:%M:%S')}] キャンセルが要求されました")
            
            # スレッド終了を待つ
            self.worker_thread.wait(3000)  # 3秒待機
            
            logger.info("Operation cancelled")
        
        self.reject()
    
    def _update_elapsed_time(self) -> None:
        """経過時間の更新"""
        if not self.is_completed and not self.is_cancelled:
            elapsed = int(time.time() - self.start_time)
            minutes, seconds = divmod(elapsed, 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            # プログレスバーのテキストに経過時間を表示
            current_value = self.progress_bar.value()
            self.progress_bar.setFormat(f"{current_value}% - {time_str}")
    
    def _show_error(self) -> None:
        """エラー表示"""
        self.progress_bar.setStyleSheet("""
            QProgressBar::chunk {
                background-color: #ff6b6b;
            }
        """)
    
    def get_result(self) -> Any:
        """結果を取得"""
        return self.result
    
    def get_error(self) -> Optional[str]:
        """エラーメッセージを取得"""
        return self.error_message
    
    def closeEvent(self, event) -> None:
        """ダイアログクローズイベント"""
        if self.worker_thread and self.worker_thread.isRunning():
            if self.cancelable:
                self._cancel_operation()
            else:
                event.ignore()
                return
        
        self.elapsed_timer.stop()
        super().closeEvent(event)


# 便利関数
def show_progress_dialog(
    parent,
    task_func: Callable,
    title: str = "処理中...",
    description: str = "処理を実行しています。",
    *args,
    **kwargs
) -> tuple[Any, Optional[str]]:
    """
    進捗ダイアログを表示してタスクを実行
    
    Args:
        parent: 親ウィジェット
        task_func: 実行するタスク関数
        title: ダイアログタイトル
        description: 処理の説明
        *args: タスク関数の引数
        **kwargs: タスク関数のキーワード引数
    
    Returns:
        tuple: (結果, エラーメッセージ)
    """
    dialog = ProgressDialog(parent, title, description)
    dialog.start_task(task_func, *args, **kwargs)
    
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        return dialog.get_result(), None
    else:
        return None, dialog.get_error() or "処理がキャンセルされました"


# テスト用のサンプルタスク
def sample_long_task(
    progress_callback=None,
    status_callback=None,
    detail_callback=None,
    is_cancelled_callback=None
):
    """サンプルの長時間タスク"""
    total_steps = 50
    
    for i in range(total_steps):
        if is_cancelled_callback and is_cancelled_callback():
            break
        
        # 進捗更新
        progress = int((i + 1) / total_steps * 100)
        if progress_callback:
            progress_callback(progress)
        
        # ステータス更新
        if status_callback:
            status_callback(f"ステップ {i + 1}/{total_steps} を処理中...")
        
        # 詳細情報更新
        if detail_callback:
            detail_callback(f"処理項目 {i + 1} を完了")
        
        # 処理をシミュレート
        time.sleep(0.1)
    
    return "処理が正常に完了しました"


if __name__ == "__main__":
    """テスト用のメイン関数"""
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Progress Dialog Test")
            self.setGeometry(100, 100, 300, 200)
            
            central_widget = QWidget()
            layout = QVBoxLayout()
            
            test_button = QPushButton("長時間処理をテスト")
            test_button.clicked.connect(self.test_progress)
            layout.addWidget(test_button)
            
            central_widget.setLayout(layout)
            self.setCentralWidget(central_widget)
        
        def test_progress(self):
            result, error = show_progress_dialog(
                self,
                sample_long_task,
                "テスト処理",
                "サンプルの長時間処理を実行しています..."
            )
            
            if error:
                print(f"エラー: {error}")
            else:
                print(f"結果: {result}")
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
