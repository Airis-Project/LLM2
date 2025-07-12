# src/utils/performance_monitor.py
"""
パフォーマンス監視システム
リアルタイムでシステムリソースを監視し、統計情報とアラートを提供
"""

import time
import threading
import queue
import json
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor
import asyncio
from contextlib import contextmanager
from enum import Enum, auto
import warnings
import gc
import tracemalloc
import sys

from src.core.logger import get_logger
from src.core.exceptions import SystemError, ConfigurationError, ValidationError
from src.core.event_system import get_event_system, Event
from src.utils.system_utils import get_system_utils, ResourceUsage, SystemInfo

logger = get_logger(__name__)


class AlertLevel(Enum):
    """アラートレベル"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class MetricType(Enum):
    """メトリクス種別"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESS = "process"
    CUSTOM = "custom"


@dataclass
class PerformanceMetric:
    """パフォーマンスメトリクス"""
    timestamp: datetime
    metric_type: MetricType
    name: str
    value: float
    unit: str
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で返す"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['metric_type'] = self.metric_type.value
        return data
    
    def to_json(self) -> str:
        """JSON文字列で返す"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class PerformanceAlert:
    """パフォーマンスアラート"""
    timestamp: datetime
    level: AlertLevel
    metric_type: MetricType
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で返す"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        data['metric_type'] = self.metric_type.value
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data
    
    def resolve(self):
        """アラートを解決済みにマーク"""
        self.resolved = True
        self.resolved_at = datetime.now(tz=timezone.utc)


@dataclass
class PerformanceStatistics:
    """パフォーマンス統計"""
    metric_name: str
    count: int
    min_value: float
    max_value: float
    mean_value: float
    median_value: float
    std_deviation: float
    percentile_95: float
    percentile_99: float
    start_time: datetime
    end_time: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で返す"""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        return data


@dataclass
class ThresholdConfig:
    """閾値設定"""
    metric_name: str
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    emergency_threshold: Optional[float] = None
    comparison_operator: str = ">"  # >, <, >=, <=, ==, !=
    duration_seconds: float = 0  # 継続時間（秒）
    enabled: bool = True
    
    def check_threshold(self, value: float) -> Optional[AlertLevel]:
        """閾値チェック"""
        if not self.enabled:
            return None
        
        def compare(val: float, threshold: float) -> bool:
            if self.comparison_operator == ">":
                return val > threshold
            elif self.comparison_operator == "<":
                return val < threshold
            elif self.comparison_operator == ">=":
                return val >= threshold
            elif self.comparison_operator == "<=":
                return val <= threshold
            elif self.comparison_operator == "==":
                return val == threshold
            elif self.comparison_operator == "!=":
                return val != threshold
            return False
        
        if self.emergency_threshold is not None and compare(value, self.emergency_threshold):
            return AlertLevel.EMERGENCY
        elif self.critical_threshold is not None and compare(value, self.critical_threshold):
            return AlertLevel.CRITICAL
        elif self.warning_threshold is not None and compare(value, self.warning_threshold):
            return AlertLevel.WARNING
        
        return None


