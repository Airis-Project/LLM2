# src/services/llm_service.py
"""
LLMサービス統合クラス
UI層とLLMクライアント間の仲介
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer

from src.llm_client_v2 import EnhancedLLMClient
from src.core.event_system import EventBus

logger = logging.getLogger(__name__)

class LLMServiceThread(QThread):
    """LLMサービス専用スレッド"""
    
    response_ready = pyqtSignal(dict)
    progress_updated = pyqtSignal(str, int)  # task_id, progress
    error_occurred = pyqtSignal(str, str)    # task_id, error
    
    def __init__(self, llm_client, task_queue):
        super().__init__()
        self.llm_client = llm_client
        self.task_queue = task_queue
        self.running = True
    
    def run(self):
        """スレッド実行"""
        while self.running:
            try:
                if not self.task_queue.empty():
                    task = self.task_queue.get()
                    self.process_task(task)
                else:
                    self.msleep(100)  # 100ms待機
                    
            except Exception as e:
                logger.error(f"LLMサービススレッドエラー: {e}")
    
    def process_task(self, task: Dict[str, Any]):
        """タスク処理"""
        try:
            task_id = task.get('id')
            prompt = task.get('prompt')
            task_type = task.get('task_type', 'general')
            priority = task.get('priority', 'balanced')
            
            self.progress_updated.emit(task_id, 10)
            
            # LLM実行
            result = self.llm_client.generate_code(
                prompt=prompt,
                task_type=task_type,
                priority=priority
            )
            
            self.progress_updated.emit(task_id, 100)
            
            # 結果にタスクIDを追加
            result['task_id'] = task_id
            self.response_ready.emit(result)
            
        except Exception as e:
            logger.error(f"タスク処理エラー: {e}")
            self.error_occurred.emit(task.get('id', 'unknown'), str(e))
    
    def stop(self):
        """スレッド停止"""
        self.running = False

class LLMService(QObject):
    """LLMサービス統合クラス"""
    
    # シグナル定義
    response_received = pyqtSignal(str, dict)  # task_id, result
    progress_updated = pyqtSignal(str, int)    # task_id, progress
    error_occurred = pyqtSignal(str, str)      # task_id, error
    status_changed = pyqtSignal(bool)          # is_available
    
    def __init__(self, config_manager, event_bus: Optional[EventBus] = None):
        super().__init__()
        
        self.config_manager = config_manager
        self.event_bus = event_bus
        
        # LLMクライアント初期化
        self.llm_client = EnhancedLLMClient()
        
        # タスク管理
        from queue import Queue
        self.task_queue = Queue()
        self.active_tasks = {}
        self.task_counter = 0
        
        # ワーカースレッド
        self.worker_thread = None
        
        # 状態監視タイマー
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_status)
        self.status_timer.start(10000)  # 10秒間隔
        
        self.setup_service()
        
        logger.info("LLMサービスが初期化されました")
    
    def setup_service(self):
        """サービス設定"""
        try:
            # ワーカースレッド開始
            self.start_worker_thread()
            
            # イベントバス接続
            if self.event_bus:
                self.event_bus.subscribe('llm_request', self.handle_event_request)
                self.event_bus.subscribe('llm_cancel', self.handle_event_cancel)
            
            # 初期状態チェック
            self.check_status()
            
        except Exception as e:
            logger.error(f"LLMサービス設定エラー: {e}")
    
    def start_worker_thread(self):
        """ワーカースレッド開始"""
        try:
            if self.worker_thread and self.worker_thread.isRunning():
                return
            
            self.worker_thread = LLMServiceThread(self.llm_client, self.task_queue)
            self.worker_thread.response_ready.connect(self.on_response_ready)
            self.worker_thread.progress_updated.connect(self.progress_updated.emit)
            self.worker_thread.error_occurred.connect(self.error_occurred.emit)
            
            self.worker_thread.start()
            logger.info("LLMワーカースレッドが開始されました")
            
        except Exception as e:
            logger.error(f"ワーカースレッド開始エラー: {e}")
    
    def submit_request(self, prompt: str, task_type: str = 'general', 
                      priority: str = 'balanced', callback: Optional[Callable] = None) -> str:
        """LLMリクエスト送信"""
        try:
            # タスクID生成
            self.task_counter += 1
            task_id = f"task_{self.task_counter}"
            
            # タスク作成
            task = {
                'id': task_id,
                'prompt': prompt,
                'task_type': task_type,
                'priority': priority,
                'callback': callback,
                'timestamp': self.get_current_timestamp()
            }
            
            # タスクキューに追加
            self.task_queue.put(task)
            self.active_tasks[task_id] = task
            
            logger.info(f"LLMリクエスト送信: {task_id} ({task_type})")
            
            return task_id
            
        except Exception as e:
            logger.error(f"リクエスト送信エラー: {e}")
            raise
    
    def cancel_request(self, task_id: str) -> bool:
        """リクエストキャンセル"""
        try:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                logger.info(f"リクエストキャンセル: {task_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"リクエストキャンセルエラー: {e}")
            return False
    
    def on_response_ready(self, result: Dict[str, Any]):
        """レスポンス受信処理"""
        try:
            task_id = result.get('task_id')
            
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                
                # コールバック実行
                if task.get('callback'):
                    task['callback'](result)
                
                # シグナル発行
                self.response_received.emit(task_id, result)
                
                # タスク完了
                del self.active_tasks[task_id]
                
                logger.info(f"レスポンス処理完了: {task_id}")
            
        except Exception as e:
            logger.error(f"レスポンス処理エラー: {e}")
    
    def check_status(self):
        """サービス状態チェック"""
        try:
            is_available = self.llm_client.is_available()
            self.status_changed.emit(is_available)
            
            # 統計情報更新
            if hasattr(self, '_last_status') and self._last_status != is_available:
                logger.info(f"LLMサービス状態変更: {'利用可能' if is_available else '利用不可'}")
            
            self._last_status = is_available
            
        except Exception as e:
            logger.error(f"状態チェックエラー: {e}")
    
    def get_service_info(self) -> Dict[str, Any]:
        """サービス情報取得"""
        try:
            return {
                'is_available': self.llm_client.is_available(),
                'available_models': self.llm_client.list_available_models(),
                'active_tasks': len(self.active_tasks),
                'queue_size': self.task_queue.qsize(),
                'performance_stats': self.llm_client.get_performance_stats()
            }
        except Exception as e:
            logger.error(f"サービス情報取得エラー: {e}")
            return {}
    
    def handle_event_request(self, event_data: Dict[str, Any]):
        """イベントバス経由のリクエスト処理"""
        try:
            prompt = event_data.get('prompt')
            task_type = event_data.get('task_type', 'general')
            priority = event_data.get('priority', 'balanced')
            
            if prompt:
                self.submit_request(prompt, task_type, priority)
                
        except Exception as e:
            logger.error(f"イベントリクエスト処理エラー: {e}")
    
    def handle_event_cancel(self, event_data: Dict[str, Any]):
        """イベントバス経由のキャンセル処理"""
        try:
            task_id = event_data.get('task_id')
            if task_id:
                self.cancel_request(task_id)
                
        except Exception as e:
            logger.error(f"イベントキャンセル処理エラー: {e}")
    
    def get_current_timestamp(self):
        """現在のタイムスタンプ取得"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def shutdown(self):
        """サービス終了"""
        try:
            # タイマー停止
            if self.status_timer:
                self.status_timer.stop()
            
            # ワーカースレッド停止
            if self.worker_thread and self.worker_thread.isRunning():
                self.worker_thread.stop()
                self.worker_thread.wait(5000)  # 5秒待機
            
            logger.info("LLMサービスが終了されました")
            
        except Exception as e:
            logger.error(f"サービス終了エラー: {e}")
