#!/usr/bin/env python3
#src/core/config_manager.py
"""
統合設定管理システム - 新LLMシステム対応版
設定の読み込み、保存、検証、マイグレーションを統一管理
"""

import copy
import json
import toml
import yaml
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import threading
from contextlib import contextmanager

from config.config_schema import SchemaValidationResult

# コアシステムインポート（循環インポートを避ける）
from .logger import get_logger
from .singleton import Singleton
from src.core.event_system import Event

logger = get_logger(__name__)

def _get_event_system():
    """イベントシステムを遅延インポートで取得"""
    try:
        from .event_system import get_event_system, Event
        return get_event_system(), Event
    except ImportError as e:
        logger.warning(f"イベントシステム読み込み失敗: {e}")
        return None, None

def _get_validation_components():
    """バリデーションコンポーネントを遅延インポートで取得"""
    try:
        from config.config_schema import ConfigSchema, SchemaType, SchemaValidationResult
        from config.config_validator import ConfigValidator
        from config.config_migrator import ConfigMigrator
        return ConfigSchema, SchemaType, SchemaValidationResult, ConfigValidator, ConfigMigrator
    except ImportError as e:
        logger.warning(f"バリデーションコンポーネント読み込み失敗: {e}")
        return None, None, None, None, None

def _get_security_components():
    """セキュリティコンポーネントを遅延インポートで取得"""
    try:
        from src.security.config_encryption import ConfigEncryption, EncryptionMethod
        return ConfigEncryption, EncryptionMethod
    except ImportError as e:
        logger.warning(f"セキュリティコンポーネント読み込み失敗: {e}")
        return None, None

class ConfigFormat(Enum):
    """設定ファイル形式"""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    INI = "ini"

class ConfigEnvironment(Enum):
    """設定環境"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    LOCAL = "local"

class ConfigLoadMode(Enum):
    """設定読み込みモード"""
    STRICT = "strict"        # 厳密モード（エラーで停止）
    LENIENT = "lenient"      # 寛容モード（警告のみ）
    FALLBACK = "fallback"    # フォールバックモード（デフォルト値使用）

@dataclass
class ConfigChangeEvent:
    """設定変更イベント"""
    section: str
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"

@dataclass
class ConfigMetadata:
    """設定メタデータ"""
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    environment: ConfigEnvironment = ConfigEnvironment.DEVELOPMENT
    format: ConfigFormat = ConfigFormat.JSON
    encrypted: bool = False
    schema_version: str = "1.0.0"

class ConfigSection:
    """設定セクション管理"""
    
    def __init__(self, name: str, data: Dict[str, Any] = None, schema: Dict[str, Any] = None):
        self.name = name
        self._data = data or {}
        self.schema = schema
        self._lock = threading.RLock()
        self._observers = []
    
    def get(self, key: str, default: Any = None) -> Any:
        """値取得"""
        with self._lock:
            return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """値設定"""
        with self._lock:
            old_value = self._data.get(key)
            self._data[key] = value
            
            # 変更通知
            if old_value != value:
                self._notify_observers(key, old_value, value)
    
    def update(self, data: Dict[str, Any]) -> None:
        """一括更新"""
        with self._lock:
            for key, value in data.items():
                self.set(key, value)
    
    def delete(self, key: str) -> bool:
        """キー削除"""
        with self._lock:
            if key in self._data:
                old_value = self._data.pop(key)
                self._notify_observers(key, old_value, None)
                return True
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で取得"""
        with self._lock:
            return self._data.copy()
    
    def add_observer(self, callback):
        """変更監視追加"""
        self._observers.append(callback)
    
    def _notify_observers(self, key: str, old_value: Any, new_value: Any):
        """変更通知"""
        for callback in self._observers:
            try:
                callback(self.name, key, old_value, new_value)
            except Exception as e:
                logger.error(f"設定変更通知エラー: {e}")

