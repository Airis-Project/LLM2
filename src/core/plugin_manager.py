#!/usr/bin/env python3
#src/core/plugin_manager.py
# -*- coding: utf-8 -*-
"""
プラグインマネージャーモジュール
プラグインの動的読み込みと管理を行う
"""

import os
import sys
import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class PluginInterface(ABC):
    """プラグインインターフェース"""
    
    @abstractmethod
    def get_name(self) -> str:
        """プラグイン名を取得"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """プラグインバージョンを取得"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """プラグインの説明を取得"""
        pass
    
    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> bool:
        """プラグインを初期化"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """プラグインのクリーンアップ"""
        pass

class PluginManager:
    """
    プラグインマネージャークラス
    プラグインの読み込み、管理、実行を行う
    """
    
    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """
        プラグインマネージャーを初期化
        
        Args:
            plugin_dirs: プラグインディレクトリのリスト
        """
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_dirs = plugin_dirs or []
        self.loaded_modules: Dict[str, Any] = {}
        
        # デフォルトのプラグインディレクトリを設定
        if not self.plugin_dirs:
            project_root = Path(__file__).parent.parent.parent
            default_plugin_dir = project_root / "plugins"
            if default_plugin_dir.exists():
                self.plugin_dirs.append(str(default_plugin_dir))
        
        # プラグインを読み込み
        self.load_plugins()
        
        logger.info("プラグインマネージャーが初期化されました")
    
    def load_plugins(self):
        """すべてのプラグインディレクトリからプラグインを読み込み"""
        try:
            discovered_plugins = []
            
            for plugin_dir in self.plugin_dirs:
                if not os.path.exists(plugin_dir):
                    logger.warning(f"プラグインディレクトリが存在しません: {plugin_dir}")
                    continue
                
                plugins_in_dir = self.discover_plugins(plugin_dir)
                discovered_plugins.extend(plugins_in_dir)
            
            # 重複を除去
            unique_plugins = {}
            for plugin_info in discovered_plugins:
                plugin_name = plugin_info['name']
                if plugin_name not in unique_plugins:
                    unique_plugins[plugin_name] = plugin_info
            
            logger.info(f"{len(unique_plugins)}個のプラグインを発見しました")
            
            # プラグインを読み込み
            loaded_count = 0
            for plugin_name, plugin_info in unique_plugins.items():
                try:
                    if self.load_plugin(plugin_info):
                        loaded_count += 1
                except Exception as e:
                    logger.error(f"プラグイン読み込み失敗: {plugin_name} - {e}")
            
            logger.info(f"{loaded_count}/{len(unique_plugins)}個のプラグインを読み込みました")
            
        except Exception as e:
            logger.error(f"プラグイン読み込み中にエラーが発生しました: {e}")
    
    def discover_plugins(self, plugin_dir: str) -> List[Dict[str, Any]]:
        """
        指定されたディレクトリからプラグインを発見
        
        Args:
            plugin_dir: プラグインディレクトリのパス
            
        Returns:
            発見されたプラグインの情報リスト
        """
        plugins = []
        
        try:
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                
                # ディレクトリの場合
                if os.path.isdir(item_path):
                    # __init__.pyまたはmain.pyが存在するかチェック
                    init_file = os.path.join(item_path, "__init__.py")
                    main_file = os.path.join(item_path, "main.py")
                    
                    if os.path.exists(init_file) or os.path.exists(main_file):
                        plugin_info = {
                            'name': item,
                            'path': item_path,
                            'type': 'directory',
                            'entry_point': main_file if os.path.exists(main_file) else init_file
                        }
                        plugins.append(plugin_info)
                        logger.info(f"プラグインを発見しました: {item}")
                
                # .pyファイルの場合
                elif item.endswith('.py') and not item.startswith('__'):
                    plugin_name = item[:-3]  # .pyを除去
                    plugin_info = {
                        'name': plugin_name,
                        'path': item_path,
                        'type': 'file',
                        'entry_point': item_path
                    }
                    plugins.append(plugin_info)
                    logger.info(f"プラグインを発見しました: {plugin_name}")
                    
        except Exception as e:
            logger.error(f"プラグイン発見中にエラーが発生しました: {e}")
        
        return plugins
    
    def load_plugin(self, plugin_info: Dict[str, Any]) -> bool:
        """
        個別のプラグインを読み込み
        
        Args:
            plugin_info: プラグイン情報
            
        Returns:
            読み込み成功の場合True
        """
        plugin_name = plugin_info['name']
        plugin_path = plugin_info['entry_point']
        
        try:
            # モジュールの仕様を作成
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None or spec.loader is None:
                logger.error(f"プラグインの仕様を作成できませんでした: {plugin_name}")
                return False
            
            # モジュールを作成
            module = importlib.util.module_from_spec(spec)
            
            # プロジェクトルートをパスに追加（相対インポート対応）
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            # プラグインディレクトリをパスに追加
            plugin_dir = Path(plugin_path).parent
            if str(plugin_dir) not in sys.path:
                sys.path.insert(0, str(plugin_dir))
            
            # モジュールを実行
            spec.loader.exec_module(module)
            
            # プラグインクラスを検索
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginInterface) and 
                    attr != PluginInterface):
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                logger.error(f"プラグインクラスが見つかりません: {plugin_name}")
                return False
            
            # プラグインインスタンスを作成
            plugin_instance = plugin_class()
            
            # プラグインを初期化
            context = {
                'plugin_manager': self,
                'plugin_name': plugin_name,
                'plugin_path': plugin_path
            }
            
            if plugin_instance.initialize(context):
                self.plugins[plugin_name] = plugin_instance
                self.loaded_modules[plugin_name] = module
                logger.info(f"プラグインを読み込みました: {plugin_name}")
                return True
            else:
                logger.error(f"プラグインの初期化に失敗しました: {plugin_name}")
                return False
                
        except Exception as e:
            logger.error(f"プラグインモジュール読み込みエラー {plugin_name}: {e}")
            logger.error(f"プラグインモジュール読み込み失敗: {plugin_name}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """
        指定されたプラグインを取得
        
        Args:
            plugin_name: プラグイン名
            
        Returns:
            プラグインインスタンス、存在しない場合はNone
        """
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginInterface]:
        """
        すべてのプラグインを取得
        
        Returns:
            プラグイン辞書
        """
        return self.plugins.copy()
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, str]]:
        """
        プラグインの情報を取得
        
        Args:
            plugin_name: プラグイン名
            
        Returns:
            プラグイン情報辞書
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return {
                'name': plugin.get_name(),
                'version': plugin.get_version(),
                'description': plugin.get_description()
            }
        return None
    
    def list_plugins(self) -> List[str]:
        """
        読み込まれているプラグインの一覧を取得
        
        Returns:
            プラグイン名のリスト
        """
        return list(self.plugins.keys())
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        プラグインをアンロード
        
        Args:
            plugin_name: プラグイン名
            
        Returns:
            アンロード成功の場合True
        """
        try:
            if plugin_name in self.plugins:
                # プラグインのクリーンアップ
                self.plugins[plugin_name].cleanup()
                
                # プラグインを削除
                del self.plugins[plugin_name]
                
                # モジュールも削除
                if plugin_name in self.loaded_modules:
                    del self.loaded_modules[plugin_name]
                
                logger.info(f"プラグインをアンロードしました: {plugin_name}")
                return True
            else:
                logger.warning(f"プラグインが見つかりません: {plugin_name}")
                return False
                
        except Exception as e:
            logger.error(f"プラグインアンロード中にエラーが発生しました: {plugin_name} - {e}")
            return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """
        プラグインを再読み込み
        
        Args:
            plugin_name: プラグイン名
            
        Returns:
            再読み込み成功の場合True
        """
        try:
            # 現在のプラグイン情報を保存
            if plugin_name not in self.plugins:
                logger.error(f"プラグインが見つかりません: {plugin_name}")
                return False
            
            # プラグインをアンロード
            if not self.unload_plugin(plugin_name):
                return False
            
            # プラグインを再読み込み
            self.load_plugins()
            
            return plugin_name in self.plugins
            
        except Exception as e:
            logger.error(f"プラグイン再読み込み中にエラーが発生しました: {plugin_name} - {e}")
            return False
    
    def cleanup(self):
        """すべてのプラグインをクリーンアップ"""
        try:
            for plugin_name in list(self.plugins.keys()):
                self.unload_plugin(plugin_name)
            
            logger.info("すべてのプラグインがクリーンアップされました")
            
        except Exception as e:
            logger.error(f"プラグインクリーンアップ中にエラーが発生しました: {e}")
