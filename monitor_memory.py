# メモリモニタリングスクリプト
#python monitor_memory.py

import psutil
import time
import subprocess

def monitor_memory():
    """メモリ使用量をモニタリング"""
    print("📊 システムメモリ監視")
    
    # システム全体のメモリ情報
    memory = psutil.virtual_memory()
    print(f"💾 総メモリ: {memory.total / (1024**3):.1f} GB")
    print(f"📈 使用中: {memory.used / (1024**3):.1f} GB ({memory.percent:.1f}%)")
    print(f"🆓 利用可能: {memory.available / (1024**3):.1f} GB")
    
    # Ollamaプロセスのメモリ使用量
    ollama_memory = 0
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            if 'ollama' in proc.info['name'].lower():
                mem_mb = proc.info['memory_info'].rss / (1024**2)
                print(f"🦙 Ollama PID {proc.info['pid']}: {mem_mb:.1f} MB")
                ollama_memory += mem_mb
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    print(f"🦙 Ollama総使用量: {ollama_memory:.1f} MB ({ollama_memory/1024:.1f} GB)")
    
    # 推奨事項
    available_gb = memory.available / (1024**3)
    if available_gb < 4:
        print("⚠️ 警告: 利用可能メモリが4GB未満です")
        print("💡 推奨: 7Bモデルのみ使用してください")
    elif available_gb < 10:
        print("💡 推奨: 7B-14Bモデルが適しています")
    else:
        print("✅ 33Bモデルまで利用可能です")

if __name__ == "__main__":
    monitor_memory()
