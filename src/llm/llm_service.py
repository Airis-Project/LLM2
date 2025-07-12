# src/llm/llm_service.py
"""
LLM中間サービスクラス
プロンプトテンプレート管理、レスポンス解析、LLMクライアント統合を提供
低レベルLLMクライアントと高レベルUIサービス間の仲介層
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json

from .base_llm import BaseLLM, LLMMessage, LLMResponse, LLMConfig, LLMRole, LLMStatus
from .llm_factory import get_llm_factory, LLMFactory
from .prompt_templates import PromptTemplateManager, get_prompt_template_manager
from .response_parser import ResponseParser, get_response_parser
from ..core.logger import get_logger
from ..core.event_system import Event
from ..utils.validation_utils import ValidationUtils
from ..utils.text_utils import TextUtils

logger = get_logger(__name__)

class TaskType(Enum):
    """タスクタイプ定義"""
    GENERAL = "general"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CODE_REFACTOR = "code_refactor"
    DOCUMENTATION = "documentation"
    TRANSLATION = "translation"
    ANALYSIS = "analysis"
    CHAT = "chat"

class TaskPriority(Enum):
    """タスク優先度定義"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class LLMTask:
    """LLMタスククラス"""
    id: str
    task_type: TaskType
    priority: TaskPriority
    prompt: str
    template_name: Optional[str] = None
    template_vars: Dict[str, Any] = field(default_factory=dict)
    provider: Optional[str] = None
    model: Optional[str] = None
    config: Optional[LLMConfig] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'task_type': self.task_type.value,
            'priority': self.priority.value,
            'prompt': self.prompt,
            'template_name': self.template_name,
            'template_vars': self.template_vars,
            'provider': self.provider,
            'model': self.model,
            'config': self.config.to_dict() if self.config else None,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class LLMResult:
    """LLM結果クラス"""
    task_id: str
    success: bool
    content: str = ""
    parsed_content: Dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[LLMResponse] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    tokens_used: int = 0
    cost_estimate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'task_id': self.task_id,
            'success': self.success,
            'content': self.content,
            'parsed_content': self.parsed_content,
            'raw_response': self.raw_response.to_dict() if self.raw_response else None,
            'error': self.error,
            'execution_time': self.execution_time,
            'tokens_used': self.tokens_used,
            'cost_estimate': self.cost_estimate,
            'metadata': self.metadata,
            'completed_at': self.completed_at.isoformat()
        }

# 遅延インポート用の関数
def get_config():
    """設定を遅延インポートで取得"""
    try:
        from ..core.config_manager import get_config
        return get_config()
    except ImportError:
        logger.warning("設定管理が利用できません")
        return {}

def get_event_system():
    """イベントシステムを遅延インポートで取得"""
    try:
        from ..core.event_system import get_event_system
        return get_event_system()
    except ImportError:
        logger.warning("イベントシステムが利用できません")
        return None

