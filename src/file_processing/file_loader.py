"""
ファイル読み込みモジュール
様々な形式のファイルを読み込み、統一されたインターフェースを提供
"""

import os
import json
import yaml
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, BinaryIO, TextIO
import mimetypes
import chardet
import logging

from ..core.logger import get_logger
from ..core.config_manager import get_config

logger = get_logger(__name__)

class FileLoader:
    """ファイル読み込みクラス"""
    
    def __init__(self, config: Optional[Any] = None):
        """
        初期化
        
        Args:
            config: 設定管理オブジェクト（オプション）
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = config or get_config()
        
        # サポートする拡張子とMIMEタイプ
        self.supported_extensions = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.html': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.yaml': 'application/x-yaml',
            '.yml': 'application/x-yaml',
            '.csv': 'text/csv',
            '.log': 'text/plain',
            '.sql': 'application/sql',
            '.sh': 'application/x-sh',
            '.bat': 'application/x-msdos-program',
            '.ini': 'text/plain',
            '.conf': 'text/plain',
            '.cfg': 'text/plain'
        }
        
        # エンコーディング検出の設定
        self.encoding_detection_enabled = self.config.get('encoding_detection', True)
        self.default_encoding = self.config.get('default_encoding', 'utf-8')
        self.max_file_size = self.config.get('max_file_size_mb', 10) * 1024 * 1024  # MB to bytes
        
        self.logger.info("FileLoader を初期化しました")
    
    def load_file(self, file_path: Union[str, Path], encoding: Optional[str] = None) -> Dict[str, Any]:
        """
        ファイルを読み込み
        
        Args:
            file_path: ファイルパス
            encoding: エンコーディング（指定しない場合は自動検出）
        
        Returns:
            Dict[str, Any]: ファイル情報と内容
        
        Raises:
            FileNotFoundError: ファイルが見つからない場合
            ValueError: サポートされていないファイル形式の場合
            IOError: ファイル読み込みエラーの場合
        """
        try:
            file_path = Path(file_path)
            
            # ファイル存在チェック
            if not file_path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
            
            # ファイルサイズチェック
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                raise ValueError(f"ファイルサイズが制限を超えています: {file_size / 1024 / 1024:.1f}MB > {self.max_file_size / 1024 / 1024}MB")
            
            # ファイル情報を取得
            file_info = self._get_file_info(file_path)
            
            # ファイル形式に応じて読み込み
            if file_info['extension'] in ['.json']:
                content = self._load_json_file(file_path, encoding)
            elif file_info['extension'] in ['.yaml', '.yml']:
                content = self._load_yaml_file(file_path, encoding)
            elif file_info['extension'] in ['.csv']:
                content = self._load_csv_file(file_path, encoding)
            elif file_info['extension'] in ['.xml']:
                content = self._load_xml_file(file_path, encoding)
            else:
                # テキストファイルとして読み込み
                content = self._load_text_file(file_path, encoding)
            
            # 結果を作成
            result = {
                'file_info': file_info,
                'content': content,
                'encoding': encoding or self._detect_encoding(file_path),
                'success': True,
                'error': None
            }
            
            self.logger.info(f"ファイルを読み込みました: {file_path}")
            return result
            
        except Exception as e:
            error_msg = f"ファイル読み込みエラー {file_path}: {e}"
            self.logger.error(error_msg)
            return {
                'file_info': {'path': str(file_path), 'name': file_path.name if isinstance(file_path, Path) else Path(file_path).name},
                'content': None,
                'encoding': None,
                'success': False,
                'error': str(e)
            }
    
    def load_multiple_files(self, file_paths: List[Union[str, Path]], 
                          encoding: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        複数ファイルを一括読み込み
        
        Args:
            file_paths: ファイルパスのリスト
            encoding: エンコーディング
        
        Returns:
            List[Dict[str, Any]]: ファイル情報と内容のリスト
        """
        try:
            results = []
            for file_path in file_paths:
                result = self.load_file(file_path, encoding)
                results.append(result)
            
            success_count = sum(1 for r in results if r['success'])
            self.logger.info(f"複数ファイル読み込み完了: {success_count}/{len(file_paths)} 成功")
            
            return results
            
        except Exception as e:
            self.logger.error(f"複数ファイル読み込みエラー: {e}")
            return []
    
    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """ファイル情報を取得"""
        try:
            stat = file_path.stat()
            extension = file_path.suffix.lower()
            mime_type = self.supported_extensions.get(extension) or mimetypes.guess_type(str(file_path))[0]
            
            return {
                'path': str(file_path),
                'name': file_path.name,
                'stem': file_path.stem,
                'extension': extension,
                'mime_type': mime_type,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'is_supported': extension in self.supported_extensions
            }
            
        except Exception as e:
            self.logger.error(f"ファイル情報取得エラー {file_path}: {e}")
            return {
                'path': str(file_path),
                'name': file_path.name,
                'extension': file_path.suffix.lower(),
                'error': str(e)
            }
    
    def _detect_encoding(self, file_path: Path) -> str:
        """エンコーディングを検出"""
        try:
            if not self.encoding_detection_enabled:
                return self.default_encoding
            
            with open(file_path, 'rb') as f:
                raw_data = f.read(8192)  # 最初の8KBで検出
                
            result = chardet.detect(raw_data)
            detected_encoding = result.get('encoding')
            confidence = result.get('confidence', 0)
            
            # 信頼度が低い場合はデフォルトエンコーディングを使用
            if confidence < 0.7:
                self.logger.warning(f"エンコーディング検出の信頼度が低いです: {confidence:.2f}")
                return self.default_encoding
            
            self.logger.debug(f"エンコーディング検出: {detected_encoding} (信頼度: {confidence:.2f})")
            return detected_encoding or self.default_encoding
            
        except Exception as e:
            self.logger.error(f"エンコーディング検出エラー {file_path}: {e}")
            return self.default_encoding
    
    def _load_text_file(self, file_path: Path, encoding: Optional[str] = None) -> str:
        """テキストファイルを読み込み"""
        try:
            if not encoding:
                encoding = self._detect_encoding(file_path)
            
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            
            return content
            
        except Exception as e:
            self.logger.error(f"テキストファイル読み込みエラー {file_path}: {e}")
            raise IOError(f"テキストファイルの読み込みに失敗しました: {e}")
    
    def _load_json_file(self, file_path: Path, encoding: Optional[str] = None) -> Any:
        """JSONファイルを読み込み"""
        try:
            content = self._load_text_file(file_path, encoding)
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析エラー {file_path}: {e}")
            raise ValueError(f"JSONファイルの解析に失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"JSONファイル読み込みエラー {file_path}: {e}")
            raise IOError(f"JSONファイルの読み込みに失敗しました: {e}")
    
    def _load_yaml_file(self, file_path: Path, encoding: Optional[str] = None) -> Any:
        """YAMLファイルを読み込み"""
        try:
            content = self._load_text_file(file_path, encoding)
            return yaml.safe_load(content)
            
        except yaml.YAMLError as e:
            self.logger.error(f"YAML解析エラー {file_path}: {e}")
            raise ValueError(f"YAMLファイルの解析に失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"YAMLファイル読み込みエラー {file_path}: {e}")
            raise IOError(f"YAMLファイルの読み込みに失敗しました: {e}")
    
    def _load_csv_file(self, file_path: Path, encoding: Optional[str] = None) -> List[Dict[str, Any]]:
        """CSVファイルを読み込み"""
        try:
            if not encoding:
                encoding = self._detect_encoding(file_path)
            
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                # CSVの方言を自動検出
                sample = f.read(1024)
                f.seek(0)
                
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(f, delimiter=delimiter)
                return list(reader)
                
        except Exception as e:
            self.logger.error(f"CSVファイル読み込みエラー {file_path}: {e}")
            raise IOError(f"CSVファイルの読み込みに失敗しました: {e}")
    
    def _load_xml_file(self, file_path: Path, encoding: Optional[str] = None) -> Dict[str, Any]:
        """XMLファイルを読み込み"""
        try:
            content = self._load_text_file(file_path, encoding)
            root = ET.fromstring(content)
            
            def xml_to_dict(element):
                """XML要素を辞書に変換"""
                result = {}
                
                # 属性を追加
                if element.attrib:
                    result['@attributes'] = element.attrib
                
                # テキストコンテンツを追加
                if element.text and element.text.strip():
                    result['text'] = element.text.strip()
                
                # 子要素を追加
                children = {}
                for child in element:
                    child_data = xml_to_dict(child)
                    if child.tag in children:
                        if not isinstance(children[child.tag], list):
                            children[child.tag] = [children[child.tag]]
                        children[child.tag].append(child_data)
                    else:
                        children[child.tag] = child_data
                
                result.update(children)
                return result
            
            return {
                'root': root.tag,
                'data': xml_to_dict(root)
            }
            
        except ET.ParseError as e:
            self.logger.error(f"XML解析エラー {file_path}: {e}")
            raise ValueError(f"XMLファイルの解析に失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"XMLファイル読み込みエラー {file_path}: {e}")
            raise IOError(f"XMLファイルの読み込みに失敗しました: {e}")
    
    def is_supported_file(self, file_path: Union[str, Path]) -> bool:
        """ファイルがサポートされているかチェック"""
        try:
            extension = Path(file_path).suffix.lower()
            return extension in self.supported_extensions
            
        except Exception as e:
            self.logger.error(f"ファイルサポートチェックエラー {file_path}: {e}")
            return False
    
    def get_supported_extensions(self) -> List[str]:
        """サポートされている拡張子のリストを取得"""
        return list(self.supported_extensions.keys())
    
    def get_file_preview(self, file_path: Union[str, Path], max_lines: int = 10) -> Dict[str, Any]:
        """ファイルのプレビューを取得"""
        try:
            file_path = Path(file_path)
            
            if not self.is_supported_file(file_path):
                return {
                    'preview': None,
                    'error': 'サポートされていないファイル形式です'
                }
            
            # ファイル情報を取得
            file_info = self._get_file_info(file_path)
            
            # テキストファイルのプレビューを取得
            try:
                encoding = self._detect_encoding(file_path)
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line.rstrip())
                
                preview = '\n'.join(lines)
                if i >= max_lines:
                    preview += f'\n... (残り {file_info.get("size", 0)} バイト)'
                
                return {
                    'file_info': file_info,
                    'preview': preview,
                    'encoding': encoding,
                    'total_lines': i + 1,
                    'error': None
                }
                
            except Exception as e:
                return {
                    'file_info': file_info,
                    'preview': None,
                    'error': f'プレビュー生成エラー: {e}'
                }
                
        except Exception as e:
            self.logger.error(f"ファイルプレビューエラー {file_path}: {e}")
            return {
                'preview': None,
                'error': str(e)
            }
    
    def validate_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """ファイルの妥当性を検証"""
        try:
            file_path = Path(file_path)
            
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'file_info': None
            }
            
            # ファイル存在チェック
            if not file_path.exists():
                validation_result['valid'] = False
                validation_result['errors'].append('ファイルが存在しません')
                return validation_result
            
            # ファイル情報を取得
            file_info = self._get_file_info(file_path)
            validation_result['file_info'] = file_info
            
            # サポート形式チェック
            if not file_info.get('is_supported', False):
                validation_result['warnings'].append('サポートされていないファイル形式です')
            
            # ファイルサイズチェック
            if file_info.get('size', 0) > self.max_file_size:
                validation_result['valid'] = False
                validation_result['errors'].append(f'ファイルサイズが制限を超えています: {file_info["size"] / 1024 / 1024:.1f}MB')
            
            # 読み取り権限チェック
            if not os.access(file_path, os.R_OK):
                validation_result['valid'] = False
                validation_result['errors'].append('ファイルの読み取り権限がありません')
            
            # エンコーディングチェック（テキストファイルの場合）
            if file_info.get('extension') in ['.txt', '.py', '.js', '.html', '.css', '.md']:
                try:
                    encoding = self._detect_encoding(file_path)
                    if encoding == self.default_encoding:
                        validation_result['warnings'].append('エンコーディングの自動検出に失敗しました')
                except Exception:
                    validation_result['warnings'].append('エンコーディングの検証に失敗しました')
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"ファイル検証エラー {file_path}: {e}")
            return {
                'valid': False,
                'errors': [str(e)],
                'warnings': [],
                'file_info': None
            }

# グローバルインスタンス管理
_file_loader_instance = None

def get_file_loader(config: Optional[Any] = None) -> FileLoader:
    """
    FileLoaderのシングルトンインスタンスを取得
    
    Args:
        config: 設定管理オブジェクト（オプション）
    
    Returns:
        FileLoader: ファイルローダーインスタンス
    """
    global _file_loader_instance
    
    if _file_loader_instance is None:
        _file_loader_instance = FileLoader(config)
    
    return _file_loader_instance

def reset_file_loader():
    """
    FileLoaderインスタンスをリセット（主にテスト用）
    """
    global _file_loader_instance
    _file_loader_instance = None
