# save_project_state.py
#!/usr/bin/env python3
"""
プロジェクト状態の完全バックアップ
使用方法: python save_project_state.py
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path

def save_complete_state():
    """プロジェクト状態を完全保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    state = {
        "metadata": {
            "timestamp": timestamp,
            "project_name": "LLM Chat System",
            "version": "1.0.0",
            "session_date": datetime.now().isoformat(),
            "total_files_created": 0,
            "total_lines_of_code": 0
        },
        "project_structure": {},
        "key_files": {},
        "progress": {
            "completed_phases": [
                "A. システムアーキテクチャ設計",
                "B. コア機能実装", 
                "C. UI実装",
                "D-1. ユニットテスト作成",
                "D-2. 統合テスト作成",
                "D-3. E2Eテスト作成",
                "D-4. CI/CD設定",
                "D-5. 最終統合テスト完了"
            ],
            "current_status": "プロジェクト完成 - 全機能実装済み",
            "completion_percentage": 100,
            "next_steps": [
                "デプロイメント準備",
                "ドキュメント最終化",
                "パフォーマンス最適化",
                "追加機能検討"
            ]
        },
        "implementation_summary": {
            "core_modules": [
                "config_manager.py - 設定管理システム",
                "logger.py - ログシステム", 
                "exceptions.py - 例外処理"
            ],
            "llm_providers": [
                "openai_provider.py - OpenAI統合",
                "anthropic_provider.py - Anthropic統合",
                "ollama_provider.py - Ollama統合"
            ],
            "ui_components": [
                "cli.py - コマンドライン界面"
            ],
            "test_suites": [
                "test_integration.py - 統合テスト",
                "test_e2e.py - エンドツーエンドテスト",
                "run_tests.py - テスト実行フレームワーク"
            ]
        },
        "important_commands": [
            "python main.py --interface cli",
            "python tests/run_tests.py --coverage",
            "python tests/generate_report.py",
            "python scripts/init.py --force",
            "python scripts/start.py --health-check"
        ],
        "configuration": {
            "supported_providers": ["openai", "anthropic", "ollama"],
            "default_provider": "openai",
            "config_file": "config/default_config.json",
            "log_level": "INFO"
        }
    }
    
    # ファイル構造とコンテンツを記録
    total_files = 0
    total_lines = 0
    
    for root, dirs, files in os.walk("."):
        # 不要なディレクトリをスキップ
        dirs[:] = [d for d in dirs if not d.startswith(('.git', '__pycache__', '.pytest_cache', 'venv', 'env'))]
        
        for file in files:
            if file.endswith(('.py', '.md', '.txt', '.json', '.yml', '.yaml', '.ini')):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, ".")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        state["key_files"][relative_path] = {
                            "content": content,
                            "lines": len(content.splitlines()),
                            "size_bytes": len(content.encode('utf-8')),
                            "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                        }
                        total_files += 1
                        total_lines += len(content.splitlines())
                except Exception as e:
                    state["key_files"][relative_path] = {
                        "error": f"読み取りエラー: {str(e)}",
                        "lines": 0,
                        "size_bytes": 0
                    }
    
    # メタデータ更新
    state["metadata"]["total_files_created"] = total_files
    state["metadata"]["total_lines_of_code"] = total_lines
    
    # プロジェクト構造を記録
    def build_tree(path, prefix=""):
        tree = {}
        try:
            items = sorted(os.listdir(path))
            for item in items:
                if item.startswith('.'):
                    continue
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    tree[f"{item}/"] = build_tree(item_path, prefix + "  ")
                else:
                    tree[item] = os.path.getsize(item_path)
        except PermissionError:
            pass
        return tree
    
    state["project_structure"] = build_tree(".")
    
    # 状態ファイル保存
    filename = f"project_state_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    
    # サマリー表示
    print("🎉 LLM Chat System - プロジェクト状態保存完了")
    print("=" * 60)
    print(f"📅 保存日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 保存ファイル: {filename}")
    print(f"📊 統計情報:")
    print(f"   • 総ファイル数: {total_files}")
    print(f"   • 総コード行数: {total_lines:,}")
    print(f"   • プロジェクト完成度: 100%")
    print(f"   • 実装フェーズ: 全完了")
    
    print(f"\n🎯 主要成果:")
    for phase in state["progress"]["completed_phases"]:
        print(f"   ✅ {phase}")
    
    print(f"\n🚀 次回セッション時の推奨アクション:")
    for step in state["progress"]["next_steps"]:
        print(f"   📌 {step}")
    
    print(f"\n💡 重要コマンド:")
    for cmd in state["important_commands"][:3]:
        print(f"   🔧 {cmd}")
    
    return filename

if __name__ == "__main__":
    save_complete_state()
