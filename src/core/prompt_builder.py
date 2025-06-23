# src/core/prompt_builder.py
"""
プロンプト構築システム
LLMへの入力プロンプトを動的に構築し、コンテキストを最適化する
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from enum import Enum

class PromptType(Enum):
    """プロンプトタイプの定義"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CODE_DEBUG = "code_debug"
    CODE_EXPLANATION = "code_explanation"
    CODE_REFACTOR = "code_refactor"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    GENERAL_CHAT = "general_chat"
    PROJECT_ANALYSIS = "project_analysis"
    ERROR_ANALYSIS = "error_analysis"

class PromptBuilder:
    """
    プロンプト構築クラス
    ユーザーの質問とコンテキストから最適なプロンプトを生成
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            config: 設定辞書
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # デフォルト設定
        self.max_context_length = self.config.get('max_context_length', 8000)
        self.max_code_examples = self.config.get('max_code_examples', 3)
        self.include_file_structure = self.config.get('include_file_structure', True)
        self.language_preference = self.config.get('language_preference', 'japanese')
        
        # プロンプトテンプレート
        self.templates = self._load_prompt_templates()
        
        self.logger.info("PromptBuilder初期化完了")
    
    def build_prompt(self, 
                    user_query: str,
                    prompt_type: PromptType,
                    context_chunks: List[Dict[str, Any]] = None,
                    project_info: Dict[str, Any] = None,
                    conversation_history: List[Dict[str, str]] = None) -> str:
        """
        メインのプロンプト構築メソッド
        
        Args:
            user_query: ユーザーの質問
            prompt_type: プロンプトタイプ
            context_chunks: 関連するコードチャンク
            project_info: プロジェクト情報
            conversation_history: 会話履歴
            
        Returns:
            構築されたプロンプト
        """
        try:
            self.logger.debug(f"プロンプト構築開始: {prompt_type.value}")
            
            # プロンプトの基本構造を構築
            prompt_parts = []
            
            # 1. システムプロンプト
            system_prompt = self._build_system_prompt(prompt_type, project_info)
            prompt_parts.append(system_prompt)
            
            # 2. コンテキスト情報
            if context_chunks:
                context_section = self._build_context_section(context_chunks)
                prompt_parts.append(context_section)
            
            # 3. プロジェクト情報
            if project_info and self.include_file_structure:
                project_section = self._build_project_section(project_info)
                prompt_parts.append(project_section)
            
            # 4. 会話履歴
            if conversation_history:
                history_section = self._build_history_section(conversation_history)
                prompt_parts.append(history_section)
            
            # 5. タスク固有の指示
            task_instructions = self._build_task_instructions(prompt_type, user_query)
            prompt_parts.append(task_instructions)
            
            # 6. ユーザークエリ
            query_section = self._build_query_section(user_query, prompt_type)
            prompt_parts.append(query_section)
            
            # プロンプトを結合
            full_prompt = "\n\n".join(filter(None, prompt_parts))
            
            # 長さ制限の適用
            optimized_prompt = self._optimize_prompt_length(full_prompt)
            
            self.logger.debug(f"プロンプト構築完了: {len(optimized_prompt)}文字")
            return optimized_prompt
            
        except Exception as e:
            self.logger.error(f"プロンプト構築エラー: {e}")
            # フォールバック: 簡単なプロンプト
            return self._build_fallback_prompt(user_query, prompt_type)
    
    def _build_system_prompt(self, prompt_type: PromptType, project_info: Dict[str, Any] = None) -> str:
        """システムプロンプトを構築"""
        base_system = """あなたは高度なプログラミングアシスタントです。以下の特徴を持っています：

🎯 **専門性**
- 複数のプログラミング言語に精通
- ベストプラクティスとデザインパターンの知識
- コードの品質、性能、保守性を重視

💡 **回答スタイル**
- 明確で実用的な回答
- 具体的なコード例の提供
- 理由と根拠の説明
- 日本語での丁寧な説明