class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self, 
                 collection_interval: float = 1.0,
                 history_size: int = 1000,
                 enable_memory_profiling: bool = False):
        """
        初期化
        
        Args:
            collection_interval: データ収集間隔（秒）
            history_size: 履歴保持サイズ
            enable_memory_profiling: メモリプロファイリング有効化
        """
        self.logger = get_logger(self.__class__.__name__)
        self.collection_interval = collection_interval
        self.history_size = history_size
        self.enable_memory_profiling = enable_memory_profiling
        
        # システムユーティリティ
        self.system_utils = get_system_utils()
        
        # イベントシステム
        self.event_system = get_event_system()
        
        # データ保存
        self.metrics_history: deque = deque(maxlen=history_size)
        self.alerts_history: deque = deque(maxlen=history_size)
        self.custom_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        
        # 閾値設定
        self.thresholds: Dict[str, ThresholdConfig] = {}
        self._setup_default_thresholds()
        
        # 監視状態
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # コールバック
        self.metric_callbacks: List[Callable[[PerformanceMetric], None]] = []
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # 統計計算用
        self.stats_cache: Dict[str, PerformanceStatistics] = {}
        self.stats_cache_time: Dict[str, datetime] = {}
        self.stats_cache_ttl = 60  # 1分
        
        # アラート状態管理
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_durations: Dict[str, datetime] = {}
        
        # スレッドプール
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="PerfMonitor")
        
        # メモリプロファイリング
        if self.enable_memory_profiling:
            tracemalloc.start()
        
        self.logger.info(f"PerformanceMonitor初期化完了 (間隔: {collection_interval}秒)")
    
    def _setup_default_thresholds(self):
        """デフォルト閾値設定"""
        # CPU使用率
        self.thresholds["cpu_percent"] = ThresholdConfig(
            metric_name="cpu_percent",
            warning_threshold=70.0,
            critical_threshold=85.0,
            emergency_threshold=95.0,
            comparison_operator=">",
            duration_seconds=10.0
        )
        
        # メモリ使用率
        self.thresholds["memory_percent"] = ThresholdConfig(
            metric_name="memory_percent",
            warning_threshold=75.0,
            critical_threshold=90.0,
            emergency_threshold=95.0,
            comparison_operator=">",
            duration_seconds=5.0
        )
        
        # ディスク使用率
        self.thresholds["disk_usage_percent"] = ThresholdConfig(
            metric_name="disk_usage_percent",
            warning_threshold=80.0,
            critical_threshold=90.0,
            emergency_threshold=95.0,
            comparison_operator=">",
            duration_seconds=0.0
        )
        
        # ネットワーク送信レート（MB/s）
        self.thresholds["network_send_rate"] = ThresholdConfig(
            metric_name="network_send_rate",
            warning_threshold=50.0,
            critical_threshold=100.0,
            emergency_threshold=200.0,
            comparison_operator=">",
            duration_seconds=30.0
        )
    
    def start_monitoring(self) -> bool:
        """監視開始"""
        try:
            if self.is_monitoring:
                self.logger.warning("監視は既に開始されています")
                return True
            
            self.logger.info("パフォーマンス監視を開始します")
            
            # 停止イベントをリセット
            self.stop_event.clear()
            
            # 監視スレッド開始
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                name="PerformanceMonitor",
                daemon=True
            )
            self.monitor_thread.start()
            
            self.is_monitoring = True
            
            # イベント発行
            self.event_system.emit(Event(
                name="performance_monitoring_started",
                data={"interval": self.collection_interval}
            ))
            
            self.logger.info("パフォーマンス監視開始完了")
            return True
            
        except Exception as e:
            self.logger.error(f"パフォーマンス監視開始エラー: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """監視停止"""
        try:
            if not self.is_monitoring:
                self.logger.warning("監視は開始されていません")
                return True
            
            self.logger.info("パフォーマンス監視を停止します")
            
            # 停止シグナル
            self.stop_event.set()
            
            # スレッド終了待機
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5.0)
                if self.monitor_thread.is_alive():
                    self.logger.warning("監視スレッドの終了がタイムアウトしました")
            
            self.is_monitoring = False
            
            # イベント発行
            self.event_system.emit(Event(
                name="performance_monitoring_stopped",
                data={}
            ))
            
            self.logger.info("パフォーマンス監視停止完了")
            return True
            
        except Exception as e:
            self.logger.error(f"パフォーマンス監視停止エラー: {e}")
            return False
    
    def _monitoring_loop(self):
        """監視ループ"""
        self.logger.debug("監視ループ開始")
        
        last_network_stats = None
        last_network_time = None
        
        while not self.stop_event.is_set():
            try:
                start_time = time.time()
                
                # システムリソース取得
                resource_usage = self.system_utils.get_resource_usage()
                
                # 基本メトリクス記録
                self._record_basic_metrics(resource_usage)
                
                # ネットワークレート計算
                current_time = time.time()
                if last_network_stats and last_network_time:
                    time_diff = current_time - last_network_time
                    if time_diff > 0:
                        send_rate = (resource_usage.network_sent_bytes - last_network_stats[0]) / time_diff / (1024 * 1024)  # MB/s
                        recv_rate = (resource_usage.network_recv_bytes - last_network_stats[1]) / time_diff / (1024 * 1024)  # MB/s
                        
                        self._record_metric(MetricType.NETWORK, "network_send_rate", send_rate, "MB/s")
                        self._record_metric(MetricType.NETWORK, "network_recv_rate", recv_rate, "MB/s")
                
                last_network_stats = (resource_usage.network_sent_bytes, resource_usage.network_recv_bytes)
                last_network_time = current_time
                
                # メモリプロファイリング
                if self.enable_memory_profiling:
                    self._record_memory_profiling()
                
                # カスタムメトリクス処理
                self._process_custom_metrics()
                
                # 処理時間計算
                processing_time = time.time() - start_time
                self._record_metric(MetricType.CUSTOM, "monitoring_processing_time", processing_time * 1000, "ms")
                
                # 次の収集まで待機
                sleep_time = max(0, self.collection_interval - processing_time)
                if self.stop_event.wait(sleep_time):
                    break
                    
            except Exception as e:
                self.logger.error(f"監視ループエラー: {e}")
                # エラー時は短時間待機してリトライ
                if self.stop_event.wait(1.0):
                    break
        
        self.logger.debug("監視ループ終了")
    
    def _record_basic_metrics(self, resource_usage: ResourceUsage):
        """基本メトリクス記録"""
        timestamp = resource_usage.timestamp
        
        # CPU
        self._record_metric(MetricType.CPU, "cpu_percent", resource_usage.cpu_percent, "%", timestamp)
        
        # メモリ
        self._record_metric(MetricType.MEMORY, "memory_percent", resource_usage.memory_percent, "%", timestamp)
        self._record_metric(MetricType.MEMORY, "memory_used", resource_usage.memory_used / (1024**3), "GB", timestamp)
        self._record_metric(MetricType.MEMORY, "memory_available", resource_usage.memory_available / (1024**3), "GB", timestamp)
        
        # ディスク
        self._record_metric(MetricType.DISK, "disk_usage_percent", resource_usage.disk_usage_percent, "%", timestamp)
        self._record_metric(MetricType.DISK, "disk_read_bytes", resource_usage.disk_read_bytes / (1024**2), "MB", timestamp)
        self._record_metric(MetricType.DISK, "disk_write_bytes", resource_usage.disk_write_bytes / (1024**2), "MB", timestamp)
        
        # ネットワーク（累積）
        self._record_metric(MetricType.NETWORK, "network_sent_bytes", resource_usage.network_sent_bytes / (1024**2), "MB", timestamp)
        self._record_metric(MetricType.NETWORK, "network_recv_bytes", resource_usage.network_recv_bytes / (1024**2), "MB", timestamp)
    
    def _record_memory_profiling(self):
        """メモリプロファイリング記録"""
        try:
            if not tracemalloc.is_tracing():
                return
            
            current, peak = tracemalloc.get_traced_memory()
            
            self._record_metric(MetricType.MEMORY, "memory_traced_current", current / (1024**2), "MB")
            self._record_metric(MetricType.MEMORY, "memory_traced_peak", peak / (1024**2), "MB")
            
            # ガベージコレクション統計
            gc_stats = gc.get_stats()
            if gc_stats:
                for i, stat in enumerate(gc_stats):
                    self._record_metric(MetricType.MEMORY, f"gc_generation_{i}_collections", stat['collections'], "count")
                    self._record_metric(MetricType.MEMORY, f"gc_generation_{i}_collected", stat['collected'], "count")
                    self._record_metric(MetricType.MEMORY, f"gc_generation_{i}_uncollectable", stat['uncollectable'], "count")
            
        except Exception as e:
            self.logger.debug(f"メモリプロファイリングエラー: {e}")
    
    def _process_custom_metrics(self):
        """カスタムメトリクス処理"""
        # プロセス数
        try:
            import psutil
            process_count = len(psutil.pids())
            self._record_metric(MetricType.PROCESS, "process_count", process_count, "count")
        except Exception:
            pass
        
        # Python固有メトリクス
        self._record_metric(MetricType.CUSTOM, "python_thread_count", threading.active_count(), "count")
        self._record_metric(MetricType.CUSTOM, "python_objects_count", len(gc.get_objects()), "count")
    
    def _record_metric(self, 
                      metric_type: MetricType, 
                      name: str, 
                      value: float, 
                      unit: str,
                      timestamp: Optional[datetime] = None,
                      tags: Optional[Dict[str, str]] = None,
                      metadata: Optional[Dict[str, Any]] = None):
        """メトリクス記録"""
        if timestamp is None:
            timestamp = datetime.now(tz=timezone.utc)
        
        metric = PerformanceMetric(
            timestamp=timestamp,
            metric_type=metric_type,
            name=name,
            value=value,
            unit=unit,
            tags=tags or {},
            metadata=metadata or {}
        )
        
        # 履歴に追加
        self.metrics_history.append(metric)
        self.custom_metrics[name].append(metric)
        
        # 閾値チェック
        self._check_thresholds(metric)
        
        # コールバック実行
        for callback in self.metric_callbacks:
            try:
                callback(metric)
            except Exception as e:
                self.logger.error(f"メトリクスコールバックエラー: {e}")
    
    def _check_thresholds(self, metric: PerformanceMetric):
        """閾値チェック"""
        threshold_config = self.thresholds.get(metric.name)
        if not threshold_config:
            return
        
        alert_level = threshold_config.check_threshold(metric.value)
        if not alert_level:
            # アラート解決チェック
            self._resolve_alert(metric.name)
            return
        
        # 継続時間チェック
        alert_key = f"{metric.name}_{alert_level.value}"
        current_time = datetime.now(tz=timezone.utc)
        
        if alert_key not in self.alert_durations:
            self.alert_durations[alert_key] = current_time
        
        duration = (current_time - self.alert_durations[alert_key]).total_seconds()
        
        if duration >= threshold_config.duration_seconds:
            # 既存アラートチェック
            if alert_key not in self.active_alerts:
                self._create_alert(metric, alert_level, threshold_config)
    
    def _create_alert(self, metric: PerformanceMetric, level: AlertLevel, threshold_config: ThresholdConfig):
        """アラート作成"""
        threshold_value = None
        if level == AlertLevel.WARNING:
            threshold_value = threshold_config.warning_threshold
        elif level == AlertLevel.CRITICAL:
            threshold_value = threshold_config.critical_threshold
        elif level == AlertLevel.EMERGENCY:
            threshold_value = threshold_config.emergency_threshold
        
        message = f"{metric.name}が{level.value}レベルに達しました: {metric.value:.2f}{metric.unit} (閾値: {threshold_value}{metric.unit})"
        
        alert = PerformanceAlert(
            timestamp=datetime.now(tz=timezone.utc),
            level=level,
            metric_type=metric.metric_type,
            metric_name=metric.name,
            current_value=metric.value,
            threshold_value=threshold_value,
            message=message,
            tags=metric.tags.copy()
        )
        
        alert_key = f"{metric.name}_{level.value}"
        self.active_alerts[alert_key] = alert
        self.alerts_history.append(alert)
        
        # ログ出力
        if level == AlertLevel.EMERGENCY:
            self.logger.critical(message)
        elif level == AlertLevel.CRITICAL:
            self.logger.error(message)
        elif level == AlertLevel.WARNING:
            self.logger.warning(message)
        else:
            self.logger.info(message)
        
        # イベント発行
        self.event_system.emit(Event(
            name="performance_alert_created",
            data=alert.to_dict()
        ))
        
        # コールバック実行
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"アラートコールバックエラー: {e}")
    
    def _resolve_alert(self, metric_name: str):
        """アラート解決"""
        resolved_alerts = []
        
        for alert_key, alert in list(self.active_alerts.items()):
            if alert.metric_name == metric_name:
                alert.resolve()
                resolved_alerts.append(alert_key)
                
                self.logger.info(f"アラート解決: {alert.message}")
                
                # イベント発行
                self.event_system.emit(Event(
                    name="performance_alert_resolved",
                    data=alert.to_dict()
                ))
        
        # アクティブアラートから削除
        for alert_key in resolved_alerts:
            del self.active_alerts[alert_key]
            if alert_key in self.alert_durations:
                del self.alert_durations[alert_key]
    
    def add_metric_callback(self, callback: Callable[[PerformanceMetric], None]):
        """メトリクスコールバック追加"""
        self.metric_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """アラートコールバック追加"""
        self.alert_callbacks.append(callback)
    
    def set_threshold(self, metric_name: str, threshold_config: ThresholdConfig):
        """閾値設定"""
        self.thresholds[metric_name] = threshold_config
        self.logger.info(f"閾値設定更新: {metric_name}")
    
    def get_metrics(self, 
                   metric_name: Optional[str] = None,
                   metric_type: Optional[MetricType] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[PerformanceMetric]:
        """メトリクス取得"""
        metrics = list(self.metrics_history)
        
        # フィルタリング
        if metric_name:
            metrics = [m for m in metrics if m.name == metric_name]
        
        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]
        
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
        
        # ソート（新しい順）
        metrics.sort(key=lambda m: m.timestamp, reverse=True)
        
        # 制限
        if limit:
            metrics = metrics[:limit]
        
        return metrics
    
    def get_alerts(self, 
                  resolved: Optional[bool] = None,
                  level: Optional[AlertLevel] = None,
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None) -> List[PerformanceAlert]:
        """アラート取得"""
        alerts = list(self.alerts_history)
        
        # フィルタリング
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if start_time:
            alerts = [a for a in alerts if a.timestamp >= start_time]
        
        if end_time:
            alerts = [a for a in alerts if a.timestamp <= end_time]
        
        # ソート（新しい順）
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        return alerts
    
    def get_statistics(self, 
                      metric_name: str,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      use_cache: bool = True) -> Optional[PerformanceStatistics]:
        """統計情報取得"""
        cache_key = f"{metric_name}_{start_time}_{end_time}"
        current_time = datetime.now(tz=timezone.utc)
        
        # キャッシュチェック
        if (use_cache and 
            cache_key in self.stats_cache and 
            cache_key in self.stats_cache_time and
            (current_time - self.stats_cache_time[cache_key]).total_seconds() < self.stats_cache_ttl):
            return self.stats_cache[cache_key]
        
        # メトリクス取得
        metrics = self.get_metrics(metric_name=metric_name, start_time=start_time, end_time=end_time)
        
        if not metrics:
            return None
        
        # 統計計算
        values = [m.value for m in metrics]
        
        try:
            stats = PerformanceStatistics(
                metric_name=metric_name,
                count=len(values),
                min_value=min(values),
                max_value=max(values),
                mean_value=statistics.mean(values),
                median_value=statistics.median(values),
                std_deviation=statistics.stdev(values) if len(values) > 1 else 0.0,
                percentile_95=self._calculate_percentile(values, 95),
                percentile_99=self._calculate_percentile(values, 99),
                start_time=metrics[-1].timestamp,  # 最古
                end_time=metrics[0].timestamp      # 最新
            )
            
            # キャッシュ保存
            if use_cache:
                self.stats_cache[cache_key] = stats
                self.stats_cache_time[cache_key] = current_time
            
            return stats
            
        except Exception as e:
            self.logger.error(f"統計計算エラー: {e}")
            return None
    
    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """パーセンタイル計算"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            if upper_index >= len(sorted_values):
                return sorted_values[-1]
            
            weight = index - lower_index
            return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
    
    def record_custom_metric(self, 
                           name: str, 
                           value: float, 
                           unit: str = "",
                           tags: Optional[Dict[str, str]] = None,
                           metadata: Optional[Dict[str, Any]] = None):
        """カスタムメトリクス記録"""
        self._record_metric(
            MetricType.CUSTOM, 
            name, 
            value, 
            unit, 
            tags=tags, 
            metadata=metadata
        )
    
    def get_current_status(self) -> Dict[str, Any]:
        """現在の監視状態を取得"""
        return {
            'is_monitoring': self.is_monitoring,
            'collection_interval': self.collection_interval,
            'history_size': self.history_size,
            'metrics_count': len(self.metrics_history),
            'alerts_count': len(self.alerts_history),
            'active_alerts_count': len(self.active_alerts),
            'thresholds_count': len(self.thresholds),
            'memory_profiling_enabled': self.enable_memory_profiling,
            'uptime': time.time() - getattr(self, '_start_time', time.time())
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """システム健全性サマリー"""
        try:
            # 最新のリソース使用量
            latest_metrics = {}
            for metric_name in ['cpu_percent', 'memory_percent', 'disk_usage_percent']:
                metrics = self.get_metrics(metric_name=metric_name, limit=1)
                if metrics:
                    latest_metrics[metric_name] = metrics[0].value
            
            # アクティブアラート
            active_alerts = list(self.active_alerts.values())
            critical_alerts = [a for a in active_alerts if a.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]]
            
            # 健全性判定
            health_status = "healthy"
            if critical_alerts:
                health_status = "critical"
            elif len(active_alerts) > 0:
                health_status = "warning"
            elif any(v > 80 for v in latest_metrics.values()):
                health_status = "degraded"
            
            return {
                'health_status': health_status,
                'latest_metrics': latest_metrics,
                'active_alerts_count': len(active_alerts),
                'critical_alerts_count': len(critical_alerts),
                'monitoring_uptime': time.time() - getattr(self, '_start_time', time.time()),
                'last_update': datetime.now(tz=timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"健全性サマリー取得エラー: {e}")
            return {
                'health_status': 'unknown',
                'error': str(e),
                'last_update': datetime.now(tz=timezone.utc).isoformat()
            }
    
    def export_metrics(self, 
                      file_path: Path,
                      format_type: str = "json",
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> bool:
        """メトリクスをファイルにエクスポート"""
        try:
            metrics = self.get_metrics(start_time=start_time, end_time=end_time)
            
            if format_type.lower() == "json":
                data = {
                    'export_time': datetime.now(tz=timezone.utc).isoformat(),
                    'metrics_count': len(metrics),
                    'metrics': [m.to_dict() for m in metrics]
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
            elif format_type.lower() == "csv":
                import csv
                
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    if metrics:
                        writer = csv.DictWriter(f, fieldnames=metrics[0].to_dict().keys())
                        writer.writeheader()
                        for metric in metrics:
                            writer.writerow(metric.to_dict())
            else:
                raise ValidationError(f"サポートされていないフォーマット: {format_type}")
            
            self.logger.info(f"メトリクスエクスポート完了: {file_path} ({len(metrics)}件)")
            return True
            
        except Exception as e:
            self.logger.error(f"メトリクスエクスポートエラー: {e}")
            return False
    
    def import_thresholds(self, config_data: Dict[str, Any]) -> bool:
        """閾値設定をインポート"""
        try:
            for metric_name, threshold_data in config_data.items():
                threshold_config = ThresholdConfig(
                    metric_name=metric_name,
                    warning_threshold=threshold_data.get('warning_threshold'),
                    critical_threshold=threshold_data.get('critical_threshold'),
                    emergency_threshold=threshold_data.get('emergency_threshold'),
                    comparison_operator=threshold_data.get('comparison_operator', '>'),
                    duration_seconds=threshold_data.get('duration_seconds', 0),
                    enabled=threshold_data.get('enabled', True)
                )
                self.thresholds[metric_name] = threshold_config
            
            self.logger.info(f"閾値設定インポート完了: {len(config_data)}件")
            return True
            
        except Exception as e:
            self.logger.error(f"閾値設定インポートエラー: {e}")
            return False
    
    def export_thresholds(self) -> Dict[str, Any]:
        """閾値設定をエクスポート"""
        return {
            name: asdict(config) for name, config in self.thresholds.items()
        }
    
    def clear_history(self, older_than: Optional[datetime] = None):
        """履歴クリア"""
        try:
            if older_than is None:
                # 全履歴クリア
                self.metrics_history.clear()
                self.alerts_history.clear()
                self.custom_metrics.clear()
                self.stats_cache.clear()
                self.stats_cache_time.clear()
                self.logger.info("全履歴をクリアしました")
            else:
                # 指定日時より古い履歴をクリア
                original_metrics_count = len(self.metrics_history)
                original_alerts_count = len(self.alerts_history)
                
                # メトリクス履歴フィルタリング
                filtered_metrics = deque(
                    [m for m in self.metrics_history if m.timestamp > older_than],
                    maxlen=self.history_size
                )
                self.metrics_history = filtered_metrics
                
                # アラート履歴フィルタリング
                filtered_alerts = deque(
                    [a for a in self.alerts_history if a.timestamp > older_than],
                    maxlen=self.history_size
                )
                self.alerts_history = filtered_alerts
                
                # カスタムメトリクス履歴フィルタリング
                for name, metrics in self.custom_metrics.items():
                    filtered_custom = deque(
                        [m for m in metrics if m.timestamp > older_than],
                        maxlen=self.history_size
                    )
                    self.custom_metrics[name] = filtered_custom
                
                # 統計キャッシュクリア
                self.stats_cache.clear()
                self.stats_cache_time.clear()
                
                removed_metrics = original_metrics_count - len(self.metrics_history)
                removed_alerts = original_alerts_count - len(self.alerts_history)
                
                self.logger.info(f"古い履歴をクリアしました (メトリクス: {removed_metrics}件, アラート: {removed_alerts}件)")
                
        except Exception as e:
            self.logger.error(f"履歴クリアエラー: {e}")
    
    @contextmanager
    def measure_performance(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """パフォーマンス測定コンテキストマネージャー"""
        start_time = time.time()
        start_memory = None
        
        if self.enable_memory_profiling and tracemalloc.is_tracing():
            start_memory = tracemalloc.get_traced_memory()[0]
        
        try:
            yield
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # 実行時間記録
            self.record_custom_metric(
                f"operation_duration_{operation_name}",
                duration_ms,
                "ms",
                tags=tags,
                metadata={'operation': operation_name}
            )
            
            # メモリ使用量記録
            if start_memory is not None and tracemalloc.is_tracing():
                end_memory = tracemalloc.get_traced_memory()[0]
                memory_diff = (end_memory - start_memory) / (1024 * 1024)  # MB
                
                self.record_custom_metric(
                    f"operation_memory_{operation_name}",
                    memory_diff,
                    "MB",
                    tags=tags,
                    metadata={'operation': operation_name}
                )
    
    def create_dashboard_data(self) -> Dict[str, Any]:
        """ダッシュボード用データ作成"""
        try:
            current_time = datetime.now(tz=timezone.utc)
            one_hour_ago = current_time - timedelta(hours=1)
            
            # 主要メトリクスの最新値と1時間の統計
            dashboard_data = {
                'timestamp': current_time.isoformat(),
                'status': self.get_health_summary(),
                'metrics': {},
                'alerts': {
                    'active': len(self.active_alerts),
                    'recent': len(self.get_alerts(start_time=one_hour_ago))
                },
                'charts': {}
            }
            
            # 主要メトリクス
            key_metrics = ['cpu_percent', 'memory_percent', 'disk_usage_percent']
            
            for metric_name in key_metrics:
                # 最新値
                latest = self.get_metrics(metric_name=metric_name, limit=1)
                if latest:
                    dashboard_data['metrics'][metric_name] = {
                        'current': latest[0].value,
                        'unit': latest[0].unit,
                        'timestamp': latest[0].timestamp.isoformat()
                    }
                
                # 統計
                stats = self.get_statistics(metric_name, start_time=one_hour_ago)
                if stats:
                    dashboard_data['metrics'][metric_name].update({
                        'min': stats.min_value,
                        'max': stats.max_value,
                        'avg': stats.mean_value,
                        'p95': stats.percentile_95
                    })
                
                # チャート用データ（過去1時間、5分間隔）
                chart_data = []
                for i in range(12):  # 12 * 5分 = 1時間
                    time_point = current_time - timedelta(minutes=5 * (11 - i))
                    time_range_start = time_point - timedelta(minutes=2.5)
                    time_range_end = time_point + timedelta(minutes=2.5)
                    
                    metrics_in_range = self.get_metrics(
                        metric_name=metric_name,
                        start_time=time_range_start,
                        end_time=time_range_end
                    )
                    
                    if metrics_in_range:
                        avg_value = sum(m.value for m in metrics_in_range) / len(metrics_in_range)
                        chart_data.append({
                            'timestamp': time_point.isoformat(),
                            'value': round(avg_value, 2)
                        })
                    else:
                        chart_data.append({
                            'timestamp': time_point.isoformat(),
                            'value': None
                        })
                
                dashboard_data['charts'][metric_name] = chart_data
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"ダッシュボードデータ作成エラー: {e}")
            return {
                'timestamp': datetime.now(tz=timezone.utc).isoformat(),
                'error': str(e),
                'status': {'health_status': 'unknown'}
            }
    
    def shutdown(self):
        """パフォーマンス監視終了処理"""
        try:
            self.logger.info("PerformanceMonitor終了処理開始")
            
            # 監視停止
            self.stop_monitoring()
            
            # スレッドプール終了
            self.executor.shutdown(wait=True)
            
            # メモリプロファイリング停止
            if self.enable_memory_profiling and tracemalloc.is_tracing():
                tracemalloc.stop()
            
            # 最終統計出力
            if self.metrics_history:
                self.logger.info(f"最終統計 - 収集メトリクス数: {len(self.metrics_history)}, アラート数: {len(self.alerts_history)}")
            
            # キャッシュクリア
            self.stats_cache.clear()
            self.stats_cache_time.clear()
            self.active_alerts.clear()
            self.alert_durations.clear()
            
            self.logger.info("PerformanceMonitor終了処理完了")
            
        except Exception as e:
            self.logger.error(f"PerformanceMonitor終了処理エラー: {e}")


# グローバルインスタンス
_performance_monitor_instance: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """PerformanceMonitorのシングルトンインスタンスを取得"""
    global _performance_monitor_instance
    if _performance_monitor_instance is None:
        _performance_monitor_instance = PerformanceMonitor()
    return _performance_monitor_instance


def create_performance_monitor(**kwargs) -> PerformanceMonitor:
    """新しいPerformanceMonitorインスタンスを作成"""
    return PerformanceMonitor(**kwargs)


# 便利関数
def start_monitoring(**kwargs) -> bool:
    """パフォーマンス監視開始"""
    monitor = get_performance_monitor()
    return monitor.start_monitoring()


def stop_monitoring() -> bool:
    """パフォーマンス監視停止"""
    monitor = get_performance_monitor()
    return monitor.stop_monitoring()


def record_metric(name: str, value: float, unit: str = "", **kwargs):
    """カスタムメトリクス記録"""
    monitor = get_performance_monitor()
    monitor.record_custom_metric(name, value, unit, **kwargs)


def get_system_health() -> Dict[str, Any]:
    """システム健全性取得"""
    monitor = get_performance_monitor()
    return monitor.get_health_summary()


@contextmanager
def measure_operation(operation_name: str, **kwargs):
    """操作のパフォーマンス測定"""
    monitor = get_performance_monitor()
    with monitor.measure_performance(operation_name, **kwargs):
        yield


# デコレータ
def monitor_performance(operation_name: Optional[str] = None, 
                       include_args: bool = False,
                       include_result: bool = False):
    """パフォーマンス監視デコレータ"""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            tags = {'function': func.__name__, 'module': func.__module__}
            
            if include_args and args:
                tags['args_count'] = str(len(args))
            if include_args and kwargs:
                tags['kwargs_count'] = str(len(kwargs))
            
            with measure_operation(name, tags=tags):
                result = func(*args, **kwargs)
                
                if include_result and result is not None:
                    if hasattr(result, '__len__'):
                        record_metric(f"{name}_result_size", len(result), "count")
                
                return result
        
        return wrapper
    return decorator


# 使用例とテスト
if __name__ == "__main__":
    import asyncio
    
    async def test_performance_monitor():
        """テスト関数"""
        print("=== PerformanceMonitor テスト ===")
        
        # インスタンス作成
        monitor = create_performance_monitor(
            collection_interval=0.5,
            history_size=100,
            enable_memory_profiling=True
        )
        
        # 監視開始
        print("監視開始...")
        monitor.start_monitoring()
        
        # カスタムメトリクス記録
        for i in range(10):
            monitor.record_custom_metric("test_metric", i * 10, "count")
            await asyncio.sleep(0.1)
        
        # パフォーマンス測定テスト
        with monitor.measure_performance("test_operation"):
            await asyncio.sleep(0.5)
            # 何らかの処理
            sum(range(1000000))
        
        # 統計取得
        await asyncio.sleep(2)
        stats = monitor.get_statistics("cpu_percent")
        if stats:
            print(f"CPU統計: 平均={stats.mean_value:.2f}%, 最大={stats.max_value:.2f}%")
        
        # 健全性チェック
        health = monitor.get_health_summary()
        print(f"システム健全性: {health['health_status']}")
        
        # ダッシュボードデータ
        dashboard = monitor.create_dashboard_data()
        print(f"ダッシュボードデータ作成完了: {len(dashboard['metrics'])}メトリクス")
        
        # 監視停止
        print("監視停止...")
        monitor.stop_monitoring()
        
        # 終了処理
        monitor.shutdown()
        
        print("テスト完了")
    
    # テスト実行
    asyncio.run(test_performance_monitor())

