"""
コードフォーマッタープラグイン
コードの整形機能を提供
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

class CodeFormatterPlugin(PluginInterface):
    """コードフォーマッタープラグインクラス"""
    
    def __init__(self):
        """プラグインを初期化"""
        self.name = "code_formatter"
        self.version = "1.0.0"
        self.description = "コードフォーマッター"
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
        """プラグインを初期化"""
        try:
            logger.info(f"プラグイン '{self.name}' を初期化しています...")
            
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
                self.initialized = False
                logger.info(f"プラグイン '{self.name}' のクリーンアップが完了しました")
                
        except Exception as e:
            logger.error(f"プラグイン '{self.name}' のクリーンアップ中にエラーが発生しました: {e}")
    
    def format_code(self, code: str, language: str = "python") -> str:
        """
        コードを整形
        
        Args:
            code: 整形するコード
            language: プログラミング言語
            
        Returns:
            整形されたコード
        """
        if not self.initialized:
            logger.error(f"プラグイン '{self.name}' が初期化されていません")
            return code
        
        try:
            # 簡単な整形処理（実際の実装では適切なフォーマッターを使用）
            lines = code.split('\n')
            formatted_lines = []
            indent_level = 0
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    formatted_lines.append('')
                    continue
                
                # インデントレベルを調整
                if stripped.endswith(':'):
                    formatted_lines.append('    ' * indent_level + stripped)
                    indent_level += 1
                elif stripped in ['else:', 'elif', 'except:', 'finally:']:
                    indent_level = max(0, indent_level - 1)
                    formatted_lines.append('    ' * indent_level + stripped)
                    indent_level += 1
                else:
                    formatted_lines.append('    ' * indent_level + stripped)
            
            return '\n'.join(formatted_lines)
            
        except Exception as e:
            logger.error(f"コード整形中にエラーが発生しました: {e}")
            return code