🔧 **対応範囲**
- コード生成・修正・デバッグ
- アーキテクチャ設計の提案
- パフォーマンス最適化
- テストとドキュメント作成"""
        
        # プロンプトタイプ別の追加指示
        type_specific = self.templates.get('system', {}).get(prompt_type.value, "")
        
        if type_specific:
            base_system += f"\n\n**今回のタスク**: {type_specific}"
        
        # プロジェクト固有の情報
        if project_info:
            project_context = self._format_project_context(project_info)
            if project_context:
                base_system += f"\n\n**プロジェクト情報**:\n{project_context}"
        
        return base_system
    
    def _build_context_section(self, context_chunks: List[Dict[str, Any]]) -> str:
        """コンテキストセクションを構築"""
        if not context_chunks:
            return ""
        
        context_parts = ["## 📁 関連コード情報"]
        
        # チャンクを重要度順にソート
        sorted_chunks = self._sort_chunks_by_relevance(context_chunks)
        
        # 最大数まで処理
        for i, chunk in enumerate(sorted_chunks[:self.max_code_examples]):
            chunk_section = self._format_chunk(chunk, i + 1)
            context_parts.append(chunk_section)
        
        return "\n\n".join(context_parts)
    
    def _build_project_section(self, project_info: Dict[str, Any]) -> str:
        """プロジェクトセクションを構築"""
        if not project_info:
            return ""
        
        section_parts = ["## 🏗️ プロジェクト構造"]
        
        # ファイル構造
        if 'file_structure' in project_info:
            structure = project_info['file_structure']
            section_parts.append(f"```\n{structure}\n```")
        
        # 技術スタック
        if 'tech_stack' in project_info:
            tech_info = project_info['tech_stack']
            tech_text = self._format_tech_stack(tech_info)
            section_parts.append(f"**技術スタック**: {tech_text}")
        
        # 設定情報
        if 'config_summary' in project_info:
            config_info = project_info['config_summary']
            section_parts.append(f"**設定情報**: {config_info}")
        
        return "\n\n".join(section_parts)
    
    def _build_history_section(self, conversation_history: List[Dict[str, str]]) -> str:
        """会話履歴セクションを構築"""
        if not conversation_history:
            return ""
        
        # 最近の会話のみを含める（最大5件）
        recent_history = conversation_history[-5:]
        
        history_parts = ["## 💬 会話履歴"]
        
        for i, exchange in enumerate(recent_history, 1):
            user_msg = exchange.get('user', '')
            assistant_msg = exchange.get('assistant', '')
            
            if user_msg:
                history_parts.append(f"**Q{i}**: {user_msg[:200]}...")
            if assistant_msg:
                history_parts.append(f"**A{i}**: {assistant_msg[:200]}...")
        
        return "\n\n".join(history_parts)
    
    def _build_task_instructions(self, prompt_type: PromptType, user_query: str) -> str:
        """タスク固有の指示を構築"""
        instructions = self.templates.get('instructions', {}).get(prompt_type.value, "")
        
        if not instructions:
            # デフォルト指示
            if prompt_type == PromptType.CODE_GENERATION:
                instructions = "新しいコードを生成してください。コメントを含め、実用的で動作するコードを提供してください。"
            elif prompt_type == PromptType.CODE_DEBUG:
                instructions = "コードの問題を特定し、修正案を提供してください。エラーの原因と解決方法を説明してください。"
            elif prompt_type == PromptType.CODE_REVIEW:
                instructions = "コードをレビューし、改善点を指摘してください。品質、性能、保守性の観点から評価してください。"
            else:
                instructions = "質問に対して適切で実用的な回答を提供してください。"
        
        # クエリから特定の言語や技術を検出
        detected_tech = self._detect_technologies(user_query)
        if detected_tech:
            tech_instruction = f"\n\n**検出された技術**: {', '.join(detected_tech)}\nこれらの技術に特化した回答を提供してください。"
            instructions += tech_instruction
        
        return f"## 🎯 タスク指示\n{instructions}"
    
    def _build_query_section(self, user_query: str, prompt_type: PromptType) -> str:
        """ユーザークエリセクションを構築"""
        query_parts = ["## ❓ ユーザーの質問"]
        
        # クエリの分析
        query_analysis = self._analyze_query(user_query)
        
        # メインクエリ
        query_parts.append(f"**質問内容**: {user_query}")
        
        # 分析結果
        if query_analysis:
            query_parts.append(f"**分析結果**: {query_analysis}")
        
        # 期待される回答形式
        expected_format = self._get_expected_format(prompt_type)
        if expected_format:
            query_parts.append(f"**期待される回答形式**: {expected_format}")
        
        return "\n\n".join(query_parts)
    
    def _format_chunk(self, chunk: Dict[str, Any], index: int) -> str:
        """チャンクを整形"""
        chunk_parts = [f"### 📄 コード例 {index}"]
        
        # ファイル情報
        file_path = chunk.get('file_path', 'unknown')
        file_name = Path(file_path).name
        language = chunk.get('language', 'text')
        
        chunk_parts.append(f"**ファイル**: `{file_name}` ({language})")
        
        # 行情報
        line_start = chunk.get('line_start', 1)
        line_end = chunk.get('line_end', 1)
        chunk_parts.append(f"**行範囲**: {line_start}-{line_end}")
        
        # 関数・クラス情報
        if chunk.get('function_name'):
            chunk_parts.append(f"**関数**: `{chunk['function_name']}`")
        if chunk.get('class_name'):
            chunk_parts.append(f"**クラス**: `{chunk['class_name']}`")
        
        # docstring
        if chunk.get('docstring'):
            chunk_parts.append(f"**説明**: {chunk['docstring'][:100]}...")
        
        # コード内容
        content = chunk.get('content', '')
        if content:
            chunk_parts.append(f"```{language}\n{content}\n```")
        
        return "\n".join(chunk_parts)
    
    def _format_project_context(self, project_info: Dict[str, Any]) -> str:
        """プロジェクト情報を整形"""
        context_parts = []
        
        if 'name' in project_info:
            context_parts.append(f"プロジェクト名: {project_info['name']}")
        
        if 'description' in project_info:
            context_parts.append(f"説明: {project_info['description']}")
        
        if 'main_language' in project_info:
            context_parts.append(f"主要言語: {project_info['main_language']}")
        
        return "\n".join(context_parts)
    
    def _format_tech_stack(self, tech_stack: Dict[str, Any]) -> str:
        """技術スタックを整形"""
        tech_parts = []
        
        for category, technologies in tech_stack.items():
            if isinstance(technologies, list):
                tech_list = ", ".join(technologies)
                tech_parts.append(f"{category}: {tech_list}")
            else:
                tech_parts.append(f"{category}: {technologies}")
        
        return " | ".join(tech_parts)
    
    def _sort_chunks_by_relevance(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """チャンクを関連度順にソート"""
        # 簡単な関連度計算（実際にはより高度なアルゴリズムを使用可能）
        def relevance_score(chunk):
            score = 0
            
            # 関数・クラスは高スコア
            if chunk.get('function_name'):
                score += 10
            if chunk.get('class_name'):
                score += 8
            
            # docstringがあるものは高スコア
            if chunk.get('docstring'):
                score += 5
            
            # インポート文は低スコア
            if chunk.get('type') == 'imports':
                score += 1
            
            # コード量による調整
            content_length = len(chunk.get('content', ''))
            if 100 < content_length < 1000:  # 適度な長さ
                score += 3
            elif content_length > 1000:  # 長すぎる
                score -= 2
            
            return score
        
        return sorted(chunks, key=relevance_score, reverse=True)
    
    def _detect_technologies(self, query: str) -> List[str]:
        """クエリから技術を検出"""
        technologies = {
            'python': ['python', 'py', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular', 'express'],
            'typescript': ['typescript', 'ts'],
            'java': ['java', 'spring', 'maven', 'gradle'],
            'cpp': ['c++', 'cpp', 'cmake'],
            'c': ['c言語', 'c'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'database', 'db'],
            'web': ['html', 'css', 'web', 'api', 'rest', 'graphql'],
            'devops': ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'ci/cd'],
            'testing': ['test', 'unittest', 'pytest', 'jest', 'testing']
        }
        
        detected = []
        query_lower = query.lower()
        
        for tech_category, keywords in technologies.items():
            for keyword in keywords:
                if keyword in query_lower:
                    detected.append(tech_category)
                    break
        
        return list(set(detected))
    
    def _analyze_query(self, query: str) -> str:
        """クエリを分析"""
        analysis_parts = []
        
        # 質問タイプの検出
        if any(word in query.lower() for word in ['なぜ', 'why', '理由', '原因']):
            analysis_parts.append("説明・理由を求める質問")
        
        if any(word in query.lower() for word in ['どうやって', 'how', '方法', 'やり方']):
            analysis_parts.append("手順・方法を求める質問")
        
        if any(word in query.lower() for word in ['エラー', 'error', 'バグ', 'bug', '動かない']):
            analysis_parts.append("エラー・デバッグ関連")
        
        if any(word in query.lower() for word in ['最適化', 'optimize', '改善', 'improve', '高速化']):
            analysis_parts.append("最適化・改善関連")
        
        if any(word in query.lower() for word in ['作成', 'create', '生成', 'generate', '書いて']):
            analysis_parts.append("コード生成要求")
        
        return " | ".join(analysis_parts) if analysis_parts else "一般的な質問"
    
    def _get_expected_format(self, prompt_type: PromptType) -> str:
        """期待される回答形式を取得"""
        format_map = {
            PromptType.CODE_GENERATION: "動作するコード + 説明 + 使用例",
            PromptType.CODE_DEBUG: "問題の特定 + 修正されたコード + 説明",
            PromptType.CODE_REVIEW: "評価ポイント + 改善提案 + 修正例",
            PromptType.CODE_EXPLANATION: "コードの動作説明 + 重要なポイント",
            PromptType.DOCUMENTATION: "構造化されたドキュメント + 例",
            PromptType.TESTING: "テストコード + テスト戦略",
            PromptType.ERROR_ANALYSIS: "エラー原因 + 解決手順 + 予防策"
        }
        
        return format_map.get(prompt_type, "適切な形式での回答")
    
    def _optimize_prompt_length(self, prompt: str) -> str:
        """プロンプト長を最適化"""
        if len(prompt) <= self.max_context_length:
            return prompt
        
        self.logger.warning(f"プロンプトが長すぎます ({len(prompt)} > {self.max_context_length})")
        
        # セクション別に優先度を設定して削減
        sections = prompt.split('\n\n')
        
        # 重要度の高いセクションを保持
        essential_sections = []
        optional_sections = []
        
        for section in sections:
            if any(marker in section for marker in ['## ❓', '## 🎯', 'システム']):
                essential_sections.append(section)
            else:
                optional_sections.append(section)
        
        # 必須セクションから開始
        optimized_prompt = '\n\n'.join(essential_sections)
        
        # 残りの長さでオプションセクションを追加
        remaining_length = self.max_context_length - len(optimized_prompt)
        
        for section in optional_sections:
            if len(section) < remaining_length:
                optimized_prompt += '\n\n' + section
                remaining_length -= len(section) + 2
            else:
                # セクションを短縮
                truncated = section[:remaining_length-100] + "\n...(省略)"
                optimized_prompt += '\n\n' + truncated
                break
        
        self.logger.info(f"プロンプト最適化完了: {len(prompt)} -> {len(optimized_prompt)}")
        return optimized_prompt
    
    def _build_fallback_prompt(self, user_query: str, prompt_type: PromptType) -> str:
        """フォールバックプロンプト"""
        return f"""あなたは経験豊富なプログラミングアシスタントです。

