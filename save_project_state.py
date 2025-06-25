# プロジェクト状態の完全バックアップ
#python save_project_state.py
#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime

def save_complete_state():
    """プロジェクト状態を完全保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    state = {
        "timestamp": timestamp,
        "project_structure": {},
        "key_files": {},
        "progress": {
            "completed_steps": [
                "Ollama クライアント作成",
                "モデル選択器実装", 
                "拡張LLMクライアント作成",
                "統合テスト実装",
                "最終版テスト実行中"
            ],
            "current_step": "完全統合テスト実行中 - テスト11で一時停止",
            "next_steps": [
                "テスト完了確認",
                "結果分析", 
                "最終レポート作成",
                "README.md更新"
            ]
        },
        "important_commands": [
            "python test_integration_final.py",
            "python src/llm_client_v2.py",
            "python src/model_selector.py",
            "python src/ollama_client.py"
        ]
    }
    
    # ファイル構造を記録
    for root, dirs, files in os.walk("."):
        if not any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache']):
            for file in files:
                if file.endswith(('.py', '.md', '.txt', '.json')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            state["key_files"][file_path] = f.read()
                    except:
                        state["key_files"][file_path] = "読み取りエラー"
    
    # 状態保存
    with open(f"project_state_{timestamp}.json", 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    
    print(f"✅ プロジェクト状態を保存: project_state_{timestamp}.json")
    return f"project_state_{timestamp}.json"

if __name__ == "__main__":
    save_complete_state()

