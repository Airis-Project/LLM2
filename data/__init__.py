# data/__init__.py
# LLM Code Assistant - データパッケージ初期化

"""
LLM Code Assistant - データパッケージ

このパッケージには、アプリケーションで使用するデータファイル、
テンプレート、サンプルコードなどが含まれています。

パッケージ構成:
- templates: コード生成用テンプレートファイル
- examples: サンプルプロジェクトとデモコード

機能:
- テンプレートファイルの管理
- サンプルデータの提供
- データファイルのバリデーション
- テンプレートの動的読み込み

作成者: LLM Code Assistant Team
バージョン: 1.0.0
作成日: 2024-01-01
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import yaml

# ロガーの設定
logger = logging.getLogger(__name__)

# データディレクトリのパス
DATA_DIR = Path(__file__).parent
PROJECT_ROOT = DATA_DIR.parent

# サブディレクトリの定義
SUBDIRECTORIES = {
    'templates': 'コード生成用テンプレート',
    'examples': 'サンプルプロジェクトとデモコード'
}

# サポートされるファイル形式
SUPPORTED_FORMATS = {
    '.json': 'JSON形式',
    '.yaml': 'YAML形式',
    '.yml': 'YAML形式',
    '.template': 'テンプレートファイル',
    '.py': 'Pythonファイル',
    '.js': 'JavaScriptファイル',
    '.html': 'HTMLファイル',
    '.css': 'CSSファイル',
    '.md': 'Markdownファイル'
}

class DataManager:
    """
    データ管理クラス
    
    データファイルの読み込み、検証、管理を行います。
    """
    
    def __init__(self):
        """初期化"""
        self.data_cache = {}
        self.template_cache = {}
        self._validate_data_structure()
    
    def _validate_data_structure(self) -> None:
        """データ構造の妥当性を検証"""
        try:
            for subdir_name, description in SUBDIRECTORIES.items():
                subdir_path = DATA_DIR / subdir_name
                
                if not subdir_path.exists():
                    logger.warning(f"サブディレクトリが見つかりません: {subdir_name} ({subdir_path})")
                    # ディレクトリを作成
                    subdir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"サブディレクトリを作成しました: {subdir_name}")
                
                if not (subdir_path / '__init__.py').exists():
                    logger.warning(f"__init__.pyが見つかりません: {subdir_name}")
                
                logger.debug(f"サブディレクトリを確認: {subdir_name} - {description}")
                
        except Exception as e:
            logger.error(f"データ構造の検証エラー: {e}")
    
    def load_json_file(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        JSONファイルを読み込み
        
        Args:
            file_path: ファイルパス
            
        Returns:
            読み込まれたデータ（失敗時はNone）
        """
        file_path = Path(file_path)
        cache_key = str(file_path)
        
        # キャッシュから確認
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        try:
            if not file_path.exists():
                logger.error(f"ファイルが見つかりません: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # キャッシュに保存
            self.data_cache[cache_key] = data
            logger.debug(f"JSONファイルを読み込み: {file_path}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {file_path} - {e}")
            return None
        except Exception as e:
            logger.error(f"ファイル読み込みエラー: {file_path} - {e}")
            return None
    
    def load_yaml_file(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        YAMLファイルを読み込み
        
        Args:
            file_path: ファイルパス
            
        Returns:
            読み込まれたデータ（失敗時はNone）
        """
        file_path = Path(file_path)
        cache_key = str(file_path)
        
        # キャッシュから確認
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        try:
            if not file_path.exists():
                logger.error(f"ファイルが見つかりません: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # キャッシュに保存
            self.data_cache[cache_key] = data
            logger.debug(f"YAMLファイルを読み込み: {file_path}")
            return data
            
        except yaml.YAMLError as e:
            logger.error(f"YAML解析エラー: {file_path} - {e}")
            return None
        except Exception as e:
            logger.error(f"ファイル読み込みエラー: {file_path} - {e}")
            return None
    
    def load_text_file(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        テキストファイルを読み込み
        
        Args:
            file_path: ファイルパス
            
        Returns:
            読み込まれたテキスト（失敗時はNone）
        """
        file_path = Path(file_path)
        cache_key = str(file_path)
        
        # キャッシュから確認
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        try:
            if not file_path.exists():
                logger.error(f"ファイルが見つかりません: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # キャッシュに保存
            self.data_cache[cache_key] = content
            logger.debug(f"テキストファイルを読み込み: {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"ファイル読み込みエラー: {file_path} - {e}")
            return None
    
    def save_json_file(self, file_path: Union[str, Path], data: Dict[str, Any], 
                      indent: int = 2) -> bool:
        """
        JSONファイルに保存
        
        Args:
            file_path: ファイルパス
            data: 保存するデータ
            indent: インデント数
            
        Returns:
            保存成功フラグ
        """
        file_path = Path(file_path)
        
        try:
            # ディレクトリが存在しない場合は作成
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            
            # キャッシュを更新
            cache_key = str(file_path)
            self.data_cache[cache_key] = data
            
            logger.debug(f"JSONファイルを保存: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"ファイル保存エラー: {file_path} - {e}")
            return False
    
    def get_template_files(self) -> List[Path]:
        """
        テンプレートファイルの一覧を取得
        
        Returns:
            テンプレートファイルのパスリスト
        """
        template_dir = DATA_DIR / 'templates'
        template_files = []
        
        if template_dir.exists():
            for file_path in template_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix in SUPPORTED_FORMATS:
                    template_files.append(file_path)
        
        return sorted(template_files)
    
    def get_example_files(self) -> List[Path]:
        """
        サンプルファイルの一覧を取得
        
        Returns:
            サンプルファイルのパスリスト
        """
        examples_dir = DATA_DIR / 'examples'
        example_files = []
        
        if examples_dir.exists():
            for file_path in examples_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix in SUPPORTED_FORMATS:
                    example_files.append(file_path)
        
        return sorted(example_files)
    
    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        self.data_cache.clear()
        self.template_cache.clear()
        logger.debug("データキャッシュをクリアしました")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        キャッシュ情報を取得
        
        Returns:
            キャッシュ情報
        """
        return {
            'data_cache_size': len(self.data_cache),
            'template_cache_size': len(self.template_cache),
            'cached_files': list(self.data_cache.keys())
        }
    
    def validate_file_format(self, file_path: Union[str, Path]) -> bool:
        """
        ファイル形式の妥当性を検証
        
        Args:
            file_path: ファイルパス
            
        Returns:
            妥当性フラグ
        """
        file_path = Path(file_path)
        return file_path.suffix in SUPPORTED_FORMATS
    
    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        ファイル情報を取得
        
        Args:
            file_path: ファイルパス
            
        Returns:
            ファイル情報
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {'exists': False}
        
        stat = file_path.stat()
        
        return {
            'exists': True,
            'name': file_path.name,
            'suffix': file_path.suffix,
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'is_supported': self.validate_file_format(file_path),
            'format_description': SUPPORTED_FORMATS.get(file_path.suffix, '不明な形式')
        }

# データマネージャーのシングルトンインスタンス
_data_manager = None

def get_data_manager() -> DataManager:
    """
    データマネージャーのシングルトンインスタンスを取得
    
    Returns:
        DataManager インスタンス
    """
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager

def load_default_data() -> Dict[str, Any]:
    """
    デフォルトデータを読み込み
    
    Returns:
        デフォルトデータ
    """
    manager = get_data_manager()
    default_data = {}
    
    # サンプルプロジェクトの読み込み
    sample_project_path = DATA_DIR / 'examples' / 'sample_project.json'
    if sample_project_path.exists():
        sample_project = manager.load_json_file(sample_project_path)
        if sample_project:
            default_data['sample_project'] = sample_project
    
    return default_data

def get_package_info() -> Dict[str, Any]:
    """
    パッケージ情報を取得
    
    Returns:
        パッケージ情報
    """
    manager = get_data_manager()
    
    return {
        'data_dir': str(DATA_DIR),
        'project_root': str(PROJECT_ROOT),
        'subdirectories': SUBDIRECTORIES,
        'supported_formats': SUPPORTED_FORMATS,
        'template_files': len(manager.get_template_files()),
        'example_files': len(manager.get_example_files()),
        'cache_info': manager.get_cache_info()
    }

# パッケージレベルでエクスポートする要素
__all__ = [
    'DataManager',
    'get_data_manager',
    'load_default_data',
    'get_package_info',
    'DATA_DIR',
    'PROJECT_ROOT',
    'SUBDIRECTORIES',
    'SUPPORTED_FORMATS'
]

# パッケージ初期化時の処理
try:
    # データマネージャーの初期化
    manager = get_data_manager()
    logger.info("データパッケージが初期化されました")
    
except Exception as e:
    logger.error(f"データパッケージ初期化エラー: {e}")

# デバッグ情報の出力
if __name__ == "__main__":
    print("LLM Code Assistant - データパッケージ")
    print(f"データディレクトリ: {DATA_DIR}")
    print(f"プロジェクトルート: {PROJECT_ROOT}")
    
    print("\nサブディレクトリ:")
    for subdir, description in SUBDIRECTORIES.items():
        print(f"  - {subdir}: {description}")
    
    print("\nサポートされるファイル形式:")
    for ext, description in SUPPORTED_FORMATS.items():
        print(f"  - {ext}: {description}")
    
    print("\nパッケージ情報:")
    info = get_package_info()
    print(f"  テンプレートファイル数: {info['template_files']}")
    print(f"  サンプルファイル数: {info['example_files']}")
    print(f"  キャッシュサイズ: {info['cache_info']['data_cache_size']}")