質問: {user_query}

上記の質問に対して、以下の点を考慮して回答してください：
- 実用的で具体的な回答
- 必要に応じてコード例を含める
- 日本語で分かりやすく説明
- ベストプラクティスに基づく提案

回答をお願いします。"""
    
    def _load_prompt_templates(self) -> Dict[str, Dict[str, str]]:
        """プロンプトテンプレートを読み込み"""
        templates = {
            'system': {
                'code_generation': "新しいコードの生成に特化しています。要件を分析し、効率的で保守性の高いコードを生成します。",
                'code_debug': "コードのデバッグとエラー解決に特化しています。問題を特定し、具体的な修正方法を提案します。",
                'code_review': "コードレビューに特化しています。品質、性能、セキュリティの観点から評価し、改善提案を行います。",
                'code_explanation': "コードの解説に特化しています。複雑なロジックを分かりやすく説明し、学習をサポートします。",
                'documentation': "ドキュメント作成に特化しています。技術文書、API仕様、使用方法を明確に記述します。",
                'testing': "テスト設計と実装に特化しています。効果的なテスト戦略とテストコードを提案します。"
            },
            'instructions': {
                'code_generation': """以下の手順でコードを生成してください：
1. 要件の分析と整理
2. 適切な設計パターンの選択
3. 実装コードの生成
4. エラーハンドリングの追加
5. コメントとドキュメントの記述
6. 使用例の提供""",
                
                'code_debug': """以下の手順でデバッグを行ってください：
