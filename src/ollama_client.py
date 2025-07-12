# -*- coding: utf-8 -*-
#src/ollama_client.py
"""
Ollama クライアント
ローカルLLMとの通信を管理
"""
"""
完全なOllamaクライアント（タイムアウト対応版）
"""

import logging
import requests
import json
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class OllamaClient:
    """完全なOllamaクライアント（タイムアウト対応）"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # モデル別タイムアウト設定
        self.model_timeouts = {
            'starcoder:7b': 180,      # 3分
            'codellama:7b': 180,      # 3分
            'phi4:14b': 600,          # 10分
            'wizardcoder:33b': 1200,  # 20分 ⭐ 重要！
            'codellama:70b': 1200,    # 20分
            'llama3.1:405b':1200,     # 20分
            'llama3.3:70b':1200,      # 20分
            'default': 300            # 5分（デフォルト）
        }
        
        logger.info(f"Ollama クライアントを初期化しました (URL: {self.base_url})")
    
    def generate(
        self,
        model: str,
        prompt: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LLM生成（タイムアウト対応）
        
        Args:
            model: モデル名
            prompt: プロンプト
            timeout: タイムアウト秒数（Noneの場合モデル別設定使用）
            **kwargs: 追加パラメータ
        """
        start_time = time.time()
        
        # タイムアウト決定
        if timeout is None:
            timeout = self.model_timeouts.get(model, self.model_timeouts['default'])
        
        logger.info(f"生成開始: {model} (タイムアウト: {timeout}秒)")
        
        try:
            # リクエストデータ準備
            data = {
                'model': model,
                'prompt': prompt,
                'stream': False,
                **kwargs
            }
            
            # HTTP タイムアウトを生成タイムアウトに設定
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=data,
                timeout=timeout  # ⭐ 重要：HTTPタイムアウト = 生成タイムアウト
            )
            
            response.raise_for_status()
            result = response.json()
            
            end_time = time.time()
            duration = end_time - start_time
            
            if 'response' in result:
                content = result['response']
                logger.info(f"生成成功: {len(content)}文字")
                
                return {
                    'success': True,
                    'response': content,
                    'model': model,
                    'duration': duration,
                    'done': result.get('done', True)
                }
            else:
                logger.error(f"生成失敗: レスポンスが空")
                return {
                    'success': False,
                    'error': 'Empty response',
                    'model': model,
                    'duration': duration
                }
                
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            error_msg = f"タイムアウト: {model}"
            logger.error(f"{error_msg} ({duration:.1f}秒)")
            
            return {
                'success': False,
                'error': error_msg,
                'model': model,
                'duration': duration
            }
            
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            error_msg = f"リクエストエラー: {str(e)}"
            logger.error(f"{error_msg}")
            
            return {
                'success': False,
                'error': error_msg,
                'model': model,
                'duration': duration
            }
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"予期しないエラー: {str(e)}"
            logger.error(f"{error_msg}")
            
            return {
                'success': False,
                'error': error_msg,
                'model': model,
                'duration': duration
            }
    
    def list_models(self) -> List[Dict[str, Any]]:
        """モデル一覧取得"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('models', [])
        except Exception as e:
            logger.error(f"モデル一覧取得失敗: {e}")
            return []
    
    def is_available(self) -> bool:
        """サーバー可用性チェック"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def set_model_timeout(self, model: str, timeout: int):
        """モデル別タイムアウト設定"""
        self.model_timeouts[model] = timeout
        logger.info(f"タイムアウト設定: {model} = {timeout}秒")
    
    def get_model_timeout(self, model: str) -> int:
        """モデルのタイムアウト取得"""
        return self.model_timeouts.get(model, self.model_timeouts['default'])