class LLMServiceCore:
    """LLM中間サービスコアクラス"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            config: サービス設定
        """
        self.logger = get_logger(self.__class__.__name__)
        
        # 設定
        self.config = config or {}
        self.app_config = get_config()
        
        # コンポーネント初期化
        self.llm_factory = get_llm_factory()
        self.prompt_manager = PromptTemplateManager()
        self.response_parser = ResponseParser()
        
        # ユーティリティ
        self.validation_utils = ValidationUtils()
        self.text_utils = TextUtils()
        
        # イベントシステム
        self.event_system = get_event_system()
        
        # 統計情報
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'average_response_time': 0.0,
            'start_time': datetime.now()
        }
        
        # アクティブなクライアント
        self.active_clients: Dict[str, BaseLLM] = {}
        
        # タスク履歴
        self.task_history: List[LLMTask] = []
        self.result_history: List[LLMResult] = []
        
        self.logger.info("LLM中間サービスを初期化しました")
    
    async def execute_task_async(self, task: LLMTask) -> LLMResult:
        """
        タスクを非同期実行
        
        Args:
            task: 実行するタスク
            
        Returns:
            LLMResult: 実行結果
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"タスク実行開始: {task.id} ({task.task_type.value})")
            
            # 統計更新
            self.stats['total_requests'] += 1
            
            # タスク履歴に追加
            self.task_history.append(task)
            
            # イベント発行
            self.event_system.emit(Event(
                'llm_task_started',
                {'task_id': task.id, 'task_type': task.task_type.value}
            ))
            
            # プロンプト準備
            prepared_prompt = await self._prepare_prompt(task)
            
            # LLMクライアント取得
            client = await self._get_client(task)
            
            # メッセージ作成
            messages = self._create_messages(prepared_prompt, task)
            
            # LLM実行
            response = await client.generate_async(messages, task.config)
            
            # レスポンス解析
            parsed_content = await self._parse_response(response, task)
            
            # 実行時間計算
            execution_time = time.time() - start_time
            
            # 結果作成
            result = LLMResult(
                task_id=task.id,
                success=True,
                content=response.content,
                parsed_content=parsed_content,
                raw_response=response,
                execution_time=execution_time,
                tokens_used=response.usage.get('total_tokens', 0),
                cost_estimate=self._estimate_cost(response),
                metadata={
                    'provider': task.provider,
                    'model': response.model,
                    'finish_reason': response.finish_reason
                }
            )
            
            # 統計更新
            self._update_stats(result, True)
            
            # 結果履歴に追加
            self.result_history.append(result)
            
            # イベント発行
            self.event_system.emit(Event(
                'llm_task_completed',
                {'task_id': task.id, 'success': True, 'execution_time': execution_time}
            ))
            
            self.logger.info(f"タスク実行完了: {task.id} ({execution_time:.2f}s)")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(f"タスク実行エラー: {task.id} - {error_msg}")
            
            # エラー結果作成
            result = LLMResult(
                task_id=task.id,
                success=False,
                error=error_msg,
                execution_time=execution_time,
                metadata={'provider': task.provider}
            )
            
            # 統計更新
            self._update_stats(result, False)
            
            # 結果履歴に追加
            self.result_history.append(result)
            
            # イベント発行
            self.event_system.emit(Event(
                'llm_task_failed',
                {'task_id': task.id, 'error': error_msg, 'execution_time': execution_time}
            ))
            
            return result
    
    def execute_task(self, task: LLMTask) -> LLMResult:
        """
        タスクを同期実行
        
        Args:
            task: 実行するタスク
            
        Returns:
            LLMResult: 実行結果
        """
        try:
            # 新しいイベントループを作成して実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.execute_task_async(task))
            finally:
                loop.close()
        except Exception as e:
            self.logger.error(f"同期タスク実行エラー: {e}")
            raise
    
    async def _prepare_prompt(self, task: LLMTask) -> str:
        """
        プロンプトを準備
        
        Args:
            task: タスク
            
        Returns:
            str: 準備されたプロンプト
        """
        try:
            if task.template_name:
                # テンプレートを使用
                template = await self.prompt_manager.get_template_async(task.template_name)
                if template:
                    return template.render(**task.template_vars)
                else:
                    self.logger.warning(f"テンプレートが見つかりません: {task.template_name}")
            
            # 直接プロンプトを使用
            return task.prompt
            
        except Exception as e:
            self.logger.error(f"プロンプト準備エラー: {e}")
            return task.prompt
    
    async def _get_client(self, task: LLMTask) -> BaseLLM:
        """
        LLMクライアントを取得
        
        Args:
            task: タスク
            
        Returns:
            BaseLLM: LLMクライアント
        """
        try:
            provider = task.provider or self._get_default_provider(task.task_type)
            client_key = f"{provider}_{task.model or 'default'}"
            
            # キャッシュされたクライアントを確認
            if client_key in self.active_clients:
                client = self.active_clients[client_key]
                if client.is_available():
                    return client
                else:
                    # 利用不可の場合は削除
                    del self.active_clients[client_key]
            
            # 新しいクライアントを作成
            config = task.config or self._get_default_config(provider, task.model)
            client = await self.llm_factory.create_client_async(provider, config)
            
            # キャッシュに保存
            self.active_clients[client_key] = client
            
            return client
            
        except Exception as e:
            self.logger.error(f"クライアント取得エラー: {e}")
            raise
    
    def _create_messages(self, prompt: str, task: LLMTask) -> List[LLMMessage]:
        """
        メッセージリストを作成
        
        Args:
            prompt: プロンプト
            task: タスク
            
        Returns:
            List[LLMMessage]: メッセージリスト
        """
        try:
            messages = []
            
            # システムプロンプトを追加
            system_prompt = self._get_system_prompt(task.task_type)
            if system_prompt:
                messages.append(LLMMessage(
                    role=LLMRole.SYSTEM,
                    content=system_prompt,
                    metadata={'task_type': task.task_type.value}
                ))
            
            # ユーザープロンプトを追加
            messages.append(LLMMessage(
                role=LLMRole.USER,
                content=prompt,
                metadata={
                    'task_id': task.id,
                    'task_type': task.task_type.value,
                    'priority': task.priority.value
                }
            ))
            
            return messages
            
        except Exception as e:
            self.logger.error(f"メッセージ作成エラー: {e}")
            raise
    
    async def _parse_response(self, response: LLMResponse, task: LLMTask) -> Dict[str, Any]:
        """
        レスポンスを解析
        
        Args:
            response: LLMレスポンス
            task: タスク
            
        Returns:
            Dict[str, Any]: 解析結果
        """
        try:
            # タスクタイプに応じた解析
            if task.task_type == TaskType.CODE_GENERATION:
                return await self.response_parser.parse_code_async(response.content)
            elif task.task_type == TaskType.CODE_REVIEW:
                return await self.response_parser.parse_review_async(response.content)
            elif task.task_type == TaskType.DOCUMENTATION:
                return await self.response_parser.parse_documentation_async(response.content)
            else:
                return await self.response_parser.parse_general_async(response.content)
                
        except Exception as e:
            self.logger.error(f"レスポンス解析エラー: {e}")
            return {'raw_content': response.content}
    
    def _get_default_provider(self, task_type: TaskType) -> str:
        """
        タスクタイプに応じたデフォルトプロバイダーを取得
        
        Args:
            task_type: タスクタイプ
            
        Returns:
            str: プロバイダー名
        """
        try:
            # 設定からタスクタイプ別プロバイダーを取得
            task_providers = self.app_config.get('llm', {}).get('task_providers', {})
            
            provider = task_providers.get(task_type.value)
            if provider:
                return provider
            
            # デフォルトプロバイダーを取得
            return self.llm_factory.get_default_provider() or 'openai'
            
        except Exception as e:
            self.logger.error(f"デフォルトプロバイダー取得エラー: {e}")
            return 'openai'
    
    def _get_default_config(self, provider: str, model: Optional[str] = None) -> LLMConfig:
        """
        デフォルト設定を取得
        
        Args:
            provider: プロバイダー名
            model: モデル名
            
        Returns:
            LLMConfig: LLM設定
        """
        try:
            # 設定ファイルから取得
            provider_config = self.app_config.get('llm', {}).get(provider, {})
            
            config = LLMConfig(
                model=model or provider_config.get('model', ''),
                temperature=provider_config.get('temperature', 0.7),
                max_tokens=provider_config.get('max_tokens', 2048),
                top_p=provider_config.get('top_p', 1.0),
                frequency_penalty=provider_config.get('frequency_penalty', 0.0),
                presence_penalty=provider_config.get('presence_penalty', 0.0),
                stop_sequences=provider_config.get('stop_sequences', []),
                timeout=provider_config.get('timeout', 30.0),
                retry_count=provider_config.get('retry_count', 3),
                retry_delay=provider_config.get('retry_delay', 1.0)
            )
            
            return config
            
        except Exception as e:
            self.logger.error(f"デフォルト設定取得エラー: {e}")
            return LLMConfig()
    
    def _get_system_prompt(self, task_type: TaskType) -> Optional[str]:
        """
        タスクタイプに応じたシステムプロンプトを取得
        
        Args:
            task_type: タスクタイプ
            
        Returns:
            Optional[str]: システムプロンプト
        """
        try:
            system_prompts = {
                TaskType.CODE_GENERATION: "あなたは優秀なソフトウェア開発者です。高品質で読みやすく、保守しやすいコードを生成してください。",
                TaskType.CODE_REVIEW: "あなたは経験豊富なコードレビュアーです。コードの品質、セキュリティ、パフォーマンスの観点から詳細なレビューを行ってください。",
                TaskType.CODE_REFACTOR: "あなたはリファクタリングの専門家です。コードの可読性、保守性、パフォーマンスを向上させる改善案を提案してください。",
                TaskType.DOCUMENTATION: "あなたは技術文書作成の専門家です。明確で分かりやすく、包括的なドキュメントを作成してください。",
                TaskType.TRANSLATION: "あなたは多言語翻訳の専門家です。文脈を理解し、自然で正確な翻訳を提供してください。",
                TaskType.ANALYSIS: "あなたは分析の専門家です。データや情報を詳細に分析し、洞察に富んだ結果を提供してください。"
            }
            
            return system_prompts.get(task_type)
            
        except Exception as e:
            self.logger.error(f"システムプロンプト取得エラー: {e}")
            return None
    
    def _estimate_cost(self, response: LLMResponse) -> float:
        """
        コストを概算
        
        Args:
            response: LLMレスポンス
            
        Returns:
            float: 概算コスト
        """
        try:
            # 簡易的なコスト計算
            tokens = response.usage.get('total_tokens', 0)
            
            # モデル別の概算料金（USD per 1K tokens）
            model_costs = {
                'gpt-4': 0.03,
                'gpt-3.5-turbo': 0.002,
                'claude-3-opus': 0.015,
                'claude-3-sonnet': 0.003,
                'claude-3-haiku': 0.00025
            }
            
            # デフォルト料金
            cost_per_1k = 0.002
            
            # モデル名からコストを取得
            for model_name, cost in model_costs.items():
                if model_name in response.model.lower():
                    cost_per_1k = cost
                    break
            
            return (tokens / 1000) * cost_per_1k
            
        except Exception as e:
            self.logger.error(f"コスト概算エラー: {e}")
            return 0.0
    
    def _update_stats(self, result: LLMResult, success: bool):
        """
        統計情報を更新
        
        Args:
            result: 実行結果
            success: 成功フラグ
        """
        try:
            if success:
                self.stats['successful_requests'] += 1
                self.stats['total_tokens'] += result.tokens_used
                self.stats['total_cost'] += result.cost_estimate
            else:
                self.stats['failed_requests'] += 1
            
            # 平均応答時間を更新
            total_requests = self.stats['successful_requests'] + self.stats['failed_requests']
            if total_requests > 0:
                total_time = sum(r.execution_time for r in self.result_history)
                self.stats['average_response_time'] = total_time / total_requests
            
        except Exception as e:
            self.logger.error(f"統計更新エラー: {e}")
    
    def create_task(self, 
                   task_type: Union[TaskType, str],
                   prompt: str,
                   priority: Union[TaskPriority, str] = TaskPriority.NORMAL,
                   template_name: Optional[str] = None,
                   template_vars: Optional[Dict[str, Any]] = None,
                   provider: Optional[str] = None,
                   model: Optional[str] = None,
                   config: Optional[LLMConfig] = None,
                   **kwargs) -> LLMTask:
        """
        タスクを作成
        
        Args:
            task_type: タスクタイプ
            prompt: プロンプト
            priority: 優先度
            template_name: テンプレート名
            template_vars: テンプレート変数
            provider: プロバイダー名
            model: モデル名
            config: LLM設定
            **kwargs: 追加メタデータ
            
        Returns:
            LLMTask: 作成されたタスク
        """
        try:
            # タスクIDを生成
            task_id = f"task_{int(time.time() * 1000)}_{len(self.task_history)}"
            
            # Enumに変換
            if isinstance(task_type, str):
                task_type = TaskType(task_type)
            if isinstance(priority, str):
                priority = TaskPriority(priority)
            
            # タスクを作成
            task = LLMTask(
                id=task_id,
                task_type=task_type,
                priority=priority,
                prompt=prompt,
                template_name=template_name,
                template_vars=template_vars or {},
                provider=provider,
                model=model,
                config=config,
                metadata=kwargs
            )
            
            self.logger.info(f"タスクを作成しました: {task_id} ({task_type.value})")
            
            return task
            
        except Exception as e:
            self.logger.error(f"タスク作成エラー: {e}")
            raise
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        サービス統計を取得
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
            
            stats = self.stats.copy()
            stats.update({
                'uptime_seconds': uptime,
                'success_rate': (
                    self.stats['successful_requests'] / max(self.stats['total_requests'], 1)
                ),
                'requests_per_minute': (
                    self.stats['total_requests'] / max(uptime / 60, 1)
                ),
                'active_clients': len(self.active_clients),
                'task_history_size': len(self.task_history),
                'result_history_size': len(self.result_history)
            })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"統計取得エラー: {e}")
            return {}
    
    def get_available_providers(self) -> List[str]:
        """利用可能なプロバイダーを取得"""
        return self.llm_factory.get_available_providers()
    
    def get_available_models(self, provider: Optional[str] = None) -> List[str]:
        """利用可能なモデルを取得"""
        try:
            if provider:
                provider_info = self.llm_factory.get_provider_info(provider)
                return provider_info.supported_models if provider_info else []
            else:
                # 全プロバイダーのモデルを取得
                all_models = []
                for provider_name in self.get_available_providers():
                    provider_info = self.llm_factory.get_provider_info(provider_name)
                    if provider_info:
                        all_models.extend(provider_info.supported_models)
                return list(set(all_models))
                
        except Exception as e:
            self.logger.error(f"モデル一覧取得エラー: {e}")
            return []
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            # アクティブクライアントをクリーンアップ
            for client in self.active_clients.values():
                if hasattr(client, 'cleanup'):
                    client.cleanup()
            
            self.active_clients.clear()
            
            self.logger.info("LLM中間サービスをクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")

# グローバルインスタンス
_service_instance: Optional[LLMServiceCore] = None

def get_llm_service() -> LLMServiceCore:
    """
    LLM中間サービスのシングルトンインスタンスを取得
    
    Returns:
        LLMServiceCore: サービスインスタンス
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = LLMServiceCore()
    return _service_instance

# 便利関数
async def execute_llm_task_async(
    task_type: Union[TaskType, str],
    prompt: str,
    **kwargs
) -> LLMResult:
    """
    LLMタスクを非同期実行（便利関数）
    
    Args:
        task_type: タスクタイプ
        prompt: プロンプト
        **kwargs: 追加パラメータ
        
    Returns:
        LLMResult: 実行結果
    """
    service = get_llm_service()
    task = service.create_task(task_type, prompt, **kwargs)
    return await service.execute_task_async(task)

def execute_llm_task(
    task_type: Union[TaskType, str],
    prompt: str,
    **kwargs
) -> LLMResult:
    """
    LLMタスクを同期実行（便利関数）
    
    Args:
        task_type: タスクタイプ
        prompt: プロンプト
        **kwargs: 追加パラメータ
        
    Returns:
        LLMResult: 実行結果
    """
    service = get_llm_service()
    task = service.create_task(task_type, prompt, **kwargs)
    return service.execute_task(task)