1. エラーメッセージの分析
2. 問題箇所の特定
3. 根本原因の調査
4. 修正方法の提案
5. 修正されたコードの提供
6. 再発防止策の提案""",
                
                'code_review': """以下の観点でレビューしてください：
1. コードの可読性と保守性
2. 性能とメモリ使用量
3. セキュリティの考慮
4. エラーハンドリング
5. テスタビリティ
6. ベストプラクティスの遵守"""
            }
        }
        
        return templates
    
    def create_specialized_prompt(self, 
                                 prompt_type: PromptType,
                                 specific_context: Dict[str, Any]) -> str:
        """特殊用途向けプロンプトを作成"""
        
        if prompt_type == PromptType.PROJECT_ANALYSIS:
            return self._create_project_analysis_prompt(specific_context)
        elif prompt_type == PromptType.ERROR_ANALYSIS:
            return self._create_error_analysis_prompt(specific_context)
        else:
            return self._build_fallback_prompt(
                specific_context.get('query', ''), 
                prompt_type
            )
    
    def _create_project_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """プロジェクト分析用プロンプト"""
        prompt = """# 🔍 プロジェクト分析タスク

あなたはソフトウェアアーキテクトとして、プロジェクトの全体的な分析を行ってください。

## 分析対象
"""
        
        if 'file_list' in context:
            prompt += f"**ファイル数**: {len(context['file_list'])} 個\n"
        
        if 'languages' in context:
            prompt += f"**使用言語**: {', '.join(context['languages'])}\n"
        
        if 'project_structure' in context:
            prompt += f"**プロジェクト構造**:\n```\n{context['project_structure']}\n```\n"
        
        prompt += """
