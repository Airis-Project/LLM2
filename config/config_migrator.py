#!/usr/bin/env python3
#config/config_migrator.py
"""
設定マイグレーションシステム完全版
バージョン間の設定変更を自動処理
"""
_config_manager_instance = None

import json
from typing import Dict, Any, List, Callable, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from packaging import version

from src.core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class MigrationRule:
    """マイグレーションルール"""
    from_version: str
    to_version: str
    section: str
    description: str
    migration_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class ConfigMigrator:
    """設定マイグレーションシステム"""
    
    def __init__(self):
        self._migration_rules: List[MigrationRule] = []
        self.current_version = "1.0.0"
        self._register_builtin_migrations()
    
    def _register_builtin_migrations(self):
        """組み込みマイグレーション登録"""
        
        # v0.9.x から v1.0.0 へのマイグレーション
        self.register_migration(
            "0.9.0", "1.0.0", "llm",
            "LLM設定の新システム対応",
            self._migrate_llm_v0_9_to_v1_0
        )
        
        self.register_migration(
            "0.9.0", "1.0.0", "ui",
            "UI設定の構造変更",
            self._migrate_ui_v0_9_to_v1_0
        )
        
        # v1.0.0 から v1.1.0 へのマイグレーション
        self.register_migration(
            "1.0.0", "1.1.0", "security",
            "セキュリティ設定の追加",
            self._migrate_security_v1_0_to_v1_1
        )
    
    def register_migration(self, from_version: str, to_version: str, section: str, 
                          description: str, migration_func: Callable):
        """マイグレーション登録"""
        rule = MigrationRule(
            from_version=from_version,
            to_version=to_version,
            section=section,
            description=description,
            migration_func=migration_func
        )
        
        self._migration_rules.append(rule)
        logger.debug(f"マイグレーション登録: {section} {from_version}→{to_version}")
    
    def migrate_section(self, section_name: str, data: Dict[str, Any], 
                       from_version: str = None) -> Dict[str, Any]:
        """セクションマイグレーション実行"""
        try:
            if not from_version:
                # バージョン情報がない場合は最新と仮定
                return data
            
            # 適用可能なマイグレーション検索
            applicable_rules = self._find_migration_path(
                section_name, from_version, self.current_version
            )
            
            if not applicable_rules:
                logger.debug(f"マイグレーション不要: {section_name} v{from_version}")
                return data
            
            # マイグレーション順次実行
            migrated_data = data.copy()
            for rule in applicable_rules:
                logger.info(f"マイグレーション実行: {rule.description}")
                migrated_data = rule.migration_func(migrated_data)
            
            logger.info(f"マイグレーション完了: {section_name} v{from_version}→v{self.current_version}")
            return migrated_data
            
        except Exception as e:
            logger.error(f"マイグレーションエラー {section_name}: {e}")
            raise
    
    def _find_migration_path(self, section: str, from_ver: str, to_ver: str) -> List[MigrationRule]:
        """マイグレーションパス検索"""
        # 該当セクションのルール抽出
        section_rules = [r for r in self._migration_rules if r.section == section]
        
        # バージョン順ソート
        section_rules.sort(key=lambda r: version.parse(r.from_version))
        
        # パス構築
        path = []
        current_ver = from_ver
        
        while version.parse(current_ver) < version.parse(to_ver):
            found_rule = None
            for rule in section_rules:
                if (version.parse(rule.from_version) <= version.parse(current_ver) and
                    version.parse(rule.to_version) > version.parse(current_ver)):
                    found_rule = rule
                    break
            
            if not found_rule:
                break
            
            path.append(found_rule)
            current_ver = found_rule.to_version
        
        return path
    
    def _migrate_llm_v0_9_to_v1_0(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """LLM設定 v0.9→v1.0 マイグレーション"""
        migrated = data.copy()
        
        # 旧形式のAPI設定を新形式に変換
        if 'api_settings' in migrated:
            old_settings = migrated.pop('api_settings')
            
            # プロバイダー設定構築
            providers = {}
            
            if 'openai' in old_settings:
                providers['openai'] = {
                    'api_key': old_settings['openai'].get('api_key', ''),
                    'base_url': 'https://api.openai.com/v1',
                    'models': ['gpt-3.5-turbo', 'gpt-4'],
                    'enabled': old_settings['openai'].get('enabled', True),
                    'timeout': 30.0,
                    'retry_count': 3,
                    'rate_limit': 60
                }
            
            migrated['providers'] = providers
            migrated['default_provider'] = 'openai'
            migrated['default_model'] = 'gpt-3.5-turbo'
        
        return migrated
    
    def _migrate_ui_v0_9_to_v1_0(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """UI設定 v0.9→v1.0 マイグレーション"""
        migrated = data.copy()
        
        # ウィンドウ設定の構造変更
        if 'window_width' in migrated or 'window_height' in migrated:
            window_config = {
                'width': migrated.pop('window_width', 800),
                'height': migrated.pop('window_height', 600),
                'x': migrated.pop('window_x', 100),
                'y': migrated.pop('window_y', 100),
                'maximized': migrated.pop('maximized', False),
                'fullscreen': False
            }
            migrated['window'] = window_config
        
        # チャット設定の追加
        if 'chat' not in migrated:
            migrated['chat'] = {
                'auto_save': True,
                'history_limit': 1000,
                'word_wrap': True,
                'syntax_highlight': True,
                'show_timestamps': False,
                'export_format': 'json'
            }
        
        return migrated
    
    def _migrate_security_v1_0_to_v1_1(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """セキュリティ設定 v1.0→v1.1 マイグレーション"""
        migrated = data.copy()
        
        # 新しいセキュリティ設定追加
        if 'password_policy' not in migrated:
            migrated['password_policy'] = {
                'min_length': 8,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_symbols': False
            }
        
        if 'proxy_settings' not in migrated:
            migrated['proxy_settings'] = {
                'enabled': False,
                'host': '',
                'port': 8080,
                'username': '',
                'password': ''
            }
        
        return migrated
    
    def get_migration_history(self, section: str, from_version: str) -> List[Dict[str, Any]]:
        """マイグレーション履歴取得"""
        applicable_rules = self._find_migration_path(section, from_version, self.current_version)
        
        history = []
        for rule in applicable_rules:
            history.append({
                'from_version': rule.from_version,
                'to_version': rule.to_version,
                'description': rule.description,
                'created_at': rule.created_at.isoformat()
            })
        
        return history
    
    def validate_migration(self, section: str, old_data: Dict[str, Any], 
                          new_data: Dict[str, Any]) -> bool:
        """マイグレーション検証"""
        try:
            # 基本検証: 必須キーの存在確認
            required_keys = self._get_required_keys(section)
            
            for key in required_keys:
                if key not in new_data:
                    logger.error(f"マイグレーション検証失敗: 必須キー不足 {key}")
                    return False
            
            # データ型検証
            if not self._validate_data_types(section, new_data):
                return False
            
            logger.debug(f"マイグレーション検証成功: {section}")
            return True
            
        except Exception as e:
            logger.error(f"マイグレーション検証エラー: {e}")
            return False
    
    def _get_required_keys(self, section: str) -> List[str]:
        """必須キー取得"""
        required_keys_map = {
            'llm': ['default_provider', 'default_model', 'providers'],
            'ui': ['theme', 'language'],
            'security': ['encryption_enabled', 'session_timeout'],
            'app': ['name', 'version']
        }
        return required_keys_map.get(section, [])
    
    def _validate_data_types(self, section: str, data: Dict[str, Any]) -> bool:
        """データ型検証"""
        type_rules = {
            'llm': {
                'default_provider': str,
                'default_model': str,
                'providers': dict
            },
            'ui': {
                'theme': str,
                'language': str,
                'font_size': int
            },
            'security': {
                'encryption_enabled': bool,
                'session_timeout': int
            }
        }
        
        rules = type_rules.get(section, {})
        
        for key, expected_type in rules.items():
            if key in data and not isinstance(data[key], expected_type):
                logger.error(f"型検証失敗: {key} は {expected_type.__name__} である必要があります")
                return False
        
        return True
    
    def export_migration_rules(self, output_path: Path):
        """マイグレーションルールエクスポート"""
        try:
            rules_data = []
            for rule in self._migration_rules:
                rules_data.append({
                    'from_version': rule.from_version,
                    'to_version': rule.to_version,
                    'section': rule.section,
                    'description': rule.description,
                    'created_at': rule.created_at.isoformat()
                })
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"マイグレーションルールエクスポート完了: {output_path}")
            
        except Exception as e:
            logger.error(f"エクスポートエラー: {e}")
            raise

# 使用例とテスト
def test_migration_system():
    """マイグレーションシステムテスト"""
    migrator = ConfigMigrator()
    
    # テスト用旧設定
    old_llm_config = {
        'api_settings': {
            'openai': {
                'api_key': 'sk-test123',
                'enabled': True
            }
        },
        'timeout': 30
    }
    
    # マイグレーション実行
    new_config = migrator.migrate_section('llm', old_llm_config, '0.9.0')
    
    print("=== マイグレーション結果 ===")
    print(json.dumps(new_config, indent=2, ensure_ascii=False))
    
    # 検証
    is_valid = migrator.validate_migration('llm', old_llm_config, new_config)
    print(f"検証結果: {'成功' if is_valid else '失敗'}")
    
    # 履歴表示
    history = migrator.get_migration_history('llm', '0.9.0')
    print("\n=== マイグレーション履歴 ===")
    for item in history:
        print(f"v{item['from_version']} → v{item['to_version']}: {item['description']}")

if __name__ == "__main__":
    test_migration_system()
