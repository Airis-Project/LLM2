# src/utils/code_parser.py
"""
コード解析・チャンク分割ユーティリティ
プロジェクトのコードファイルを解析し、意味のある単位に分割する
"""

import ast
import re
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json

class CodeParser:
    """
    コードファイルを解析し、検索・LLM処理に適したチャンクに分割するクラス
    """
    
    def __init__(self, max_chunk_size: int = 1000, overlap_size: int = 100):
        """
        初期化
        
        Args:
            max_chunk_size: チャンクの最大サイズ（文字数）
            overlap_size: チャンク間のオーバーラップサイズ
        """
        self.logger = logging.getLogger(__name__)
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        
        # サポートする言語の拡張子
        self.supported_extensions = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.md': 'markdown',
            '.txt': 'text',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql'
        }
        
        self.logger.info(f"CodeParser初期化完了 - チャンクサイズ: {max_chunk_size}")
    
    def parse_and_chunk(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """
        ファイル内容を解析してチャンクに分割
        
        Args:
            content: ファイルの内容
            file_path: ファイルパス
            
        Returns:
            チャンクのリスト
        """
        try:
            file_ext = Path(file_path).suffix.lower()
            language = self.supported_extensions.get(file_ext, 'text')
            
            self.logger.debug(f"ファイル解析開始: {file_path} ({language})")
            
            # 言語別の解析
            if language == 'python':
                chunks = self._parse_python(content, file_path)
            elif language in ['javascript', 'typescript']:
                chunks = self._parse_javascript(content, file_path)
            elif language == 'java':
                chunks = self._parse_java(content, file_path)
            elif language in ['cpp', 'c']:
                chunks = self._parse_cpp(content, file_path)
            elif language == 'markdown':
                chunks = self._parse_markdown(content, file_path)
            elif language == 'json':
                chunks = self._parse_json(content, file_path)
            else:
                chunks = self._parse_generic(content, file_path)
            
            # チャンクサイズの調整
            adjusted_chunks = self._adjust_chunk_sizes(chunks)
            
            self.logger.debug(f"解析完了: {len(adjusted_chunks)}チャンク生成")
            return adjusted_chunks
            
        except Exception as e:
            self.logger.error(f"コード解析エラー {file_path}: {e}")
            # エラー時は全体を1つのチャンクとして返す
            return [{
                'content': content,
                'type': 'file',
                'file_path': file_path,
                'line_start': 1,
                'line_end': len(content.split('\n')),
                'function_name': '',
                'class_name': '',
                'language': self.supported_extensions.get(Path(file_path).suffix.lower(), 'text')
            }]
    
    def _parse_python(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Python ファイルの解析"""
        chunks = []
        lines = content.split('\n')
        
        try:
            # AST を使用した解析
            tree = ast.parse(content)
            
            # インポート文を抽出
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_line = ast.get_source_segment(content, node)
                    if import_line:
                        imports.append({
                            'content': import_line,
                            'type': 'import',
                            'line_start': node.lineno,
                            'line_end': node.end_lineno or node.lineno
                        })
            
            # インポート文をまとめて1つのチャンクに
            if imports:
                import_content = '\n'.join([imp['content'] for imp in imports])
                chunks.append({
                    'content': import_content,
                    'type': 'imports',
                    'file_path': file_path,
                    'line_start': imports[0]['line_start'],
                    'line_end': imports[-1]['line_end'],
                    'function_name': '',
                    'class_name': '',
                    'language': 'python'
                })
            
            # クラスと関数を抽出
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_content = self._extract_node_content(content, node)
                    chunks.append({
                        'content': class_content,
                        'type': 'class',
                        'file_path': file_path,
                        'line_start': node.lineno,
                        'line_end': node.end_lineno or node.lineno,
                        'function_name': '',
                        'class_name': node.name,
                        'language': 'python',
                        'docstring': self._extract_docstring(node)
                    })
                    
                elif isinstance(node, ast.FunctionDef):
                    # トップレベルの関数のみ（クラス内メソッドは除く）
                    if self._is_top_level_function(tree, node):
                        func_content = self._extract_node_content(content, node)
                        chunks.append({
                            'content': func_content,
                            'type': 'function',
                            'file_path': file_path,
                            'line_start': node.lineno,
                            'line_end': node.end_lineno or node.lineno,
                            'function_name': node.name,
                            'class_name': '',
                            'language': 'python',
                            'docstring': self._extract_docstring(node),
                            'parameters': [arg.arg for arg in node.args.args]
                        })
            
        except SyntaxError as e:
            self.logger.warning(f"Python構文エラー {file_path}: {e}")
            # 構文エラーの場合は汎用パーサーを使用
            return self._parse_generic(content, file_path)
        
        # チャンクが生成されなかった場合は全体を1つのチャンクに
        if not chunks:
            chunks.append({
                'content': content,
                'type': 'file',
                'file_path': file_path,
                'line_start': 1,
                'line_end': len(lines),
                'function_name': '',
                'class_name': '',
                'language': 'python'
            })
        
        return chunks
    
    def _parse_javascript(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """JavaScript/TypeScript ファイルの解析"""
        chunks = []
        lines = content.split('\n')
        
        # 正規表現パターン
        patterns = {
            'function': re.compile(r'^(\s*)(function\s+(\w+)|(\w+)\s*:\s*function|(\w+)\s*=\s*function|const\s+(\w+)\s*=\s*\([^)]*\)\s*=>|function\s*\*\s*(\w+))', re.MULTILINE),
            'class': re.compile(r'^(\s*)class\s+(\w+)', re.MULTILINE),
            'method': re.compile(r'^(\s*)(\w+)\s*\([^)]*\)\s*{', re.MULTILINE),
            'arrow_function': re.compile(r'^(\s*)const\s+(\w+)\s*=\s*\([^)]*\)\s*=>', re.MULTILINE),
            'import': re.compile(r'^(\s*)(import\s+.*|const\s+.*=\s*require\()', re.MULTILINE),
            'export': re.compile(r'^(\s*)export\s+', re.MULTILINE)
        }
        
        # インポート文を抽出
        import_lines = []
        for match in patterns['import'].finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            import_lines.append((line_num, match.group().strip()))
        
        if import_lines:
            import_content = '\n'.join([line[1] for line in import_lines])
            chunks.append({
                'content': import_content,
                'type': 'imports',
                'file_path': file_path,
                'line_start': import_lines[0][0],
                'line_end': import_lines[-1][0],
                'function_name': '',
                'class_name': '',
                'language': 'javascript'
            })
        
        # 関数を抽出
        for match in patterns['function'].finditer(content):
            func_name = (match.group(3) or match.group(4) or match.group(5) or 
                        match.group(6) or match.group(7) or 'anonymous')
            line_start = content[:match.start()].count('\n') + 1
            
            # 関数の終了位置を見つける
            line_end = self._find_block_end(lines, line_start - 1)
            
            func_content = '\n'.join(lines[line_start-1:line_end])
            chunks.append({
                'content': func_content,
                'type': 'function',
                'file_path': file_path,
                'line_start': line_start,
                'line_end': line_end,
                'function_name': func_name,
                'class_name': '',
                'language': 'javascript'
            })
        
        # クラスを抽出
        for match in patterns['class'].finditer(content):
            class_name = match.group(2)
            line_start = content[:match.start()].count('\n') + 1
            line_end = self._find_block_end(lines, line_start - 1)
            
            class_content = '\n'.join(lines[line_start-1:line_end])
            chunks.append({
                'content': class_content,
                'type': 'class',
                'file_path': file_path,
                'line_start': line_start,
                'line_end': line_end,
                'function_name': '',
                'class_name': class_name,
                'language': 'javascript'
            })
        
        # チャンクが生成されなかった場合
        if not chunks:
            chunks.append({
                'content': content,
                'type': 'file',
                'file_path': file_path,
                'line_start': 1,
                'line_end': len(lines),
                'function_name': '',
                'class_name': '',
                'language': 'javascript'
            })
        
        return chunks
    
    def _parse_java(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Java ファイルの解析"""
        chunks = []
        lines = content.split('\n')
        
        # パッケージ文とインポート文
        package_imports = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('package ') or stripped.startswith('import '):
                package_imports.append((i + 1, line))
        
        if package_imports:
            import_content = '\n'.join([line[1] for line in package_imports])
            chunks.append({
                'content': import_content,
                'type': 'imports',
                'file_path': file_path,
                'line_start': package_imports[0][0],
                'line_end': package_imports[-1][0],
                'function_name': '',
                'class_name': '',
                'language': 'java'
            })
        
        # クラスとメソッドの抽出
        class_pattern = re.compile(r'^(\s*)(public\s+|private\s+|protected\s+)?(class|interface|enum)\s+(\w+)', re.MULTILINE)
        method_pattern = re.compile(r'^(\s*)(public\s+|private\s+|protected\s+|static\s+)*\w+\s+(\w+)\s*\([^)]*\)\s*{', re.MULTILINE)
        
        for match in class_pattern.finditer(content):
            class_name = match.group(4)
            line_start = content[:match.start()].count('\n') + 1
            line_end = self._find_block_end(lines, line_start - 1)
            
            class_content = '\n'.join(lines[line_start-1:line_end])
            chunks.append({
                'content': class_content,
                'type': 'class',
                'file_path': file_path,
                'line_start': line_start,
                'line_end': line_end,
                'function_name': '',
                'class_name': class_name,
                'language': 'java'
            })
        
        return chunks if chunks else [self._create_fallback_chunk(content, file_path, 'java')]
    
    def _parse_cpp(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """C/C++ ファイルの解析"""
        chunks = []
        lines = content.split('\n')
        
        # インクルード文
        includes = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#include'):
                includes.append((i + 1, line))
        
        if includes:
            include_content = '\n'.join([line[1] for line in includes])
            chunks.append({
                'content': include_content,
                'type': 'includes',
                'file_path': file_path,
                'line_start': includes[0][0],
                'line_end': includes[-1][0],
                'function_name': '',
                'class_name': '',
                'language': 'cpp'
            })
        
        # 関数とクラスの抽出
        function_pattern = re.compile(r'^(\s*)(\w+\s+)*(\w+)\s*\([^)]*\)\s*{', re.MULTILINE)
        class_pattern = re.compile(r'^(\s*)(class|struct)\s+(\w+)', re.MULTILINE)
        
        for match in function_pattern.finditer(content):
            func_name = match.group(3)
            line_start = content[:match.start()].count('\n') + 1
            line_end = self._find_block_end(lines, line_start - 1)
            
            func_content = '\n'.join(lines[line_start-1:line_end])
            chunks.append({
                'content': func_content,
                'type': 'function',
                'file_path': file_path,
                'line_start': line_start,
                'line_end': line_end,
                'function_name': func_name,
                'class_name': '',
                'language': 'cpp'
            })
        
        for match in class_pattern.finditer(content):
            class_name = match.group(3)
            line_start = content[:match.start()].count('\n') + 1
            line_end = self._find_block_end(lines, line_start - 1)
            
            class_content = '\n'.join(lines[line_start-1:line_end])
            chunks.append({
                'content': class_content,
                'type': 'class',
                'file_path': file_path,
                'line_start': line_start,
                'line_end': line_end,
                'function_name': '',
                'class_name': class_name,
                'language': 'cpp'
            })
        
        return chunks if chunks else [self._create_fallback_chunk(content, file_path, 'cpp')]
    
    def _parse_markdown(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Markdown ファイルの解析"""
        chunks = []
        lines = content.split('\n')
        
        current_section = []
        current_header = ""
        current_level = 0
        line_start = 1
        
        for i, line in enumerate(lines):
            # ヘッダーの検出
            if line.strip().startswith('#'):
                # 前のセクションを保存
                if current_section:
                    section_content = '\n'.join(current_section)
                    chunks.append({
                        'content': section_content,
                        'type': 'section',
                        'file_path': file_path,
                        'line_start': line_start,
                        'line_end': i,
                        'function_name': '',
                        'class_name': '',
                        'language': 'markdown',
                        'section_title': current_header,
                        'section_level': current_level
                    })
                
                # 新しいセクションを開始
                current_header = line.strip()
                current_level = len(line) - len(line.lstrip('#'))
                current_section = [line]
                line_start = i + 1
            else:
                current_section.append(line)
        
        # 最後のセクションを保存
        if current_section:
            section_content = '\n'.join(current_section)
            chunks.append({
                'content': section_content,
                'type': 'section',
                'file_path': file_path,
                'line_start': line_start,
                'line_end': len(lines),
                'function_name': '',
                'class_name': '',
                'language': 'markdown',
                'section_title': current_header,
                'section_level': current_level
            })
        
        return chunks if chunks else [self._create_fallback_chunk(content, file_path, 'markdown')]
    
    def _parse_json(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """JSON ファイルの解析"""
        try:
            data = json.loads(content)
            
            # JSONの構造に基づいてチャンクを作成
            if isinstance(data, dict):
                chunks = []
                for key, value in data.items():
                    chunk_content = f'"{key}": {json.dumps(value, indent=2, ensure_ascii=False)}'
                    chunks.append({
                        'content': chunk_content,
                        'type': 'json_property',
                        'file_path': file_path,
                        'line_start': 1,
                        'line_end': len(content.split('\n')),
                        'function_name': '',
                        'class_name': '',
                        'language': 'json',
                        'property_name': key
                    })
                return chunks
            else:
                return [self._create_fallback_chunk(content, file_path, 'json')]
                
        except json.JSONDecodeError:
            self.logger.warning(f"JSON解析エラー: {file_path}")
            return [self._create_fallback_chunk(content, file_path, 'json')]
    
    def _parse_generic(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """汎用ファイルの解析（行ベース分割）"""
        lines = content.split('\n')
        chunks = []
        
        # 行数が少ない場合は全体を1つのチャンクに
        if len(lines) <= 50:
            return [self._create_fallback_chunk(content, file_path, 'text')]
        
        # 行ベースでチャンクを作成
        chunk_size = max(20, self.max_chunk_size // 50)  # 文字数をおおよその行数に変換
        
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunk_content = '\n'.join(chunk_lines)
            
            chunks.append({
                'content': chunk_content,
                'type': 'text_block',
                'file_path': file_path,
                'line_start': i + 1,
                'line_end': min(i + chunk_size, len(lines)),
                'function_name': '',
                'class_name': '',
                'language': 'text'
            })
        
        return chunks
    def _extract_node_content(self, content: str, node: ast.AST) -> str:
        """ASTノードから対応するソースコードを抽出"""
        try:
            return ast.get_source_segment(content, node) or ""
        except Exception:
            # フォールバック: 行番号ベースで抽出
            lines = content.split('\n')
            start_line = node.lineno - 1
            end_line = getattr(node, 'end_lineno', node.lineno) - 1
            return '\n'.join(lines[start_line:end_line + 1])
    
    def _extract_docstring(self, node: ast.AST) -> str:
        """ASTノードからdocstringを抽出"""
        try:
            if (isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and
                node.body and isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, ast.Constant) and
                isinstance(node.body[0].value.value, str)):
                return node.body[0].value.value
        except Exception:
            pass
        return ""
    
    def _is_top_level_function(self, tree: ast.AST, func_node: ast.FunctionDef) -> bool:
        """関数がトップレベルかどうかを判定"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in ast.walk(node):
                    if child is func_node:
                        return False
        return True
    
    def _find_block_end(self, lines: List[str], start_line: int) -> int:
        """ブロック（{}で囲まれた部分）の終了行を見つける"""
        brace_count = 0
        in_string = False
        string_char = None
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            j = 0
            while j < len(line):
                char = line[j]
                
                # 文字列の処理
                if not in_string and char in ['"', "'"]:
                    in_string = True
                    string_char = char
                elif in_string and char == string_char:
                    # エスケープされていない場合のみ文字列終了
                    if j == 0 or line[j-1] != '\\':
                        in_string = False
                        string_char = None
                
                # 文字列内でない場合のブレース処理
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return i + 1
                
                j += 1
        
        # ブレースが見つからない場合は適当な行数を返す
        return min(start_line + 20, len(lines))
    
    def _adjust_chunk_sizes(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """チャンクサイズを調整"""
        adjusted_chunks = []
        
        for chunk in chunks:
            content = chunk['content']
            
            # チャンクが大きすぎる場合は分割
            if len(content) > self.max_chunk_size:
                sub_chunks = self._split_large_chunk(chunk)
                adjusted_chunks.extend(sub_chunks)
            else:
                adjusted_chunks.append(chunk)
        
        return adjusted_chunks
    
    def _split_large_chunk(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """大きなチャンクを分割"""
        content = chunk['content']
        lines = content.split('\n')
        sub_chunks = []
        
        # 行ベースで分割
        lines_per_chunk = max(10, self.max_chunk_size // 80)  # 1行平均80文字と仮定
        
        for i in range(0, len(lines), lines_per_chunk):
            # オーバーラップを考慮
            start_idx = max(0, i - self.overlap_size // 80) if i > 0 else 0
            end_idx = min(len(lines), i + lines_per_chunk)
            
            sub_content = '\n'.join(lines[start_idx:end_idx])
            
            # 元のチャンク情報をコピーして更新
            sub_chunk = chunk.copy()
            sub_chunk.update({
                'content': sub_content,
                'line_start': chunk['line_start'] + start_idx,
                'line_end': chunk['line_start'] + end_idx - 1,
                'is_split': True,
                'split_index': len(sub_chunks)
            })
            
            sub_chunks.append(sub_chunk)
        
        return sub_chunks
    
    def _create_fallback_chunk(self, content: str, file_path: str, language: str) -> Dict[str, Any]:
        """フォールバック用のチャンクを作成"""
        lines = content.split('\n')
        return {
            'content': content,
            'type': 'file',
            'file_path': file_path,
            'line_start': 1,
            'line_end': len(lines),
            'function_name': '',
            'class_name': '',
            'language': language
        }
    
    def get_chunk_summary(self, chunk: Dict[str, Any]) -> str:
        """チャンクの要約を生成"""
        chunk_type = chunk.get('type', 'unknown')
        file_path = chunk.get('file_path', '')
        function_name = chunk.get('function_name', '')
        class_name = chunk.get('class_name', '')
        
        # ファイル名を取得
        filename = Path(file_path).name if file_path else 'unknown'
        
        # 要約文を構築
        if chunk_type == 'function' and function_name:
            summary = f"関数 {function_name}() in {filename}"
        elif chunk_type == 'class' and class_name:
            summary = f"クラス {class_name} in {filename}"
        elif chunk_type == 'imports':
            summary = f"インポート文 in {filename}"
        elif chunk_type == 'section':
            section_title = chunk.get('section_title', '')
            summary = f"セクション {section_title} in {filename}"
        else:
            line_start = chunk.get('line_start', 1)
            line_end = chunk.get('line_end', 1)
            summary = f"{filename} (行 {line_start}-{line_end})"
        
        return summary
    
    def extract_keywords(self, chunk: Dict[str, Any]) -> List[str]:
        """チャンクからキーワードを抽出"""
        keywords = []
        content = chunk.get('content', '')
        
        # 基本情報をキーワードに追加
        if chunk.get('function_name'):
            keywords.append(chunk['function_name'])
        if chunk.get('class_name'):
            keywords.append(chunk['class_name'])
        
        # 言語固有のキーワード抽出
        language = chunk.get('language', 'text')
        
        if language == 'python':
            keywords.extend(self._extract_python_keywords(content))
        elif language in ['javascript', 'typescript']:
            keywords.extend(self._extract_js_keywords(content))
        elif language == 'java':
            keywords.extend(self._extract_java_keywords(content))
        
        # 一般的なプログラミングキーワード
        programming_keywords = [
            'error', 'exception', 'try', 'catch', 'finally', 'throw',
            'async', 'await', 'promise', 'callback',
            'database', 'db', 'sql', 'query',
            'api', 'http', 'request', 'response',
            'config', 'setting', 'parameter',
            'test', 'unittest', 'mock',
            'log', 'logger', 'debug'
        ]
        
        content_lower = content.lower()
        for keyword in programming_keywords:
            if keyword in content_lower:
                keywords.append(keyword)
        
        return list(set(keywords))  # 重複を除去
    
    def _extract_python_keywords(self, content: str) -> List[str]:
        """Pythonコードからキーワードを抽出"""
        keywords = []
        
        # デコレータを抽出
        decorator_pattern = re.compile(r'@(\w+)')
        decorators = decorator_pattern.findall(content)
        keywords.extend(decorators)
        
        # 例外クラスを抽出
        exception_pattern = re.compile(r'except\s+(\w+)')
        exceptions = exception_pattern.findall(content)
        keywords.extend(exceptions)
        
        # インポートモジュールを抽出
        import_pattern = re.compile(r'(?:from\s+(\w+)|import\s+(\w+))')
        imports = import_pattern.findall(content)
        for imp in imports:
            keywords.extend([i for i in imp if i])
        
        return keywords
    
    def _extract_js_keywords(self, content: str) -> List[str]:
        """JavaScript/TypeScriptコードからキーワードを抽出"""
        keywords = []
        
        # require/importを抽出
        require_pattern = re.compile(r'require\([\'"]([^\'"]+)[\'"]')
        import_pattern = re.compile(r'from\s+[\'"]([^\'"]+)[\'"]')
        
        requires = require_pattern.findall(content)
        imports = import_pattern.findall(content)
        
        keywords.extend(requires)
        keywords.extend(imports)
        
        return keywords
    
    def _extract_java_keywords(self, content: str) -> List[str]:
        """Javaコードからキーワードを抽出"""
        keywords = []
        
        # パッケージ名を抽出
        package_pattern = re.compile(r'package\s+([\w.]+)')
        package_match = package_pattern.search(content)
        if package_match:
            keywords.append(package_match.group(1))
        
        # インポートを抽出
        import_pattern = re.compile(r'import\s+([\w.]+)')
        imports = import_pattern.findall(content)
        keywords.extend(imports)
        
        # アノテーションを抽出
        annotation_pattern = re.compile(r'@(\w+)')
        annotations = annotation_pattern.findall(content)
        keywords.extend(annotations)
        
        return keywords
    
    def validate_chunk(self, chunk: Dict[str, Any]) -> bool:
        """チャンクの妥当性を検証"""
        required_fields = ['content', 'type', 'file_path', 'line_start', 'line_end', 'language']
        
        for field in required_fields:
            if field not in chunk:
                self.logger.warning(f"チャンクに必須フィールド '{field}' がありません")
                return False
        
        # 内容が空でないことを確認
        if not chunk['content'].strip():
            self.logger.warning("チャンクの内容が空です")
            return False
        
        # 行番号の妥当性を確認
        if chunk['line_start'] > chunk['line_end']:
            self.logger.warning("行番号が不正です")
            return False
        
        return True
    
    def get_supported_languages(self) -> List[str]:
        """サポートしている言語のリストを取得"""
        return list(set(self.supported_extensions.values()))
    
    def get_file_language(self, file_path: str) -> str:
        """ファイルパスから言語を判定"""
        ext = Path(file_path).suffix.lower()
        return self.supported_extensions.get(ext, 'text')
    
    def create_chunk_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """チャンクのメタデータを作成"""
        content = chunk.get('content', '')
        
        metadata = {
            'file_path': chunk.get('file_path', ''),
            'language': chunk.get('language', 'text'),
            'type': chunk.get('type', 'unknown'),
            'line_start': chunk.get('line_start', 1),
            'line_end': chunk.get('line_end', 1),
            'character_count': len(content),
            'line_count': len(content.split('\n')),
            'keywords': self.extract_keywords(chunk),
            'summary': self.get_chunk_summary(chunk)
        }
        
        # 関数・クラス情報があれば追加
        if chunk.get('function_name'):
            metadata['function_name'] = chunk['function_name']
        if chunk.get('class_name'):
            metadata['class_name'] = chunk['class_name']
        if chunk.get('docstring'):
            metadata['docstring'] = chunk['docstring']
        if chunk.get('parameters'):
            metadata['parameters'] = chunk['parameters']
        
        return metadata
    
    def get_chunk_statistics(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """チャンク統計情報を取得"""
        if not chunks:
            return {}
        
        # 言語別統計
        language_stats = {}
        type_stats = {}
        total_chars = 0
        total_lines = 0
        
        for chunk in chunks:
            language = chunk.get('language', 'unknown')
            chunk_type = chunk.get('type', 'unknown')
            content = chunk.get('content', '')
            
            # 言語別カウント
            language_stats[language] = language_stats.get(language, 0) + 1
            
            # タイプ別カウント
            type_stats[chunk_type] = type_stats.get(chunk_type, 0) + 1
            
            # 文字数・行数
            total_chars += len(content)
            total_lines += len(content.split('\n'))
        
        return {
            'total_chunks': len(chunks),
            'total_characters': total_chars,
            'total_lines': total_lines,
            'average_chunk_size': total_chars // len(chunks) if chunks else 0,
            'language_distribution': language_stats,
            'type_distribution': type_stats,
            'supported_languages': self.get_supported_languages()
        }
    
    def export_chunks_to_json(self, chunks: List[Dict[str, Any]], output_path: str) -> bool:
        """チャンクをJSONファイルにエクスポート"""
        try:
            export_data = {
                'chunks': chunks,
                'statistics': self.get_chunk_statistics(chunks),
                'export_timestamp': self._get_current_timestamp(),
                'parser_config': {
                    'max_chunk_size': self.max_chunk_size,
                    'overlap_size': self.overlap_size,
                    'supported_extensions': self.supported_extensions
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"チャンクをエクスポートしました: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"エクスポートエラー: {e}")
            return False
    
    def import_chunks_from_json(self, input_path: str) -> List[Dict[str, Any]]:
        """JSONファイルからチャンクをインポート"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chunks = data.get('chunks', [])
            
            # チャンクの妥当性を検証
            valid_chunks = []
            for chunk in chunks:
                if self.validate_chunk(chunk):
                    valid_chunks.append(chunk)
                else:
                    self.logger.warning(f"無効なチャンクをスキップしました: {chunk.get('file_path', 'unknown')}")
            
            self.logger.info(f"チャンクをインポートしました: {len(valid_chunks)}/{len(chunks)} 個")
            return valid_chunks
            
        except Exception as e:
            self.logger.error(f"インポートエラー: {e}")
            return []
    
    def merge_similar_chunks(self, chunks: List[Dict[str, Any]], similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """類似したチャンクをマージ"""
        if len(chunks) <= 1:
            return chunks
        
        merged_chunks = []
        used_indices = set()
        
        for i, chunk1 in enumerate(chunks):
            if i in used_indices:
                continue
            
            similar_chunks = [chunk1]
            used_indices.add(i)
            
            for j, chunk2 in enumerate(chunks[i+1:], i+1):
                if j in used_indices:
                    continue
                
                # 類似度を計算（簡単な実装）
                similarity = self._calculate_chunk_similarity(chunk1, chunk2)
                
                if similarity >= similarity_threshold:
                    similar_chunks.append(chunk2)
                    used_indices.add(j)
            
            # 類似チャンクをマージ
            if len(similar_chunks) > 1:
                merged_chunk = self._merge_chunks(similar_chunks)
                merged_chunks.append(merged_chunk)
            else:
                merged_chunks.append(chunk1)
        
        self.logger.info(f"チャンクマージ完了: {len(chunks)} -> {len(merged_chunks)}")
        return merged_chunks
    
    def _calculate_chunk_similarity(self, chunk1: Dict[str, Any], chunk2: Dict[str, Any]) -> float:
        """チャンク間の類似度を計算（簡易版）"""
        # ファイルパスが同じかどうか
        if chunk1.get('file_path') != chunk2.get('file_path'):
            return 0.0
        
        # タイプが同じかどうか
        if chunk1.get('type') != chunk2.get('type'):
            return 0.0
        
        # 行番号が近いかどうか
        line1_end = chunk1.get('line_end', 0)
        line2_start = chunk2.get('line_start', float('inf'))
        
        if abs(line2_start - line1_end) <= 3:  # 3行以内
            return 0.9
        
        return 0.0
    
    def _merge_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """複数のチャンクをマージ"""
        if not chunks:
            return {}
        
        # 最初のチャンクをベースにする
        merged = chunks[0].copy()
        
        # 内容をマージ
        contents = [chunk['content'] for chunk in chunks]
        merged['content'] = '\n'.join(contents)
        
        # 行番号を更新
        merged['line_start'] = min(chunk.get('line_start', float('inf')) for chunk in chunks)
        merged['line_end'] = max(chunk.get('line_end', 0) for chunk in chunks)
        
        # マージ情報を追加
        merged['is_merged'] = True
        merged['merged_count'] = len(chunks)
        
        return merged
    
    def _get_current_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def cleanup_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """チャンクのクリーンアップ"""
        cleaned_chunks = []
        
        for chunk in chunks:
            # 空のチャンクを除外
            if not chunk.get('content', '').strip():
                continue
            
            # 重複するメタデータを除去
            cleaned_chunk = {}
            for key, value in chunk.items():
                if value is not None and value != '':
                    cleaned_chunk[key] = value
            
            # 必須フィールドの確認
            if self.validate_chunk(cleaned_chunk):
                cleaned_chunks.append(cleaned_chunk)
        
        return cleaned_chunks
    
    def get_chunk_by_line(self, chunks: List[Dict[str, Any]], file_path: str, line_number: int) -> Optional[Dict[str, Any]]:
        """指定された行番号を含むチャンクを取得"""
        for chunk in chunks:
            if (chunk.get('file_path') == file_path and
                chunk.get('line_start', 0) <= line_number <= chunk.get('line_end', 0)):
                return chunk
        return None
    
    def search_chunks_by_keyword(self, chunks: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
        """キーワードでチャンクを検索"""
        matching_chunks = []
        keyword_lower = keyword.lower()
        
        for chunk in chunks:
            # 内容から検索
            if keyword_lower in chunk.get('content', '').lower():
                matching_chunks.append(chunk)
                continue
            
            # メタデータから検索
            if (keyword_lower in chunk.get('function_name', '').lower() or
                keyword_lower in chunk.get('class_name', '').lower() or
                keyword_lower in str(chunk.get('keywords', [])).lower()):
                matching_chunks.append(chunk)
        
        return matching_chunks
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"CodeParser(max_chunk_size={self.max_chunk_size}, supported_languages={len(self.get_supported_languages())})"
    
    def __repr__(self) -> str:
        """デバッグ用文字列表現"""
        return self.__str__()


# 使用例とテスト用の関数
def example_usage():
    """CodeParserの使用例"""
    parser = CodeParser(max_chunk_size=800, overlap_size=50)
    
    # サンプルPythonコード
    sample_code = '''
import os
import sys
from typing import List, Dict

class DataProcessor:
    """データ処理クラス"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def process_data(self, data: List[str]) -> List[str]:
        """データを処理する"""
        processed = []
        for item in data:
            if self.validate_item(item):
                processed.append(self.transform_item(item))
        return processed
    
    def validate_item(self, item: str) -> bool:
        """アイテムの妥当性を検証"""
        return len(item) > 0 and item.strip()

def main():
    """メイン関数"""
    processor = DataProcessor({'debug': True})
    data = ['item1', 'item2', '']
    result = processor.process_data(data)
    print(f"処理結果: {result}")

if __name__ == "__main__":
    main()
'''
    
    # コードを解析
    chunks = parser.parse_and_chunk(sample_code, 'example.py')
    
    # 結果を表示
    print(f"生成されたチャンク数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"\nチャンク {i+1}:")
        print(f"  タイプ: {chunk['type']}")
        print(f"  行範囲: {chunk['line_start']}-{chunk['line_end']}")
        if chunk.get('function_name'):
            print(f"  関数名: {chunk['function_name']}")
        if chunk.get('class_name'):
            print(f"  クラス名: {chunk['class_name']}")
        print(f"  内容プレビュー: {chunk['content'][:100]}...")
    
    # 統計情報
    stats = parser.get_chunk_statistics(chunks)
    print(f"\n統計情報: {stats}")


if __name__ == "__main__":
    example_usage()
