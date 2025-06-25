# -*- coding: utf-8 -*-
"""
Ollama クライアント
ローカルLLMとの通信を管理
"""
import requests
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class OllamaClient:
    """Ollama API クライアント"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Ollama クライアント初期化
        
        Args:
            base_url: Ollama サーバーのベースURL
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 300  # 5分のタイムアウト
        
        logger.info(f"Ollama クライアントを初期化しました (URL: {self.base_url})")
    
    def is_available(self) -> bool:
        """
        Ollama サーバーが利用可能かチェック
        
        Returns:
            サーバーが利用可能な場合True
        """
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama サーバー接続チェック失敗: {e}")
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        利用可能なモデル一覧を取得
        
        Returns:
            モデル情報のリスト
        """
        try:
            if not self.is_available():
                logger.warning("Ollama サーバーが利用できません")
                return []
            
            response = self.session.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = data.get('models', [])
            
            logger.info(f"利用可能なモデル: {len(models)}個")
            return models
            
        except Exception as e:
            logger.error(f"モデル一覧取得エラー: {e}")
            return []
    
    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        テキスト生成
        
        Args:
            model: 使用するモデル名
            prompt: 入力プロンプト
            system: システムプロンプト
            stream: ストリーミング有効化
            **kwargs: 追加パラメータ
            
        Returns:
            生成結果辞書
        """
        try:
            if not self.is_available():
                return {
                    'success': False,
                    'error': 'Ollama サーバーが利用できません'
                }
            
            # リクエストデータ構築
            data = {
                'model': model,
                'prompt': prompt,
                'stream': stream
            }
            
            if system:
                data['system'] = system
            
            # 追加パラメータを追加
            for key, value in kwargs.items():
                if key not in data:
                    data[key] = value
            
            logger.debug(f"生成リクエスト: model={model}, prompt_length={len(prompt)}")
            
            # API呼び出し
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=data,
                timeout=300
            )
            response.raise_for_status()
            
            if stream:
                # ストリーミングレスポンス処理
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8'))
                            if 'response' in chunk:
                                full_response += chunk['response']
                            if chunk.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
                
                result = {
                    'success': True,
                    'response': full_response,
                    'model': model
                }
            else:
                # 通常のレスポンス処理
                result_data = response.json()
                result = {
                    'success': True,
                    'response': result_data.get('response', ''),
                    'model': model,
                    'context': result_data.get('context', []),
                    'done': result_data.get('done', True)
                }
            
            logger.info(f"生成成功: {len(result['response'])}文字")
            return result
            
        except requests.exceptions.Timeout:
            error_msg = f"タイムアウト: {model}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"API呼び出しエラー: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"予期しないエラー: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def pull_model(self, model: str) -> Dict[str, Any]:
        """
        モデルをダウンロード
        
        Args:
            model: ダウンロードするモデル名
            
        Returns:
            ダウンロード結果
        """
        try:
            if not self.is_available():
                return {
                    'success': False,
                    'error': 'Ollama サーバーが利用できません'
                }
            
            logger.info(f"モデルダウンロード開始: {model}")
            
            response = self.session.post(
                f"{self.base_url}/api/pull",
                json={'name': model},
                timeout=1800  # 30分のタイムアウト
            )
            response.raise_for_status()
            
            logger.info(f"モデルダウンロード完了: {model}")
            return {
                'success': True,
                'model': model
            }
            
        except Exception as e:
            error_msg = f"モデルダウンロードエラー: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        モデル情報取得
        
        Args:
            model: モデル名
            
        Returns:
            モデル情報
        """
        try:
            models = self.list_models()
            for model_info in models:
                if model_info.get('name', '').startswith(model):
                    return {
                        'success': True,
                        'info': model_info
                    }
            
            return {
                'success': False,
                'error': f'モデルが見つかりません: {model}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'モデル情報取得エラー: {e}'
            }
