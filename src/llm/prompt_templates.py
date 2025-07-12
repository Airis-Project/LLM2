# src/llm/prompt_templates.py
"""
プロンプトテンプレート管理モジュール
様々なタスクに対応したプロンプトテンプレートを管理・生成する
"""

import os
import json
import yaml
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import re
from datetime import datetime

from ..core.logger import get_logger
#from ..core.config_manager import get_config

def get_config(*args, **kwargs):
    from ..core.config_manager import get_config
    return get_config(*args, **kwargs)


logger = get_logger(__name__)

class TemplateCategory(Enum):
    """テンプレートカテゴリ"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUG_ASSISTANCE = "debug_assistance"
    DOCUMENTATION = "documentation"
    EXPLANATION = "explanation"
    TRANSLATION = "translation"
    GENERAL = "general"
    CUSTOM = "custom"

@dataclass
class TemplateVariable:
    """テンプレート変数定義"""
    name: str
    description: str
    type: str = "string"  # string, number, boolean, list
    required: bool = True
    default_value: Optional[Any] = None
    validation_pattern: Optional[str] = None
    options: Optional[List[str]] = None  # 選択肢がある場合

@dataclass
class PromptTemplate:
    """プロンプトテンプレート"""
    id: str
    name: str
    description: str
    category: TemplateCategory
    template: str
    variables: List[TemplateVariable]
    language: str = "ja"
    version: str = "1.0"
    author: str = "system"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class PromptTemplateManager:
    """プロンプトテンプレート管理クラス"""
    
    def __init__(self, templates_dir: str = "templates"):
        """
        初期化
        
        Args:
            templates_dir: テンプレートディレクトリのパス
        """
        self.logger = get_logger(self.__class__.__name__)
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, PromptTemplate] = {}
        
        # テンプレートディレクトリを作成
        self.templates_dir.mkdir(exist_ok=True)
        
        # デフォルトテンプレートを初期化
        self._initialize_default_templates()
        
        # 既存のテンプレートを読み込み
        self._load_templates()
        
        self.logger.info(f"PromptTemplateManager を初期化しました: {len(self.templates)} テンプレート")
    
    def _initialize_default_templates(self):
        """デフォルトテンプレートを初期化"""
        try:
            default_templates = self._get_default_templates()
            
            for template in default_templates:
                self.templates[template.id] = template
                
                # ファイルに保存
                self._save_template_to_file(template)
            
            self.logger.info(f"{len(default_templates)} 個のデフォルトテンプレートを初期化しました")
            
        except Exception as e:
            self.logger.error(f"デフォルトテンプレート初期化エラー: {e}")
    
    def _get_default_templates(self) -> List[PromptTemplate]:
        """デフォルトテンプレートを取得"""
        templates = []
        
        # コード生成テンプレート
        templates.append(PromptTemplate(
            id="code_generation_basic",
            name="基本的なコード生成",
            description="指定された要件に基づいてコードを生成します",
            category=TemplateCategory.CODE_GENERATION,
            template="""以下の要件に基づいて、{language}でコードを生成してください。

    要件:
    {requirements}

    追加の条件:
    - コードにはコメントを含めてください
    - エラーハンドリングを考慮してください
    - ベストプラクティスに従ってください
    - 実用的で動作するコードにしてください

    {additional_instructions}

    コードを生成してください:""",
                variables=[
                    TemplateVariable("language", "プログラミング言語", "string", True, "Python"),
                    TemplateVariable("requirements", "要件の詳細", "string", True),
                    TemplateVariable("additional_instructions", "追加の指示", "string", False, "")
                ]
            ))
            
            # コードレビューテンプレート
        templates.append(PromptTemplate(
                id="code_review_comprehensive",
                name="包括的なコードレビュー",
                description="コードの品質、セキュリティ、パフォーマンスを総合的にレビューします",
                category=TemplateCategory.CODE_REVIEW,
                template="""以下のコードをレビューしてください。

    コード:
    ```{language}
    {code}
    レビュー観点:

    コードの品質と可読性
    セキュリティの問題
    パフォーマンスの改善点
    ベストプラクティスの遵守
    バグの可能性
    保守性の観点
    {specific_concerns}

    詳細なレビュー結果を提供してください:""",
    variables=[
    TemplateVariable("language", "プログラミング言語", "string", True, "python"),
    TemplateVariable("code", "レビュー対象のコード", "string", True),
    TemplateVariable("specific_concerns", "特定の懸念事項", "string", False, "")
    ]
    ))
        # デバッグ支援テンプレート
        templates.append(PromptTemplate(
                id="debug_assistance",
                name="デバッグ支援",
                description="エラーの原因を特定し、解決策を提案します",
                category=TemplateCategory.DEBUG_ASSISTANCE,
            template="""以下のエラーについて、原因を特定し解決策を提案してください。
    エラー情報:
    {error_message}

    関連するコード:
    {code}
    実行環境:
    {environment}

    期待する動作:
    {expected_behavior}

    実際の動作:
    {actual_behavior}

    詳細な分析と解決策を提供してください:""",
    variables=[
    TemplateVariable("error_message", "エラーメッセージ", "string", True),
    TemplateVariable("language", "プログラミング言語", "string", True, "python"),
    TemplateVariable("code", "関連するコード", "string", True),
    TemplateVariable("environment", "実行環境", "string", False, ""),
    TemplateVariable("expected_behavior", "期待する動作", "string", False, ""),
    TemplateVariable("actual_behavior", "実際の動作", "string", False, "")
    ]
    ))
        # ドキュメント生成テンプレート
        templates.append(PromptTemplate(
            id="documentation_generation",
            name="ドキュメント生成",
            description="コードのドキュメントを自動生成します",
            category=TemplateCategory.DOCUMENTATION,
            template="""以下のコードについて、詳細なドキュメントを生成してください。
    コード:
    {code}
    ドキュメントに含める内容:

    概要と目的
    関数/クラスの説明
    パラメータの詳細
    戻り値の説明
    使用例
    注意事項
    {documentation_style}

    Markdown形式でドキュメントを生成してください:""",
    variables=[
    TemplateVariable("language", "プログラミング言語", "string", True, "python"),
    TemplateVariable("code", "ドキュメント対象のコード", "string", True),
    TemplateVariable("documentation_style", "ドキュメントスタイル", "string", False, "標準的なAPIドキュメント形式")
    ]
    ))
        # コード説明テンプレート
        templates.append(PromptTemplate(
            id="code_explanation",
            name="コード説明",
            description="コードの動作原理を詳しく説明します",
            category=TemplateCategory.EXPLANATION,
            template="""以下のコードについて、動作原理を詳しく説明してください。
    コード:
    {code}
    説明レベル: {explanation_level}

    以下の観点から説明してください:

    コードの全体的な流れ
    各部分の役割と機能
    使用されているアルゴリズムや技術
    重要なポイントや注意点
    改善の余地があれば提案
    {specific_questions}

    わかりやすく詳細な説明を提供してください:""",
    variables=[
    TemplateVariable("language", "プログラミング言語", "string", True, "python"),
    TemplateVariable("code", "説明対象のコード", "string", True),
    TemplateVariable("explanation_level", "説明レベル", "string", False, "中級者向け",
    options=["初心者向け", "中級者向け", "上級者向け"]),
    TemplateVariable("specific_questions", "特定の質問", "string", False, "")
    ]
    ))
        # 翻訳テンプレート
        templates.append(PromptTemplate(
            id="code_translation",
            name="コード翻訳",
            description="コードを他の言語に翻訳します",
            category=TemplateCategory.TRANSLATION,
            template="""以下の{source_language}コードを{target_language}に翻訳してください。
    元のコード:
    {code}
    翻訳時の注意点:

    機能を完全に保持してください
    ターゲット言語のベストプラクティスに従ってください
    適切なエラーハンドリングを含めてください
    コメントも翻訳してください
    {additional_requirements}

    翻訳されたコードを提供してください:""",
    variables=[
    TemplateVariable("source_language", "元の言語", "string", True),
    TemplateVariable("target_language", "翻訳先の言語", "string", True),
    TemplateVariable("code", "翻訳対象のコード", "string", True),
    TemplateVariable("additional_requirements", "追加要件", "string", False, "")
    ]
    ))
        # 一般的な質問テンプレート
        templates.append(PromptTemplate(
            id="general_question",
            name="一般的な質問",
            description="プログラミングに関する一般的な質問に回答します",
            category=TemplateCategory.GENERAL,
            template="""以下の質問について、詳しく回答してください。
    質問: {question}

    回答の観点:
    {answer_perspective}

    具体例やコード例があれば含めてください。
    実用的で理解しやすい回答を提供してください:""",
    variables=[
    TemplateVariable("question", "質問内容", "string", True),
    TemplateVariable("answer_perspective", "回答の観点", "string", False, "初心者にもわかりやすく")
    ]
    ))
        return templates

def _load_templates(self):
    """既存のテンプレートファイルを読み込み"""
    try:
        template_files = list(self.templates_dir.glob("*.json")) + list(self.templates_dir.glob("*.yaml"))
        
        for file_path in template_files:
            try:
                template = self._load_template_from_file(file_path)
                if template:
                    self.templates[template.id] = template
                    
            except Exception as e:
                self.logger.error(f"テンプレートファイル読み込みエラー {file_path}: {e}")
        
        self.logger.info(f"{len(template_files)} 個のテンプレートファイルを処理しました")
        
    except Exception as e:
        self.logger.error(f"テンプレート読み込みエラー: {e}")

def _load_template_from_file(self, file_path: Path) -> Optional[PromptTemplate]:
    """ファイルからテンプレートを読み込み"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix == '.json':
                data = json.load(f)
            else:  # yaml
                data = yaml.safe_load(f)
        
        # 変数リストを TemplateVariable オブジェクトに変換
        variables = []
        for var_data in data.get('variables', []):
            variables.append(TemplateVariable(**var_data))
        
        # datetime フィールドを処理
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        template = PromptTemplate(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            category=TemplateCategory(data['category']),
            template=data['template'],
            variables=variables,
            language=data.get('language', 'ja'),
            version=data.get('version', '1.0'),
            author=data.get('author', 'unknown'),
            created_at=created_at,
            updated_at=updated_at,
            tags=data.get('tags', [])
        )
        
        return template
        
    except Exception as e:
        self.logger.error(f"テンプレートファイル解析エラー {file_path}: {e}")
        return None

def _save_template_to_file(self, template: PromptTemplate):
    """テンプレートをファイルに保存"""
    try:
        file_path = self.templates_dir / f"{template.id}.json"
        
        # TemplateVariable を辞書に変換
        template_dict = asdict(template)
        template_dict['category'] = template.category.value
        
        # datetime を文字列に変換
        if template_dict['created_at']:
            template_dict['created_at'] = template.created_at.isoformat()
        if template_dict['updated_at']:
            template_dict['updated_at'] = template.updated_at.isoformat()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(template_dict, f, ensure_ascii=False, indent=2)
        
    except Exception as e:
        self.logger.error(f"テンプレート保存エラー {template.id}: {e}")

def get_template(self, template_id: str) -> Optional[PromptTemplate]:
    """
    テンプレートを取得
    
    Args:
        template_id: テンプレートID
        
    Returns:
        PromptTemplate: テンプレート（存在しない場合はNone）
    """
    return self.templates.get(template_id)

def get_all_templates(self) -> Dict[str, PromptTemplate]:
    """すべてのテンプレートを取得"""
    return self.templates.copy()

def get_templates_by_category(self, category: TemplateCategory) -> Dict[str, PromptTemplate]:
    """
    カテゴリ別にテンプレートを取得
    
    Args:
        category: テンプレートカテゴリ
        
    Returns:
        Dict[str, PromptTemplate]: カテゴリに属するテンプレート
    """
    return {
        template_id: template 
        for template_id, template in self.templates.items()
        if template.category == category
    }

def search_templates(self, query: str) -> Dict[str, PromptTemplate]:
    """
    テンプレートを検索
    
    Args:
        query: 検索クエリ
        
    Returns:
        Dict[str, PromptTemplate]: 検索結果
    """
    try:
        query_lower = query.lower()
        results = {}
        
        for template_id, template in self.templates.items():
            # 名前、説明、タグで検索
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                results[template_id] = template
        
        return results
        
    except Exception as e:
        self.logger.error(f"テンプレート検索エラー: {e}")
        return {}

def render_template(self, template_id: str, variables: Dict[str, Any]) -> str:
    """
    テンプレートを変数で置換してレンダリング
    
    Args:
        template_id: テンプレートID
        variables: 変数の値
        
    Returns:
        str: レンダリングされたプロンプト
    """
    try:
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"テンプレートが見つかりません: {template_id}")
        
        # 必須変数のチェック
        self._validate_variables(template, variables)
        
        # デフォルト値を設定
        render_variables = self._apply_default_values(template, variables)
        
        # テンプレートをレンダリング
        rendered = template.template.format(**render_variables)
        
        return rendered
        
    except Exception as e:
        self.logger.error(f"テンプレートレンダリングエラー {template_id}: {e}")
        raise

def _validate_variables(self, template: PromptTemplate, variables: Dict[str, Any]):
    """変数の妥当性を検証"""
    try:
        for var in template.variables:
            if var.required and var.name not in variables:
                raise ValueError(f"必須変数が不足しています: {var.name}")
            
            if var.name in variables:
                value = variables[var.name]
                
                # 型チェック
                if var.type == "number" and not isinstance(value, (int, float)):
                    try:
                        variables[var.name] = float(value)
                    except ValueError:
                        raise ValueError(f"変数 {var.name} は数値である必要があります")
                
                elif var.type == "boolean" and not isinstance(value, bool):
                    if isinstance(value, str):
                        variables[var.name] = value.lower() in ['true', '1', 'yes', 'on']
                    else:
                        variables[var.name] = bool(value)
                
                # 選択肢チェック
                if var.options and value not in var.options:
                    raise ValueError(f"変数 {var.name} の値は {var.options} のいずれかである必要があります")
                
                # パターンチェック
                if var.validation_pattern and isinstance(value, str):
                    if not re.match(var.validation_pattern, value):
                        raise ValueError(f"変数 {var.name} の値がパターンに一致しません: {var.validation_pattern}")
        
    except Exception as e:
        self.logger.error(f"変数検証エラー: {e}")
        raise

def _apply_default_values(self, template: PromptTemplate, variables: Dict[str, Any]) -> Dict[str, Any]:
    """デフォルト値を適用"""
    try:
        result = variables.copy()
        
        for var in template.variables:
            if var.name not in result and var.default_value is not None:
                result[var.name] = var.default_value
        
        return result
        
    except Exception as e:
        self.logger.error(f"デフォルト値適用エラー: {e}")
        return variables

def add_template(self, template: PromptTemplate) -> bool:
    """
    新しいテンプレートを追加
    
    Args:
        template: 追加するテンプレート
        
    Returns:
        bool: 追加が成功した場合True
    """
    try:
        # IDの重複チェック
        if template.id in self.templates:
            raise ValueError(f"テンプレートID '{template.id}' は既に存在します")
        
        # テンプレートを追加
        self.templates[template.id] = template
        
        # ファイルに保存
        self._save_template_to_file(template)
        
        self.logger.info(f"テンプレートを追加しました: {template.id}")
        return True
        
    except Exception as e:
        self.logger.error(f"テンプレート追加エラー: {e}")
        return False

def update_template(self, template: PromptTemplate) -> bool:
    """
    既存のテンプレートを更新
    
    Args:
        template: 更新するテンプレート
        
    Returns:
        bool: 更新が成功した場合True
    """
    try:
        if template.id not in self.templates:
            raise ValueError(f"テンプレートが見つかりません: {template.id}")
        
        # 更新日時を設定
        template.updated_at = datetime.now()
        
        # テンプレートを更新
        self.templates[template.id] = template
        
        # ファイルに保存
        self._save_template_to_file(template)
        
        self.logger.info(f"テンプレートを更新しました: {template.id}")
        return True
        
    except Exception as e:
        self.logger.error(f"テンプレート更新エラー: {e}")
        return False

def delete_template(self, template_id: str) -> bool:
    """
    テンプレートを削除
    
    Args:
        template_id: 削除するテンプレートID
        
    Returns:
        bool: 削除が成功した場合True
    """
    try:
        if template_id not in self.templates:
            raise ValueError(f"テンプレートが見つかりません: {template_id}")
        
        # メモリから削除
        del self.templates[template_id]
        
        # ファイルを削除
        file_path = self.templates_dir / f"{template_id}.json"
        if file_path.exists():
            file_path.unlink()
        
        self.logger.info(f"テンプレートを削除しました: {template_id}")
        return True
        
    except Exception as e:
        self.logger.error(f"テンプレート削除エラー: {e}")
        return False
_template_manager_instance = None

def get_prompt_template_manager() -> PromptTemplateManager:
    """PromptTemplateManager のシングルトンインスタンスを取得"""
    global _template_manager_instance
    if _template_manager_instance is None:
        _template_manager_instance = PromptTemplateManager()
    return _template_manager_instance

def create_code_generation_prompt(language: str, requirements: str,
    additional_instructions: str = "") -> str:
    """
    コード生成プロンプトを作成する便利関数
    Args:
        language: プログラミング言語
        requirements: 要件
        additional_instructions: 追加の指示
        
    Returns:
        str: 生成されたプロンプト
    """
    manager = get_prompt_template_manager()
    return manager.render_template("code_generation_basic", {
        "language": language,
        "requirements": requirements,
        "additional_instructions": additional_instructions
    })
def create_code_review_prompt(language: str, code: str,
    specific_concerns: str = "") -> str:
    """
    コードレビュープロンプトを作成する便利関数
    Args:
        language: プログラミング言語
        code: レビュー対象のコード
        specific_concerns: 特定の懸念事項
        
    Returns:
        str: 生成されたプロンプト
    """
    manager = get_prompt_template_manager()
    return manager.render_template("code_review_comprehensive", {
        "language": language,
        "code": code,
        "specific_concerns": specific_concerns
    })
