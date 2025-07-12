# src/utils/system_utils.py
"""
システムユーティリティ
OS、ハードウェア、プロセス管理などのシステム関連機能
"""

import os
import sys
import platform
import subprocess
import psutil
import threading
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import shutil
import tempfile
import hashlib
import socket
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import signal
from contextlib import contextmanager

from src.core.logger import get_logger
from src.core.exceptions import SystemError, ResourceNotFoundError, PermissionError

logger = get_logger(__name__)


@dataclass
class SystemInfo:
    """システム情報データクラス"""
    os_name: str
    os_version: str
    architecture: str
    processor: str
    cpu_count: int
    memory_total: int
    memory_available: int
    disk_total: int
    disk_free: int
    python_version: str
    hostname: str
    username: str
    uptime: float
    boot_time: datetime
    network_interfaces: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で返す"""
        data = asdict(self)
        # datetime を文字列に変換
        data['boot_time'] = self.boot_time.isoformat()
        return data
    
    def to_json(self) -> str:
        """JSON文字列で返す"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class ProcessInfo:
    """プロセス情報データクラス"""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int
    memory_vms: int
    num_threads: int
    create_time: datetime
    cmdline: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で返す"""
        data = asdict(self)
        data['create_time'] = self.create_time.isoformat()
        return data


@dataclass
class ResourceUsage:
    """リソース使用量データクラス"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_available: int
    disk_usage_percent: float
    disk_read_bytes: int
    disk_write_bytes: int
    network_sent_bytes: int
    network_recv_bytes: int
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で返す"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class SystemUtils:
    """システムユーティリティクラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = get_logger(self.__class__.__name__)
        self._process_cache = {}
        self._cache_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="SystemUtils")
        
        # システム情報キャッシュ
        self._system_info_cache: Optional[SystemInfo] = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5分
        
        self.logger.debug("SystemUtils初期化完了")
    
    def get_system_info(self, use_cache: bool = True) -> SystemInfo:
        """
        システム情報を取得
        
        Args:
            use_cache: キャッシュを使用するか
            
        Returns:
            SystemInfo: システム情報
        """
        try:
            current_time = time.time()
            
            # キャッシュチェック
            if (use_cache and 
                self._system_info_cache and 
                current_time - self._cache_timestamp < self._cache_ttl):
                return self._system_info_cache
            
            self.logger.debug("システム情報を取得中...")
            
            # OS情報
            os_info = platform.uname()
            
            # メモリ情報
            memory = psutil.virtual_memory()
            
            # ディスク情報
            disk = psutil.disk_usage('/')
            
            # ネットワークインターフェース情報
            network_interfaces = []
            try:
                for interface, addresses in psutil.net_if_addrs().items():
                    interface_info = {
                        'name': interface,
                        'addresses': []
                    }
                    for addr in addresses:
                        interface_info['addresses'].append({
                            'family': str(addr.family),
                            'address': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast
                        })
                    network_interfaces.append(interface_info)
            except Exception as e:
                self.logger.warning(f"ネットワーク情報取得エラー: {e}")
                network_interfaces = []
            
            # システム情報作成
            system_info = SystemInfo(
                os_name=os_info.system,
                os_version=os_info.release,
                architecture=os_info.machine,
                processor=os_info.processor or platform.processor(),
                cpu_count=psutil.cpu_count(),
                memory_total=memory.total,
                memory_available=memory.available,
                disk_total=disk.total,
                disk_free=disk.free,
                python_version=sys.version,
                hostname=socket.gethostname(),
                username=os.getenv('USER') or os.getenv('USERNAME', 'unknown'),
                uptime=time.time() - psutil.boot_time(),
                boot_time=datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc),
                network_interfaces=network_interfaces
            )
            
            # キャッシュ更新
            if use_cache:
                self._system_info_cache = system_info
                self._cache_timestamp = current_time
            
            self.logger.debug("システム情報取得完了")
            return system_info
            
        except Exception as e:
            self.logger.error(f"システム情報取得エラー: {e}")
            raise SystemError(f"システム情報の取得に失敗しました: {e}")
    
    def get_resource_usage(self) -> ResourceUsage:
        """
        現在のリソース使用量を取得
        
        Returns:
            ResourceUsage: リソース使用量
        """
        try:
            # CPU使用率（1秒間の平均）
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用量
            memory = psutil.virtual_memory()
            
            # ディスク使用量
            disk = psutil.disk_usage('/')
            
            # ディスクI/O
            disk_io = psutil.disk_io_counters()
            
            # ネットワークI/O
            network_io = psutil.net_io_counters()
            
            return ResourceUsage(
                timestamp=datetime.now(tz=timezone.utc),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used=memory.used,
                memory_available=memory.available,
                disk_usage_percent=(disk.used / disk.total) * 100,
                disk_read_bytes=disk_io.read_bytes if disk_io else 0,
                disk_write_bytes=disk_io.write_bytes if disk_io else 0,
                network_sent_bytes=network_io.bytes_sent if network_io else 0,
                network_recv_bytes=network_io.bytes_recv if network_io else 0
            )
            
        except Exception as e:
            self.logger.error(f"リソース使用量取得エラー: {e}")
            raise SystemError(f"リソース使用量の取得に失敗しました: {e}")
    
    def get_process_info(self, pid: int = None) -> Union[ProcessInfo, List[ProcessInfo]]:
        """
        プロセス情報を取得
        
        Args:
            pid: プロセスID（Noneの場合は全プロセス）
            
        Returns:
            ProcessInfo or List[ProcessInfo]: プロセス情報
        """
        try:
            if pid is not None:
                # 特定プロセスの情報
                return self._get_single_process_info(pid)
            else:
                # 全プロセスの情報
                return self._get_all_processes_info()
                
        except Exception as e:
            self.logger.error(f"プロセス情報取得エラー: {e}")
            raise SystemError(f"プロセス情報の取得に失敗しました: {e}")
    
    def _get_single_process_info(self, pid: int) -> ProcessInfo:
        """単一プロセス情報を取得"""
        try:
            process = psutil.Process(pid)
            
            return ProcessInfo(
                pid=process.pid,
                name=process.name(),
                status=process.status(),
                cpu_percent=process.cpu_percent(),
                memory_percent=process.memory_percent(),
                memory_rss=process.memory_info().rss,
                memory_vms=process.memory_info().vms,
                num_threads=process.num_threads(),
                create_time=datetime.fromtimestamp(process.create_time(), tz=timezone.utc),
                cmdline=process.cmdline()
            )
            
        except psutil.NoSuchProcess:
            raise ResourceNotFoundError(f"プロセス {pid} が見つかりません")
        except psutil.AccessDenied:
            raise PermissionError(f"プロセス {pid} へのアクセスが拒否されました")
    
    def _get_all_processes_info(self) -> List[ProcessInfo]:
        """全プロセス情報を取得"""
        processes = []
        
        for process in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 
                                          'memory_percent', 'memory_info', 'num_threads',
                                          'create_time', 'cmdline']):
            try:
                info = process.info
                processes.append(ProcessInfo(
                    pid=info['pid'],
                    name=info['name'],
                    status=info['status'],
                    cpu_percent=info['cpu_percent'] or 0.0,
                    memory_percent=info['memory_percent'] or 0.0,
                    memory_rss=info['memory_info'].rss if info['memory_info'] else 0,
                    memory_vms=info['memory_info'].vms if info['memory_info'] else 0,
                    num_threads=info['num_threads'] or 0,
                    create_time=datetime.fromtimestamp(info['create_time'], tz=timezone.utc) if info['create_time'] else datetime.now(tz=timezone.utc),
                    cmdline=info['cmdline'] or []
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return processes
    
    def kill_process(self, pid: int, force: bool = False) -> bool:
        """
        プロセスを終了
        
        Args:
            pid: プロセスID
            force: 強制終了フラグ
            
        Returns:
            bool: 成功フラグ
        """
        try:
            process = psutil.Process(pid)
            
            if force:
                process.kill()
                self.logger.info(f"プロセス {pid} を強制終了しました")
            else:
                process.terminate()
                self.logger.info(f"プロセス {pid} に終了シグナルを送信しました")
            
            # 終了確認（最大5秒待機）
            try:
                process.wait(timeout=5)
                return True
            except psutil.TimeoutExpired:
                if not force:
                    # 強制終了を試行
                    self.logger.warning(f"プロセス {pid} が応答しないため強制終了します")
                    return self.kill_process(pid, force=True)
                else:
                    self.logger.error(f"プロセス {pid} の強制終了に失敗しました")
                    return False
                    
        except psutil.NoSuchProcess:
            self.logger.warning(f"プロセス {pid} は既に存在しません")
            return True
        except psutil.AccessDenied:
            self.logger.error(f"プロセス {pid} の終了権限がありません")
            return False
        except Exception as e:
            self.logger.error(f"プロセス {pid} 終了エラー: {e}")
            return False
    
    def execute_command(self, command: Union[str, List[str]], 
                       timeout: float = 30.0,
                       capture_output: bool = True,
                       working_dir: Optional[Path] = None,
                       env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        """
        コマンドを実行
        
        Args:
            command: 実行するコマンド
            timeout: タイムアウト時間（秒）
            capture_output: 出力をキャプチャするか
            working_dir: 作業ディレクトリ
            env: 環境変数
            
        Returns:
            Tuple[int, str, str]: (終了コード, 標準出力, 標準エラー)
        """
        try:
            self.logger.debug(f"コマンド実行: {command}")
            
            # 環境変数設定
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)
            
            # コマンド実行
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=working_dir,
                env=exec_env,
                shell=isinstance(command, str)
            )
            
            self.logger.debug(f"コマンド実行完了: 終了コード={result.returncode}")
            
            return result.returncode, result.stdout or "", result.stderr or ""
            
        except subprocess.TimeoutExpired:
            error_msg = f"コマンドがタイムアウトしました: {command}"
            self.logger.error(error_msg)
            return -1, "", error_msg
        except FileNotFoundError:
            error_msg = f"コマンドが見つかりません: {command}"
            self.logger.error(error_msg)
            return -1, "", error_msg
        except Exception as e:
            error_msg = f"コマンド実行エラー: {e}"
            self.logger.error(error_msg)
            return -1, "", error_msg
    
    def get_disk_usage(self, path: Union[str, Path] = '/') -> Dict[str, int]:
        """
        ディスク使用量を取得
        
        Args:
            path: チェックするパス
            
        Returns:
            Dict[str, int]: ディスク使用量情報
        """
        try:
            usage = psutil.disk_usage(str(path))
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': (usage.used / usage.total) * 100
            }
        except Exception as e:
            self.logger.error(f"ディスク使用量取得エラー: {e}")
            return {'total': 0, 'used': 0, 'free': 0, 'percent': 0}
    
    def get_network_connections(self) -> List[Dict[str, Any]]:
        """
        ネットワーク接続情報を取得
        
        Returns:
            List[Dict[str, Any]]: 接続情報リスト
        """
        try:
            connections = []
            for conn in psutil.net_connections(kind='inet'):
                connections.append({
                    'fd': conn.fd,
                    'family': str(conn.family),
                    'type': str(conn.type),
                    'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    'status': conn.status,
                    'pid': conn.pid
                })
            return connections
        except Exception as e:
            self.logger.error(f"ネットワーク接続情報取得エラー: {e}")
            return []
    
    def create_temp_directory(self, prefix: str = "llm_temp_") -> Path:
        """
        一時ディレクトリを作成
        
        Args:
            prefix: ディレクトリ名のプレフィックス
            
        Returns:
            Path: 作成されたディレクトリパス
        """
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
            self.logger.debug(f"一時ディレクトリ作成: {temp_dir}")
            return temp_dir
        except Exception as e:
            self.logger.error(f"一時ディレクトリ作成エラー: {e}")
            raise SystemError(f"一時ディレクトリの作成に失敗しました: {e}")
    
    def cleanup_temp_directory(self, temp_dir: Path) -> bool:
        """
        一時ディレクトリを削除
        
        Args:
            temp_dir: 削除するディレクトリパス
            
        Returns:
            bool: 成功フラグ
        """
        try:
            if temp_dir.exists() and temp_dir.is_dir():
                shutil.rmtree(temp_dir)
                self.logger.debug(f"一時ディレクトリ削除: {temp_dir}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"一時ディレクトリ削除エラー: {e}")
            return False
    
    def calculate_file_hash(self, file_path: Path, algorithm: str = 'sha256') -> str:
        """
        ファイルのハッシュ値を計算
        
        Args:
            file_path: ファイルパス
            algorithm: ハッシュアルゴリズム
            
        Returns:
            str: ハッシュ値
        """
        try:
            hash_obj = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            hash_value = hash_obj.hexdigest()
            self.logger.debug(f"ファイルハッシュ計算完了: {file_path} -> {hash_value}")
            return hash_value
            
        except Exception as e:
            self.logger.error(f"ファイルハッシュ計算エラー: {e}")
            raise SystemError(f"ファイルハッシュの計算に失敗しました: {e}")
    
    def get_available_port(self, start_port: int = 8000, max_attempts: int = 100) -> Optional[int]:
        """
        利用可能なポートを取得
        
        Args:
            start_port: 開始ポート番号
            max_attempts: 最大試行回数
            
        Returns:
            Optional[int]: 利用可能なポート番号
        """
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind(('localhost', port))
                    self.logger.debug(f"利用可能ポート発見: {port}")
                    return port
            except OSError:
                continue
        
        self.logger.warning(f"利用可能ポートが見つかりません (範囲: {start_port}-{start_port + max_attempts})")
        return None
    
    def is_port_open(self, host: str, port: int, timeout: float = 3.0) -> bool:
        """
        ポートが開いているかチェック
        
        Args:
            host: ホスト名またはIPアドレス
            port: ポート番号
            timeout: タイムアウト時間
            
        Returns:
            bool: ポートが開いているか
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False
    
    def generate_unique_id(self) -> str:
        """
        ユニークIDを生成
        
        Returns:
            str: ユニークID
        """
        return str(uuid.uuid4())
    
    @contextmanager
    def temporary_directory(self, prefix: str = "llm_temp_"):
        """
        一時ディレクトリのコンテキストマネージャー
        
        Args:
            prefix: ディレクトリ名のプレフィックス
        """
        temp_dir = None
        try:
            temp_dir = self.create_temp_directory(prefix)
            yield temp_dir
        finally:
            if temp_dir:
                self.cleanup_temp_directory(temp_dir)
    
    def shutdown(self):
        """システムユーティリティ終了処理"""
        try:
            self.logger.info("SystemUtils終了処理開始")
            
            # スレッドプール終了
            self._executor.shutdown(wait=True)
            
            # キャッシュクリア
            with self._cache_lock:
                self._process_cache.clear()
                self._system_info_cache = None
            
            self.logger.info("SystemUtils終了処理完了")
            
        except Exception as e:
            self.logger.error(f"SystemUtils終了処理エラー: {e}")


