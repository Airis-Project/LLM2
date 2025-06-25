#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定管理モジュール - LLM Code Assistant

アプリケーションの設定を管理するモジュール
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from src.core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class AppConfig:
    """アプリケーション設定クラス"""
    # アプリケーション基本設定
    app_name: str = "LLM Code Assistant"
    version: str = "1.0.0"
    debug: bool = False
    
    # ディレクトリ設定
    base_dir: str = ""
    data_dir: str = "data"
    templates_dir: str = "data/templates"
    output_dir: str = "output"
    logs_dir: str = "logs"
    
    # LLM設定
    llm_provider: str = "openai"
    llm_model: str = "gpt-3.5-turbo"
    max_tokens: int = 2000
    temperature: float = 0.7
    
    # テンプレート設定
    template_encoding: str = "utf-8"
    template_extension: str = ".template"
    
    # プラグイン設定
    plugins_enabled: bool = True
    plugin_dirs: list = field(default_factory=lambda: ["plugins"])
    
    # イベントシステム設定
    event_system: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "max_listeners": 100,
        "async_enabled": True,
        "debug": False
    })
    
    # プロジェクト管理設定
    project_manager: Dict[str, Any] = field(default_factory=lambda: {
        "auto_save": True,
        "backup_enabled": True,
        "max_backups": 5
    })
    
    # その他の設定
    _config_data: Dict[str, Any] = field(default_factory=dict, init=False)
    
    def __post_init__(self):
        """初期化後の処理"""
        if not self.base_dir:
            self.base_dir = str(Path.cwd())
        
        # 相対パスを絶対パスに変換
        self._resolve_paths()
        
        # 設定データの初期化
        self._config_data = asdict(self)
    
    def _resolve_paths(self):
        """パスの解決"""
        base_path = Path(self.base_dir)
        
        # 各ディレクトリパスを絶対パスに変換
        self.data_dir = str(base_path / self.data_dir)
        self.templates_dir = str(base_path / self.templates_dir)
        self.output_dir = str(base_path / self.output_dir)
        self.logs_dir = str(base_path / self.logs_dir)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値を取得（辞書形式のアクセス）
        
        Args:
            key: 設定キー（ドット記法対応）
            default: デフォルト値
            
        Returns:
            Any: 設定値
        """
        try:
            keys = key.split('.')
            value = self._config_data
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
        except Exception:
            return default
    
    def set(self, key: str, value: Any):
        """
        設定値を設定（ドット記法対応）
        
        Args:
            key: 設定キー
            value: 設定値
        """
        try:
            keys = key.split('.')
            config = self._config_data
            
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            config[keys[-1]] = value
            
            # データクラスの属性も更新
            if hasattr(self, keys[0]):
                if len(keys) == 1:
                    setattr(self, keys[0], value)
                elif len(keys) == 2 and hasattr(self, keys[0]):
                    attr = getattr(self, keys[0])
                    if isinstance(attr, dict):
                        attr[keys[1]] = value
                        
        except Exception as e:
            logger.error(f"設定値の設定に失敗: {key} = {value}, エラー: {e}")
    
    def update(self, config_dict: Dict[str, Any]):
        """
        設定の一括更新
        
        Args:
            config_dict: 設定辞書
        """
        try:
            self._config_data.update(config_dict)
            
            # データクラス属性の更新
            for key, value in config_dict.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    
        except Exception as e:
            logger.error(f"設定の一括更新に失敗: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """設定を辞書として取得"""
        return self._config_data.copy()
    
    def __getitem__(self, key: str) -> Any:
        """辞書形式のアクセス"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """辞書形式の設定"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """キーの存在確認"""
        return self.get(key) is not None

class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初期化
        
        Args:
            config_file: 設定ファイルパス
        """
        self.config_file = config_file
        self.config = AppConfig()
        self._load_config()
    
    def _load_config(self):
        """設定ファイルの読み込み"""
        try:
            if self.config_file and Path(self.config_file).exists():
                logger.info(f"設定ファイルを読み込み中: {self.config_file}")
                
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)
                
                if config_data:
                    self.config.update(config_data)
                    logger.info("設定ファイルの読み込みが完了しました")
            else:
                logger.info("デフォルト設定ファイルを読み込み中...")
                # デフォルト設定ファイルの検索
                default_configs = [
                    "config.yaml",
                    "config.yml", 
                    "config.json",
                    "data/config.yaml",
                    "data/config.yml",
                    "data/config.json"
                ]
                
                for config_path in default_configs:
                    if Path(config_path).exists():
                        self.config_file = config_path
                        return self._load_config()
                
                logger.info("設定ファイルの読み込みが完了しました")
                
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗: {e}")
            logger.info("デフォルト設定を使用します")
    
    def save_config(self, config_file: Optional[str] = None):
        """
        設定ファイルの保存
        
        Args:
            config_file: 保存先ファイルパス
        """
        try:
            save_path = config_file or self.config_file or "config.yaml"
            
            # ディレクトリの作成
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.endswith('.yaml') or save_path.endswith('.yml'):
                    yaml.dump(self.config.to_dict(), f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"設定ファイルを保存しました: {save_path}")
            
        except Exception as e:
            logger.error(f"設定ファイルの保存に失敗: {e}")
    
    def get_config(self, section: str = None, default: Any = None) -> Any:
        """
        設定を取得する
        
        Args:
            section: 設定セクション名
            default: デフォルト値
            
        Returns:
            設定値
        """
        if section is None:
            return self.config
        
        return self.config.get(section, default)
    
    def reload_config(self):
        """設定の再読み込み"""
        self._load_config()

# グローバル設定インスタンス
_config_manager: Optional[ConfigManager] = None

def get_config() -> AppConfig:
    """
    グローバル設定インスタンスを取得
    
    Returns:
        AppConfig: 設定オブジェクト
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    return _config_manager.get_config()

def init_config(config_file: Optional[str] = None) -> AppConfig:
    """
    設定の初期化
    
    Args:
        config_file: 設定ファイルパス
        
    Returns:
        AppConfig: 設定オブジェクト
    """
    global _config_manager
    _config_manager = ConfigManager(config_file)
    return _config_manager.get_config()

def save_config(config_file: Optional[str] = None):
    """
    設定の保存
    
    Args:
        config_file: 保存先ファイルパス
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    _config_manager.save_config(config_file)
