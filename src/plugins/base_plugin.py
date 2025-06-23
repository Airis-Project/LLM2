# src/plugins/base_plugin.py
"""
プラグインシステムの基底クラス
全てのプラグインはこのクラスを継承する
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from ..core.logger import get_logger
from ..core.event_system import EventEmitter


class PluginStatus(Enum):
    """プラグインの状態"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    LOADING = "loading"
    DISABLED = "disabled"


class PluginError(Exception):
    """プラグイン固有のエラー"""
    def __init__(self, message: str, plugin_name: str = None):
        super().__init__(message)
        self.plugin_name = plugin_name


@dataclass
class PluginInfo:
    """プラグイン情報"""
    name: str
    version: str
    description: str
    author: str
    license: str = "MIT"
    dependencies: List[str] = None
    min_app_version: str = "1.0.0"
    max_app_version: str = None
    website: str = None
    repository: str = None
    tags: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginInfo':
        """辞書から作成"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class PluginConfig:
    """プラグイン設定"""
    enabled: bool = True
    auto_load: bool = True
    priority: int = 0
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


class BasePlugin(ABC, EventEmitter):
    """プラグインの基底クラス"""
    
    def __init__(self, plugin_info: PluginInfo, config: PluginConfig = None):
        super().__init__()
        self.info = plugin_info
        self.config = config or PluginConfig()
        self.status = PluginStatus.INACTIVE
        self.logger = get_logger(f"plugin.{self.info.name}")
        self._error_message: Optional[str] = None
        self._dependencies_loaded: Set[str] = set()
        
        # プラグインディレクトリのパス
        self.plugin_dir = Path(__file__).parent
        
        # 設定ファイルのパス
        self.config_file = self.plugin_dir / f"{self.info.name}_config.json"
        
        # プラグイン固有のデータディレクトリ
        self.data_dir = self.plugin_dir / "data" / self.info.name
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 設定を読み込み
        self._load_config()
    
    @property
    def name(self) -> str:
        """プラグイン名"""
        return self.info.name
    
    @property
    def version(self) -> str:
        """プラグインバージョン"""
        return self.info.version
    
    @property
    def is_active(self) -> bool:
        """プラグインがアクティブかどうか"""
        return self.status == PluginStatus.ACTIVE
    
    @property
    def is_enabled(self) -> bool:
        """プラグインが有効かどうか"""
        return self.config.enabled
    
    @property
    def error_message(self) -> Optional[str]:
        """エラーメッセージ"""
        return self._error_message
    
    def _load_config(self):
        """設定を読み込み"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.config = PluginConfig(**config_data)
                self.logger.debug(f"設定を読み込みました: {self.config_file}")
        except Exception as e:
            self.logger.warning(f"設定読み込みエラー: {e}")
    
    def _save_config(self):
        """設定を保存"""
        try:
            config_data = asdict(self.config)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"設定を保存しました: {self.config_file}")
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self.config.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """設定値を設定"""
        self.config.settings[key] = value
        self._save_config()
    
    def update_settings(self, settings: Dict[str, Any]):
        """設定を一括更新"""
        self.config.settings.update(settings)
        self._save_config()
    
    def check_dependencies(self) -> bool:
        """依存関係をチェック"""
        try:
            for dependency in self.info.dependencies:
                try:
                    __import__(dependency)
                    self._dependencies_loaded.add(dependency)
                except ImportError:
                    self.logger.error(f"依存関係が見つかりません: {dependency}")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"依存関係チェックエラー: {e}")
            return False
    
    def load(self) -> bool:
        """プラグインを読み込み"""
        try:
            if not self.config.enabled:
                self.logger.info("プラグインは無効です")
                self.status = PluginStatus.DISABLED
                return False
            
            self.status = PluginStatus.LOADING
            self.emit('plugin_loading', {'plugin': self.name})
            
            # 依存関係をチェック
            if not self.check_dependencies():
                self._error_message = "依存関係の不足"
                self.status = PluginStatus.ERROR
                self.emit('plugin_error', {'plugin': self.name, 'error': self._error_message})
                return False
            
            # プラグイン固有の初期化
            if not self.initialize():
                self._error_message = "初期化に失敗"
                self.status = PluginStatus.ERROR
                self.emit('plugin_error', {'plugin': self.name, 'error': self._error_message})
                return False
            
            self.status = PluginStatus.ACTIVE
            self.logger.info(f"プラグインを読み込みました: {self.name} v{self.version}")
            self.emit('plugin_loaded', {'plugin': self.name})
            return True
            
        except Exception as e:
            self._error_message = str(e)
            self.status = PluginStatus.ERROR
            self.logger.error(f"プラグイン読み込みエラー: {e}")
            self.emit('plugin_error', {'plugin': self.name, 'error': str(e)})
            return False
    
    def unload(self) -> bool:
        """プラグインをアンロード"""
        try:
            if self.status == PluginStatus.ACTIVE:
                self.emit('plugin_unloading', {'plugin': self.name})
                
                # プラグイン固有のクリーンアップ
                self.cleanup()
                
                self.status = PluginStatus.INACTIVE
                self._error_message = None
                self.logger.info(f"プラグインをアンロードしました: {self.name}")
                self.emit('plugin_unloaded', {'plugin': self.name})
            
            return True
            
        except Exception as e:
            self.logger.error(f"プラグインアンロードエラー: {e}")
            self.emit('plugin_error', {'plugin': self.name, 'error': str(e)})
            return False
    
    def reload(self) -> bool:
        """プラグインを再読み込み"""
        self.logger.info(f"プラグインを再読み込みします: {self.name}")
        if self.unload():
            return self.load()
        return False
    
    def enable(self):
        """プラグインを有効にする"""
        self.config.enabled = True
        self._save_config()
        self.logger.info(f"プラグインを有効にしました: {self.name}")
        self.emit('plugin_enabled', {'plugin': self.name})
    
    def disable(self):
        """プラグインを無効にする"""
        if self.is_active:
            self.unload()
        self.config.enabled = False
        self._save_config()
        self.status = PluginStatus.DISABLED
        self.logger.info(f"プラグインを無効にしました: {self.name}")
        self.emit('plugin_disabled', {'plugin': self.name})
    
    @abstractmethod
    def initialize(self) -> bool:
        """プラグイン固有の初期化処理"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """プラグイン固有のクリーンアップ処理"""
        pass
    
    @abstractmethod
    def get_commands(self) -> Dict[str, callable]:
        """プラグインが提供するコマンドを返す"""
        return {}
    
    @abstractmethod
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """プラグインが提供するメニュー項目を返す"""
        return []
    
    @abstractmethod
    def get_toolbar_items(self) -> List[Dict[str, Any]]:
        """プラグインが提供するツールバー項目を返す"""
        return []
    
    def get_status_info(self) -> Dict[str, Any]:
        """プラグインの状態情報を返す"""
        return {
            'name': self.name,
            'version': self.version,
            'status': self.status.value,
            'enabled': self.config.enabled,
            'error_message': self._error_message,
            'dependencies_loaded': list(self._dependencies_loaded),
            'settings_count': len(self.config.settings)
        }
    
    def export_settings(self, file_path: Union[str, Path]) -> bool:
        """設定をファイルにエクスポート"""
        try:
            export_data = {
                'plugin_info': self.info.to_dict(),
                'config': asdict(self.config),
                'exported_at': datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"設定をエクスポートしました: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"設定エクスポートエラー: {e}")
            return False
    
    def import_settings(self, file_path: Union[str, Path]) -> bool:
        """ファイルから設定をインポート"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if 'config' in import_data:
                self.config = PluginConfig(**import_data['config'])
                self._save_config()
                self.logger.info(f"設定をインポートしました: {file_path}")
                return True
            else:
                self.logger.error("無効な設定ファイル形式")
                return False
                
        except Exception as e:
            self.logger.error(f"設定インポートエラー: {e}")
            return False
    
    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.status.value})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name} v{self.version}>"
