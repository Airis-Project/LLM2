# src/plugins/export_tools/export_formats.py
"""
エクスポート形式の実装
様々な形式でのエクスポート機能を提供
"""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod
import zipfile
import tarfile

from ...core.logger import get_logger


class BaseExporter(ABC):
    """エクスポーターの基底クラス"""
    
    def __init__(self, format_name: str):
        self.format_name = format_name
        self.logger = get_logger(f"exporter_{format_name}")
        self.settings = {}
    
    @abstractmethod
    def export_project(self, project_data: Dict[str, Any], output_path: str, 
                      options: Dict[str, Any]) -> bool:
        """プロジェクトをエクスポート"""
        pass
    
    @abstractmethod
    def export_file(self, file_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """ファイルをエクスポート"""
        pass
    
    @abstractmethod
    def export_code(self, code_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """コードをエクスポート"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """エクスポーターが利用可能かチェック"""
        pass
    
    def update_settings(self, settings: Dict[str, Any]):
        """設定を更新"""
        self.settings.update(settings)
    
    def _ensure_output_directory(self, output_path: str):
        """出力ディレクトリを確保"""
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)


class PDFExporter(BaseExporter):
    """PDFエクスポーター"""
    
    def __init__(self):
        super().__init__("pdf")
        self._check_dependencies()
    
    def _check_dependencies(self):
        """依存関係をチェック"""
        try:
            import reportlab
            self.has_reportlab = True
        except ImportError:
            self.has_reportlab = False
            self.logger.warning("reportlab が見つかりません。PDFエクスポートが無効です")
    
    def is_available(self) -> bool:
        """PDFエクスポーターが利用可能かチェック"""
        return self.has_reportlab
    
    def export_project(self, project_data: Dict[str, Any], output_path: str,
                      options: Dict[str, Any]) -> bool:
        """プロジェクトをPDFでエクスポート"""
        if not self.is_available():
            return False
        
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            
            self._ensure_output_directory(output_path)
            
            # PDFドキュメントを作成
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # タイトル
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=1  # 中央揃え
            )
            story.append(Paragraph(f"プロジェクト: {project_data['name']}", title_style))
            story.append(Spacer(1, 20))
            
            # プロジェクト情報
            info_style = styles['Normal']
            story.append(Paragraph(f"エクスポート日時: {project_data['metadata']['export_time']}", info_style))
            story.append(Paragraph(f"ファイル数: {project_data['metadata']['total_files']}", info_style))
            story.append(Paragraph(f"総サイズ: {self._format_size(project_data['metadata']['total_size'])}", info_style))
            story.append(Spacer(1, 20))
            
            # ファイル一覧
            if options.get('include_file_list', True):
                story.append(Paragraph("ファイル一覧", styles['Heading2']))
                for file_info in project_data['files']:
                    file_text = f"{file_info['relative_path']} ({file_info.get('language', 'unknown')})"
                    story.append(Paragraph(file_text, styles['Normal']))
                story.append(Spacer(1, 20))
            
            # ファイル内容
            if options.get('include_content', False):
                story.append(Paragraph("ファイル内容", styles['Heading2']))
                for file_info in project_data['files'][:options.get('max_files', 50)]:
                    if self._should_include_file_content(file_info, options):
                        story.append(Paragraph(f"ファイル: {file_info['relative_path']}", styles['Heading3']))
                        
                        try:
                            with open(file_info['path'], 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if len(content) > options.get('max_content_length', 10000):
                                    content = content[:options.get('max_content_length', 10000)] + "\n... (省略)"
                                
                                code_style = ParagraphStyle(
                                    'Code',
                                    parent=styles['Code'],
                                    fontSize=8,
                                    leftIndent=20
                                )
                                story.append(Preformatted(content, code_style))
                                story.append(Spacer(1, 12))
                        except Exception as e:
                            story.append(Paragraph(f"ファイル読み込みエラー: {e}", styles['Normal']))
            
            # PDFを生成
            doc.build(story)
            self.logger.info(f"PDFエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"PDFエクスポートエラー: {e}")
            return False
    
    def export_file(self, file_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """ファイルをPDFでエクスポート"""
        if not self.is_available():
            return False
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
            from reportlab.lib.styles import getSampleStyleSheet
            
            self._ensure_output_directory(output_path)
            
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # ファイル情報
            story.append(Paragraph(f"ファイル: {file_data['name']}", styles['Heading1']))
            story.append(Paragraph(f"パス: {file_data['path']}", styles['Normal']))
            story.append(Paragraph(f"言語: {file_data.get('language', 'unknown')}", styles['Normal']))
            story.append(Paragraph(f"サイズ: {self._format_size(file_data.get('size', 0))}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # ファイル内容
            if 'content' in file_data and file_data['content']:
                story.append(Paragraph("内容", styles['Heading2']))
                story.append(Preformatted(file_data['content'], styles['Code']))
            
            doc.build(story)
            self.logger.info(f"ファイルPDFエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルPDFエクスポートエラー: {e}")
            return False
    
    def export_code(self, code_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """コードをPDFでエクスポート"""
        if not self.is_available():
            return False
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
            from reportlab.lib.styles import getSampleStyleSheet
            
            self._ensure_output_directory(output_path)
            
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # コード情報
            story.append(Paragraph("コードスニペット", styles['Heading1']))
            story.append(Paragraph(f"言語: {code_data['language']}", styles['Normal']))
            story.append(Paragraph(f"エクスポート日時: {code_data['timestamp']}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # コード内容
            story.append(Paragraph("コード", styles['Heading2']))
            story.append(Preformatted(code_data['content'], styles['Code']))
            
            doc.build(story)
            self.logger.info(f"コードPDFエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"コードPDFエクスポートエラー: {e}")
            return False
    
    def _format_size(self, size_bytes: int) -> str:
        """ファイルサイズをフォーマット"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _should_include_file_content(self, file_info: Dict[str, Any], options: Dict[str, Any]) -> bool:
        """ファイル内容を含めるかチェック"""
        # バイナリファイルは除外
        if file_info.get('language') in ['binary', 'image', 'video', 'audio']:
            return False
        
        # サイズ制限
        max_size = options.get('max_file_size', 1024 * 1024)  # 1MB
        if file_info.get('size', 0) > max_size:
            return False
        
        return True


class HTMLExporter(BaseExporter):
    """HTMLエクスポーター"""
    
    def __init__(self):
        super().__init__("html")
    
    def is_available(self) -> bool:
        """HTMLエクスポーターは常に利用可能"""
        return True
    
    def export_project(self, project_data: Dict[str, Any], output_path: str,
                      options: Dict[str, Any]) -> bool:
        """プロジェクトをHTMLでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            html_content = self._generate_project_html(project_data, options)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"HTMLエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"HTMLエクスポートエラー: {e}")
            return False
    
    def export_file(self, file_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """ファイルをHTMLでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            html_content = self._generate_file_html(file_data, options)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"ファイルHTMLエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルHTMLエクスポートエラー: {e}")
            return False
    
    def export_code(self, code_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """コードをHTMLでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            html_content = self._generate_code_html(code_data, options)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"コードHTMLエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"コードHTMLエクスポートエラー: {e}")
            return False
    
    def _generate_project_html(self, project_data: Dict[str, Any], options: Dict[str, Any]) -> str:
        """プロジェクト用HTMLを生成"""
        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>プロジェクト: {project_data['name']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007acc; }}
        h2 {{ color: #555; }}
        .info {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .file-list {{ margin: 20px 0; }}
        .file-item {{ margin: 5px 0; padding: 5px; background: #f9f9f9; }}
        .code {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        pre {{ margin: 0; }}
    </style>
</head>
<body>
    <h1>プロジェクト: {project_data['name']}</h1>
    
    <div class="info">
        <h2>プロジェクト情報</h2>
        <p><strong>エクスポート日時:</strong> {project_data['metadata']['export_time']}</p>
        <p><strong>ファイル数:</strong> {project_data['metadata']['total_files']}</p>
        <p><strong>総サイズ:</strong> {self._format_size(project_data['metadata']['total_size'])}</p>
    </div>
"""
        
        # ファイル一覧
        if options.get('include_file_list', True):
            html += '<h2>ファイル一覧</h2>\n<div class="file-list">\n'
            for file_info in project_data['files']:
                html += f'<div class="file-item">{file_info["relative_path"]} ({file_info.get("language", "unknown")})</div>\n'
            html += '</div>\n'
        
        html += '</body>\n</html>'
        return html
    
    def _generate_file_html(self, file_data: Dict[str, Any], options: Dict[str, Any]) -> str:
        """ファイル用HTMLを生成"""
        content = file_data.get('content', '')
        escaped_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ファイル: {file_data['name']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007acc; }}
        .info {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .code {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        pre {{ margin: 0; font-family: 'Courier New', monospace; }}
    </style>
</head>
<body>
    <h1>ファイル: {file_data['name']}</h1>
    
    <div class="info">
        <p><strong>パス:</strong> {file_data['path']}</p>
        <p><strong>言語:</strong> {file_data.get('language', 'unknown')}</p>
        <p><strong>サイズ:</strong> {self._format_size(file_data.get('size', 0))}</p>
    </div>
    
    <h2>内容</h2>
    <div class="code">
        <pre>{escaped_content}</pre>
    </div>
</body>
</html>"""
    
    def _generate_code_html(self, code_data: Dict[str, Any], options: Dict[str, Any]) -> str:
        """コード用HTMLを生成"""
        escaped_content = code_data['content'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>コードスニペット</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007acc; }}
        .info {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .code {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        pre {{ margin: 0; font-family: 'Courier New', monospace; }}
    </style>
</head>
<body>
    <h1>コードスニペット</h1>
    
    <div class="info">
        <p><strong>言語:</strong> {code_data['language']}</p>
        <p><strong>エクスポート日時:</strong> {code_data['timestamp']}</p>
    </div>
    
    <h2>コード</h2>
    <div class="code">
        <pre>{escaped_content}</pre>
    </div>
</body>
</html>"""
    
    def _format_size(self, size_bytes: int) -> str:
        """ファイルサイズをフォーマット"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


class MarkdownExporter(BaseExporter):
    """Markdownエクスポーター"""
    
    def __init__(self):
        super().__init__("markdown")
    
    def is_available(self) -> bool:
        """Markdownエクスポーターは常に利用可能"""
        return True
    
    def export_project(self, project_data: Dict[str, Any], output_path: str,
                      options: Dict[str, Any]) -> bool:
        """プロジェクトをMarkdownでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            markdown_content = self._generate_project_markdown(project_data, options)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(f"Markdownエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Markdownエクスポートエラー: {e}")
            return False
    
    def export_file(self, file_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """ファイルをMarkdownでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            markdown_content = self._generate_file_markdown(file_data, options)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(f"ファイルMarkdownエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルMarkdownエクスポートエラー: {e}")
            return False
    
    def export_code(self, code_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """コードをMarkdownでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            markdown_content = self._generate_code_markdown(code_data, options)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(f"コードMarkdownエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"コードMarkdownエクスポートエラー: {e}")
            return False
    
    def _generate_project_markdown(self, project_data: Dict[str, Any], options: Dict[str, Any]) -> str:
        """プロジェクト用Markdownを生成"""
        markdown = f"""# プロジェクト: {project_data['name']}

## プロジェクト情報

- **エクスポート日時:** {project_data['metadata']['export_time']}
- **ファイル数:** {project_data['metadata']['total_files']}
- **総サイズ:** {self._format_size(project_data['metadata']['total_size'])}

"""
        
        # ファイル一覧
        if options.get('include_file_list', True):
            markdown += "## ファイル一覧\n\n"
            for file_info in project_data['files']:
                markdown += f"- `{file_info['relative_path']}` ({file_info.get('language', 'unknown')})\n"
            markdown += "\n"
        
        return markdown
    
    def _generate_file_markdown(self, file_data: Dict[str, Any], options: Dict[str, Any]) -> str:
        """ファイル用Markdownを生成"""
        markdown = f"""# ファイル: {file_data['name']}

        ## ファイル情報

        - **パス:** `{file_data['path']}`
        - **言語:** {file_data.get('language', 'unknown')}
        - **サイズ:** {self._format_size(file_data.get('size', 0))}

        ## 内容

        ```{file_data.get('language', 'text')}
        {file_data.get('content', '')}

        """
        return markdown
    
    def _generate_code_markdown(self, code_data: Dict[str, Any], options: Dict[str, Any]) -> str:
        """コード用Markdownを生成"""
        markdown = f"""# コードスニペット
        情報
        言語: {code_data['language']}
        エクスポート日時: {code_data['timestamp']}
        {code_data['content']}
        """
        return markdown
    
    def _format_size(self, size_bytes: int) -> str:
        """ファイルサイズをフォーマット"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

class ZipExporter(BaseExporter):
    """ZIPエクスポーター"""
def __init__(self):
    super().__init__("zip")

def is_available(self) -> bool:
    """ZIPエクスポーターは常に利用可能"""
    return True

def export_project(self, project_data: Dict[str, Any], output_path: str,
                  options: Dict[str, Any]) -> bool:
    """プロジェクトをZIPでエクスポート"""
    try:
        self._ensure_output_directory(output_path)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # プロジェクト情報をJSONで追加
            project_info = {
                'name': project_data['name'],
                'metadata': project_data['metadata'],
                'export_time': datetime.now().isoformat()
            }
            zipf.writestr('project_info.json', json.dumps(project_info, ensure_ascii=False, indent=2))
            
            # ファイルを追加
            for file_info in project_data['files']:
                try:
                    zipf.write(file_info['path'], file_info['relative_path'])
                except Exception as e:
                    self.logger.warning(f"ファイル追加エラー ({file_info['path']}): {e}")
        
        self.logger.info(f"ZIPエクスポート完了: {output_path}")
        return True
        
    except Exception as e:
        self.logger.error(f"ZIPエクスポートエラー: {e}")
        return False

def export_file(self, file_data: Dict[str, Any], output_path: str,
               options: Dict[str, Any]) -> bool:
    """ファイルをZIPでエクスポート"""
    try:
        self._ensure_output_directory(output_path)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # ファイル情報をJSONで追加
            file_info = {
                'name': file_data['name'],
                'metadata': file_data.get('metadata', {}),
                'export_time': datetime.now().isoformat()
            }
            zipf.writestr('file_info.json', json.dumps(file_info, ensure_ascii=False, indent=2))
            
            # ファイルを追加
            zipf.write(file_data['path'], file_data['name'])
        
        self.logger.info(f"ファイルZIPエクスポート完了: {output_path}")
        return True
        
    except Exception as e:
        self.logger.error(f"ファイルZIPエクスポートエラー: {e}")
        return False

def export_code(self, code_data: Dict[str, Any], output_path: str,
               options: Dict[str, Any]) -> bool:
    """コードをZIPでエクスポート"""
    try:
        self._ensure_output_directory(output_path)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # コード情報をJSONで追加
            code_info = {
                'language': code_data['language'],
                'timestamp': code_data['timestamp'],
                'metadata': code_data.get('metadata', {}),
                'export_time': datetime.now().isoformat()
            }
            zipf.writestr('code_info.json', json.dumps(code_info, ensure_ascii=False, indent=2))
            
            # コードファイルを追加
            file_extension = self._get_file_extension(code_data['language'])
            zipf.writestr(f'code{file_extension}', code_data['content'])
        
        self.logger.info(f"コードZIPエクスポート完了: {output_path}")
        return True
        
    except Exception as e:
        self.logger.error(f"コードZIPエクスポートエラー: {e}")
        return False

def _get_file_extension(self, language: str) -> str:
    """言語に対応するファイル拡張子を取得"""
    extension_map = {
        'python': '.py',
        'javascript': '.js',
        'typescript': '.ts',
        'html': '.html',
        'css': '.css',
        'java': '.java',
        'cpp': '.cpp',
        'c': '.c',
        'csharp': '.cs',
        'php': '.php',
        'ruby': '.rb',
        'go': '.go',
        'rust': '.rs',
        'sql': '.sql',
        'json': '.json',
        'xml': '.xml',
        'yaml': '.yaml',
        'markdown': '.md'
    }
    return extension_map.get(language.lower(), '.txt')

class TarExporter(BaseExporter):
    """TARエクスポーター"""
    
    def __init__(self):
        super().__init__("tar")
    
    def is_available(self) -> bool:
        """TARエクスポーターは常に利用可能"""
        return True
    
    def export_project(self, project_data: Dict[str, Any], output_path: str,
                      options: Dict[str, Any]) -> bool:
        """プロジェクトをTARでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            compression = options.get('compression', 'gz')  # gz, bz2, xz
            mode = f'w:{compression}' if compression else 'w'
            
            with tarfile.open(output_path, mode) as tar:
                # プロジェクト情報をJSONで追加
                project_info = {
                    'name': project_data['name'],
                    'metadata': project_data['metadata'],
                    'export_time': datetime.now().isoformat()
                }
                
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(project_info, temp_file, ensure_ascii=False, indent=2)
                    temp_file.flush()
                    tar.add(temp_file.name, arcname='project_info.json')
                
                # ファイルを追加
                for file_info in project_data['files']:
                    try:
                        tar.add(file_info['path'], arcname=file_info['relative_path'])
                    except Exception as e:
                        self.logger.warning(f"ファイル追加エラー ({file_info['path']}): {e}")
            
            self.logger.info(f"TARエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"TARエクスポートエラー: {e}")
            return False
    
    def export_file(self, file_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """ファイルをTARでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            compression = options.get('compression', 'gz')
            mode = f'w:{compression}' if compression else 'w'
            
            with tarfile.open(output_path, mode) as tar:
                # ファイル情報をJSONで追加
                file_info = {
                    'name': file_data['name'],
                    'metadata': file_data.get('metadata', {}),
                    'export_time': datetime.now().isoformat()
                }
                
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(file_info, temp_file, ensure_ascii=False, indent=2)
                    temp_file.flush()
                    tar.add(temp_file.name, arcname='file_info.json')
                
                # ファイルを追加
                tar.add(file_data['path'], arcname=file_data['name'])
            
            self.logger.info(f"ファイルTARエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルTARエクスポートエラー: {e}")
            return False
    
    def export_code(self, code_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """コードをTARでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            compression = options.get('compression', 'gz')
            mode = f'w:{compression}' if compression else 'w'
            
            with tarfile.open(output_path, mode) as tar:
                # コード情報をJSONで追加
                code_info = {
                    'language': code_data['language'],
                    'timestamp': code_data['timestamp'],
                    'metadata': code_data.get('metadata', {}),
                    'export_time': datetime.now().isoformat()
                }
                
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(code_info, temp_file, ensure_ascii=False, indent=2)
                    temp_file.flush()
                    tar.add(temp_file.name, arcname='code_info.json')
                
                # コードファイルを追加
                file_extension = self._get_file_extension(code_data['language'])
                with tempfile.NamedTemporaryFile(mode='w', suffix=file_extension, delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(code_data['content'])
                    temp_file.flush()
                    tar.add(temp_file.name, arcname=f'code{file_extension}')
            
            self.logger.info(f"コードTARエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"コードTARエクスポートエラー: {e}")
            return False
    
    def _get_file_extension(self, language: str) -> str:
        """言語に対応するファイル拡張子を取得"""
        extension_map = {
            'python': '.py',
            'javascript': '.js',
            'typescript': '.ts',
            'html': '.html',
            'css': '.css',
            'java': '.java',
            'cpp': '.cpp',
            'c': '.c',
            'csharp': '.cs',
            'php': '.php',
            'ruby': '.rb',
            'go': '.go',
            'rust': '.rs',
            'sql': '.sql',
            'json': '.json',
            'xml': '.xml',
            'yaml': '.yaml',
            'markdown': '.md'
        }
        return extension_map.get(language.lower(), '.txt')


class JSONExporter(BaseExporter):
    """JSONエクスポーター"""
    
    def __init__(self):
        super().__init__("json")
    
    def is_available(self) -> bool:
        """JSONエクスポーターは常に利用可能"""
        return True
    
    def export_project(self, project_data: Dict[str, Any], output_path: str,
                      options: Dict[str, Any]) -> bool:
        """プロジェクトをJSONでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            # プロジェクトデータを整理
            export_data = {
                'project': {
                    'name': project_data['name'],
                    'path': project_data['path'],
                    'metadata': project_data['metadata']
                },
                'files': [],
                'structure': project_data.get('structure', {}),
                'export_info': {
                    'format': 'json',
                    'timestamp': datetime.now().isoformat(),
                    'options': options
                }
            }
            
            # ファイル情報を追加
            for file_info in project_data['files']:
                file_data = {
                    'path': file_info['relative_path'],
                    'name': file_info['name'],
                    'extension': file_info.get('extension', ''),
                    'language': file_info.get('language', 'text'),
                    'size': file_info.get('size', 0),
                    'modified_time': file_info.get('modified_time', ''),
                    'created_time': file_info.get('created_time', '')
                }
                
                # ファイル内容を含める場合
                if options.get('include_content', False):
                    try:
                        with open(file_info['path'], 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if len(content) <= options.get('max_content_length', 100000):
                                file_data['content'] = content
                            else:
                                file_data['content'] = content[:options.get('max_content_length', 100000)] + "\n... (省略)"
                                file_data['content_truncated'] = True
                    except Exception as e:
                        file_data['content_error'] = str(e)
                
                export_data['files'].append(file_data)
            
            # JSONファイルに書き込み
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"JSONエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"JSONエクスポートエラー: {e}")
            return False
    
    def export_file(self, file_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """ファイルをJSONでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            export_data = {
                'file': {
                    'name': file_data['name'],
                    'path': file_data['path'],
                    'language': file_data.get('language', 'text'),
                    'size': file_data.get('size', 0),
                    'extension': file_data.get('extension', ''),
                    'modified_time': file_data.get('modified_time', ''),
                    'created_time': file_data.get('created_time', ''),
                    'content': file_data.get('content', '')
                },
                'metadata': file_data.get('metadata', {}),
                'export_info': {
                    'format': 'json',
                    'timestamp': datetime.now().isoformat(),
                    'options': options
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"ファイルJSONエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルJSONエクスポートエラー: {e}")
            return False
    
    def export_code(self, code_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """コードをJSONでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            export_data = {
                'code': {
                    'content': code_data['content'],
                    'language': code_data['language'],
                    'timestamp': code_data['timestamp']
                },
                'metadata': code_data.get('metadata', {}),
                'export_info': {
                    'format': 'json',
                    'timestamp': datetime.now().isoformat(),
                    'options': options
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"コードJSONエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"コードJSONエクスポートエラー: {e}")
            return False


class XMLExporter(BaseExporter):
    """XMLエクスポーター"""
    
    def __init__(self):
        super().__init__("xml")
    
    def is_available(self) -> bool:
        """XMLエクスポーターは常に利用可能"""
        return True
    
    def export_project(self, project_data: Dict[str, Any], output_path: str,
                      options: Dict[str, Any]) -> bool:
        """プロジェクトをXMLでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            # ルート要素を作成
            root = ET.Element('project')
            root.set('name', project_data['name'])
            root.set('export_time', datetime.now().isoformat())
            
            # メタデータ
            metadata_elem = ET.SubElement(root, 'metadata')
            for key, value in project_data['metadata'].items():
                meta_elem = ET.SubElement(metadata_elem, key)
                meta_elem.text = str(value)
            
            # ファイル一覧
            files_elem = ET.SubElement(root, 'files')
            for file_info in project_data['files']:
                file_elem = ET.SubElement(files_elem, 'file')
                file_elem.set('path', file_info['relative_path'])
                file_elem.set('name', file_info['name'])
                file_elem.set('language', file_info.get('language', 'text'))
                file_elem.set('size', str(file_info.get('size', 0)))
                
                if options.get('include_content', False):
                    try:
                        with open(file_info['path'], 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if len(content) <= options.get('max_content_length', 50000):
                                content_elem = ET.SubElement(file_elem, 'content')
                                content_elem.text = content
                    except Exception as e:
                        error_elem = ET.SubElement(file_elem, 'error')
                        error_elem.text = str(e)
            
            # XMLファイルに書き込み
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ", level=0)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            self.logger.info(f"XMLエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"XMLエクスポートエラー: {e}")
            return False
    
    def export_file(self, file_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """ファイルをXMLでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            # ルート要素を作成
            root = ET.Element('file')
            root.set('name', file_data['name'])
            root.set('path', file_data['path'])
            root.set('language', file_data.get('language', 'text'))
            root.set('export_time', datetime.now().isoformat())
            
            # ファイル情報
            info_elem = ET.SubElement(root, 'info')
            size_elem = ET.SubElement(info_elem, 'size')
            size_elem.text = str(file_data.get('size', 0))
            
            if 'modified_time' in file_data:
                modified_elem = ET.SubElement(info_elem, 'modified_time')
                modified_elem.text = file_data['modified_time']
            
            # ファイル内容
            if 'content' in file_data and file_data['content']:
                content_elem = ET.SubElement(root, 'content')
                content_elem.text = file_data['content']
            
            # XMLファイルに書き込み
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ", level=0)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            self.logger.info(f"ファイルXMLエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルXMLエクスポートエラー: {e}")
            return False
    
    def export_code(self, code_data: Dict[str, Any], output_path: str,
                   options: Dict[str, Any]) -> bool:
        """コードをXMLでエクスポート"""
        try:
            self._ensure_output_directory(output_path)
            
            # ルート要素を作成
            root = ET.Element('code')
            root.set('language', code_data['language'])
            root.set('timestamp', code_data['timestamp'])
            root.set('export_time', datetime.now().isoformat())
            
            # コード内容
            content_elem = ET.SubElement(root, 'content')
            content_elem.text = code_data['content']
            
            # メタデータ
            if 'metadata' in code_data and code_data['metadata']:
                metadata_elem = ET.SubElement(root, 'metadata')
                for key, value in code_data['metadata'].items():
                    meta_elem = ET.SubElement(metadata_elem, key)
                    meta_elem.text = str(value)
            
            # XMLファイルに書き込み
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ", level=0)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            self.logger.info(f"コードXMLエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"コードXMLエクスポートエラー: {e}")
            return False

