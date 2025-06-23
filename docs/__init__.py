# docs/__init__.py
# LLM Code Assistant - ドキュメントパッケージ初期化

"""
LLM Code Assistant - ドキュメントパッケージ

このパッケージには、LLM Code Assistantのドキュメント関連の機能が含まれています。

モジュール:
- user_guide: ユーザーガイド
- api_reference: API リファレンス
- development_guide: 開発ガイド
- architecture: アーキテクチャ設計書

作成者: LLM Code Assistant Team
バージョン: 1.0.0
作成日: 2024-01-01
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# ロガーの設定
logger = logging.getLogger(__name__)

# ドキュメントディレクトリのパス
DOCS_DIR = Path(__file__).parent
PROJECT_ROOT = DOCS_DIR.parent

# ドキュメントファイルの定義
DOCUMENT_FILES = {
    'user_guide': 'user_guide.md',
    'api_reference': 'api_reference.md', 
    'development_guide': 'development_guide.md',
    'architecture': 'architecture.md'
}

# サポートされているドキュメント形式
SUPPORTED_FORMATS = ['.md', '.rst', '.txt', '.html']

class DocumentationManager:
    """
    ドキュメント管理クラス
    
    ドキュメントファイルの読み込み、検索、生成などの機能を提供します。
    """
    
    def __init__(self, docs_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            docs_dir: ドキュメントディレクトリのパス
        """
        self.docs_dir = docs_dir or DOCS_DIR
        self.documents = {}
        self._load_documents()
    
    def _load_documents(self) -> None:
        """ドキュメントファイルを読み込み"""
        try:
            for doc_type, filename in DOCUMENT_FILES.items():
                file_path = self.docs_dir / filename
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.documents[doc_type] = {
                            'content': f.read(),
                            'path': file_path,
                            'last_modified': file_path.stat().st_mtime
                        }
                    logger.debug(f"ドキュメントを読み込みました: {filename}")
                else:
                    logger.warning(f"ドキュメントファイルが見つかりません: {filename}")
        except Exception as e:
            logger.error(f"ドキュメント読み込みエラー: {e}")
    
    def get_document(self, doc_type: str) -> Optional[Dict[str, Any]]:
        """
        指定されたタイプのドキュメントを取得
        
        Args:
            doc_type: ドキュメントタイプ
            
        Returns:
            ドキュメント情報（存在しない場合はNone）
        """
        return self.documents.get(doc_type)
    
    def get_document_content(self, doc_type: str) -> Optional[str]:
        """
        指定されたタイプのドキュメント内容を取得
        
        Args:
            doc_type: ドキュメントタイプ
            
        Returns:
            ドキュメント内容（存在しない場合はNone）
        """
        doc = self.get_document(doc_type)
        return doc['content'] if doc else None
    
    def list_documents(self) -> List[str]:
        """
        利用可能なドキュメントタイプの一覧を取得
        
        Returns:
            ドキュメントタイプのリスト
        """
        return list(self.documents.keys())
    
    def search_documents(self, query: str, case_sensitive: bool = False) -> Dict[str, List[str]]:
        """
        ドキュメント内をキーワード検索
        
        Args:
            query: 検索クエリ
            case_sensitive: 大文字小文字を区別するか
            
        Returns:
            検索結果（ドキュメントタイプ -> マッチした行のリスト）
        """
        results = {}
        
        if not case_sensitive:
            query = query.lower()
        
        for doc_type, doc_info in self.documents.items():
            content = doc_info['content']
            if not case_sensitive:
                content = content.lower()
            
            matching_lines = []
            for line_num, line in enumerate(content.split('\n'), 1):
                if query in line:
                    matching_lines.append(f"Line {line_num}: {line.strip()}")
            
            if matching_lines:
                results[doc_type] = matching_lines
        
        return results
    
    def reload_documents(self) -> None:
        """ドキュメントを再読み込み"""
        self.documents.clear()
        self._load_documents()
        logger.info("ドキュメントを再読み込みしました")

def get_documentation_manager() -> DocumentationManager:
    """
    ドキュメントマネージャーのシングルトンインスタンスを取得
    
    Returns:
        DocumentationManager インスタンス
    """
    if not hasattr(get_documentation_manager, '_instance'):
        get_documentation_manager._instance = DocumentationManager()
    return get_documentation_manager._instance

def get_document_path(doc_type: str) -> Optional[Path]:
    """
    指定されたドキュメントタイプのファイルパスを取得
    
    Args:
        doc_type: ドキュメントタイプ
        
    Returns:
        ファイルパス（存在しない場合はNone）
    """
    if doc_type in DOCUMENT_FILES:
        return DOCS_DIR / DOCUMENT_FILES[doc_type]
    return None

def is_document_available(doc_type: str) -> bool:
    """
    指定されたドキュメントが利用可能かチェック
    
    Args:
        doc_type: ドキュメントタイプ
        
    Returns:
        利用可能かどうか
    """
    doc_path = get_document_path(doc_type)
    return doc_path is not None and doc_path.exists()

def get_all_document_paths() -> Dict[str, Path]:
    """
    全てのドキュメントファイルのパスを取得
    
    Returns:
        ドキュメントタイプ -> ファイルパスの辞書
    """
    return {
        doc_type: DOCS_DIR / filename
        for doc_type, filename in DOCUMENT_FILES.items()
    }

def validate_document_structure() -> Dict[str, bool]:
    """
    ドキュメント構造の妥当性を検証
    
    Returns:
        ドキュメントタイプ -> 存在するかどうかの辞書
    """
    validation_results = {}
    
    for doc_type, filename in DOCUMENT_FILES.items():
        file_path = DOCS_DIR / filename
        validation_results[doc_type] = file_path.exists()
        
        if not file_path.exists():
            logger.warning(f"ドキュメントファイルが見つかりません: {filename}")
    
    return validation_results

# パッケージレベルの関数とクラスをエクスポート
__all__ = [
    'DocumentationManager',
    'get_documentation_manager',
    'get_document_path',
    'is_document_available',
    'get_all_document_paths',
    'validate_document_structure',
    'DOCS_DIR',
    'PROJECT_ROOT',
    'DOCUMENT_FILES',
    'SUPPORTED_FORMATS'
]

# パッケージ情報
__version__ = '1.0.0'
__author__ = 'LLM Code Assistant Team'
__email__ = 'team@llm-code-assistant.com'
__description__ = 'LLM Code Assistant Documentation Package'

# 初期化時の処理
try:
    # ドキュメント構造の検証
    validation_results = validate_document_structure()
    missing_docs = [doc_type for doc_type, exists in validation_results.items() if not exists]
    
    if missing_docs:
        logger.warning(f"以下のドキュメントファイルが見つかりません: {', '.join(missing_docs)}")
    else:
        logger.info("全てのドキュメントファイルが確認されました")
        
except Exception as e:
    logger.error(f"ドキュメントパッケージの初期化エラー: {e}")

# デバッグ情報
if __name__ == "__main__":
    print(f"LLM Code Assistant - ドキュメントパッケージ v{__version__}")
    print(f"ドキュメントディレクトリ: {DOCS_DIR}")
    print(f"プロジェクトルート: {PROJECT_ROOT}")
    print("\n利用可能なドキュメント:")
    
    for doc_type, filename in DOCUMENT_FILES.items():
        file_path = DOCS_DIR / filename
        status = "✓" if file_path.exists() else "✗"
        print(f"  {status} {doc_type}: {filename}")