class EnhancedConfigManager(Singleton):
    """統合設定管理システム"""
    
    def __init__(self, config_dir: Union[str, Path] = None):
        if hasattr(self, '_initialized'):
            return
        
        # 基本設定
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 環境設定
        self.environment = self._detect_environment()
        
       # コンポーネント初期化（遅延）
        self.schema_validator = None
        self.config_migrator = None
        self.config_encryption = None
        self.event_system = None
        
        # 設定管理
        self._sections: Dict[str, ConfigSection] = {}
        self._metadata = ConfigMetadata(environment=self.environment)
        self._lock = threading.RLock()
        
        # # LLM設定管理（遅延インポート）
        self.llm_config_manager = None
        
        # 初期化
        self.setup_config_system()
        self._initialized = True
        
        logger.info(f"設定管理システム初期化完了: {self.environment.value}")
    
    def _get_llm_config_manager(self):
        """LLMConfigManagerの遅延初期化"""
        if self.llm_config_manager is None:
            try:
                from config.llm_config_manager import LLMConfigManager
                self.llm_config_manager = LLMConfigManager(self)
            except ImportError as e:
                logger.warning(f"LLMConfigManager読み込み失敗: {e}")
                self.llm_config_manager = None
        return self.llm_config_manager
    
    def _initialize_components(self):
        """コンポーネントの遅延初期化"""
        # バリデーションコンポーネント
        if self.schema_validator is None:
            components = _get_validation_components()
            if components[3] is not None:  # ConfigValidator
                self.schema_validator = components[3]()
            else:
                self.schema_validator = self._create_dummy_validator()
        
        # マイグレーションコンポーネント
        if self.config_migrator is None:
            components = _get_validation_components()
            if components[4] is not None:  # ConfigMigrator
                self.config_migrator = components[4]()
            else:
                self.config_migrator = self._create_dummy_migrator()
        
        # 暗号化コンポーネント
        if self.config_encryption is None:
            components = _get_security_components()
            if components[0] is not None:  # ConfigEncryption
                self.config_encryption = components[0]()
            else:
                self.config_encryption = self._create_dummy_encryption()
        
        # イベントシステム
        if self.event_system is None:
            event_system, _ = _get_event_system()
            self.event_system = event_system
    
    def _create_dummy_validator(self):
        """ダミーバリデーター作成"""
        class DummyValidator:
            def register_schema(self, name, schema): pass
            def validate_section(self, name, data): pass
        return DummyValidator()
    
    def _create_dummy_migrator(self):
        """ダミーマイグレーター作成"""
        class DummyMigrator:
            def migrate_section(self, name, data): return data
        return DummyMigrator()
    
    def _create_dummy_encryption(self):
        """ダミー暗号化作成"""
        class DummyEncryption:
            def encrypt_config(self, data): return data
            def decrypt_config(self, data): return data
        return DummyEncryption()
    
    # LLM設定関連のメソッドを追加
    def get_llm_config_manager(self):
        """LLMConfigManager取得"""
        return self._get_llm_config_manager()
    
    def setup_config_system(self):
        """設定システム初期化"""
        try:
            # デフォルト設定ファイル作成
            self._ensure_default_configs()
            
            # 設定スキーマ登録
            self._register_schemas()
            
            # 既存設定読み込み
            self._load_all_configs()
            
            # マイグレーション実行
            self._run_migrations()
            
            # 設定検証
            self._validate_all_configs()
            
            logger.info("設定システム初期化完了")
            
        except Exception as e:
            logger.error(f"設定システム初期化エラー: {e}")
            raise
    
    def _detect_environment(self) -> ConfigEnvironment:
        """環境自動検出"""
        env_var = os.getenv('APP_ENV', '').lower()
        
        env_mapping = {
            'prod': ConfigEnvironment.PRODUCTION,
            'production': ConfigEnvironment.PRODUCTION,
            'test': ConfigEnvironment.TESTING,
            'testing': ConfigEnvironment.TESTING,
            'dev': ConfigEnvironment.DEVELOPMENT,
            'development': ConfigEnvironment.DEVELOPMENT,
            'local': ConfigEnvironment.LOCAL
        }
        
        return env_mapping.get(env_var, ConfigEnvironment.DEVELOPMENT)
    
    def _ensure_default_configs(self):
        """デフォルト設定ファイル作成"""
        default_configs = {
            'app.json': {
                'name': 'LLM Application',
                'version': '1.0.0',
                'debug': True,
                'log_level': 'INFO'
            },
            'llm.json': {
                'default_provider': 'openai',
                'default_model': 'gpt-3.5-turbo',
                'timeout': 30.0,
                'retry_count': 3,
                'providers': {
                    'openai': {
                        'api_key': '',
                        'base_url': 'https://api.openai.com/v1',
                        'models': ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']
                    },
                    'claude': {
                        'api_key': '',
                        'base_url': 'https://api.anthropic.com',
                        'models': ['claude-3-sonnet', 'claude-3-haiku', 'claude-3-opus']
                    }
                }
            },
            'ui.json': {
                'theme': 'light',
                'language': 'ja',
                'window': {
                    'width': 1200,
                    'height': 800,
                    'maximized': False
                },
                'chat': {
                    'font_size': 12,
                    'font_family': 'Consolas',
                    'auto_save': True,
                    'history_limit': 1000
                }
            },
            'security.json': {
                'encryption_enabled': False,
                'api_key_encryption': True,
                'session_timeout': 3600,
                'max_login_attempts': 5
            }
        }
        
        for filename, config in default_configs.items():
            config_path = self.config_dir / filename
            if not config_path.exists():
                self._save_config_file(config_path, config)
                logger.info(f"デフォルト設定作成: {filename}")
    
    def _register_schemas(self):
        """設定スキーマ登録"""
        schemas = {
            'app': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'version': {'type': 'string', 'pattern': r'^\d+\.\d+\.\d+$'},
                    'debug': {'type': 'boolean'},
                    'log_level': {'type': 'string', 'enum': ['DEBUG', 'INFO', 'WARNING', 'ERROR']}
                },
                'required': ['name', 'version']
            },
            'llm': {
                'type': 'object',
                'properties': {
                    'default_provider': {'type': 'string'},
                    'default_model': {'type': 'string'},
                    'timeout': {'type': 'number', 'minimum': 1.0},
                    'retry_count': {'type': 'integer', 'minimum': 0},
                    'providers': {
                        'type': 'object',
                        'additionalProperties': {
                            'type': 'object',
                            'properties': {
                                'api_key': {'type': 'string'},
                                'base_url': {'type': 'string', 'format': 'uri'},
                                'models': {'type': 'array', 'items': {'type': 'string'}}
                            }
                        }
                    }
                },
                'required': ['default_provider', 'default_model']
            },
            'ui': {
                'type': 'object',
                'properties': {
                    'theme': {'type': 'string', 'enum': ['light', 'dark']},
                    'language': {'type': 'string'},
                    'window': {
                        'type': 'object',
                        'properties': {
                            'width': {'type': 'integer', 'minimum': 400},
                            'height': {'type': 'integer', 'minimum': 300}
                        }
                    }
                }
            }
        }
        
        for section_name, schema in schemas.items():
            self.schema_validator.register_schema(section_name, schema)
    
    def _load_all_configs(self):
        """全設定読み込み"""
        config_files = list(self.config_dir.glob("*.json")) + list(self.config_dir.glob("*.yaml"))
        
        for config_file in config_files:
            try:
                section_name = config_file.stem
                config_data = self._load_config_file(config_file)
                
                # 環境固有設定のマージ
                env_config = self._load_environment_config(section_name)
                if env_config:
                    config_data = self._merge_configs(config_data, env_config)
                
                # セクション作成
                section = ConfigSection(section_name, config_data)
                section.add_observer(self._on_config_changed)
                self._sections[section_name] = section
                
                logger.debug(f"設定読み込み完了: {section_name}")
                
            except Exception as e:
                logger.error(f"設定読み込みエラー {config_file}: {e}")
    
    def _load_environment_config(self, section_name: str) -> Optional[Dict[str, Any]]:
        """環境固有設定読み込み"""
        env_config_file = self.config_dir / f"{section_name}.{self.environment.value}.json"
        
        if env_config_file.exists():
            try:
                return self._load_config_file(env_config_file)
            except Exception as e:
                logger.warning(f"環境設定読み込みエラー {env_config_file}: {e}")
        
        return None
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """設定マージ"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """設定ファイル読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix == '.json':
                    data = json.load(f)
                elif file_path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    raise ValueError(f"未対応ファイル形式: {file_path.suffix}")
            
            # 暗号化データの復号化
            if self._is_encrypted_config(data):
                data = self.config_encryption.decrypt_config(data)
            
            return data
            
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー {file_path}: {e}")
            raise
    
    def _save_config_file(self, file_path: Path, data: Dict[str, Any]):
        """設定ファイル保存"""
        try:
            # バックアップ作成
            if file_path.exists():
                backup_path = file_path.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                shutil.copy2(file_path, backup_path)
            
            # 暗号化が必要な場合
            if self._should_encrypt_config(file_path.stem, data):
                data = self.config_encryption.encrypt_config(data)
            
            # ファイル保存
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix == '.json':
                    json.dump(data, f, ensure_ascii=False, indent=2)
                elif file_path.suffix in ['.yaml', '.yml']:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            logger.debug(f"設定ファイル保存完了: {file_path}")
            
        except Exception as e:
            logger.error(f"設定ファイル保存エラー {file_path}: {e}")
            raise
    
    def _run_migrations(self):
        """設定マイグレーション実行"""
        try:
            for section_name, section in self._sections.items():
                migrated_data = self.config_migrator.migrate_section(
                    section_name, section.to_dict()
                )
                
                if migrated_data != section.to_dict():
                    section.update(migrated_data)
                    logger.info(f"設定マイグレーション実行: {section_name}")
            
        except Exception as e:
            logger.error(f"設定マイグレーションエラー: {e}")
    
    def _validate_all_configs(self):
        """全設定検証"""
        validation_errors = []
        
        for section_name, section in self._sections.items():
            try:
                self.schema_validator.validate_section(section_name, section.to_dict())
                logger.debug(f"設定検証成功: {section_name}")
                
            except Exception as e:
                error_msg = f"設定検証エラー {section_name}: {e}"
                validation_errors.append(error_msg)
                logger.error(error_msg)
        
        if validation_errors:
            logger.warning(f"設定検証で{len(validation_errors)}個のエラーが発生")
    
    def _is_encrypted_config(self, data: Dict[str, Any]) -> bool:
        """暗号化設定判定"""
        return data.get('_encrypted', False)
    
    def _should_encrypt_config(self, section_name: str, data: Dict[str, Any]) -> bool:
        """暗号化要否判定"""
        # セキュリティ関連設定は暗号化
        if section_name in ['security', 'llm']:
            return True
        
        # API キーを含む場合は暗号化
        if self._contains_sensitive_data(data):
            return True
        
        return False
    
    def _contains_sensitive_data(self, data: Any) -> bool:
        """機密データ判定"""
        if isinstance(data, dict):
            for key, value in data.items():
                if 'key' in key.lower() or 'password' in key.lower() or 'token' in key.lower():
                    return True
                if self._contains_sensitive_data(value):
                    return True
        elif isinstance(data, list):
            return any(self._contains_sensitive_data(item) for item in data)
        
        return False
    
    def _on_config_changed(self, section_name: str, key: str, old_value: Any, new_value: Any):
        """設定変更イベント処理"""
        try:
            # イベント発火
            self.event_system.publish(Event(
                'config_changed',
                {
                    'section': section_name,
                    'key': key,
                    'old_value': old_value,
                    'new_value': new_value,
                    'timestamp': datetime.now()
                }
            ))
            
            # 自動保存
            if self.get_section('app', {}).get('auto_save', True):
                self.save_section(section_name)
            
            logger.debug(f"設定変更: {section_name}.{key} = {new_value}")
            
        except Exception as e:
            logger.error(f"設定変更処理エラー: {e}")
    
    # === パブリックAPI ===
    
    def get_section(self, section_name: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """セクション取得"""
        with self._lock:
            section = self._sections.get(section_name)
            return section.to_dict() if section else (default or {})
    
    def set_section(self, section_name: str, data: Dict[str, Any]) -> None:
        """セクション設定"""
        with self._lock:
            if section_name not in self._sections:
                self._sections[section_name] = ConfigSection(section_name)
                self._sections[section_name].add_observer(self._on_config_changed)
            
            self._sections[section_name].update(data)
    
    def get_value(self, section_name: str, key: str, default: Any = None) -> Any:
        """値取得"""
        with self._lock:
            section = self._sections.get(section_name)
            return section.get(key, default) if section else default
    
    def set_value(self, section_name: str, key: str, value: Any) -> None:
        """値設定"""
        with self._lock:
            if section_name not in self._sections:
                self._sections[section_name] = ConfigSection(section_name)
                self._sections[section_name].add_observer(self._on_config_changed)
            
            self._sections[section_name].set(key, value)
    
    def save_section(self, section_name: str) -> None:
        """セクション保存"""
        try:
            section = self._sections.get(section_name)
            if not section:
                logger.warning(f"存在しないセクション: {section_name}")
                return
            
            config_file = self.config_dir / f"{section_name}.json"
            self._save_config_file(config_file, section.to_dict())
            
            logger.info(f"設定保存完了: {section_name}")
            
        except Exception as e:
            logger.error(f"設定保存エラー {section_name}: {e}")
            raise
    
    def save_all_configs(self) -> None:
        """全設定保存"""
        try:
            for section_name in self._sections.keys():
                self.save_section(section_name)
            
            logger.info("全設定保存完了")
            
        except Exception as e:
            logger.error(f"全設定保存エラー: {e}")
            raise
    
    def reload_section(self, section_name: str) -> None:
        """セクション再読み込み"""
        try:
            config_file = self.config_dir / f"{section_name}.json"
            if config_file.exists():
                config_data = self._load_config_file(config_file)
                
                # 環境固有設定マージ
                env_config = self._load_environment_config(section_name)
                if env_config:
                    config_data = self._merge_configs(config_data, env_config)
                
                # セクション更新
                if section_name in self._sections:
                    self._sections[section_name].update(config_data)
                else:
                    section = ConfigSection(section_name, config_data)
                    section.add_observer(self._on_config_changed)
                    self._sections[section_name] = section
                
                logger.info(f"設定再読み込み完了: {section_name}")
            
        except Exception as e:
            logger.error(f"設定再読み込みエラー {section_name}: {e}")
            raise
    
    def validate_section(self, section_name: str) -> bool:
        """セクション検証"""
        try:
            section = self._sections.get(section_name)
            if not section:
                return False
            
            self.schema_validator.validate_section(section_name, section.to_dict())
            return True
            
        except Exception as e:
            logger.error(f"設定検証エラー {section_name}: {e}")
            return False
    
    def export_config(self, output_path: Path, sections: List[str] = None, format: ConfigFormat = ConfigFormat.JSON) -> None:
        """設定エクスポート"""
        try:
            sections = sections or list(self._sections.keys())
            export_data = {}
            
            for section_name in sections:
                if section_name in self._sections:
                    export_data[section_name] = self._sections[section_name].to_dict()
            
            # メタデータ追加
            export_data['_metadata'] = {
                'exported_at': datetime.now().isoformat(),
                'environment': self.environment.value,
                'version': self._metadata.version,
                'sections': sections
            }
            
            # ファイル保存
            with open(output_path, 'w', encoding='utf-8') as f:
                if format == ConfigFormat.JSON:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                elif format == ConfigFormat.YAML:
                    yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"設定エクスポート完了: {output_path}")
            
        except Exception as e:
            logger.error(f"設定エクスポートエラー: {e}")
            raise
    
    def import_config(self, input_path: Path, sections: List[str] = None, merge: bool = True) -> None:
        """設定インポート"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                if input_path.suffix == '.json':
                    import_data = json.load(f)
                elif input_path.suffix in ['.yaml', '.yml']:
                    import_data = yaml.safe_load(f)
                else:
                    raise ValueError(f"未対応ファイル形式: {input_path.suffix}")
            
            # メタデータ除外
            import_data.pop('_metadata', None)
            
            sections = sections or list(import_data.keys())
            
            for section_name in sections:
                if section_name in import_data:
                    if merge and section_name in self._sections:
                        # マージモード
                        current_data = self._sections[section_name].to_dict()
                        merged_data = self._merge_configs(current_data, import_data[section_name])
                        self._sections[section_name].update(merged_data)
                    else:
                        # 置換モード
                        self.set_section(section_name, import_data[section_name])
            
            logger.info(f"設定インポート完了: {input_path}")
            
        except Exception as e:
            logger.error(f"設定インポートエラー: {e}")
            raise
    
    @contextmanager
    def config_transaction(self):
        """設定トランザクション"""
        backup_data = {}
        
        try:
            # バックアップ作成
            for section_name, section in self._sections.items():
                backup_data[section_name] = section.to_dict()
            
            yield self
            
            # 成功時: 設定保存
            self.save_all_configs()
            
        except Exception as e:
            # 失敗時: ロールバック
            logger.error(f"設定トランザクションエラー: {e}")
            
            for section_name, data in backup_data.items():
                if section_name in self._sections:
                    self._sections[section_name].update(data)
            
            raise
    
    def get_environment(self) -> ConfigEnvironment:
        """現在の環境取得"""
        return self.environment
    
    def get_metadata(self) -> ConfigMetadata:
        """メタデータ取得"""
        return self._metadata
    
    def list_sections(self) -> List[str]:
        """セクション一覧取得"""
        return list(self._sections.keys())
    
    def section_exists(self, section_name: str) -> bool:
        """セクション存在確認"""
        return section_name in self._sections

@dataclass
class ConfigLoadResult:
    """設定読み込み結果"""
    success: bool
    config_data: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_results: Dict[str, SchemaValidationResult] = field(default_factory=dict)
    loaded_files: List[Path] = field(default_factory=list)


class ConfigManager(Singleton):
    """設定管理クラス（シングルトン）"""
    
    def __init__(self):
        # 重複初期化防止
        if hasattr(self, '_initialized'):
            return
        
        # 基本設定
        self.config_dir = Path("config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 設定データ
        self._config_data: Dict[str, Dict[str, Any]] = {}
        self._original_config: Dict[str, Dict[str, Any]] = {}
        
        # 依存システム（遅延初期化）
        self._schema_manager = None
        self._encryption = None
        
        # 設定ファイル管理
        self._config_files: Dict[str, Path] = {}
        self._file_formats: Dict[str, ConfigFormat] = {}
        self._last_modified: Dict[str, datetime] = {}
        
        # 変更管理
        self._change_listeners: List[Callable[[ConfigChangeEvent], None]] = []
        self._change_history: List[ConfigChangeEvent] = []
        self._lock = threading.RLock()
        
        # 読み込み設定
        self.load_mode = ConfigLoadMode.LENIENT
        self.auto_reload = False
        self.auto_save = True
        self.encryption_enabled = False
        
        # デフォルト設定ファイル
        self._default_files = {
            'main': 'config.json',
            'application': 'app_config.json',
            'llm': 'llm_config.json',
            'ui': 'ui_config.json',
            'security': 'security_config.json',
            'logging': 'logging_config.json'
        }
        
        # 初期化完了
        self._initialized = True
        logger.info("設定管理システム初期化完了")
    
    def _initialize_dependencies(self):
        """依存関係の遅延初期化"""
        if self._schema_manager is None:
            components = _get_validation_components()
            if components[0] is not None:  # ConfigSchema
                self._schema_manager = components[0]()
        
        if self._encryption is None:
            components = _get_security_components()
            if components[0] is not None:  # ConfigEncryption
                self._encryption = components[0]()

    def initialize(self, 
                   config_dir: Union[str, Path] = None,
                   encryption_password: Optional[str] = None,
                   load_mode: ConfigLoadMode = ConfigLoadMode.LENIENT) -> bool:
        """設定管理システム初期化"""
        try:
            with self._lock:
                if config_dir:
                    self.config_dir = Path(config_dir)
                    self.config_dir.mkdir(parents=True, exist_ok=True)
                
                self.load_mode = load_mode
                
                # 暗号化初期化
                if encryption_password or self.encryption_enabled:
                    if not self._encryption.initialize_master_key(encryption_password):
                        logger.warning("暗号化初期化失敗、暗号化を無効化")
                        self.encryption_enabled = False
                
                # デフォルト設定ファイル登録
                self._register_default_files()
                
                # 設定読み込み
                result = self.load_all_configs()
                
                if result.success or self.load_mode != ConfigLoadMode.STRICT:
                    logger.info("設定管理システム初期化完了")
                    return True
                else:
                    logger.error("設定管理システム初期化失敗")
                    return False
                    
        except Exception as e:
            logger.error(f"設定管理システム初期化エラー: {e}")
            return False
    
    def _register_default_files(self):
        """デフォルト設定ファイル登録"""
        for section, filename in self._default_files.items():
            file_path = self.config_dir / filename
            self.register_config_file(section, file_path)
    
    def register_config_file(self, 
                           section: str, 
                           file_path: Union[str, Path],
                           format_type: Optional[ConfigFormat] = None) -> bool:
        """設定ファイル登録"""
        try:
            file_path = Path(file_path)
            
            # フォーマット自動判定
            if format_type is None:
                format_type = self._detect_format(file_path)
            
            with self._lock:
                self._config_files[section] = file_path
                self._file_formats[section] = format_type
                
                # ファイルが存在する場合は最終更新時刻を記録
                if file_path.exists():
                    self._last_modified[section] = datetime.fromtimestamp(file_path.stat().st_mtime)
                
            logger.debug(f"設定ファイル登録: {section} -> {file_path} ({format_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"設定ファイル登録エラー {section}: {e}")
            return False
    
    def _detect_format(self, file_path: Path) -> ConfigFormat:
        """設定ファイル形式検出"""
        suffix = file_path.suffix.lower()
        
        if suffix in ['.json']:
            return ConfigFormat.JSON
        elif suffix in ['.yaml', '.yml']:
            return ConfigFormat.YAML
        elif suffix in ['.toml']:
            return ConfigFormat.TOML
        else:
            # デフォルトはJSON
            return ConfigFormat.JSON
    
    def load_all_configs(self) -> ConfigLoadResult:
        """全設定読み込み"""
        result = ConfigLoadResult(
            success=True,
            config_data={}
        )
        
        try:
            with self._lock:
                # 各セクションの設定を読み込み
                for section in self._config_files.keys():
                    section_result = self.load_config(section)
                    
                    if section_result.success:
                        result.config_data[section] = section_result.config_data.get(section, {})
                        result.loaded_files.extend(section_result.loaded_files)
                    else:
                        result.errors.extend([f"[{section}] {error}" for error in section_result.errors])
                        result.success = False
                    
                    result.warnings.extend([f"[{section}] {warning}" for warning in section_result.warnings])
                    result.validation_results.update(section_result.validation_results)
                
                # 設定データを保存
                self._config_data.update(result.config_data)
                self._original_config = copy.deepcopy(self._config_data)
                
                # 全体検証
                if result.config_data:
                    validation_results = self._schema_manager.validate_all_sections(result.config_data)
                    result.validation_results.update(validation_results)
                    
                    # 検証失敗時の処理
                    for section, validation_result in validation_results.items():
                        if not validation_result.is_valid:
                            if self.load_mode == ConfigLoadMode.STRICT:
                                result.success = False
                                result.errors.extend([f"[{section}] {error}" for error in validation_result.errors])
                            else:
                                result.warnings.extend([f"[{section}] {error}" for error in validation_result.errors])
                
                logger.info(f"設定読み込み完了: {len(result.config_data)}セクション")
                
        except Exception as e:
            logger.error(f"全設定読み込みエラー: {e}")
            result.success = False
            result.errors.append(f"全設定読み込みエラー: {e}")
        
        return result
    
    def load_config(self, section: str) -> ConfigLoadResult:
        """指定セクションの設定読み込み"""
        result = ConfigLoadResult(
            success=True,
            config_data={}
        )
        
        try:
            file_path = self._config_files.get(section)
            if not file_path:
                # デフォルト設定を使用
                default_config = self._schema_manager.get_default_config(section)
                result.config_data[section] = default_config
                result.warnings.append(f"設定ファイルが未登録、デフォルト設定を使用: {section}")
                return result
            
            if not file_path.exists():
                if self.load_mode == ConfigLoadMode.STRICT:
                    result.success = False
                    result.errors.append(f"設定ファイルが見つかりません: {file_path}")
                    return result
                else:
                    # デフォルト設定を使用
                    default_config = self._schema_manager.get_default_config(section)
                    result.config_data[section] = default_config
                    result.warnings.append(f"設定ファイルが見つかりません、デフォルト設定を使用: {file_path}")
                    return result
            
            # ファイル読み込み
            format_type = self._file_formats.get(section, ConfigFormat.JSON)
            config_data = self._load_file(file_path, format_type)
            
            # 暗号化データの復号化
            if self.encryption_enabled and self._encryption._master_key:
                try:
                    config_data = self._encryption.decrypt_config(config_data)
                except Exception as e:
                    logger.warning(f"復号化失敗、平文として処理: {e}")
            
            # スキーマ検証
            validation_result = self._schema_manager.validate_config(section, config_data)
            result.validation_results[section] = validation_result
            
            if not validation_result.is_valid:
                if self.load_mode == ConfigLoadMode.STRICT:
                    result.success = False
                    result.errors.extend(validation_result.errors)
                    return result
                else:
                    result.warnings.extend(validation_result.errors)
            
            result.warnings.extend(validation_result.warnings)
            
            result.config_data[section] = config_data
            result.loaded_files.append(file_path)
            
            # 最終更新時刻更新
            self._last_modified[section] = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            logger.debug(f"設定読み込み完了: {section}")
            
        except Exception as e:
            logger.error(f"設定読み込みエラー {section}: {e}")
            result.success = False
            result.errors.append(f"設定読み込みエラー: {e}")
        
        return result
    
    def _load_file(self, file_path: Path, format_type: ConfigFormat) -> Dict[str, Any]:
        """設定ファイル読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if format_type == ConfigFormat.JSON:
                    return json.load(f)
                elif format_type == ConfigFormat.YAML:
                    return yaml.safe_load(f) or {}
                elif format_type == ConfigFormat.TOML:
                    return toml.load(f)
                else:
                    raise ValueError(f"未対応のファイル形式: {format_type}")
                    
        except Exception as e:
            logger.error(f"ファイル読み込みエラー {file_path}: {e}")
            raise
    
    def save_config(self, section: str, force: bool = False) -> bool:
        """指定セクションの設定保存"""
        try:
            with self._lock:
                if section not in self._config_data:
                    logger.warning(f"保存対象セクションが見つかりません: {section}")
                    return False
                
                file_path = self._config_files.get(section)
                if not file_path:
                    logger.error(f"設定ファイルが未登録: {section}")
                    return False
                
                config_data = self._config_data[section]
                
                # スキーマ検証
                if not force:
                    validation_result = self._schema_manager.validate_config(section, config_data)
                    if not validation_result.is_valid:
                        logger.error(f"設定検証失敗、保存中止 {section}: {validation_result.errors}")
                        return False
                
                # 暗号化
                save_data = config_data
                if self.encryption_enabled and self._encryption._master_key:
                    try:
                        save_data = self._encryption.encrypt_config(config_data)
                    except Exception as e:
                        logger.error(f"暗号化失敗 {section}: {e}")
                        if not force:
                            return False
                
                # ファイル保存
                format_type = self._file_formats.get(section, ConfigFormat.JSON)
                self._save_file(file_path, save_data, format_type)
                
                # 最終更新時刻更新
                self._last_modified[section] = datetime.now()
                
                logger.info(f"設定保存完了: {section}")
                return True
                
        except Exception as e:
            logger.error(f"設定保存エラー {section}: {e}")
            return False
    
    def _save_file(self, file_path: Path, data: Dict[str, Any], format_type: ConfigFormat):
        """設定ファイル保存"""
        try:
            # バックアップ作成
            if file_path.exists():
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                file_path.rename(backup_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if format_type == ConfigFormat.JSON:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                elif format_type == ConfigFormat.YAML:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
                elif format_type == ConfigFormat.TOML:
                    toml.dump(data, f)
                else:
                    raise ValueError(f"未対応のファイル形式: {format_type}")
                    
        except Exception as e:
            logger.error(f"ファイル保存エラー {file_path}: {e}")
            raise
    
    def save_all_configs(self, force: bool = False) -> bool:
        """全設定保存"""
        try:
            success_count = 0
            total_count = len(self._config_data)
            
            for section in self._config_data.keys():
                if self.save_config(section, force):
                    success_count += 1
            
            if success_count == total_count:
                logger.info(f"全設定保存完了: {success_count}/{total_count}")
                return True
            else:
                logger.warning(f"一部設定保存失敗: {success_count}/{total_count}")
                return False
                
        except Exception as e:
            logger.error(f"全設定保存エラー: {e}")
            return False
    
    def get_config(self, section: str, key: str = None, default: Any = None) -> Any:
        """設定値取得"""
        try:
            with self._lock:
                section_data = self._config_data.get(section, {})
                
                if key is None:
                    return section_data
                
                # ドット記法対応 (例: "ui.window.width")
                keys = key.split('.')
                value = section_data
                
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                
                return value
                
        except Exception as e:
            logger.error(f"設定取得エラー {section}.{key}: {e}")
            return default
    
    def set_config(self, section: str, key: str, value: Any, save_immediately: bool = None) -> bool:
        """設定値設定"""
        try:
            with self._lock:
                if section not in self._config_data:
                    self._config_data[section] = {}
                
                # 現在の値を取得
                old_value = self.get_config(section, key)
                
                # ドット記法対応
                keys = key.split('.')
                target = self._config_data[section]
                
                # 階層を作成
                for k in keys[:-1]:
                    if k not in target:
                        target[k] = {}
                    target = target[k]
                
                # 値を設定
                target[keys[-1]] = value
                
                # 変更イベント発火
                event = ConfigChangeEvent(
                    section=section,
                    key=key,
                    old_value=old_value,
                    new_value=value,
                    source="set_config"
                )
                self._fire_change_event(event)
                
                # 自動保存
                if save_immediately or (save_immediately is None and self.auto_save):
                    self.save_config(section)
                
                logger.debug(f"設定更新: {section}.{key} = {value}")
                return True
                
        except Exception as e:
            logger.error(f"設定更新エラー {section}.{key}: {e}")
            return False
    
    def _fire_change_event(self, event: ConfigChangeEvent):
        """設定変更イベント発火"""
        try:
            # 履歴に追加
            self._change_history.append(event)
            
            # 履歴サイズ制限
            if len(self._change_history) > 1000:
                self._change_history = self._change_history[-500:]
            
            # リスナーに通知
            for listener in self._change_listeners:
                try:
                    listener(event)
                except Exception as e:
                    logger.error(f"設定変更リスナーエラー: {e}")
                    
        except Exception as e:
            logger.error(f"設定変更イベント処理エラー: {e}")
    
    def add_change_listener(self, listener: Callable[[ConfigChangeEvent], None]):
        """設定変更リスナー追加"""
        if listener not in self._change_listeners:
            self._change_listeners.append(listener)
            logger.debug("設定変更リスナー追加")
    
    def remove_change_listener(self, listener: Callable[[ConfigChangeEvent], None]):
        """設定変更リスナー削除"""
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)
            logger.debug("設定変更リスナー削除")
    
    def get_sections(self) -> List[str]:
        """設定セクション一覧取得"""
        return list(self._config_data.keys())
    
    def has_section(self, section: str) -> bool:
        """設定セクション存在確認"""
        return section in self._config_data
    
    def has_config(self, section: str, key: str) -> bool:
        """設定キー存在確認"""
        return self.get_config(section, key) is not None
    
    def reset_section(self, section: str) -> bool:
        """セクション設定リセット"""
        try:
            with self._lock:
                # デフォルト設定を取得
                default_config = self._schema_manager.get_default_config(section)
                
                if default_config:
                    old_config = self._config_data.get(section, {})
                    self._config_data[section] = default_config
                    
                    # 変更イベント発火
                    event = ConfigChangeEvent(
                        section=section,
                        key="*",
                        old_value=old_config,
                        new_value=default_config,
                        source="reset_section"
                    )
                    self._fire_change_event(event)
                    
                    logger.info(f"セクション設定リセット: {section}")
                    return True
                else:
                    logger.warning(f"デフォルト設定が見つかりません: {section}")
                    return False
                    
        except Exception as e:
            logger.error(f"セクション設定リセットエラー {section}: {e}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """設定管理情報取得"""
        with self._lock:
            return {
                'sections': list(self._config_data.keys()),
                'config_files': {k: str(v) for k, v in self._config_files.items()},
                'file_formats': {k: v.value for k, v in self._file_formats.items()},
                'last_modified': {k: v.isoformat() for k, v in self._last_modified.items()},
                'load_mode': self.load_mode.value,
                'auto_reload': self.auto_reload,
                'auto_save': self.auto_save,
                'encryption_enabled': self.encryption_enabled,
                'change_listeners': len(self._change_listeners),
                'change_history_count': len(self._change_history)
            }


# グローバルインスタンス取得関数
def get_config_manager() -> ConfigManager:
    """ConfigManagerのシングルトンインスタンスを取得"""
    return ConfigManager.get_instance()
    #global _config_manager_instance
    #if _config_manager_instance is None:
    #    _config_manager_instance = ConfigManager()
    #return _config_manager_instance


# 便利関数
def get_config(section: str = None, key: str = None, default: Any = None) -> Any:
    """設定値取得（便利関数）"""
    try:
        manager = get_config_manager()
        if section is None:
            return manager._config_data
        return manager.get_config(section, key, default)
    except Exception as e:
        logger.error(f"設定取得エラー: {e}")
        return default

def set_config(section: str, key: str, value: Any, save_immediately: bool = None) -> bool:
    """設定値設定（便利関数）"""
    try:
        return get_config_manager().set_config(section, key, value, save_immediately)
    except Exception as e:
        logger.error(f"設定更新エラー: {e}")
        return False

# 使用例とテスト
if __name__ == "__main__":
    def test_config_manager():
        """設定管理テスト"""
        print("=== 設定管理テスト ===")
        
        try:
            # 初期化
            manager = get_config_manager()
            manager.initialize()
            
            # 設定値設定
            manager.set_config('application', 'name', 'Test App')
            manager.set_config('application', 'version', '1.0.0')
            manager.set_config('ui.window', 'width', 800)
            
            # 設定値取得
            app_name = manager.get_config('application', 'name')
            window_width = manager.get_config('ui', 'window.width')
            
            print(f"アプリ名: {app_name}")
            print(f"ウィンドウ幅: {window_width}")
            
            # セクション一覧
            sections = manager.get_sections()
            print(f"設定セクション: {sections}")
            
            # 設定情報
            info = manager.get_config_info()
            print(f"設定管理情報: {info}")
            
        except Exception as e:
            print(f"テストエラー: {e}")
    
    test_config_manager()