## 分析項目
以下の観点から分析してください：

1. **アーキテクチャ評価**
   - 設計パターンの使用状況
   - モジュール間の依存関係
   - 拡張性と保守性

2. **コード品質**
   - コーディング規約の遵守
   - テストカバレッジ
   - ドキュメント化状況

3. **技術的負債**
   - 改善が必要な箇所
   - リファクタリング候補
   - セキュリティ上の懸念

4. **改善提案**
   - 優先度付きの改善案
   - 実装方法の提案
   - 期待される効果

詳細な分析結果を日本語で提供してください。
"""
        
        return prompt
    
    def _create_error_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """エラー分析用プロンプト"""
        prompt = """# 🚨 エラー分析・解決タスク

システムエラーの分析と解決策の提案を行ってください。

## エラー情報
"""
        
        if 'error_message' in context:
            prompt += f"**エラーメッセージ**:\n```\n{context['error_message']}\n```\n\n"
        
        if 'stack_trace' in context:
            prompt += f"**スタックトレース**:\n```\n{context['stack_trace']}\n```\n\n"
        
        if 'error_context' in context:
            prompt += f"**発生状況**: {context['error_context']}\n\n"
        
        prompt += """## 分析・解決手順

以下の手順で分析してください：

1. **エラーの分類**
   - エラーの種類と重要度
   - 影響範囲の特定

2. **原因分析**
   - 直接的な原因
   - 根本的な原因
   - 関連する要因

3. **解決策の提案**
   - 即座に適用可能な修正
   - 根本的な解決方法
   - 代替案の検討

