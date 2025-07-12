# src/llm/prompt_templates.py
"""
プロンプトテンプレートモジュール
様々な用途に応じたプロンプトテンプレートを管理・生成
"""

import json
import re
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from ..core.logger import get_logger
from ..core.config_manager import get_config
from ..utils.text_utils import TextUtils
from ..utils.validation_utils import ValidationUtils

logger = get_logger(__name__)

class PromptType(Enum):
    """プロンプトタイプ列挙型"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CODE_EXPLANATION = "code_explanation"
    CODE_REFACTORING = "code_refactoring"
    DEBUG_ASSISTANCE = "debug_assistance"
    DOCUMENTATION = "documentation"
    TRANSLATION = "translation"
    GENERAL_CHAT = "general_chat"
    SYSTEM_PROMPT = "system_prompt"
    CUSTOM = "custom"

class PromptRole(Enum):
    """プロンプトロール列挙型"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

@dataclass
class PromptVariable:
    """プロンプト変数定義"""
    name: str
    description: str
    required: bool = True
    default_value: Optional[str] = None
    validation_pattern: Optional[str] = None
    validation_function: Optional[Callable[[str], bool]] = None

@dataclass
class PromptTemplate:
    """プロンプトテンプレート"""
    id: str
    name: str
    description: str
    prompt_type: PromptType
    role: PromptRole
    template: str
    variables: List[PromptVariable] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    language: str = "ja"
    version: str = "1.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class PromptTemplateManager:
    """プロンプトテンプレート管理クラス"""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            template_dir: テンプレートディレクトリパス
        """
        self.logger = get_logger(self.__class__.__name__)
        self.text_utils = TextUtils()
        self.validation_utils = ValidationUtils()
        
        # テンプレートディレクトリ
        self.template_dir = Path(template_dir) if template_dir else Path("data/templates")
        
        # テンプレート辞書
        self._templates: Dict[str, PromptTemplate] = {}
        
        # 初期化
        self._initialize_default_templates()
        self._load_custom_templates()
        
        self.logger.info("プロンプトテンプレート管理を初期化しました")
    
    def _initialize_default_templates(self):
        """デフォルトテンプレートを初期化"""
        try:
            # システムプロンプト
            self.register_template(PromptTemplate(
                id="system_code_assistant",
                name="コードアシスタント システムプロンプト",
                description="コードアシスタント用のシステムプロンプト",
                prompt_type=PromptType.SYSTEM_PROMPT,
                role=PromptRole.SYSTEM,
                template="""あなたは優秀なプログラミングアシスタントです。以下の特徴を持っています：

            1. **専門知識**: 多様なプログラミング言語とフレームワークに精通
            2. **コード品質**: 読みやすく、保守性の高いコードを重視
            3. **ベストプラクティス**: 業界標準のコーディング規約を遵守
            4. **セキュリティ**: セキュアなコードの実装を心がける
            5. **パフォーマンス**: 効率的で最適化されたソリューションを提供

            **対応言語**: Python, JavaScript, TypeScript, Java, C#, Go, Rust, HTML, CSS, SQL等
            **回答形式**: 
            - コードには適切なコメントを含める
            - 説明は簡潔で分かりやすく
            - エラーハンドリングを考慮
            - 日本語で回答

            どのようなプログラミングの質問でもお気軽にどうぞ！""",
                            tags=["system", "programming", "assistant"],
                            language="ja"
                        ))
                        
                        # コード生成
            self.register_template(PromptTemplate(
                id="code_generation_basic",
                name="基本コード生成",
                description="指定された要件に基づいてコードを生成",
                prompt_type=PromptType.CODE_GENERATION,
                role=PromptRole.USER,
                template="""以下の要件に基づいて{language}のコードを生成してください：

            **要件**:
            {requirements}

            **追加条件**:
            - 適切なコメントを含めてください
            - エラーハンドリングを実装してください
            - ベストプラクティスに従ってください
            - 読みやすいコードにしてください

            {additional_context}""",
                            variables=[
                                PromptVariable("language", "プログラミング言語", required=True),
                                PromptVariable("requirements", "コード要件", required=True),
                                PromptVariable("additional_context", "追加コンテキスト", required=False, default_value="")
                            ],
                            tags=["code", "generation"],
                            language="ja"
                        ))
                        
                        # コードレビュー
            self.register_template(PromptTemplate(
                id="code_review_comprehensive",
                name="包括的コードレビュー",
                description="コードの品質、セキュリティ、パフォーマンスを総合的にレビュー",
                prompt_type=PromptType.CODE_REVIEW,
                role=PromptRole.USER,
                template="""以下のコードをレビューしてください：

            ```{language}

            {code}

            レビュー観点:

            コード品質: 可読性、保守性、設計パターン
            セキュリティ: 脆弱性、セキュリティベストプラクティス
            パフォーマンス: 効率性、最適化の余地
            バグ: 潜在的な問題、エラーハンドリング
            ベストプラクティス: 言語固有の推奨事項
            出力形式:

            問題点と改善提案
            修正されたコード例（必要に応じて）
            評価スコア（1-10）
                            {focus_areas}""",
                            variables=[
                            PromptVariable("language", "プログラミング言語", required=True),
                            PromptVariable("code", "レビュー対象コード", required=True),
                            PromptVariable("focus_areas", "重点レビュー領域", required=False, default_value="")
                            ],
                            tags=["code", "review", "quality"],
                            language="ja"
                            ))
                        # コード説明
            self.register_template(PromptTemplate(
                id="code_explanation_detailed",
                name="詳細コード説明",
                description="コードの動作と仕組みを詳しく説明",
                prompt_type=PromptType.CODE_EXPLANATION,
                role=PromptRole.USER,
                template="""以下のコードについて詳しく説明してください：

                    {code}

                    説明内容:

            概要: このコードが何をするか
            処理フロー: ステップバイステップの動作
            重要な部分: キーとなるロジックや処理
            使用技術: 使われているライブラリや手法
            改善点: より良くするための提案
            対象レベル: {target_level}

                        {specific_questions}""",
                        variables=[
                        PromptVariable("language", "プログラミング言語", required=True),
                        PromptVariable("code", "説明対象コード", required=True),
                        PromptVariable("target_level", "対象レベル（初心者/中級者/上級者）", required=False, default_value="中級者"),
                        PromptVariable("specific_questions", "特定の質問", required=False, default_value="")
                        ],
                        tags=["code", "explanation", "learning"],
                        language="ja"
                        ))
                        # リファクタリング
            self.register_template(PromptTemplate(
                id="code_refactoring_improvement",
                name="コードリファクタリング",
                description="コードの構造と品質を改善",
                prompt_type=PromptType.CODE_REFACTORING,
                role=PromptRole.USER,
                template="""以下のコードをリファクタリングしてください：

                        {code}

                        リファクタリング目標:
                        {refactoring_goals}

            重点項目:

            コードの可読性向上
            重複コードの削除
            関数/クラスの適切な分割
            命名の改善
            パフォーマンスの最適化
            制約条件:
                        {constraints}

            出力:

            リファクタリング後のコード

            変更点の説明

            改善された点の詳細""",
                        variables=[
                        PromptVariable("language", "プログラミング言語", required=True),
                        PromptVariable("code", "リファクタリング対象コード", required=True),
                        PromptVariable("refactoring_goals", "リファクタリング目標", required=False, default_value="コード品質の向上"),
                        PromptVariable("constraints", "制約条件", required=False, default_value="なし")
                        ],
                        tags=["code", "refactoring", "improvement"],
                        language="ja"
                        ))
                    # デバッグ支援
            self.register_template(PromptTemplate(
                id="debug_assistance_comprehensive",
                name="包括的デバッグ支援",
                description="エラーの原因特定と解決策の提案",
                prompt_type=PromptType.DEBUG_ASSISTANCE,
                role=PromptRole.USER,
                template="""以下のコードでエラーが発生しています。デバッグを支援してください：

                    {code}

                    {error_message}

                    
            発生状況:
            {error_context}

            期待する動作:
            {expected_behavior}

            デバッグ支援内容:

            エラーの原因分析
            修正方法の提案
            修正されたコード例
            再発防止策
            テスト方法の提案
                        {additional_info}""",
                        variables=[
                        PromptVariable("language", "プログラミング言語", required=True),
                        PromptVariable("code", "問題のあるコード", required=True),
                        PromptVariable("error_message", "エラーメッセージ", required=True),
                        PromptVariable("error_context", "エラー発生状況", required=False, default_value=""),
                        PromptVariable("expected_behavior", "期待する動作", required=False, default_value=""),
                        PromptVariable("additional_info", "追加情報", required=False, default_value="")
                        ],
                        tags=["debug", "error", "troubleshooting"],
                        language="ja"
                        ))
                    # ドキュメント生成
            self.register_template(PromptTemplate(
                id="documentation_generation",
                name="ドキュメント生成",
                description="コードのドキュメントを自動生成",
                prompt_type=PromptType.DOCUMENTATION,
                role=PromptRole.USER,
                template="""以下のコードのドキュメントを生成してください：

                {code}

            ドキュメント形式: {doc_format}

            含める内容:

            概要: 機能の説明
            パラメータ: 引数の説明
            戻り値: 返り値の説明
            使用例: 実際の使用方法
            注意事項: 使用時の注意点
            関連情報: 関連する関数やクラス
            スタイル: {doc_style}

                        {special_requirements}""",
                        variables=[
                        PromptVariable("language", "プログラミング言語", required=True),
                        PromptVariable("code", "ドキュメント対象コード", required=True),
                        PromptVariable("doc_format", "ドキュメント形式（Markdown/reStructuredText/Docstring）", required=False, default_value="Markdown"),
                        PromptVariable("doc_style", "ドキュメントスタイル", required=False, default_value="詳細"),
                        PromptVariable("special_requirements", "特別な要件", required=False, default_value="")
                        ],
                        tags=["documentation", "code", "generation"],
                        language="ja"
                        ))
            # 一般的なチャット
            self.register_template(PromptTemplate(
                id="general_chat_programming",
                name="プログラミング一般チャット",
                description="プログラミングに関する一般的な質問対応",
                prompt_type=PromptType.GENERAL_CHAT,
                role=PromptRole.USER,
                template="""プログラミングに関する質問があります：

                {question}

            コンテキスト:
            {context}

            希望する回答形式:

            分かりやすい説明
            具体例やコード例（必要に応じて）
            実践的なアドバイス
            関連リソースの紹介（あれば）
                        {additional_requirements}""",
                        variables=[
                        PromptVariable("question", "質問内容", required=True),
                        PromptVariable("context", "質問のコンテキスト", required=False, default_value=""),
                        PromptVariable("additional_requirements", "追加要件", required=False, default_value="")
                        ],
                        tags=["chat", "programming", "general"],
                        language="ja"
                        ))
                
            self.logger.info("デフォルトテンプレートを初期化しました")
        
        except Exception as e:
            self.logger.error(f"デフォルトテンプレート初期化エラー: {e}")

    def _load_custom_templates(self):
        """カスタムテンプレートをロード"""
        try:
            if not self.template_dir.exists():
                self.template_dir.mkdir(parents=True, exist_ok=True)
                return
            
            # JSONファイルからテンプレートを読み込み
            for template_file in self.template_dir.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    template = self._dict_to_template(template_data)
                    self.register_template(template)
                    
                except Exception as e:
                    self.logger.warning(f"テンプレートファイル読み込みエラー {template_file}: {e}")
            
            self.logger.info("カスタムテンプレートをロードしました")
            
        except Exception as e:
            self.logger.error(f"カスタムテンプレートロードエラー: {e}")

    def _dict_to_template(self, data: Dict[str, Any]) -> PromptTemplate:
        """辞書からPromptTemplateオブジェクトを作成"""
        try:
            # 変数の変換
            variables = []
            for var_data in data.get('variables', []):
                variables.append(PromptVariable(
                    name=var_data['name'],
                    description=var_data['description'],
                    required=var_data.get('required', True),
                    default_value=var_data.get('default_value'),
                    validation_pattern=var_data.get('validation_pattern'),
                ))
            
            # 日時の変換
            created_at = None
            updated_at = None
            if data.get('created_at'):
                created_at = datetime.fromisoformat(data['created_at'])
            if data.get('updated_at'):
                updated_at = datetime.fromisoformat(data['updated_at'])
            
            return PromptTemplate(
                id=data['id'],
                name=data['name'],
                description=data['description'],
                prompt_type=PromptType(data['prompt_type']),
                role=PromptRole(data['role']),
                template=data['template'],
                variables=variables,
                tags=data.get('tags', []),
                language=data.get('language', 'ja'),
                version=data.get('version', '1.0'),
                created_at=created_at,
                updated_at=updated_at,
                metadata=data.get('metadata', {})
            )
            
        except Exception as e:
            self.logger.error(f"テンプレート変換エラー: {e}")
            raise

    def _template_to_dict(self, template: PromptTemplate) -> Dict[str, Any]:
        """PromptTemplateオブジェクトを辞書に変換"""
        try:
            # 変数の変換
            variables = []
            for var in template.variables:
                var_dict = {
                    'name': var.name,
                    'description': var.description,
                    'required': var.required
                }
                if var.default_value is not None:
                    var_dict['default_value'] = var.default_value
                if var.validation_pattern is not None:
                    var_dict['validation_pattern'] = var.validation_pattern
                variables.append(var_dict)
            
            data = {
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'prompt_type': template.prompt_type.value,
                'role': template.role.value,
                'template': template.template,
                'variables': variables,
                'tags': template.tags,
                'language': template.language,
                'version': template.version,
                'metadata': template.metadata
            }
            
            # 日時の変換
            if template.created_at:
                data['created_at'] = template.created_at.isoformat()
            if template.updated_at:
                data['updated_at'] = template.updated_at.isoformat()
            
            return data
            
        except Exception as e:
            self.logger.error(f"テンプレート辞書変換エラー: {e}")
            raise

    def register_template(self, template: PromptTemplate):
        """
        テンプレートを登録
        
        Args:
            template: プロンプトテンプレート
        """
        try:
            if not isinstance(template, PromptTemplate):
                raise ValueError("テンプレートオブジェクトが正しくありません")
            
            # 重複チェック
            if template.id in self._templates:
                self.logger.warning(f"テンプレートIDが重複しています: {template.id}")
            
            # 更新日時を設定
            if not template.created_at:
                template.created_at = datetime.now()
            template.updated_at = datetime.now()
            
            self._templates[template.id] = template
            self.logger.info(f"テンプレートを登録しました: {template.id}")
            
        except Exception as e:
            self.logger.error(f"テンプレート登録エラー: {e}")
            raise

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """
        テンプレートを取得
        
        Args:
            template_id: テンプレートID
            
        Returns:
            Optional[PromptTemplate]: テンプレート
        """
        return self._templates.get(template_id)

    def get_templates_by_type(self, prompt_type: PromptType) -> List[PromptTemplate]:
        """
        タイプ別テンプレート一覧を取得
        
        Args:
            prompt_type: プロンプトタイプ
            
        Returns:
            List[PromptTemplate]: テンプレート一覧
        """
        return [
            template for template in self._templates.values()
            if template.prompt_type == prompt_type
        ]

    def get_templates_by_tag(self, tag: str) -> List[PromptTemplate]:
        """
        タグ別テンプレート一覧を取得
        
        Args:
            tag: タグ
            
        Returns:
            List[PromptTemplate]: テンプレート一覧
        """
        return [
            template for template in self._templates.values()
            if tag in template.tags
        ]

    def search_templates(self, query: str) -> List[PromptTemplate]:
        """
        テンプレートを検索
        
        Args:
            query: 検索クエリ
            
        Returns:
            List[PromptTemplate]: 検索結果
        """
        try:
            query_lower = query.lower()
            results = []
            
            for template in self._templates.values():
                # 名前、説明、タグで検索
                if (query_lower in template.name.lower() or
                    query_lower in template.description.lower() or
                    any(query_lower in tag.lower() for tag in template.tags)):
                    results.append(template)
            
            return results
            
        except Exception as e:
            self.logger.error(f"テンプレート検索エラー: {e}")
            return []

    def render_template(self, 
                    template_id: str, 
                    variables: Dict[str, Any],
                    validate: bool = True) -> str:
        """
        テンプレートをレンダリング
        
        Args:
            template_id: テンプレートID
            variables: 変数辞書
            validate: 変数検証を行うか
            
        Returns:
            str: レンダリング結果
        """
        try:
            template = self.get_template(template_id)
            if not template:
                raise ValueError(f"テンプレートが見つかりません: {template_id}")
            
            # 変数検証
            if validate:
                self._validate_variables(template, variables)
            
            # デフォルト値を適用
            effective_variables = self._apply_default_values(template, variables)
            
            # テンプレートレンダリング
            rendered = template.template.format(**effective_variables)
            
            return rendered
            
        except Exception as e:
            self.logger.error(f"テンプレートレンダリングエラー: {e}")
            raise

    def _validate_variables(self, template: PromptTemplate, variables: Dict[str, Any]):
        """変数を検証"""
        try:
            # 必須変数のチェック
            for var in template.variables:
                if var.required and var.name not in variables:
                    raise ValueError(f"必須変数が不足しています: {var.name}")
                
                # 値の検証
                if var.name in variables:
                    value = variables[var.name]
                    
                    # パターン検証
                    if var.validation_pattern and isinstance(value, str):
                        if not re.match(var.validation_pattern, value):
                            raise ValueError(f"変数の形式が正しくありません: {var.name}")
                    
                    # 関数検証
                    if var.validation_function:
                        if not var.validation_function(value):
                            raise ValueError(f"変数の検証に失敗しました: {var.name}")
            
        except Exception as e:
            self.logger.error(f"変数検証エラー: {e}")
            raise

    def _apply_default_values(self, 
                            template: PromptTemplate, 
                            variables: Dict[str, Any]) -> Dict[str, Any]:
        """デフォルト値を適用"""
        try:
            effective_variables = variables.copy()
            
            for var in template.variables:
                if var.name not in effective_variables and var.default_value is not None:
                    effective_variables[var.name] = var.default_value
            
            return effective_variables
            
        except Exception as e:
            self.logger.error(f"デフォルト値適用エラー: {e}")
            raise

    def save_template(self, template: PromptTemplate, file_path: Optional[str] = None):
        """
        テンプレートをファイルに保存
        
        Args:
            template: プロンプトテンプレート
            file_path: 保存先ファイルパス
        """
        try:
            if not file_path:
                file_path = self.template_dir / f"{template.id}.json"
            else:
                file_path = Path(file_path)
            
            # ディレクトリ作成
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # テンプレートを辞書に変換
            template_data = self._template_to_dict(template)
            
            # ファイルに保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"テンプレートを保存しました: {file_path}")
            
        except Exception as e:
            self.logger.error(f"テンプレート保存エラー: {e}")
            raise

    def load_template_from_file(self, file_path: str) -> PromptTemplate:
        """
        ファイルからテンプレートをロード
        
        Args:
            file_path: ファイルパス
            
        Returns:
            PromptTemplate: テンプレート
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            template = self._dict_to_template(template_data)
            return template
            
        except Exception as e:
            self.logger.error(f"テンプレートファイル読み込みエラー: {e}")
            raise

    def delete_template(self, template_id: str):
        """
        テンプレートを削除
        
        Args:
            template_id: テンプレートID
        """
        try:
            if template_id in self._templates:
                del self._templates[template_id]
                
                # ファイルも削除
                file_path = self.template_dir / f"{template_id}.json"
                if file_path.exists():
                    file_path.unlink()
                
                self.logger.info(f"テンプレートを削除しました: {template_id}")
            else:
                self.logger.warning(f"テンプレートが見つかりません: {template_id}")
                
        except Exception as e:
            self.logger.error(f"テンプレート削除エラー: {e}")
            raise

    def get_all_templates(self) -> Dict[str, PromptTemplate]:
        """
        全テンプレートを取得
        
        Returns:
            Dict[str, PromptTemplate]: テンプレート辞書
        """
        return self._templates.copy()

    def get_template_stats(self) -> Dict[str, Any]:
        """
        テンプレート統計情報を取得
        
        Returns:
        Dict[str, Any]: 統計情報
        """
        try:
            stats = {
                'total_templates': len(self._templates),
                'by_type': {},
                'by_language': {},
                'by_role': {},
                'total_variables': 0
            }
            
            for template in self._templates.values():
                # タイプ別統計
                type_key = template.prompt_type.value
                stats['by_type'][type_key] = stats['by_type'].get(type_key, 0) + 1
                
                # 言語別統計
                lang_key = template.language
                stats['by_language'][lang_key] = stats['by_language'].get(lang_key, 0) + 1
                
                # ロール別統計
                role_key = template.role.value
                stats['by_role'][role_key] = stats['by_role'].get(role_key, 0) + 1
                    
                # 変数数の統計
                stats['total_variables'] += len(template.variables)
                
                return stats
                
        except Exception as e:
            self.logger.error(f"テンプレート統計取得エラー: {e}")
            return {}
        
    def export_templates(self, file_path: str, template_ids: Optional[List[str]] = None):
        """
        テンプレートをエクスポート
        
        Args:
            file_path: エクスポート先ファイルパス
            template_ids: エクスポートするテンプレートID一覧（Noneの場合は全て）
        """
        try:
            # エクスポート対象の決定
            if template_ids:
                templates_to_export = {
                    tid: template for tid, template in self._templates.items()
                    if tid in template_ids
                }
            else:
                templates_to_export = self._templates
            
            # 辞書形式に変換
            export_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0',
                    'total_templates': len(templates_to_export)
                },
                'templates': {
                    tid: self._template_to_dict(template)
                    for tid, template in templates_to_export.items()
                }
            }
            
            # ファイルに保存
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"テンプレートをエクスポートしました: {file_path}")
            
        except Exception as e:
            self.logger.error(f"テンプレートエクスポートエラー: {e}")
            raise

    def import_templates(self, file_path: str, overwrite: bool = False):
        """
        テンプレートをインポート
        
        Args:
            file_path: インポート元ファイルパス
            overwrite: 既存テンプレートを上書きするか
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            templates_data = import_data.get('templates', {})
            imported_count = 0
            skipped_count = 0
            
            for template_id, template_data in templates_data.items():
                try:
                    # 既存チェック
                    if template_id in self._templates and not overwrite:
                        self.logger.warning(f"テンプレートが既に存在します（スキップ）: {template_id}")
                        skipped_count += 1
                        continue
                    
                    # テンプレート作成
                    template = self._dict_to_template(template_data)
                    self.register_template(template)
                    imported_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"テンプレートインポートエラー {template_id}: {e}")
                    skipped_count += 1
            
            self.logger.info(f"テンプレートインポート完了: {imported_count}件成功, {skipped_count}件スキップ")
            
        except Exception as e:
            self.logger.error(f"テンプレートインポートエラー: {e}")
            raise

    def create_template_from_conversation(self, 
                                        conversation: List[Dict[str, str]], 
                                        template_id: str,
                                        name: str,
                                        description: str,
                                        prompt_type: PromptType) -> PromptTemplate:
        """
        会話履歴からテンプレートを作成
        
        Args:
            conversation: 会話履歴
            template_id: テンプレートID
            name: テンプレート名
            description: 説明
            prompt_type: プロンプトタイプ
            
        Returns:
            PromptTemplate: 作成されたテンプレート
        """
        try:
            # ユーザーメッセージを抽出してテンプレート化
            user_messages = [
                msg['content'] for msg in conversation
                if msg.get('role') == 'user'
            ]
            
            if not user_messages:
                raise ValueError("ユーザーメッセージが見つかりません")
            
            # 最初のユーザーメッセージをベースにテンプレート作成
            base_content = user_messages[0]
            
            # 変数を自動検出（簡単な実装）
            variables = []
            variable_pattern = r'\{([^}]+)\}'
            found_vars = re.findall(variable_pattern, base_content)
            
            for var_name in set(found_vars):
                variables.append(PromptVariable(
                    name=var_name,
                    description=f"変数: {var_name}",
                    required=True
                ))
            
            # テンプレート作成
            template = PromptTemplate(
                id=template_id,
                name=name,
                description=description,
                prompt_type=prompt_type,
                role=PromptRole.USER,
                template=base_content,
                variables=variables,
                tags=["generated", "conversation"],
                language="ja"
            )
            
            self.register_template(template)
            return template
            
        except Exception as e:
            self.logger.error(f"会話からテンプレート作成エラー: {e}")
            raise

    def optimize_template(self, template_id: str) -> PromptTemplate:
        """
        テンプレートを最適化
        
        Args:
            template_id: テンプレートID
            
        Returns:
            PromptTemplate: 最適化されたテンプレート
        """
        try:
            template = self.get_template(template_id)
            if not template:
                raise ValueError(f"テンプレートが見つかりません: {template_id}")
            
            # テンプレートの最適化処理
            optimized_template = template.template
            
            # 1. 冗長な空白を削除
            optimized_template = re.sub(r'\n\s*\n\s*\n', '\n\n', optimized_template)
            optimized_template = re.sub(r'[ \t]+', ' ', optimized_template)
            
            # 2. 不要な文字を削除
            optimized_template = optimized_template.strip()
            
            # 3. 変数の整理
            used_variables = re.findall(r'\{([^}]+)\}', optimized_template)
            optimized_variables = [
                var for var in template.variables
                if var.name in used_variables
            ]
            
            # 最適化されたテンプレートを作成
            optimized = PromptTemplate(
                id=f"{template.id}_optimized",
                name=f"{template.name} (最適化版)",
                description=f"{template.description} - 最適化済み",
                prompt_type=template.prompt_type,
                role=template.role,
                template=optimized_template,
                variables=optimized_variables,
                tags=template.tags + ["optimized"],
                language=template.language,
                version=template.version,
                metadata=template.metadata.copy()
            )
            
            return optimized
            
        except Exception as e:
            self.logger.error(f"テンプレート最適化エラー: {e}")
            raise

    def validate_template_syntax(self, template: PromptTemplate) -> Dict[str, Any]:
        """
        テンプレート構文を検証
        
        Args:
            template: プロンプトテンプレート
            
        Returns:
            Dict[str, Any]: 検証結果
        """
        try:
            result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'suggestions': []
            }
            
            # 1. 変数構文チェック
            variable_pattern = r'\{([^}]+)\}'
            found_vars = re.findall(variable_pattern, template.template)
            declared_vars = {var.name for var in template.variables}
            
            # 未定義変数チェック
            for var_name in found_vars:
                if var_name not in declared_vars:
                    result['errors'].append(f"未定義変数: {var_name}")
                    result['valid'] = False
            
            # 未使用変数チェック
            for var in template.variables:
                if var.name not in found_vars:
                    result['warnings'].append(f"未使用変数: {var.name}")
            
            # 2. 構文エラーチェック
            try:
                # テスト用変数でフォーマット試行
                test_vars = {var.name: f"test_{var.name}" for var in template.variables}
                template.template.format(**test_vars)
            except KeyError as e:
                result['errors'].append(f"フォーマットエラー: {e}")
                result['valid'] = False
            except Exception as e:
                result['errors'].append(f"構文エラー: {e}")
                result['valid'] = False
            
            # 3. 品質チェック
            if len(template.template) < 10:
                result['warnings'].append("テンプレートが短すぎます")
            
            if not template.description:
                result['warnings'].append("説明が設定されていません")
            
            if not template.tags:
                result['suggestions'].append("タグを設定することを推奨します")
            
            # 4. 変数検証パターンチェック
            for var in template.variables:
                if var.validation_pattern:
                    try:
                        re.compile(var.validation_pattern)
                    except re.error as e:
                        result['errors'].append(f"変数 {var.name} の検証パターンが無効: {e}")
                        result['valid'] = False
            
            return result
            
        except Exception as e:
            self.logger.error(f"テンプレート構文検証エラー: {e}")
            return {
                'valid': False,
                'errors': [str(e)],
                'warnings': [],
                'suggestions': []
            }

    def get_template_usage_stats(self, template_id: str) -> Dict[str, Any]:
        """
        テンプレート使用統計を取得（将来の拡張用）
        
        Args:
            template_id: テンプレートID
            
        Returns:
            Dict[str, Any]: 使用統計
        """
        try:
            # 現在は基本情報のみ返す（将来的に使用ログを追加）
            template = self.get_template(template_id)
            if not template:
                return {}
            
            return {
                'template_id': template_id,
                'name': template.name,
                'type': template.prompt_type.value,
                'created_at': template.created_at.isoformat() if template.created_at else None,
                'updated_at': template.updated_at.isoformat() if template.updated_at else None,
                'variable_count': len(template.variables),
                'template_length': len(template.template),
                'tags': template.tags
            }
            
        except Exception as e:
            self.logger.error(f"テンプレート使用統計取得エラー: {e}")
            return {}

# グローバルテンプレート管理インスタンス
_template_manager_instance: Optional[PromptTemplateManager] = None

def get_prompt_template_manager() -> PromptTemplateManager:
    """
    プロンプトテンプレート管理のシングルトンインスタンスを取得
    
    Returns:
        PromptTemplateManager: テンプレート管理インスタンス
    """
    global _template_manager_instance
    if _template_manager_instance is None:
        _template_manager_instance = PromptTemplateManager()
    return _template_manager_instance

def render_prompt(template_id: str, 
                 variables: Dict[str, Any],
                 validate: bool = True) -> str:
    """
    プロンプトをレンダリング（便利関数）
    
    Args:
        template_id: テンプレートID
        variables: 変数辞書
        validate: 変数検証を行うか
        
    Returns:
        str: レンダリング結果
    """
    manager = get_prompt_template_manager()
    return manager.render_template(template_id, variables, validate)

def create_code_generation_prompt(language: str, 
                                 requirements: str,
                                 additional_context: str = "") -> str:
    """
    コード生成プロンプトを作成（便利関数）
    
    Args:
        language: プログラミング言語
        requirements: 要件
        additional_context: 追加コンテキスト
        
    Returns:
        str: プロンプト
    """
    return render_prompt("code_generation_basic", {
        "language": language,
        "requirements": requirements,
        "additional_context": additional_context
    })

def create_code_review_prompt(language: str, 
                             code: str,
                             focus_areas: str = "") -> str:
    """
    コードレビュープロンプトを作成（便利関数）
    
    Args:
        language: プログラミング言語
        code: レビュー対象コード
        focus_areas: 重点領域
        
    Returns:
        str: プロンプト
    """
    return render_prompt("code_review_comprehensive", {
        "language": language,
        "code": code,
        "focus_areas": focus_areas
    })

def create_debug_prompt(language: str,
                       code: str,
                       error_message: str,
                       error_context: str = "",
                       expected_behavior: str = "",
                       additional_info: str = "") -> str:
    """
    デバッグプロンプトを作成（便利関数）
    
    Args:
        language: プログラミング言語
        code: 問題のあるコード
        error_message: エラーメッセージ
        error_context: エラー発生状況
        expected_behavior: 期待する動作
        additional_info: 追加情報
        
    Returns:
        str: プロンプト
    """
    return render_prompt("debug_assistance_comprehensive", {
        "language": language,
        "code": code,
        "error_message": error_message,
        "error_context": error_context,
        "expected_behavior": expected_behavior,
        "additional_info": additional_info
    })
