# src/core/event_system.py
"""
イベントシステムモジュール
アプリケーション全体でのイベント駆動型アーキテクチャを提供
イベントの発行、購読、処理を管理
"""

import threading
import queue
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import weakref
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

from .logger import get_logger
from .config_manager import get_config

logger = get_logger(__name__)

class EventPriority(Enum):
    """イベント優先度"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Event:
    """イベントデータクラス"""
    name: str
    data: Any = None
    source: str = ""
    priority: EventPriority = EventPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(int(time.time() * 1000000)))
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'name': self.name,
            'data': self.data,
            'source': self.source,
            'priority': self.priority.name,
            'timestamp': self.timestamp.isoformat(),
            'event_id': self.event_id,
            'tags': self.tags,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """辞書からイベントを作成"""
        return cls(
            name=data['name'],
            data=data.get('data'),
            source=data.get('source', ''),
            priority=EventPriority[data.get('priority', 'NORMAL')],
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            event_id=data.get('event_id', ''),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {})
        )

@dataclass
class EventSubscription:
    """イベント購読情報"""
    event_name: str
    callback: Callable
    priority: int = 0
    once: bool = False
    condition: Optional[Callable[[Event], bool]] = None
    subscriber_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)

class EventFilter:
    """イベントフィルタークラス"""
    
    def __init__(self):
        """初期化"""
        self.filters: List[Callable[[Event], bool]] = []
    
    def add_filter(self, filter_func: Callable[[Event], bool]):
        """フィルターを追加"""
        self.filters.append(filter_func)
    
    def remove_filter(self, filter_func: Callable[[Event], bool]):
        """フィルターを削除"""
        if filter_func in self.filters:
            self.filters.remove(filter_func)
    
    def apply(self, event: Event) -> bool:
        """フィルターを適用"""
        for filter_func in self.filters:
            try:
                if not filter_func(event):
                    return False
            except Exception as e:
                logger.error(f"イベントフィルターエラー: {e}")
                return False
        return True

class EventHistory:
    """イベント履歴管理クラス"""
    
    def __init__(self, max_size: int = 1000):
        """
        初期化
        
        Args:
            max_size: 最大履歴サイズ
        """
        self.max_size = max_size
        self.events: List[Event] = []
        self.lock = threading.Lock()
    
    def add_event(self, event: Event):
        """イベントを履歴に追加"""
        with self.lock:
            self.events.append(event)
            
            # サイズ制限を適用
            if len(self.events) > self.max_size:
                self.events = self.events[-self.max_size:]
    
    def get_events(self, 
                   event_name: Optional[str] = None,
                   source: Optional[str] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[Event]:
        """
        イベントを検索
        
        Args:
            event_name: イベント名フィルター
            source: ソースフィルター
            start_time: 開始時刻フィルター
            end_time: 終了時刻フィルター
            limit: 結果数制限
            
        Returns:
            List[Event]: フィルターされたイベントリスト
        """
        with self.lock:
            filtered_events = self.events.copy()
        
        # フィルターを適用
        if event_name:
            filtered_events = [e for e in filtered_events if e.name == event_name]
        
        if source:
            filtered_events = [e for e in filtered_events if e.source == source]
        
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        
        # 時刻でソート（新しい順）
        filtered_events.sort(key=lambda e: e.timestamp, reverse=True)
        
        # 制限を適用
        if limit:
            filtered_events = filtered_events[:limit]
        
        return filtered_events
    
    def clear(self):
        """履歴をクリア"""
        with self.lock:
            self.events.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        with self.lock:
            events = self.events.copy()
        
        if not events:
            return {}
        
        # イベント名別カウント
        event_counts = {}
        source_counts = {}
        priority_counts = {}
        
        for event in events:
            event_counts[event.name] = event_counts.get(event.name, 0) + 1
            source_counts[event.source] = source_counts.get(event.source, 0) + 1
            priority_counts[event.priority.name] = priority_counts.get(event.priority.name, 0) + 1
        
        return {
            'total_events': len(events),
            'event_counts': event_counts,
            'source_counts': source_counts,
            'priority_counts': priority_counts,
            'oldest_event': min(events, key=lambda e: e.timestamp).timestamp.isoformat(),
            'newest_event': max(events, key=lambda e: e.timestamp).timestamp.isoformat()
        }

class EventBus:
    """イベントバスクラス"""
    
    def __init__(self, max_workers: int = 4):
        """
        初期化
        
        Args:
            max_workers: 最大ワーカー数
        """
        # 購読者管理
        self.subscriptions: Dict[str, List[EventSubscription]] = {}
        self.global_subscriptions: List[EventSubscription] = []
        
        # スレッド管理
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # イベントキュー
        self.event_queue = queue.PriorityQueue()
        self.processing_thread = None
        self.running = False
        
        # コンポーネント
        self.filter = EventFilter()
        self.history = EventHistory()
        
        # 統計情報
        self.stats = {
            'events_emitted': 0,
            'events_processed': 0,
            'events_failed': 0,
            'subscribers_count': 0
        }
        
        self.logger = get_logger(__name__)
        
        # 処理スレッドを開始
        self.start()
    
    def start(self):
        """イベント処理を開始"""
        if not self.running:
            self.running = True
            self.processing_thread = threading.Thread(target=self._process_events, daemon=True)
            self.processing_thread.start()
            self.logger.info("イベントバスを開始しました")
    
    def stop(self):
        """イベント処理を停止"""
        if self.running:
            self.running = False
            
            # 停止イベントを送信
            self.event_queue.put((0, None))
            
            if self.processing_thread:
                self.processing_thread.join(timeout=5.0)
            
            self.executor.shutdown(wait=True)
            self.logger.info("イベントバスを停止しました")
    
    def emit(self, event: Union[Event, str], data: Any = None, **kwargs):
        """
        イベントを発行
        
        Args:
            event: イベントオブジェクトまたはイベント名
            data: イベントデータ
            **kwargs: 追加パラメータ
        """
        try:
            # イベントオブジェクトを作成
            if isinstance(event, str):
                event_obj = Event(name=event, data=data, **kwargs)
            else:
                event_obj = event
            
            # フィルターを適用
            if not self.filter.apply(event_obj):
                return
            
            # 履歴に追加
            self.history.add_event(event_obj)
            
            # キューに追加
            priority_value = 5 - event_obj.priority.value  # 優先度を逆転（高い値ほど優先）
            self.event_queue.put((priority_value, event_obj))
            
            # 統計を更新
            self.stats['events_emitted'] += 1
            
        except Exception as e:
            self.logger.error(f"イベント発行エラー: {e}")
    
    def subscribe(self, 
                  event_name: str, 
                  callback: Callable,
                  priority: int = 0,
                  once: bool = False,
                  condition: Optional[Callable[[Event], bool]] = None,
                  subscriber_id: str = "") -> str:
        """
        イベントを購読
        
        Args:
            event_name: イベント名（"*"で全イベント）
            callback: コールバック関数
            priority: 優先度（高い値ほど先に実行）
            once: 一度だけ実行するか
            condition: 実行条件
            subscriber_id: 購読者ID
            
        Returns:
            str: 購読ID
        """
        try:
            subscription = EventSubscription(
                event_name=event_name,
                callback=callback,
                priority=priority,
                once=once,
                condition=condition,
                subscriber_id=subscriber_id or f"sub_{int(time.time() * 1000000)}"
            )
            
            with self.lock:
                if event_name == "*":
                    self.global_subscriptions.append(subscription)
                else:
                    if event_name not in self.subscriptions:
                        self.subscriptions[event_name] = []
                    self.subscriptions[event_name].append(subscription)
                
                # 優先度でソート
                if event_name == "*":
                    self.global_subscriptions.sort(key=lambda s: s.priority, reverse=True)
                else:
                    self.subscriptions[event_name].sort(key=lambda s: s.priority, reverse=True)
                
                self.stats['subscribers_count'] += 1
            
            self.logger.debug(f"イベント購読を追加しました: {event_name}")
            return subscription.subscriber_id
            
        except Exception as e:
            self.logger.error(f"イベント購読エラー: {e}")
            return ""
    
    def unsubscribe(self, event_name: str, subscriber_id: str) -> bool:
        """
        イベント購読を解除
        
        Args:
            event_name: イベント名
            subscriber_id: 購読者ID
            
        Returns:
            bool: 解除成功フラグ
        """
        try:
            with self.lock:
                if event_name == "*":
                    self.global_subscriptions = [
                        s for s in self.global_subscriptions 
                        if s.subscriber_id != subscriber_id
                    ]
                else:
                    if event_name in self.subscriptions:
                        original_count = len(self.subscriptions[event_name])
                        self.subscriptions[event_name] = [
                            s for s in self.subscriptions[event_name] 
                            if s.subscriber_id != subscriber_id
                        ]
                        
                        if len(self.subscriptions[event_name]) < original_count:
                            self.stats['subscribers_count'] -= 1
                            self.logger.debug(f"イベント購読を解除しました: {event_name}")
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"イベント購読解除エラー: {e}")
            return False
    
    def unsubscribe_all(self, subscriber_id: str) -> int:
        """
        指定購読者の全購読を解除
        
        Args:
            subscriber_id: 購読者ID
            
        Returns:
            int: 解除した購読数
        """
        count = 0
        
        try:
            with self.lock:
                # グローバル購読を解除
                original_global_count = len(self.global_subscriptions)
                self.global_subscriptions = [
                    s for s in self.global_subscriptions 
                    if s.subscriber_id != subscriber_id
                ]
                count += original_global_count - len(self.global_subscriptions)
                
                # 個別購読を解除
                for event_name in list(self.subscriptions.keys()):
                    original_count = len(self.subscriptions[event_name])
                    self.subscriptions[event_name] = [
                        s for s in self.subscriptions[event_name] 
                        if s.subscriber_id != subscriber_id
                    ]
                    count += original_count - len(self.subscriptions[event_name])
                    
                    # 空になったら削除
                    if not self.subscriptions[event_name]:
                        del self.subscriptions[event_name]
                
                self.stats['subscribers_count'] -= count
            
            if count > 0:
                self.logger.debug(f"{count}個のイベント購読を解除しました: {subscriber_id}")
            
            return count
            
        except Exception as e:
            self.logger.error(f"全イベント購読解除エラー: {e}")
            return 0
    
    def _process_events(self):
        """イベント処理メインループ"""
        while self.running:
            try:
                # イベントを取得（タイムアウト付き）
                try:
                    priority, event = self.event_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 停止シグナルをチェック
                if event is None:
                    break
                
                # イベントを処理
                self._handle_event(event)
                self.stats['events_processed'] += 1
                
            except Exception as e:
                self.logger.error(f"イベント処理エラー: {e}")
                self.stats['events_failed'] += 1
    
    def _handle_event(self, event: Event):
        """イベントを処理"""
        try:
            # 購読者を取得
            subscribers = []
            
            with self.lock:
                # 特定イベントの購読者
                if event.name in self.subscriptions:
                    subscribers.extend(self.subscriptions[event.name])
                
                # グローバル購読者
                subscribers.extend(self.global_subscriptions)
            
            # 購読者がいない場合は終了
            if not subscribers:
                return
            
            # 購読者を実行
            for subscription in subscribers:
                try:
                    # 条件をチェック
                    if subscription.condition and not subscription.condition(event):
                        continue
                    
                    # コールバックを実行
                    self.executor.submit(self._execute_callback, subscription, event)
                    
                    # 一度だけの場合は削除
                    if subscription.once:
                        self._remove_subscription(subscription)
                        
                except Exception as e:
                    self.logger.error(f"購読者実行エラー: {e}")
            
        except Exception as e:
            self.logger.error(f"イベントハンドリングエラー: {e}")
    
    def _execute_callback(self, subscription: EventSubscription, event: Event):
        """コールバックを実行"""
        try:
            # 弱参照の場合は有効性をチェック
            if isinstance(subscription.callback, weakref.ref):
                callback = subscription.callback()
                if callback is None:
                    # 参照が無効になった場合は削除
                    self._remove_subscription(subscription)
                    return
            else:
                callback = subscription.callback
            
            # コールバックを実行
            if asyncio.iscoroutinefunction(callback):
                # 非同期関数の場合
                asyncio.create_task(callback(event))
            else:
                # 同期関数の場合
                callback(event)
                
        except Exception as e:
            self.logger.error(f"コールバック実行エラー: {e}")
    
    def _remove_subscription(self, subscription: EventSubscription):
        """購読を削除"""
        try:
            with self.lock:
                if subscription.event_name == "*":
                    if subscription in self.global_subscriptions:
                        self.global_subscriptions.remove(subscription)
                        self.stats['subscribers_count'] -= 1
                else:
                    if (subscription.event_name in self.subscriptions and 
                        subscription in self.subscriptions[subscription.event_name]):
                        self.subscriptions[subscription.event_name].remove(subscription)
                        self.stats['subscribers_count'] -= 1
                        
                        # 空になったら削除
                        if not self.subscriptions[subscription.event_name]:
                            del self.subscriptions[subscription.event_name]
                            
        except Exception as e:
            self.logger.error(f"購読削除エラー: {e}")
    
    def get_subscribers(self, event_name: Optional[str] = None) -> List[EventSubscription]:
        """
        購読者一覧を取得
        
        Args:
            event_name: イベント名（Noneの場合は全て）
            
        Returns:
            List[EventSubscription]: 購読者リスト
        """
        subscribers = []
        
        with self.lock:
            if event_name is None:
                # 全購読者
                for subs in self.subscriptions.values():
                    subscribers.extend(subs)
                subscribers.extend(self.global_subscriptions)
            elif event_name == "*":
                # グローバル購読者のみ
                subscribers.extend(self.global_subscriptions)
            else:
                # 特定イベントの購読者
                if event_name in self.subscriptions:
                    subscribers.extend(self.subscriptions[event_name])
        
        return subscribers
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        with self.lock:
            stats = self.stats.copy()
        
        # 履歴統計を追加
        history_stats = self.history.get_statistics()
        stats.update({
            'history': history_stats,
            'queue_size': self.event_queue.qsize(),
            'subscription_count_by_event': {
                event_name: len(subs) 
                for event_name, subs in self.subscriptions.items()
            },
            'global_subscriptions': len(self.global_subscriptions)
        })
        
        return stats
    
    def clear_history(self):
        """履歴をクリア"""
        self.history.clear()
    
    def add_filter(self, filter_func: Callable[[Event], bool]):
        """フィルターを追加"""
        self.filter.add_filter(filter_func)
    
    def remove_filter(self, filter_func: Callable[[Event], bool]):
        """フィルターを削除"""
        self.filter.remove_filter(filter_func)

class EventSystem:
    """イベントシステムクラス"""
    
    def __init__(self):
        """初期化"""
        config = get_config()
        event_config = config.get('event_system', {})
        
        max_workers = event_config.get('max_workers', 4)
        self.event_bus = EventBus(max_workers)
        
        self.logger = get_logger(__name__)
        self.logger.info("イベントシステムを初期化しました")
    
    def emit(self, event: Union[Event, str], data: Any = None, **kwargs):
        """イベントを発行"""
        self.event_bus.emit(event, data, **kwargs)
    
    def subscribe(self, event_name: str, callback: Callable, **kwargs) -> str:
        """イベントを購読"""
        return self.event_bus.subscribe(event_name, callback, **kwargs)
    
    def unsubscribe(self, event_name: str, subscriber_id: str) -> bool:
        """イベント購読を解除"""
        return self.event_bus.unsubscribe(event_name, subscriber_id)
    
    def unsubscribe_all(self, subscriber_id: str) -> int:
        """全イベント購読を解除"""
        return self.event_bus.unsubscribe_all(subscriber_id)
    
    def get_history(self, **filters) -> List[Event]:
        """イベント履歴を取得"""
        return self.event_bus.history.get_events(**filters)
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return self.event_bus.get_statistics()
    
    def add_filter(self, filter_func: Callable[[Event], bool]):
        """フィルターを追加"""
        self.event_bus.add_filter(filter_func)
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        self.event_bus.stop()
        self.logger.info("イベントシステムをクリーンアップしました")

# グローバルイベントシステムインスタンス
event_system = EventSystem()

def get_event_system() -> EventSystem:
    """グローバルイベントシステムを取得"""
    return event_system
