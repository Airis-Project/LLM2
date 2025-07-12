#src/llm/local_llm.py
import requests
import json
from typing import Iterator
from .base_llm import BaseLLM

class LocalLLM(BaseLLM):
    """ローカルLLM用クライアント（Ollama対応）"""
    
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
    
    def chat_stream(self, messages: list, **kwargs) -> Iterator[str]:
        """ストリーミングチャット"""
        try:
            prompt = self._convert_messages_to_prompt(messages)
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True
            }
            
            response = requests.post(
                f"{self.api_url}/generate",
                json=payload,
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if 'response' in data:
                            yield data['response']
                        if data.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except requests.exceptions.RequestException as e:
            raise Exception(f"ローカルLLMエラー: {str(e)}")
    
    def chat(self, messages: list, **kwargs) -> str:
        """一括チャット"""
        response_parts = []
        for part in self.chat_stream(messages, **kwargs):
            response_parts.append(part)
        return ''.join(response_parts)
    
    def _convert_messages_to_prompt(self, messages: list) -> str:
        """メッセージをプロンプト形式に変換"""
        prompt_parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"Human: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
    
    def is_available(self) -> bool:
        """ローカルLLMサーバーの可用性チェック"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
