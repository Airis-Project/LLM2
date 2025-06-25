# 改良版LLMクライアント
#python src/llm_client_v2.py
# llm_client_v2.pyを絶対インポートに修正
# -*- coding: utf-8 -*-
"""
拡張LLMクライアント v2.0
スマートモデル選択、性能監視、エラーハンドリングを統合
"""

import time
import logging
import sys
import os
from typing import Dict, Any, Optional, List

# プロジェクトルートをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 絶対インポート
from src.model_selector import SmartModelSelector, TaskType
from src.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

class EnhancedLLMClient:
    """拡張LLMクライアント - スマート機能統合版"""
    
    def __init__(self, config_path: Optional[str] = None):
        """クライアント初期化"""
        self.model_selector = SmartModelSelector(config_path)
        self.ollama_client = OllamaClient()
        
        # 性能監視
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'model_usage': {},
            'error_counts': {}
        }
        
        logger.info("拡張LLMクライアントを初期化しました")
    
    def generate_code(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        priority: str = "balanced",
        **kwargs
    ) -> Dict[str, Any]:
        """
        コード生成（スマートモデル選択付き）
        
        Args:
            prompt: 入力プロンプト
            task_type: タスクタイプ
            priority: 優先度 ("speed", "quality", "balanced")
            **kwargs: 追加パラメータ
            
        Returns:
            生成結果辞書
        """
        start_time = time.time()
        self.performance_stats['total_requests'] += 1
        
        try:
            # スマートモデル選択
            selected_model = self.model_selector.select_model(
                task_type=task_type,
                priority=priority,
                context_length=len(prompt)
            )
            
            logger.info(f"選択されたモデル: {selected_model} (タスク: {task_type.value}, 優先度: {priority})")
            
            # モデル使用統計更新
            if selected_model not in self.performance_stats['model_usage']:
                self.performance_stats['model_usage'][selected_model] = 0
            self.performance_stats['model_usage'][selected_model] += 1
            
            # LLM呼び出し
            response = self.ollama_client.generate(
                model=selected_model,
                prompt=prompt,
                **kwargs
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.get('success', False):
                self.performance_stats['successful_requests'] += 1
                self.performance_stats['total_response_time'] += response_time
                
                logger.info(f"生成成功 ({response_time:.1f}s): {len(response.get('response', ''))}文字")
                
                return {
                    'success': True,
                    'response': response.get('response', ''),
                    'model': selected_model,
                    'response_time': response_time,
                    'task_type': task_type.value,
                    'priority': priority
                }
            else:
                self.performance_stats['failed_requests'] += 1
                error_msg = response.get('error', 'Unknown error')
                
                # エラー統計更新
                if error_msg not in self.performance_stats['error_counts']:
                    self.performance_stats['error_counts'][error_msg] = 0
                self.performance_stats['error_counts'][error_msg] += 1
                
                logger.error(f"生成失敗: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'model': selected_model,
                    'response_time': response_time
                }
                
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            
            self.performance_stats['failed_requests'] += 1
            error_msg = str(e)
            
            if error_msg not in self.performance_stats['error_counts']:
                self.performance_stats['error_counts'][error_msg] = 0
            self.performance_stats['error_counts'][error_msg] += 1
            
            logger.error(f"生成例外: {e}")
            
            return {
                'success': False,
                'error': error_msg,
                'response_time': response_time
            }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """性能レポート取得"""
        total_requests = self.performance_stats['total_requests']
        
        if total_requests == 0:
            return {
                'total_requests': 0,
                'success_rate': 0.0,
                'avg_response_time': 0.0,
                'model_usage': {},
                'error_summary': {}
            }
        
        success_rate = self.performance_stats['successful_requests'] / total_requests
        avg_response_time = (
            self.performance_stats['total_response_time'] / 
            max(self.performance_stats['successful_requests'], 1)
        )
        
        return {
            'total_requests': total_requests,
            'successful_requests': self.performance_stats['successful_requests'],
            'failed_requests': self.performance_stats['failed_requests'],
            'success_rate': f"{success_rate:.1%}",
            'avg_response_time': f"{avg_response_time:.1f}s",
            'model_usage': self.performance_stats['model_usage'],
            'error_summary': self.performance_stats['error_counts']
        }
    
    def reset_performance_stats(self):
        """性能統計リセット"""
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'model_usage': {},
            'error_counts': {}
        }
        logger.info("性能統計をリセットしました")
    
    def get_available_models(self) -> List[str]:
        """利用可能なモデル一覧取得"""
        return self.model_selector.get_available_models()
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """モデル情報取得"""
        return self.model_selector.get_model_info(model_name)