4. **予防策**
   - 再発防止のための対策
   - 監視・検知の改善
   - プロセスの見直し

実用的で具体的な解決策を日本語で提供してください。
"""
        
        return prompt
    
    def validate_prompt(self, prompt: str) -> Tuple[bool, List[str]]:
        """プロンプトの妥当性を検証"""
        issues = []
        
        # 長さチェック
        if len(prompt) > self.max_context_length:
            issues.append(f"プロンプトが長すぎます: {len(prompt)} > {self.max_context_length}")
        
        # 必須セクションの確認
        required_sections = ['質問', 'タスク']
        for section in required_sections:
            if section not in prompt:
                issues.append(f"必須セクション '{section}' が見つかりません")
        
        # 文字エンコーディングチェック
        try:
            prompt.encode('utf-8')
        except UnicodeEncodeError:
            issues.append("文字エンコーディングエラー")
        
        return len(issues) == 0, issues
    
    def get_prompt_statistics(self, prompt: str) -> Dict[str, Any]:
        """プロンプトの統計情報を取得"""
        lines = prompt.split('\n')
        words = prompt.split()
        
        return {
            'character_count': len(prompt),
            'line_count': len(lines),
            'word_count': len(words),
            'section_count': prompt.count('##'),
            'code_block_count': prompt.count('```'),
            'estimated_tokens': len(words) * 1.3,  # 概算
            'complexity_score': self._calculate_complexity_score(prompt)
        }
    
    def _calculate_complexity_score(self, prompt: str) -> float:
        """プロンプトの複雑度スコアを計算"""
        score = 0.0
        
        # 長さによる基本スコア
        score += len(prompt) / 1000
        
        # セクション数
        score += prompt.count('##') * 0.5
        
        # コードブロック数
        score += prompt.count('```') * 0.3
        
        # 専門用語の使用
        technical_terms = ['API', 'データベース', 'アルゴリズム', 'フレームワーク']
        for term in technical_terms:
            if term in prompt:
                score += 0.1
        
        return round(score, 2)
    
    def export_prompt_template(self, prompt_type: PromptType, file_path: str) -> bool:
        """プロンプトテンプレートをエクスポート"""
        try:
            template_data = {
                'type': prompt_type.value,
                'system_prompt': self.templates.get('system', {}).get(prompt_type.value, ''),
                'instructions': self.templates.get('instructions', {}).get(prompt_type.value, ''),
                'created_at': datetime.now().isoformat(),
                'config': {
                    'max_context_length': self.max_context_length,
                    'max_code_examples': self.max_code_examples,
                    'language_preference': self.language_preference
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"テンプレートをエクスポートしました: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"エクスポートエラー: {e}")
            return False
    
    def __str__(self) -> str:
        return f"PromptBuilder(max_length={self.max_context_length}, templates={len(self.templates)})"


# 使用例
def example_usage():
    """PromptBuilderの使用例"""
    
    # 初期化
    config = {
        'max_context_length': 6000,
        'max_code_examples': 2,
        'language_preference': 'japanese'
    }
    
    builder = PromptBuilder(config)
    
    # サンプルコンテキスト
    context_chunks = [
        {
            'content': 'def calculate_sum(numbers):\n    return sum(numbers)',
            'type': 'function',
            'file_path': 'utils.py',
            'function_name': 'calculate_sum',
            'language': 'python',
            'line_start': 1,
            'line_end': 2
        }
    ]
    
    project_info = {
        'name': 'Sample Project',
        'main_language': 'Python',
        'tech_stack': {
            'backend': ['Python', 'FastAPI'],
            'database': ['PostgreSQL']
        }
    }
    
    # プロンプト生成
    user_query = "この関数を改善してエラーハンドリングを追加してください"
    
    prompt = builder.build_prompt(
        user_query=user_query,
        prompt_type=PromptType.CODE_REVIEW,
        context_chunks=context_chunks,
        project_info=project_info
    )
    
    print("=== 生成されたプロンプト ===")
    print(prompt)
    
    # 統計情報
    stats = builder.get_prompt_statistics(prompt)
    print(f"\n=== 統計情報 ===")
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    example_usage()
