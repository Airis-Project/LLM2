# エラー詳細確認スクリプトを作成
import requests
import json

def debug_ollama_error():
    """Ollama エラー詳細確認"""
    print("🔍 Ollama エラー詳細確認")
    
    # 1. サーバー状態確認
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=10)
        print(f"Ollamaバージョン: {response.json() if response.status_code == 200 else 'エラー'}")
    except Exception as e:
        print(f"バージョン確認エラー: {e}")
    
    # 2. 簡単なテストリクエスト
    test_requests = [
        {
            "name": "最小リクエスト",
            "payload": {
                "model": "codellama:70b",
                "prompt": "Hello",
                "stream": False
            }
        },
        {
            "name": "小文字モデル名",
            "payload": {
                "model": "codellama:70b",  # 小文字
                "prompt": "Hello",
                "stream": False
            }
        },
        {
            "name": "軽量モデルテスト",
            "payload": {
                "model": "codellama:7b",
                "prompt": "Hello",
                "stream": False
            }
        }
    ]
    
    for test in test_requests:
        print(f"\n📝 {test['name']} テスト:")
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=test["payload"],
                timeout=60
            )
            
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code != 200:
                print(f"エラー詳細: {response.text}")
            else:
                result = response.json()
                print(f"✅ 成功: {result.get('response', '')[:50]}...")
                
        except Exception as e:
            print(f"❌ リクエストエラー: {e}")

if __name__ == "__main__":
    debug_ollama_error()

#python debug_ollama_error.py
