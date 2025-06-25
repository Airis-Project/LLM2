# -*- coding: utf-8 -*-
"""
スマートモデル選択器（軽量化版）
"""

import logging
import requests
import json
from enum import Enum
from typing import Dict, Any, Optional, List
from .ollama_client import OllamaClient

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """タスクタイプ定義"""
    GENERAL = "general"
    CODE_GENERATION = "code_generation" 
    CODE_EXPLANATION = "code_explanation"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    QUICK_RESPONSE = "quick_response"
    COMPLEX_ANALYSIS = "complex_analysis"


class SmartModelSelector:
    """スマートモデル選択器（軽量化版）"""
    
    def __init__(self, config_path: Optional[str] = None):
        """選択器初期化"""
        self.ollama_client = OllamaClient()
        
        # 軽量化されたモデル設定（小さなモデルを優先）
        self.model_preferences = {
            TaskType.QUICK_RESPONSE: {
                "speed": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "balanced": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "quality": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"]
            },
            TaskType.CODE_GENERATION: {
                "speed": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "balanced": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "quality": ["tarcoder:7b", "wizardcoder:33b", "phi4:14b"]
            },
            TaskType.CODE_EXPLANATION: {
                "speed": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "balanced": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "quality": ["tarcoder:7b", "wizardcoder:33b", "phi4:14b"]
            },
            TaskType.DEBUGGING: {
                "speed": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "balanced": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "quality": ["tarcoder:7b", "wizardcoder:33b", "phi4:14b"]
            },
            TaskType.REFACTORING: {
                "speed": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "balanced": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "quality": ["tarcoder:7b", "wizardcoder:33b", "phi4:14b"]
            },
            TaskType.COMPLEX_ANALYSIS: {
                "speed": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "balanced": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "quality": ["wizardcoder:33b", "tarcoder:7b", "phi4:14b"]
            },
            TaskType.GENERAL: {
                "speed": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "balanced": ["tarcoder:7b", "phi4:14b", "wizardcoder:33b"],
                "quality": ["tarcoder:7b", "wizardcoder:33b", "phi4:14b"]
            }
        }
        
        # 利用可能なモデルをキャッシュ
        self._available_models = None
        self._refresh_available_models()
        
        logger.info("スマートモデル選択器を初期化しました（軽量化版）")
    
    def _refresh_available_models(self):
        """利用可能なモデル一覧を更新"""
        try:
            models = self.ollama_client.list_models()
            self._available_models = [model.get('name', '') for model in models]
            
            # 軽量モデルのみをフィルタリング（70B以上は除外）
            filtered_models = []
            for model in self._available_models:
                model_lower = model.lower()
                if not any(size in model_lower for size in ['70b', '72b', '34b']):
                    filtered_models.append(model)
            
            self._available_models = filtered_models
            logger.info(f"利用可能なモデル（軽量版のみ）: {len(self._available_models)}個")
            
        except Exception as e:
            logger.warning(f"モデル一覧取得失敗: {e}")
            self._available_models = []
    
    def select_model(
        self,
        task_type: TaskType = TaskType.GENERAL,
        priority: str = "balanced",
        context_length: int = 0
    ) -> str:
        """
        最適なモデルを選択（軽量モデル優先）
        """
        try:
            # 利用可能なモデルを確認
            if not self._available_models:
                self._refresh_available_models()
            
            if not self._available_models:
                logger.warning("利用可能なモデルがありません")
                return "tarcoder:7b"  # フォールバック
            
            # 優先度に基づくモデル候補取得
            candidates = self.model_preferences.get(task_type, {}).get(priority, [])
            
            # 利用可能なモデルから選択
            for candidate in candidates:
                for available in self._available_models:
                    if candidate.lower() in available.lower():
                        logger.info(f"選択されたモデル: {available} (タスク: {task_type.value}, 優先度: {priority})")
                        return available
            
            # 候補が見つからない場合、利用可能な最初のモデルを使用
            if self._available_models:
                fallback_model = self._available_models[0]
                logger.warning(f"適切なモデルが見つかりません - フォールバック: {fallback_model}")
                return fallback_model
            
            return "tarcoder:7b"  # 最終フォールバック
            
        except Exception as e:
            logger.error(f"モデル選択エラー: {e}")
            return "tarcoder:7b"
    
    def get_available_models(self) -> List[str]:
        """利用可能なモデル一覧取得"""
        if not self._available_models:
            self._refresh_available_models()
        return self._available_models.copy() if self._available_models else []
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """モデル情報取得"""
        try:
            models = self.ollama_client.list_models()
            for model_info in models:
                if model_info.get('name', '').startswith(model_name):
                    return {
                        'success': True,
                        'info': model_info
                    }
            
            return {
                'success': False,
                'error': f'モデルが見つかりません: {model_name}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'モデル情報取得エラー: {e}'
            }
    
    def add_custom_preference(
        self,
        task_type: TaskType,
        priority: str,
        models: List[str]
    ):
        """カスタムモデル設定追加"""
        if task_type not in self.model_preferences:
            self.model_preferences[task_type] = {}
        
        self.model_preferences[task_type][priority] = models
        logger.info(f"カスタム設定追加: {task_type.value} - {priority}")
