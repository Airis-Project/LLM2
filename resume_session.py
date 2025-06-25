#!/usr/bin/env python3
"""
セッション再開用スクリプト
"""
import os
import json
import glob
from datetime import datetime

def show_project_status():
    """プロジェクト状況表示"""
    print("🔄 LLM Code Assistant プロジェクト再開")
    print("="*50)
    
    # 最新の状態ファイルを探す
    state_files = glob.glob("project_state_*.json")
    if state_files:
        latest_state = max(state_files)
        print(f"📁 最新状態ファイル: {latest_state}")
        
        try:
            with open(latest_state, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            print(f"💾 保存日時: {state['timestamp']}")
            print(f"📍 進行状況: {state['progress']['current_step']}")
            
            print(f"\n✅ 完了済み:")
            for step in state['progress']['completed_steps']:
                print(f"   • {step}")
            
            print(f"\n📋 次のステップ:")
            for step in state['progress']['next_steps']:
                print(f"   • {step}")
            
            print(f"\n🔧 重要コマンド:")
            for cmd in state['progress'].get('important_commands', []):
                print(f"   • {cmd}")
                
        except Exception as e:
            print(f"❌ 状態ファイル読み込みエラー: {e}")
    
    # ファイル構造確認
    print(f"\n📂 現在のファイル構造:")
    for root, dirs, files in os.walk("."):
        level = root.replace(".", "").count(os.sep)
        indent = " " * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 2 * (level + 1)
        for file in files:
            if file.endswith(('.py', '.md', '.txt')):
                print(f"{subindent}{file}")
    
    # 現在実行中のプロセス確認
    print(f"\n🔍 Ollama状態確認:")
    os.system("ollama list 2>/dev/null || echo 'Ollamaが起動していません'")
    
    print(f"\n🚀 再開方法:")
    print("1. テストが完了していない場合:")
    print("   python test_integration_final.py")
    print("2. 新しいテストを実行:")
    print("   python src/llm_client_v2.py")
    print("3. プロジェクト状況確認:")
    print("   python resume_session.py")

if __name__ == "__main__":
    show_project_status()
