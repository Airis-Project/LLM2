# src/core/context_builder.py
"""
コンテキスト構築システム - 検索結果と会話履歴を統合した文脈生成
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib
from pathlib import Path

from .vector_store import SearchResult
from .conversation_manager import Message, MessageRole

class ContextType(Enum):
    """コンテキストの種類"""
    CODE_SNIPPET = "code_snippet"
    FUNCTION_DEFINITION = "function_definition"
    CLASS_DEFINITION = "class_definition"
    DOCUMENTATION = "documentation"
    CONVERSATION_HISTORY = "conversation_history"
    FILE_STRUCTURE = "file_structure"
    RELATED_FILES = "related_files"
    ERROR_CONTEXT = "error_context"

class RelevanceLevel(Enum):
    """関連度レベル"""
    CRITICAL = "critical"      # 必須の情報
    HIGH = "high"             # 高い関連性
    MEDIUM = "medium"         # 中程度の関連性
    LOW = "low"               # 低い関連性
    REFERENCE = "reference"   # 参考情報

@dataclass
class ContextItem:
    """コンテキストアイテム"""
    id: str
    type: ContextType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevance: RelevanceLevel = RelevanceLevel.MEDIUM
    source: str = ""
    tokens: int = 0
    priority: int = 0
    
    def __post_init__(self):
        if not self.tokens:
            self.tokens = self._estimate_tokens()
    
    def _estimate_tokens(self) -> int:
        """トークン数を推定"""
        return int(len(self.content.split()) * 1.3)

@dataclass
class ContextBundle:
    """構築されたコンテキストバンドル"""
    items: List[ContextItem] = field(default_factory=list)
    total_tokens: int = 0
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_item(self, item: ContextItem):
        """アイテムを追加"""
        self.items.append(item)
        self.total_tokens += item.tokens
    
    def get_by_type(self, context_type: ContextType) -> List[ContextItem]:
        """タイプ別にアイテムを取得"""
        return [item for item in self.items if item.type == context_type]
    
    def get_by_relevance(self, relevance: RelevanceLevel) -> List[ContextItem]:
        """関連度別にアイテムを取得"""
        return [item for item in self.items if item.relevance == relevance]

class ContextBuilder:
    """
    コンテキスト構築クラス
    検索結果、会話履歴、コード情報を統合して最適な文脈を生成
    """
    
    def __init__(self,
                 max_context_tokens: int = 8000,
                 max_code_snippets: int = 10,
                 max_conversation_messages: int = 15,
                 include_file_structure: bool = True,
                 include_related_files: bool = True):
        """
        初期化
        
        Args:
            max_context_tokens: 最大コンテキストトークン数
            max_code_snippets: 最大コードスニペット数
            max_conversation_messages: 最大会話メッセージ数
            include_file_structure: ファイル構造を含めるか
            include_related_files: 関連ファイルを含めるか
        """
        self.logger = logging.getLogger(__name__)
        self.max_context_tokens = max_context_tokens
        self.max_code_snippets = max_code_snippets
        self.max_conversation_messages = max_conversation_messages
        self.include_file_structure = include_file_structure
        self.include_related_files = include_related_files
        
        # 優先度設定
        self.type_priorities = {
            ContextType.ERROR_CONTEXT: 100,
            ContextType.FUNCTION_DEFINITION: 90,
            ContextType.CLASS_DEFINITION: 85,
            ContextType.CODE_SNIPPET: 80,
            ContextType.DOCUMENTATION: 70,
            ContextType.CONVERSATION_HISTORY: 60,
            ContextType.FILE_STRUCTURE: 50,
            ContextType.RELATED_FILES: 40
        }
        
        self.relevance_priorities = {
            RelevanceLevel.CRITICAL: 100,
            RelevanceLevel.HIGH: 80,
            RelevanceLevel.MEDIUM: 60,
            RelevanceLevel.LOW: 40,
            RelevanceLevel.REFERENCE: 20
        }
        
        self.logger.info("ContextBuilder初期化完了")
    
    def build_context(self,
                     query: str,
                     search_results: List[SearchResult] = None,
                     conversation_history: List[Message] = None,
                     current_file_path: str = None,
                     error_context: str = None,
                     additional_context: Dict[str, Any] = None) -> ContextBundle:
        """
        コンテキストを構築
        
        Args:
            query: ユーザーのクエリ
            search_results: 検索結果
            conversation_history: 会話履歴
            current_file_path: 現在のファイルパス
            error_context: エラー文脈
            additional_context: 追加の文脈情報
            
        Returns:
            構築されたコンテキストバンドル
        """
        try:
            bundle = ContextBundle()
            
            # 1. エラーコンテキストの追加（最優先）
            if error_context:
                self._add_error_context(bundle, error_context, query)
            
            # 2. 検索結果からコードコンテキストを追加
            if search_results:
                self._add_search_results_context(bundle, search_results, query)
            
            # 3. 会話履歴の追加
            if conversation_history:
                self._add_conversation_context(bundle, conversation_history, query)
            
            # 4. ファイル構造の追加
            if self.include_file_structure and current_file_path:
                self._add_file_structure_context(bundle, current_file_path)
            
            # 5. 関連ファイルの追加
            if self.include_related_files and search_results:
                self._add_related_files_context(bundle, search_results)
            
            # 6. 追加コンテキストの処理
            if additional_context:
                self._add_additional_context(bundle, additional_context)
            
            # 7. コンテキストの最適化
            self._optimize_context(bundle, query)
            
            # 8. サマリーの生成
            bundle.summary = self._generate_context_summary(bundle, query)
            
            # 9. メタデータの設定
            bundle.metadata = {
                'query': query,
                'current_file': current_file_path,
                'has_error_context': bool(error_context),
                'search_results_count': len(search_results) if search_results else 0,
                'conversation_messages_count': len(conversation_history) if conversation_history else 0,
                'generated_at': datetime.now().isoformat(),
                'context_types': list(set(item.type.value for item in bundle.items)),
                'relevance_distribution': self._get_relevance_distribution(bundle)
            }
            
            self.logger.info(f"コンテキスト構築完了: {len(bundle.items)} アイテム, {bundle.total_tokens} トークン")
            return bundle
            
        except Exception as e:
            self.logger.error(f"コンテキスト構築エラー: {e}")
            return ContextBundle()
    
    def _add_error_context(self, bundle: ContextBundle, error_context: str, query: str):
        """エラーコンテキストを追加"""
        try:
            # エラーメッセージの解析
            error_info = self._parse_error_context(error_context)
            
            # エラーコンテキストアイテムを作成
            item = ContextItem(
                id=f"error_{hashlib.md5(error_context.encode()).hexdigest()[:8]}",
                type=ContextType.ERROR_CONTEXT,
                content=error_context,
                metadata=error_info,
                relevance=RelevanceLevel.CRITICAL,
                source="error_context",
                priority=self.type_priorities[ContextType.ERROR_CONTEXT] + 
                        self.relevance_priorities[RelevanceLevel.CRITICAL]
            )
            
            bundle.add_item(item)
            
        except Exception as e:
            self.logger.error(f"エラーコンテキスト追加エラー: {e}")
    
    def _parse_error_context(self, error_context: str) -> Dict[str, Any]:
        """エラーコンテキストを解析"""
        error_info = {
            'error_type': 'unknown',
            'file_path': None,
            'line_number': None,
            'function_name': None,
            'error_message': error_context
        }
        
        # Pythonのトレースバック解析
        traceback_pattern = r'File "([^"]+)", line (\d+)(?:, in (\w+))?'
        matches = re.findall(traceback_pattern, error_context)
        
        if matches:
            last_match = matches[-1]
            error_info['file_path'] = last_match[0]
            error_info['line_number'] = int(last_match[1])
            if last_match[2]:
                error_info['function_name'] = last_match[2]
        
        # エラータイプの抽出
        error_type_pattern = r'(\w+Error): (.+)'
        error_match = re.search(error_type_pattern, error_context)
        if error_match:
            error_info['error_type'] = error_match.group(1)
            error_info['error_message'] = error_match.group(2)
        
        return error_info
    
    def _add_search_results_context(self, bundle: ContextBundle, search_results: List[SearchResult], query: str):
        """検索結果からコンテキストを追加"""
        try:
            added_count = 0
            seen_content = set()
            
            # 類似度順にソート
            sorted_results = sorted(search_results, key=lambda x: x.similarity_score, reverse=True)
            
            for result in sorted_results:
                if added_count >= self.max_code_snippets:
                    break
                
                # 重複チェック
                content_hash = hashlib.md5(result.content.encode()).hexdigest()
                if content_hash in seen_content:
                    continue
                seen_content.add(content_hash)
                
                # コンテキストタイプの決定
                context_type = self._determine_context_type(result)
                
                # 関連度の決定
                relevance = self._determine_relevance(result, query)
                
                # コンテキストアイテムを作成
                item = ContextItem(
                    id=result.chunk_id,
                    type=context_type,
                    content=self._format_code_content(result),
                    metadata={
                        'file_path': result.file_path,
                        'line_start': result.line_start,
                        'line_end': result.line_end,
                        'similarity_score': result.similarity_score,
                        'function_name': result.metadata.get('function_name'),
                        'class_name': result.metadata.get('class_name'),
                        'docstring': result.metadata.get('docstring'),
                        'keywords': result.metadata.get('keywords', [])
                    },
                    relevance=relevance,
                    source=f"search_result:{result.file_path}",
                    priority=self.type_priorities[context_type] + 
                            self.relevance_priorities[relevance] +
                            int(result.similarity_score * 10)
                )
                
                bundle.add_item(item)
                added_count += 1
                
        except Exception as e:
            self.logger.error(f"検索結果コンテキスト追加エラー: {e}")
    
    def _determine_context_type(self, result: SearchResult) -> ContextType:
        """検索結果からコンテキストタイプを決定"""
        content = result.content.lower()
        metadata = result.metadata
        
        # 関数定義
        if (metadata.get('function_name') or 
            re.search(r'\bdef\s+\w+\s*\(', content) or
            re.search(r'\bfunction\s+\w+\s*\(', content)):
            return ContextType.FUNCTION_DEFINITION
        
        # クラス定義
        if (metadata.get('class_name') or 
            re.search(r'\bclass\s+\w+', content)):
            return ContextType.CLASS_DEFINITION
        
        # ドキュメント
        if (metadata.get('docstring') or 
            len(re.findall(r'""".*?"""', content, re.DOTALL)) > 0 or
            content.count('#') > 3):
            return ContextType.DOCUMENTATION
        
        # デフォルトはコードスニペット
        return ContextType.CODE_SNIPPET
    
    def _determine_relevance(self, result: SearchResult, query: str) -> RelevanceLevel:
        """検索結果の関連度を決定"""
        score = result.similarity_score
        
        # クエリとの直接的な関連性をチェック
        query_lower = query.lower()
        content_lower = result.content.lower()
        
        # 関数名やクラス名がクエリに含まれている場合
        function_name = result.metadata.get('function_name', '')
        class_name = result.metadata.get('class_name', '')
        
        if (function_name and function_name.lower() in query_lower) or \
           (class_name and class_name.lower() in query_lower):
            return RelevanceLevel.CRITICAL
        
        # 高い類似度スコア
        if score > 0.8:
            return RelevanceLevel.HIGH
        elif score > 0.6:
            return RelevanceLevel.MEDIUM
        elif score > 0.4:
            return RelevanceLevel.LOW
        else:
            return RelevanceLevel.REFERENCE
    
    def _format_code_content(self, result: SearchResult) -> str:
        """コード内容をフォーマット"""
        content_parts = []
        
        # ファイル情報
        content_parts.append(f"# File: {result.file_path} (lines {result.line_start}-{result.line_end})")
        
        # 関数/クラス情報
        if result.metadata.get('function_name'):
            content_parts.append(f"# Function: {result.metadata['function_name']}")
        if result.metadata.get('class_name'):
            content_parts.append(f"# Class: {result.metadata['class_name']}")
        
        # ドキュメント
        if result.metadata.get('docstring'):
            content_parts.append(f"# Description: {result.metadata['docstring']}")
        
        # コード本体
        content_parts.append("")
        content_parts.append(result.content)
        
        return "\n".join(content_parts)
    
    def _add_conversation_context(self, bundle: ContextBundle, conversation_history: List[Message], query: str):
        """会話履歴からコンテキストを追加"""
        try:
            # 最新のメッセージから選択
            recent_messages = conversation_history[-self.max_conversation_messages:]
            
            # 関連性の高いメッセージを選択
            relevant_messages = self._select_relevant_messages(recent_messages, query)
            
            if relevant_messages:
                # 会話履歴を一つのアイテムとして追加
                conversation_content = self._format_conversation_history(relevant_messages)
                
                item = ContextItem(
                    id=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    type=ContextType.CONVERSATION_HISTORY,
                    content=conversation_content,
                    metadata={
                        'message_count': len(relevant_messages),
                        'time_span': self._get_conversation_time_span(relevant_messages),
                        'topics': self._extract_conversation_topics(relevant_messages)
                    },
                    relevance=RelevanceLevel.MEDIUM,
                    source="conversation_history",
                    priority=self.type_priorities[ContextType.CONVERSATION_HISTORY] + 
                            self.relevance_priorities[RelevanceLevel.MEDIUM]
                )
                
                bundle.add_item(item)
                
        except Exception as e:
            self.logger.error(f"会話コンテキスト追加エラー: {e}")
    
    def _select_relevant_messages(self, messages: List[Message], query: str) -> List[Message]:
        """関連性の高いメッセージを選択"""
        relevant_messages = []
        query_lower = query.lower()
        
        for message in messages:
            # システムメッセージはスキップ
            if message.role == MessageRole.SYSTEM:
                continue
            
            # 関連性スコアを計算
            relevance_score = self._calculate_message_relevance(message, query_lower)
            
            if relevance_score > 0.1:  # 閾値
                relevant_messages.append(message)
        
        return relevant_messages
    
    def _calculate_message_relevance(self, message: Message, query_lower: str) -> float:
        """メッセージの関連性スコアを計算"""
        content_lower = message.content.lower()
        
        # 単純なキーワードマッチング
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        if not query_words:
            return 0.0
        
        # 共通単語の割合
        common_words = query_words.intersection(content_words)
        relevance_score = len(common_words) / len(query_words)
        
        # コードが含まれている場合はボーナス
        if '```' in message.content or 'def ' in content_lower or 'class ' in content_lower:
            relevance_score += 0.2
        
        # 使用されたコンテキストがある場合はボーナス
        if message.context_used:
            relevance_score += 0.1
        
        return min(relevance_score, 1.0)
    
    def _format_conversation_history(self, messages: List[Message]) -> str:
        """会話履歴をフォーマット"""
        formatted_parts = ["# Recent Conversation History"]
        
        for message in messages:
            role_name = message.role.value.upper()
            timestamp = message.timestamp.strftime("%H:%M")
            
            # メッセージ内容を適切に切り詰め
            content = message.content
            if len(content) > 500:
                content = content[:500] + "..."
            
            formatted_parts.append(f"\n## {role_name} ({timestamp})")
            formatted_parts.append(content)
            
            # 使用されたコンテキストファイルを表示
            if message.context_used:
                formatted_parts.append(f"*Referenced files: {', '.join(message.context_used)}*")
        
        return "\n".join(formatted_parts)
    
    def _get_conversation_time_span(self, messages: List[Message]) -> str:
        """会話の時間範囲を取得"""
        if not messages:
            return "Unknown"
        
        start_time = min(msg.timestamp for msg in messages)
        end_time = max(msg.timestamp for msg in messages)
        
        if start_time.date() == end_time.date():
            return f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        else:
            return f"{start_time.strftime('%m/%d %H:%M')} - {end_time.strftime('%m/%d %H:%M')}"
    
    def _extract_conversation_topics(self, messages: List[Message]) -> List[str]:
        """会話のトピックを抽出"""
        topics = set()
        
        for message in messages:
            # メタデータからトピックを抽出
            if 'topics' in message.metadata:
                topics.update(message.metadata['topics'])
            
            # コンテキストファイルからトピックを推測
            for context_file in message.context_used:
                file_path = Path(context_file)
                topics.add(file_path.stem)
        
        return list(topics)[:5]  # 最大5つのトピック
    
    def _add_file_structure_context(self, bundle: ContextBundle, current_file_path: str):
        """ファイル構造コンテキストを追加"""
        try:
            file_path = Path(current_file_path)
            
            if not file_path.exists():
                return
            
            # プロジェクトルートを推定
            project_root = self._find_project_root(file_path)
            
            # ファイル構造を生成
            structure = self._generate_file_structure(project_root, current_file_path)
            
            if structure:
                item = ContextItem(
                    id=f"file_structure_{hashlib.md5(str(project_root).encode()).hexdigest()[:8]}",
                    type=ContextType.FILE_STRUCTURE,
                    content=structure,
                    metadata={
                        'project_root': str(project_root),
                        'current_file': current_file_path,
                        'file_count': structure.count('\n')
                    },
                    relevance=RelevanceLevel.LOW,
                    source="file_system",
                    priority=self.type_priorities[ContextType.FILE_STRUCTURE] + 
                            self.relevance_priorities[RelevanceLevel.LOW]
                )
                
                bundle.add_item(item)
                
        except Exception as e:
            self.logger.error(f"ファイル構造コンテキスト追加エラー: {e}")
    
    def _find_project_root(self, file_path: Path) -> Path:
        """プロジェクトルートを見つける"""
        current = file_path.parent
        
        # 一般的なプロジェクトルートの指標
        root_indicators = [
            '.git', '.gitignore', 'setup.py', 'requirements.txt', 
            'package.json', 'Cargo.toml', 'pom.xml', 'build.gradle'
        ]
        
        while current != current.parent:
            for indicator in root_indicators:
                if (current / indicator).exists():
                    return current
            current = current.parent
        
        return file_path.parent
    
    def _generate_file_structure(self, project_root: Path, current_file: str, max_depth: int = 3) -> str:
        """ファイル構造を生成"""
        try:
            structure_lines = [f"# Project Structure (from {project_root.name})"]
            
            def add_directory(path: Path, depth: int = 0, prefix: str = ""):
                if depth > max_depth:
                    return
                
                items = []
                try:
                    for item in sorted(path.iterdir()):
                        # 隠しファイルやディレクトリをスキップ
                        if item.name.startswith('.') and item.name not in ['.gitignore']:
                            continue
                        
                        # 不要なディレクトリをスキップ
                        if item.is_dir() and item.name in ['__pycache__', 'node_modules', '.git', 'venv', 'env']:
                            continue
                        
                        items.append(item)
                except PermissionError:
                    return
                
                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    
                    # 現在のファイルをハイライト
                    name = item.name
                    if str(item) == current_file:
                        name = f"**{name}** (current)"
                    
                    structure_lines.append(f"{prefix}{current_prefix}{name}")
                    
                    if item.is_dir() and depth < max_depth:
                        add_directory(item, depth + 1, next_prefix)
            
            add_directory(project_root)
            return "\n".join(structure_lines)
            
        except Exception as e:
            self.logger.error(f"ファイル構造生成エラー: {e}")
            return ""
    
    def _add_related_files_context(self, bundle: ContextBundle, search_results: List[SearchResult]):
        """関連ファイルコンテキストを追加"""
        try:
            # 検索結果から関連ファイルを抽出
            file_paths = set()
            for result in search_results[:5]:  # 上位5件から
                file_paths.add(result.file_path)
            
            if file_paths:
                related_files_content = self._format_related_files(file_paths)
                
                item = ContextItem(
                    id=f"related_files_{hashlib.md5(str(sorted(file_paths)).encode()).hexdigest()[:8]}",
                    type=ContextType.RELATED_FILES,
                    content=related_files_content,
                    metadata={
                        'file_paths': list(file_paths),
                        'file_count': len(file_paths)
                    },
                    relevance=RelevanceLevel.REFERENCE,
                    source="search_results",
                    priority=self.type_priorities[ContextType.RELATED_FILES] + 
                            self.relevance_priorities[RelevanceLevel.REFERENCE]
                )
                
                bundle.add_item(item)
                
        except Exception as e:
            self.logger.error(f"関連ファイルコンテキスト追加エラー: {e}")
    
    def _format_related_files(self, file_paths: Set[str]) -> str:
        """関連ファイルをフォーマット"""
        content_parts = ["# Related Files"]
        
        for file_path in sorted(file_paths):
            path_obj = Path(file_path)
            content_parts.append(f"- {path_obj.name} ({file_path})")
        
        return "\n".join(content_parts)
    
    def _add_additional_context(self, bundle: ContextBundle, additional_context: Dict[str, Any]):
        """追加コンテキストを処理"""
        try:
            for key, value in additional_context.items():
                if isinstance(value, str) and value.strip():
                    item = ContextItem(
                        id=f"additional_{key}_{hashlib.md5(value.encode()).hexdigest()[:8]}",
                        type=ContextType.DOCUMENTATION,  # デフォルトタイプ
                        content=f"# {key.replace('_', ' ').title()}\n\n{value}",
                        metadata={'source_key': key},
                        relevance=RelevanceLevel.MEDIUM,
                        source=f"additional_context:{key}",
                        priority=self.type_priorities[ContextType.DOCUMENTATION] + 
                                self.relevance_priorities[RelevanceLevel.MEDIUM]
                    )
                    
                    bundle.add_item(item)
                    
        except Exception as e:
            self.logger.error(f"追加コンテキスト処理エラー: {e}")
    
    def _optimize_context(self, bundle: ContextBundle, query: str):
        """コンテキストを最適化"""
        try:
            # 優先度順にソート
            bundle.items.sort(key=lambda x: x.priority, reverse=True)
            
            # トークン制限内に収める
            optimized_items = []
            total_tokens = 0
            
            for item in bundle.items:
                if total_tokens + item.tokens <= self.max_context_tokens:
                    optimized_items.append(item)
                    total_tokens += item.tokens
                else:
                    # 重要なアイテムは切り詰めて含める
                    if item.relevance in [RelevanceLevel.CRITICAL, RelevanceLevel.HIGH]:
                        remaining_tokens = self.max_context_tokens - total_tokens
                        if remaining_tokens > 100:  # 最小限のトークン数
                            truncated_item = self._truncate_context_item(item, remaining_tokens)
                            optimized_items.append(truncated_item)
                            total_tokens += truncated_item.tokens
                    break
            
            bundle.items = optimized_items
            bundle.total_tokens = total_tokens
            
        except Exception as e:
            self.logger.error(f"コンテキスト最適化エラー: {e}")
    
    def _truncate_context_item(self, item: ContextItem, max_tokens: int) -> ContextItem:
        """コンテキストアイテムを切り詰める"""
        try:
            # 推定文字数を計算（トークン数 / 1.3）
            max_chars = int(max_tokens / 1.3 * 4)  # 余裕を持たせる
            
            if len(item.content) <= max_chars:
                return item
            
            # 重要な部分を保持して切り詰める
            truncated_content = item.content[:max_chars]
            
            # 行の途中で切れないように調整
            last_newline = truncated_content.rfind('\n')
            if last_newline > max_chars * 0.8:  # 80%以上の位置にある場合
                truncated_content = truncated_content[:last_newline]
            
            truncated_content += "\n\n... (truncated)"
            
            # 新しいアイテムを作成
            truncated_item = ContextItem(
                id=item.id + "_truncated",
                type=item.type,
                content=truncated_content,
                metadata={**item.metadata, 'truncated': True},
                relevance=item.relevance,
                source=item.source,
                priority=item.priority
            )
            
            return truncated_item
            
        except Exception as e:
            self.logger.error(f"コンテキストアイテム切り詰めエラー: {e}")
            return item
    
    def _generate_context_summary(self, bundle: ContextBundle, query: str) -> str:
        """コンテキストサマリーを生成"""
        try:
            summary_parts = []
            
            # 基本情報
            summary_parts.append(f"Context for query: '{query}'")
            summary_parts.append(f"Total items: {len(bundle.items)}, Total tokens: {bundle.total_tokens}")
            
            # タイプ別統計
            type_counts = {}
            for item in bundle.items:
                type_name = item.type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            if type_counts:
                type_summary = ", ".join([f"{k}: {v}" for k, v in type_counts.items()])
                summary_parts.append(f"Content types: {type_summary}")
            
            # 関連度別統計
            relevance_counts = {}
            for item in bundle.items:
                rel_name = item.relevance.value
                relevance_counts[rel_name] = relevance_counts.get(rel_name, 0) + 1
            
            if relevance_counts:
                relevance_summary = ", ".join([f"{k}: {v}" for k, v in relevance_counts.items()])
                summary_parts.append(f"Relevance levels: {relevance_summary}")
            
            # 主要なファイル
            file_paths = set()
            for item in bundle.items:
                if 'file_path' in item.metadata:
                    file_paths.add(Path(item.metadata['file_path']).name)
            
            if file_paths:
                files_summary = ", ".join(sorted(file_paths)[:5])
                if len(file_paths) > 5:
                    files_summary += f" and {len(file_paths) - 5} more"
                summary_parts.append(f"Main files: {files_summary}")
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            self.logger.error(f"コンテキストサマリー生成エラー: {e}")
            return f"Context for query: '{query}' ({len(bundle.items)} items)"
    
    def _get_relevance_distribution(self, bundle: ContextBundle) -> Dict[str, int]:
        """関連度の分布を取得"""
        distribution = {}
        for item in bundle.items:
            rel_name = item.relevance.value
            distribution[rel_name] = distribution.get(rel_name, 0) + 1
        return distribution
    
    def format_context_for_llm(self, bundle: ContextBundle, include_metadata: bool = False) -> str:
        """LLM用にコンテキストをフォーマット"""
        try:
            formatted_parts = []
            
            # ヘッダー
            formatted_parts.append("=== CONTEXT INFORMATION ===")
            formatted_parts.append(f"Query Context: {bundle.summary}")
            formatted_parts.append("")
            
            # 重要度順にアイテムを整理
            critical_items = bundle.get_by_relevance(RelevanceLevel.CRITICAL)
            high_items = bundle.get_by_relevance(RelevanceLevel.HIGH)
            medium_items = bundle.get_by_relevance(RelevanceLevel.MEDIUM)
            low_items = bundle.get_by_relevance(RelevanceLevel.LOW)
            reference_items = bundle.get_by_relevance(RelevanceLevel.REFERENCE)
            
            # セクション別に出力
            sections = [
                ("CRITICAL CONTEXT", critical_items),
                ("HIGH RELEVANCE", high_items),
                ("MEDIUM RELEVANCE", medium_items),
                ("LOW RELEVANCE", low_items),
                ("REFERENCE", reference_items)
            ]
            
            for section_name, items in sections:
                if items:
                    formatted_parts.append(f"--- {section_name} ---")
                    
                    for item in items:
                        formatted_parts.append(f"\n[{item.type.value.upper()}] {item.source}")
                        
                        if include_metadata and item.metadata:
                            meta_info = []
                            for key, value in item.metadata.items():
                                if key in ['file_path', 'function_name', 'class_name', 'line_start', 'line_end']:
                                    meta_info.append(f"{key}: {value}")
                            if meta_info:
                                formatted_parts.append(f"Metadata: {', '.join(meta_info)}")
                        
                        formatted_parts.append(item.content)
                        formatted_parts.append("")
            
            formatted_parts.append("=== END CONTEXT ===")
            
            return "\n".join(formatted_parts)
            
        except Exception as e:
            self.logger.error(f"LLM用フォーマットエラー: {e}")
            return f"Error formatting context: {e}"
    
    def analyze_context_quality(self, bundle: ContextBundle, query: str) -> Dict[str, Any]:
        """コンテキストの品質を分析"""
        try:
            analysis = {
                'overall_score': 0.0,
                'token_efficiency': 0.0,
                'relevance_score': 0.0,
                'diversity_score': 0.0,
                'completeness_score': 0.0,
                'recommendations': []
            }
            
            if not bundle.items:
                analysis['recommendations'].append("No context items found")
                return analysis
            
            # トークン効率性
            if bundle.total_tokens > 0:
                analysis['token_efficiency'] = min(1.0, self.max_context_tokens / bundle.total_tokens)
            
            # 関連度スコア
            relevance_scores = {
                RelevanceLevel.CRITICAL: 1.0,
                RelevanceLevel.HIGH: 0.8,
                RelevanceLevel.MEDIUM: 0.6,
                RelevanceLevel.LOW: 0.4,
                RelevanceLevel.REFERENCE: 0.2
            }
            
            total_relevance = sum(relevance_scores[item.relevance] for item in bundle.items)
            analysis['relevance_score'] = total_relevance / len(bundle.items)
            
            # 多様性スコア（異なるタイプの数）
            unique_types = len(set(item.type for item in bundle.items))
            max_types = len(ContextType)
            analysis['diversity_score'] = unique_types / max_types
            
            # 完全性スコア（重要なタイプが含まれているか）
            important_types = {ContextType.CODE_SNIPPET, ContextType.FUNCTION_DEFINITION, ContextType.CLASS_DEFINITION}
            present_important_types = set(item.type for item in bundle.items) & important_types
            analysis['completeness_score'] = len(present_important_types) / len(important_types)
            
            # 総合スコア
            analysis['overall_score'] = (
                analysis['token_efficiency'] * 0.2 +
                analysis['relevance_score'] * 0.4 +
                analysis['diversity_score'] * 0.2 +
                analysis['completeness_score'] * 0.2
            )
            
            # 推奨事項
            if analysis['token_efficiency'] < 0.8:
                analysis['recommendations'].append("Context is using tokens efficiently")
            elif analysis['token_efficiency'] > 1.2:
                analysis['recommendations'].append("Context exceeds token limit, consider optimization")
            
            if analysis['relevance_score'] < 0.5:
                analysis['recommendations'].append("Low relevance score, consider refining search")
            
            if analysis['diversity_score'] < 0.3:
                analysis['recommendations'].append("Low diversity, consider broader context sources")
            
            if analysis['completeness_score'] < 0.5:
                analysis['recommendations'].append("Missing important code context types")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"コンテキスト品質分析エラー: {e}")
            return {'overall_score': 0.0, 'error': str(e)}
    
    def create_focused_context(self, 
                             bundle: ContextBundle, 
                             focus_types: List[ContextType],
                             max_tokens: int = None) -> ContextBundle:
        """特定のタイプに焦点を当てたコンテキストを作成"""
        try:
            if max_tokens is None:
                max_tokens = self.max_context_tokens // 2
            
            focused_bundle = ContextBundle()
            
            # 指定されたタイプのアイテムを優先度順に選択
            relevant_items = []
            for item in bundle.items:
                if item.type in focus_types:
                    relevant_items.append(item)
            
            # 優先度順にソート
            relevant_items.sort(key=lambda x: x.priority, reverse=True)
            
            # トークン制限内で追加
            total_tokens = 0
            for item in relevant_items:
                if total_tokens + item.tokens <= max_tokens:
                    focused_bundle.add_item(item)
                    total_tokens += item.tokens
                else:
                    break
            
            # メタデータを更新
            focused_bundle.metadata = {
                **bundle.metadata,
                'focused_types': [t.value for t in focus_types],
                'original_items': len(bundle.items),
                'focused_items': len(focused_bundle.items)
            }
            
            # サマリーを更新
            type_names = ", ".join([t.value for t in focus_types])
            focused_bundle.summary = f"Focused context ({type_names}): {len(focused_bundle.items)} items, {focused_bundle.total_tokens} tokens"
            
            return focused_bundle
            
        except Exception as e:
            self.logger.error(f"フォーカスコンテキスト作成エラー: {e}")
            return ContextBundle()
    
    def merge_context_bundles(self, *bundles: ContextBundle) -> ContextBundle:
        """複数のコンテキストバンドルをマージ"""
        try:
            merged_bundle = ContextBundle()
            seen_ids = set()
            
            # 全てのアイテムを収集（重複除去）
            all_items = []
            for bundle in bundles:
                for item in bundle.items:
                    if item.id not in seen_ids:
                        all_items.append(item)
                        seen_ids.add(item.id)
            
            # 優先度順にソート
            all_items.sort(key=lambda x: x.priority, reverse=True)
            
            # トークン制限内で追加
            total_tokens = 0
            for item in all_items:
                if total_tokens + item.tokens <= self.max_context_tokens:
                    merged_bundle.add_item(item)
                    total_tokens += item.tokens
                else:
                    break
            
            # メタデータをマージ
            merged_bundle.metadata = {
                'merged_from': len(bundles),
                'total_original_items': sum(len(b.items) for b in bundles),
                'merged_items': len(merged_bundle.items),
                'merged_at': datetime.now().isoformat()
            }
            
            # サマリーを生成
            merged_bundle.summary = f"Merged context: {len(merged_bundle.items)} items from {len(bundles)} bundles, {merged_bundle.total_tokens} tokens"
            
            return merged_bundle
            
        except Exception as e:
            self.logger.error(f"コンテキストバンドルマージエラー: {e}")
            return ContextBundle()
    
    def export_context_bundle(self, bundle: ContextBundle, export_path: str) -> bool:
        """コンテキストバンドルをエクスポート"""
        try:
            export_data = {
                'bundle_metadata': bundle.metadata,
                'summary': bundle.summary,
                'total_tokens': bundle.total_tokens,
                'items': []
            }
            
            for item in bundle.items:
                item_data = {
                    'id': item.id,
                    'type': item.type.value,
                    'content': item.content,
                    'metadata': item.metadata,
                    'relevance': item.relevance.value,
                    'source': item.source,
                    'tokens': item.tokens,
                    'priority': item.priority
                }
                export_data['items'].append(item_data)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"コンテキストバンドルをエクスポートしました: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"コンテキストバンドルエクスポートエラー: {e}")
            return False
    
    def import_context_bundle(self, import_path: str) -> Optional[ContextBundle]:
        """コンテキストバンドルをインポート"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            bundle = ContextBundle()
            bundle.metadata = import_data.get('bundle_metadata', {})
            bundle.summary = import_data.get('summary', '')
            
            for item_data in import_data.get('items', []):
                item = ContextItem(
                    id=item_data['id'],
                    type=ContextType(item_data['type']),
                    content=item_data['content'],
                    metadata=item_data.get('metadata', {}),
                    relevance=RelevanceLevel(item_data['relevance']),
                    source=item_data.get('source', ''),
                    tokens=item_data.get('tokens', 0),
                    priority=item_data.get('priority', 0)
                )
                bundle.add_item(item)
            
            self.logger.info(f"コンテキストバンドルをインポートしました: {import_path}")
            return bundle
            
        except Exception as e:
            self.logger.error(f"コンテキストバンドルインポートエラー: {e}")
            return None


