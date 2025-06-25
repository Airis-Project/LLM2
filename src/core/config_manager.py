#!/usr/bin/env python3
"""
統合設定管理システム - 新LLMシステム対応版
設定の読み込み、保存、検証、マイグレーションを統一管理
"""

import json
import yaml
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import threading
from contextlib import contextmanager

# 新LLMシステムインポート
from src.llm import (
    LLMConfig, 
    LLMProvider, 
    get_available_providers,
    validate_llm_config
)

# コアシステムインポート
from src.core.logger import get_logger
from src.core.event_system import get_event_system, Event
from src.core.singleton import Singleton

# バリデーション・スキーマ
from src.core.config_schema import ConfigSchema, SchemaType
from src.core.config_validator import ConfigValidator
from src.core.config_migrator import ConfigMigrator

# 暗号化サポート
from src.security.config_encryption import ConfigEncryption

logger = get_logger(__name__)

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
        
        # コンポーネント初期化
        self.schema_validator = ConfigValidator()
        self.config_migrator = ConfigMigrator()
        self.config_encryption = ConfigEncryption()
        self.event_system = get_event_system()
        
        # 設定管理
        self._sections: Dict[str, ConfigSection] = {}
        self._metadata = ConfigMetadata(environment=self.environment)
        self._lock = threading.RLock()
        
        # LLM設定管理
        self.llm_config_manager = LLMConfigManager(self)
        
        # 初期化
        self.setup_config_system()
        self._initialized = True
        
        logger.info(f"設定管理システム初期化完了: {self.environment.value}")
    
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