# グローバルインスタンス
_system_utils_instance: Optional[SystemUtils] = None


def get_system_utils() -> SystemUtils:
    """SystemUtilsのシングルトンインスタンスを取得"""
    global _system_utils_instance
    if _system_utils_instance is None:
        _system_utils_instance = SystemUtils()
    return _system_utils_instance


# 便利関数
def get_current_system_info() -> SystemInfo:
    """現在のシステム情報を取得"""
    return get_system_utils().get_system_info()


def get_current_resource_usage() -> ResourceUsage:
    """現在のリソース使用量を取得"""
    return get_system_utils().get_resource_usage()


def execute_system_command(command: Union[str, List[str]], **kwargs) -> Tuple[int, str, str]:
    """システムコマンドを実行"""
    return get_system_utils().execute_command(command, **kwargs)


def is_system_healthy() -> bool:
    """システムの健全性をチェック"""
    try:
        usage = get_current_resource_usage()
        
        # 基本的な健全性チェック
        if usage.cpu_percent > 90:
            logger.warning(f"CPU使用率が高すぎます: {usage.cpu_percent}%")
            return False
        
        if usage.memory_percent > 90:
            logger.warning(f"メモリ使用率が高すぎます: {usage.memory_percent}%")
            return False
        
        if usage.disk_usage_percent > 95:
            logger.warning(f"ディスク使用率が高すぎます: {usage.disk_usage_percent}%")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"システム健全性チェックエラー: {e}")
        return False


# 使用例
if __name__ == "__main__":
    # システム情報表示
    system_utils = get_system_utils()
    
    print("=== システム情報 ===")
    system_info = system_utils.get_system_info()
    print(system_info.to_json())
    
    print("\n=== リソース使用量 ===")
    resource_usage = system_utils.get_resource_usage()
    print(json.dumps(resource_usage.to_dict(), ensure_ascii=False, indent=2))
    
    print(f"\n=== システム健全性 ===")
    print(f"健全性: {'OK' if is_system_healthy() else 'NG'}")
    
    # 終了処理
    system_utils.shutdown()