# 使用例とテスト関数
def example_usage():
    """ContextBuilderの使用例"""
    
    # サンプルデータの準備
    from .vector_store import SearchResult
    from .conversation_manager import Message, MessageRole
    from datetime import datetime
    
    # サンプル検索結果
    search_results = [
        SearchResult(
            chunk_id="chunk_1",
            content='''def fibonacci(n):
    """フィボナッチ数列のn番目を計算"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)''',
            metadata={
                'function_name': 'fibonacci',
                'docstring': 'フィボナッチ数列のn番目を計算',
                'keywords': ['fibonacci', 'recursive']
            },
            similarity_score=0.95,
            file_path='math_utils.py',
            line_start=1,
            line_end=5
        ),
        SearchResult(
            chunk_id="chunk_2",
            content='''class Calculator:
    """基本的な計算機クラス"""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        return a + b''',
            metadata={
                'class_name': 'Calculator',
                'docstring': '基本的な計算機クラス'
            },
            similarity_score=0.75,
            file_path='calculator.py',
            line_start=1,
            line_end=8
        )
    ]
    
    # サンプル会話履歴
    conversation_history = [
        Message(
            id="msg_1",
            role=MessageRole.USER,
            content="Pythonでフィボナッチ数列を計算したいです",
            timestamp=datetime.now(),
            context_used=['math_utils.py']
        ),
        Message(
            id="msg_2",
            role=MessageRole.ASSISTANT,
            content="フィボナッチ数列の実装方法をいくつか紹介しますね。再帰版と反復版があります。",
            timestamp=datetime.now()
        )
    ]
    
    # ContextBuilderの初期化
    builder = ContextBuilder(
        max_context_tokens=4000,
        max_code_snippets=5,
        max_conversation_messages=10
    )
    
    # コンテキストの構築
    print("=== コンテキスト構築 ===")
    query = "フィボナッチ数列の最適化"
    
    context_bundle = builder.build_context(
        query=query,
        search_results=search_results,
        conversation_history=conversation_history,
        current_file_path="math_utils.py",
        error_context=None,
        additional_context={
            'performance_notes': 'メモ化を使用すると大幅に高速化できます'
        }
    )
    
    # 結果の表示
    print(f"構築されたコンテキスト:")
    print(f"  アイテム数: {len(context_bundle.items)}")
    print(f"  総トークン数: {context_bundle.total_tokens}")
    print(f"  サマリー: {context_bundle.summary}")
    
    # アイテム別詳細
    print("\n=== コンテキストアイテム ===")
    for item in context_bundle.items:
        print(f"ID: {item.id}")
        print(f"タイプ: {item.type.value}")
        print(f"関連度: {item.relevance.value}")
        print(f"トークン数: {item.tokens}")
        print(f"ソース: {item.source}")
        print(f"内容: {item.content[:100]}...")
        print("-" * 50)
    
    # LLM用フォーマット
    print("\n=== LLM用フォーマット ===")
    formatted_context = builder.format_context_for_llm(context_bundle, include_metadata=True)
    print(formatted_context[:1000] + "..." if len(formatted_context) > 1000 else formatted_context)
    
    # 品質分析
    print("\n=== 品質分析 ===")
    quality_analysis = builder.analyze_context_quality(context_bundle, query)
    print(f"総合スコア: {quality_analysis['overall_score']:.2f}")
    print(f"関連度スコア: {quality_analysis['relevance_score']:.2f}")
    print(f"多様性スコア: {quality_analysis['diversity_score']:.2f}")
    print(f"完全性スコア: {quality_analysis['completeness_score']:.2f}")
    
    if quality_analysis['recommendations']:
        print("推奨事項:")
        for rec in quality_analysis['recommendations']:
            print(f"  - {rec}")
    
    # フォーカスコンテキストの作成
    print("\n=== フォーカスコンテキスト ===")
    focused_bundle = builder.create_focused_context(
        context_bundle,
        focus_types=[ContextType.FUNCTION_DEFINITION, ContextType.CODE_SNIPPET],
        max_tokens=2000
    )
    
    print(f"フォーカス後:")
    print(f"  アイテム数: {len(focused_bundle.items)}")
    print(f"  総トークン数: {focused_bundle.total_tokens}")
    print(f"  サマリー: {focused_bundle.summary}")
    
    # エクスポート
    print("\n=== エクスポート ===")
    export_success = builder.export_context_bundle(context_bundle, "context_bundle.json")
    print(f"エクスポート成功: {export_success}")


if __name__ == "__main__":
    example_usage()

