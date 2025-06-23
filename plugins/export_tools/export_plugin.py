# src/plugins/export_tools/export_plugin.py
"""
エクスポートツールプラグイン
プロジェクトやコードを様々な形式でエクスポートする機能を提供
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ..base_plugin import BasePlugin
from ...core.logger import get_logger
from ...core.event_system import EventSystem
from .export_formats import (
    PDFExporter,
    HTMLExporter,
    MarkdownExporter,
    ZipExporter,
    TarExporter,
    JSONExporter,
    XMLExporter
)


class ExportPlugin(BasePlugin):
    """エクスポートツールプラグイン"""
    
    def __init__(self):
        super().__init__(
            name="export_tools",
            version="1.0.0",
            description="プロジェクトやコードを様々な形式でエクスポート"
        )
        self.logger = get_logger("export_plugin")
        self.event_system = EventSystem()
        self.exporters = {}
        self._initialize_exporters()
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """プラグインを初期化"""
        try:
            self.config = config.get('export_tools', {})
            
            # エクスポーターの設定を更新
            for exporter_name, exporter in self.exporters.items():
                exporter_config = self.config.get(exporter_name, {})
                exporter.update_settings(exporter_config)
            
            # イベントハンドラーを登録
            self._register_event_handlers()
            
            self.logger.info("エクスポートプラグインが初期化されました")
            return True
            
        except Exception as e:
            self.logger.error(f"エクスポートプラグイン初期化エラー: {e}")
            return False
    
    def _initialize_exporters(self):
        """エクスポーターを初期化"""
        self.exporters = {
            'pdf': PDFExporter(),
            'html': HTMLExporter(),
            'markdown': MarkdownExporter(),
            'zip': ZipExporter(),
            'tar': TarExporter(),
            'json': JSONExporter(),
            'xml': XMLExporter()
        }
    
    def _register_event_handlers(self):
        """イベントハンドラーを登録"""
        self.event_system.subscribe('project_export_requested', self._handle_project_export)
        self.event_system.subscribe('file_export_requested', self._handle_file_export)
        self.event_system.subscribe('code_export_requested', self._handle_code_export)
    
    def get_available_formats(self) -> List[str]:
        """利用可能なエクスポート形式を取得"""
        available_formats = []
        
        for format_name, exporter in self.exporters.items():
            if exporter.is_available():
                available_formats.append(format_name)
        
        return available_formats
    
    def export_project(self, project_path: str, export_format: str, 
                      output_path: str, options: Dict[str, Any] = None) -> Tuple[bool, str]:
        """プロジェクト全体をエクスポート"""
        try:
            if export_format not in self.exporters:
                return False, f"サポートされていない形式: {export_format}"
            
            exporter = self.exporters[export_format]
            if not exporter.is_available():
                return False, f"エクスポーター '{export_format}' が利用できません"
            
            # プロジェクト情報を収集
            project_data = self._collect_project_data(project_path, options or {})
            
            # エクスポート実行
            success = exporter.export_project(project_data, output_path, options or {})
            
            if success:
                self.event_system.emit('project_exported', {
                    'project_path': project_path,
                    'format': export_format,
                    'output_path': output_path,
                    'timestamp': datetime.now().isoformat()
                })
                return True, f"プロジェクトが正常にエクスポートされました: {output_path}"
            else:
                return False, "エクスポート処理中にエラーが発生しました"
                
        except Exception as e:
            self.logger.error(f"プロジェクトエクスポートエラー: {e}")
            return False, f"エクスポートエラー: {str(e)}"
    
    def export_file(self, file_path: str, export_format: str, 
                   output_path: str, options: Dict[str, Any] = None) -> Tuple[bool, str]:
        """単一ファイルをエクスポート"""
        try:
            if export_format not in self.exporters:
                return False, f"サポートされていない形式: {export_format}"
            
            exporter = self.exporters[export_format]
            if not exporter.is_available():
                return False, f"エクスポーター '{export_format}' が利用できません"
            
            # ファイル情報を収集
            file_data = self._collect_file_data(file_path, options or {})
            
            # エクスポート実行
            success = exporter.export_file(file_data, output_path, options or {})
            
            if success:
                self.event_system.emit('file_exported', {
                    'file_path': file_path,
                    'format': export_format,
                    'output_path': output_path,
                    'timestamp': datetime.now().isoformat()
                })
                return True, f"ファイルが正常にエクスポートされました: {output_path}"
            else:
                return False, "エクスポート処理中にエラーが発生しました"
                
        except Exception as e:
            self.logger.error(f"ファイルエクスポートエラー: {e}")
            return False, f"エクスポートエラー: {str(e)}"
    
    def export_code_snippet(self, code: str, language: str, export_format: str,
                           output_path: str, options: Dict[str, Any] = None) -> Tuple[bool, str]:
        """コードスニペットをエクスポート"""
        try:
            if export_format not in self.exporters:
                return False, f"サポートされていない形式: {export_format}"
            
            exporter = self.exporters[export_format]
            if not exporter.is_available():
                return False, f"エクスポーター '{export_format}' が利用できません"
            
            # コードデータを準備
            code_data = {
                'content': code,
                'language': language,
                'timestamp': datetime.now().isoformat(),
                'metadata': options.get('metadata', {})
            }
            
            # エクスポート実行
            success = exporter.export_code(code_data, output_path, options or {})
            
            if success:
                self.event_system.emit('code_exported', {
                    'language': language,
                    'format': export_format,
                    'output_path': output_path,
                    'timestamp': datetime.now().isoformat()
                })
                return True, f"コードが正常にエクスポートされました: {output_path}"
            else:
                return False, "エクスポート処理中にエラーが発生しました"
                
        except Exception as e:
            self.logger.error(f"コードエクスポートエラー: {e}")
            return False, f"エクスポートエラー: {str(e)}"
    
    def _collect_project_data(self, project_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """プロジェクトデータを収集"""
        project_data = {
            'name': Path(project_path).name,
            'path': project_path,
            'files': [],
            'structure': {},
            'metadata': {
                'export_time': datetime.now().isoformat(),
                'total_files': 0,
                'total_size': 0
            }
        }
        
        try:
            # ファイル除外パターン
            exclude_patterns = options.get('exclude_patterns', [
                '*.pyc', '__pycache__', '.git', '.svn', 'node_modules',
                '*.log', '*.tmp', '.DS_Store'
            ])
            
            # ファイルを収集
            for root, dirs, files in os.walk(project_path):
                # 除外ディレクトリをスキップ
                dirs[:] = [d for d in dirs if not self._should_exclude(d, exclude_patterns)]
                
                for file in files:
                    if self._should_exclude(file, exclude_patterns):
                        continue
                    
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, project_path)
                    
                    file_info = self._get_file_info(file_path, relative_path)
                    if file_info:
                        project_data['files'].append(file_info)
                        project_data['metadata']['total_files'] += 1
                        project_data['metadata']['total_size'] += file_info.get('size', 0)
            
            # プロジェクト構造を構築
            project_data['structure'] = self._build_project_structure(project_data['files'])
            
        except Exception as e:
            self.logger.error(f"プロジェクトデータ収集エラー: {e}")
        
        return project_data
    
    def _collect_file_data(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """ファイルデータを収集"""
        file_data = {
            'path': file_path,
            'name': Path(file_path).name,
            'content': '',
            'metadata': {
                'export_time': datetime.now().isoformat()
            }
        }
        
        try:
            # ファイル情報を取得
            file_info = self._get_file_info(file_path, file_path)
            file_data.update(file_info)
            
            # ファイル内容を読み込み
            if options.get('include_content', True):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_data['content'] = f.read()
            
        except Exception as e:
            self.logger.error(f"ファイルデータ収集エラー: {e}")
        
        return file_data
    
    def _get_file_info(self, file_path: str, relative_path: str) -> Optional[Dict[str, Any]]:
        """ファイル情報を取得"""
        try:
            stat = os.stat(file_path)
            
            return {
                'path': file_path,
                'relative_path': relative_path,
                'name': Path(file_path).name,
                'extension': Path(file_path).suffix,
                'size': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'language': self._detect_language(file_path)
            }
            
        except Exception as e:
            self.logger.error(f"ファイル情報取得エラー ({file_path}): {e}")
            return None
    
    def _detect_language(self, file_path: str) -> str:
        """ファイルの言語を検出"""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.sql': 'sql',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.txt': 'text'
        }
        
        extension = Path(file_path).suffix.lower()
        return extension_map.get(extension, 'text')
    
    def _should_exclude(self, name: str, patterns: List[str]) -> bool:
        """ファイル/ディレクトリを除外するかチェック"""
        import fnmatch
        
        for pattern in patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False
    
    def _build_project_structure(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """プロジェクト構造を構築"""
        structure = {}
        
        for file_info in files:
            path_parts = Path(file_info['relative_path']).parts
            current = structure
            
            for part in path_parts[:-1]:  # ディレクトリ部分
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # ファイル部分
            file_name = path_parts[-1]
            current[file_name] = {
                'type': 'file',
                'size': file_info.get('size', 0),
                'language': file_info.get('language', 'text')
            }
        
        return structure
    
    def _handle_project_export(self, event_data: Dict[str, Any]):
        """プロジェクトエクスポートイベントハンドラー"""
        self.logger.info(f"プロジェクトエクスポート要求: {event_data}")
    
    def _handle_file_export(self, event_data: Dict[str, Any]):
        """ファイルエクスポートイベントハンドラー"""
        self.logger.info(f"ファイルエクスポート要求: {event_data}")
    
    def _handle_code_export(self, event_data: Dict[str, Any]):
        """コードエクスポートイベントハンドラー"""
        self.logger.info(f"コードエクスポート要求: {event_data}")
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """エクスポート履歴を取得"""
        # 実装は設定管理システムと連携
        return []
    
    def cleanup(self):
        """プラグインのクリーンアップ"""
        try:
            # イベントハンドラーの登録解除
            self.event_system.unsubscribe('project_export_requested', self._handle_project_export)
            self.event_system.unsubscribe('file_export_requested', self._handle_file_export)
            self.event_system.unsubscribe('code_export_requested', self._handle_code_export)
            
            # エクスポーターのクリーンアップ
            for exporter in self.exporters.values():
                if hasattr(exporter, 'cleanup'):
                    exporter.cleanup()
            
            self.logger.info("エクスポートプラグインがクリーンアップされました")
            
        except Exception as e:
            self.logger.error(f"エクスポートプラグインクリーンアップエラー: {e}")
