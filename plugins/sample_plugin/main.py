#plugins/sample_plugin/main.py
"""
サンプルプラグイン
プラグインの基本的な実装例
"""

import logging
from typing import Dict, Any
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.plugin_manager import PluginInterface

logger = logging.getLogger(__name__)

class SamplePlugin(PluginInterface):
    """サンプルプラグインクラス"""
    
    def __init__(self):
        """プラグインを初期化"""
        self.name = "sample_plugin"
        self.version = "1.0.0"
        self.description = "サンプルプラグイン"
        self.initialized = False
    
    def get_name(self) -> str:
        """プラグイン名を取得"""
        return self.name
    
    def get_version(self) -> str:
        """プラグインバージョンを取得"""
        return self.version
    
    def get_description(self) -> str:
        """プラグインの説明を取得"""
        return self.description
    
    def initialize(self, context: Dict[str, Any]) -> bool:
        """
        プラグインを初期化
        
        Args:
            context: 初期化コンテキスト
            
        Returns:
            初期化成功の場合True
        """
        try:
            logger.info(f"プラグイン '{self.name}' を初期化しています...")
            
            # 初期化処理をここに記述
            self.plugin_manager = context.get('plugin_manager')
            self.plugin_path = context.get('plugin_path')
            
            self.initialized = True
            logger.info(f"プラグイン '{self.name}' の初期化が完了しました")
            
            return True
            
        except Exception as e:
            logger.error(f"プラグイン '{self.name}' の初期化中にエラーが発生しました: {e}")
            return False
    
    def cleanup(self) -> None:
        """プラグインのクリーンアップ"""
        try:
            if self.initialized:
                logger.info(f"プラグイン '{self.name}' をクリーンアップしています...")
                
                # クリーンアップ処理をここに記述
                
                self.initialized = False
                logger.info(f"プラグイン '{self.name}' のクリーンアップが完了しました")
                
        except Exception as e:
            logger.error(f"プラグイン '{self.name}' のクリーンアップ中にエラーが発生しました: {e}")
    
    def execute_action(self, action: str, params: Dict[str, Any] = None) -> Any:
        """
        プラグインのアクションを実行
        
        Args:
            action: アクション名
            params: パラメータ
            
        Returns:
            実行結果
        """
        if not self.initialized:
            logger.error(f"プラグイン '{self.name}' が初期化されていません")
            return None
        
        try:
            if action == "hello":
                return f"Hello from {self.name}!"
            elif action == "info":
                return {
                    'name': self.name,
                    'version': self.version,
                    'description': self.description
                }
            else:
                logger.warning(f"未知のアクション: {action}")
                return None
                
        except Exception as e:
            logger.error(f"アクション実行中にエラーが発生しました: {e}")
            return None
