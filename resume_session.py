# resume_session.py
#!/usr/bin/env python3
"""
セッション再開用スクリプト
使用方法: python resume_session.py
"""
import os
import json
import glob
import sys
from datetime import datetime
from pathlib import Path

def show_project_status():
    """プロジェクト状況表示"""
    print("🚀 LLM Chat System - セッション再開")
    print("=" * 60)
    
    # 最新の状態ファイルを探す
    state_files = glob.glob("project_state_*.json")
    if state_files:
        latest_state = max(state_files, key=os.path.getctime)
        print(f"📂 最新状態ファイル: {latest_state}")
        
        try:
            with open(latest_state, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            metadata = state.get("metadata", {})
            progress = state.get("progress", {})
            
            print(f"📅 前回セッション: {metadata.get('session_date', 'N/A')}")
            print(f"📊 プロジェクト完成度: {progress.get('completion_percentage', 0)}%")
            print(f"📈 現在状況: {progress.get('current_status', 'N/A')}")
            
            print(f"\n✅ 完了済みフェーズ:")
            for phase in progress.get("completed_phases", []):
                print(f"   🎯 {phase}")
            
            print(f"\n📋 次のステップ:")
            for step in progress.get("next_steps", []):
                print(f"   📌 {step}")
            
            print(f"\n🔧 重要コマンド:")
            for cmd in state.get("important_commands", []):
                print(f"   💻 {cmd}")
            
            # プロジェクト統計
            print(f"\n📊 プロジェクト統計:")
            print(f"   • 総ファイル数: {metadata.get('total_files_created', 0)}")
            print(f"   • 総コード行数: {metadata.get('total_lines_of_code', 0):,}")
            
            # 設定情報
            config_info = state.get("configuration", {})
            print(f"\n⚙️  現在の設定:")
            print(f"   • サポートプロバイダー: {', '.join(config_info.get('supported_providers', []))}")
            print(f"   • デフォルトプロバイダー: {config_info.get('default_provider', 'N/A')}")
            print(f"   • 設定ファイル: {config_info.get('config_file', 'N/A')}")
                
        except Exception as e:
            print(f"❌ 状態ファイル読み込みエラー: {e}")
    else:
        print("⚠️  状態ファイルが見つかりません")
    
    # 現在のファイル構造確認
    print(f"\n📁 現在のプロジェクト構造:")
    show_project_tree(".", max_depth=3)
    
    # システム環境確認
    print(f"\n🖥️  システム環境:")
    print(f"   • Python: {sys.version.split()[0]}")
    print(f"   • 作業ディレクトリ: {os.getcwd()}")
    
    # 環境変数確認
    env_status = []
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        status = "設定済み" if os.getenv(key) else "未設定"
        env_status.append(f"{key}: {status}")
    
    print(f"   • 環境変数: {', '.join(env_status)}")
    
    # 推奨アクション
    print(f"\n🎯 推奨アクション:")
    print("1. システム動作確認:")
    print("   python scripts/start.py --health-check")
    print("2. テスト実行:")
    print("   python tests/run_tests.py")
    print("3. チャット開始:")
    print("   python main.py --interface cli")
    print("4. 詳細レポート生成:")
    print("   python tests/generate_report.py")

def show_project_tree(path, prefix="", max_depth=3, current_depth=0):
    """プロジェクトツリー表示"""
    if current_depth >= max_depth:
        return
    
    try:
        items = sorted([item for item in os.listdir(path) 
                       if not item.startswith('.') and 
                       item not in ['__pycache__', 'venv', 'env']])
        
        for i, item in enumerate(items):
            item_path = os.path.join(path, item)
            is_last = i == len(items) - 1
            
            current_prefix = "└── " if is_last else "├── "
            print(f"{prefix}{current_prefix}{item}")
            
            if os.path.isdir(item_path) and current_depth < max_depth - 1:
                extension = "    " if is_last else "│   "
                show_project_tree(item_path, prefix + extension, max_depth, current_depth + 1)
                
    except PermissionError:
        pass

def check_system_health():
    """システムヘルスチェック"""
    print(f"\n🔍 システムヘルスチェック:")
    
    # 必要なファイルの存在確認
    critical_files = [
        "main.py",
        "src/core/config_manager.py",
        "src/services/llm_service.py",
        "config/default_config.json"
    ]
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} (不足)")
    
    # Python依存関係確認
    required_modules = ["json", "os", "sys", "pathlib", "logging"]
    for module in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {module} モジュール")
        except ImportError:
            print(f"   ❌ {module} モジュール (不足)")

if __name__ == "__main__":
    show_project_status()
    check_system_health()
    
    print(f"\n🎉 セッション再開準備完了！")
    print("上記のコマンドを使用してプロジェクトを続行してください。")
