# scripts/start.py
"""
LLM Chat System Startup Script
システムの起動とヘルスチェックを行うスクリプト
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import setup_logger
from src.core.config_manager import ConfigManager
from src.core.exceptions import LLMChatError


class SystemStarter:
    """システム起動クラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.logger = setup_logger("SystemStarter")
        
    def start(self, interface: str = "cli", config_path: Optional[str] = None, 
              debug: bool = False) -> bool:
        """システムを起動"""
        try:
            self.logger.info("Starting LLM Chat System...")
            
            # 1. プリフライトチェック
            if not self._preflight_check():
                return False
            
            # 2. 設定の検証
            if not self._validate_configuration(config_path):
                return False
            
            # 3. 依存関係チェック
            if not self._check_dependencies():
                return False
            
            # 4. システム起動
            return self._launch_system(interface, config_path, debug)
            
        except Exception as e:
            self.logger.error(f"System startup failed: {e}")
            return False
    
    def _preflight_check(self) -> bool:
        """起動前チェック"""
        self.logger.info("Performing preflight checks...")
        
        checks = [
            ("Project structure", self._check_project_structure),
            ("Configuration files", self._check_configuration_files),
            ("Environment variables", self._check_environment_variables),
            ("Permissions", self._check_permissions),
            ("Disk space", self._check_disk_space)
        ]
        
        failed_checks = []
        
        for check_name, check_func in checks:
            try:
                if check_func():
                    self.logger.debug(f"✅ {check_name}: OK")
                else:
                    self.logger.warning(f"❌ {check_name}: FAILED")
                    failed_checks.append(check_name)
            except Exception as e:
                self.logger.error(f"❌ {check_name}: ERROR - {e}")
                failed_checks.append(check_name)
        
        if failed_checks:
            self.logger.error(f"Preflight checks failed: {', '.join(failed_checks)}")
            return False
        
        self.logger.info("All preflight checks passed")
        return True
    
    def _check_project_structure(self) -> bool:
        """プロジェクト構造をチェック"""
        required_paths = [
            "src",
            "src/core",
            "src/llm",
            "src/services",
            "src/ui",
            "config",
            "logs",
            "main.py"
        ]
        
        for path in required_paths:
            if not (self.project_root / path).exists():
                self.logger.error(f"Missing required path: {path}")
                return False
        
        return True
    
    def _check_configuration_files(self) -> bool:
        """設定ファイルをチェック"""
        config_files = [
            "config/default_config.json"
        ]
        
        for config_file in config_files:
            config_path = self.project_root / config_file
            if not config_path.exists():
                self.logger.error(f"Missing configuration file: {config_file}")
                return False
            
            # JSONファイルの構文チェック
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in {config_file}: {e}")
                return False
        
        return True
    
    def _check_environment_variables(self) -> bool:
        """環境変数をチェック"""
        # 必須ではないが、警告を出す
        important_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
        missing_vars = []
        
        for var in important_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
            self.logger.warning("Some LLM providers may not be available")
        
        return True  # 環境変数がなくても起動は可能
    
    def _check_permissions(self) -> bool:
        """権限をチェック"""
        # 書き込み権限が必要なディレクトリ
        write_dirs = ["logs", "data", "config/backup", "temp"]
        
        for dir_name in write_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                if not os.access(dir_path, os.W_OK):
                    self.logger.error(f"No write permission for directory: {dir_name}")
                    return False
        
        return True
    
    def _check_disk_space(self) -> bool:
        """ディスク容量をチェック"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.project_root)
            
            # 100MB以上の空き容量が必要
            min_free_space = 100 * 1024 * 1024  # 100MB
            
            if free < min_free_space:
                self.logger.error(f"Insufficient disk space: {free / (1024*1024):.1f}MB available")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")
            return True  # チェックできない場合は続行
    
    def _validate_configuration(self, config_path: Optional[str]) -> bool:
        """設定を検証"""
        try:
            config_manager = ConfigManager()
            
            if config_path:
                config_manager.load_config(config_path)
            else:
                # デフォルト設定を使用
                default_config = self.project_root / "config" / "default_config.json"
                if default_config.exists():
                    config_manager.load_config(str(default_config))
            
            self.logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
    
    def _check_dependencies(self) -> bool:
        """依存関係をチェック"""
        required_modules = [
            "openai",
            "requests",
            "pydantic",
            "jsonschema"
        ]
        
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            self.logger.error(f"Missing required modules: {', '.join(missing_modules)}")
            self.logger.error("Please run: pip install -r requirements.txt")
            return False
        
        return True
    
    def _launch_system(self, interface: str, config_path: Optional[str], 
                      debug: bool) -> bool:
        """システムを起動"""
        try:
            # 起動コマンドを構築
            cmd = [sys.executable, "main.py"]
            
            if interface:
                cmd.extend(["--interface", interface])
            
            if config_path:
                cmd.extend(["--config", config_path])
            
            if debug:
                cmd.append("--debug")
            
            self.logger.info(f"Launching system with command: {' '.join(cmd)}")
            
            # システムを起動
            os.chdir(self.project_root)
            subprocess.run(cmd, check=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"System launch failed with exit code {e.returncode}")
            return False
        except Exception as e:
            self.logger.error(f"System launch failed: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """システムヘルスチェック"""
        health_status = {
            "timestamp": time.time(),
            "status": "unknown",
            "checks": {}
        }
        
        checks = [
            ("project_structure", self._check_project_structure),
            ("configuration", self._check_configuration_files),
            ("dependencies", self._check_dependencies),
            ("permissions", self._check_permissions)
        ]
        
        all_passed = True
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                health_status["checks"][check_name] = {
                    "status": "pass" if result else "fail",
                    "timestamp": time.time()
                }
                if not result:
                    all_passed = False
            except Exception as e:
                health_status["checks"][check_name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": time.time()
                }
                all_passed = False
        
        health_status["status"] = "healthy" if all_passed else "unhealthy"
        return health_status


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM Chat System Starter")
    parser.add_argument(
        "--interface", "-i",
        choices=["cli", "gui"],
        default="cli",
        help="User interface to launch"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Configuration file path"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Perform health check only"
    )
    
    args = parser.parse_args()
    
    starter = SystemStarter()
    
    if args.health_check:
        # ヘルスチェックのみ実行
        print("\n🏥 System Health Check")
        print("=" * 50)
        
        health_status = starter.health_check()
        
        print(f"Overall Status: {'✅ HEALTHY' if health_status['status'] == 'healthy' else '❌ UNHEALTHY'}")
        print("\nDetailed Checks:")
        
        for check_name, check_result in health_status["checks"].items():
            status_icon = {
                "pass": "✅",
                "fail": "❌",
                "error": "⚠️"
            }.get(check_result["status"], "❓")
            
            print(f"  {status_icon} {check_name}: {check_result['status'].upper()}")
            if "error" in check_result:
                print(f"    Error: {check_result['error']}")
        
        return
    
    # システム起動
    print("\n🚀 LLM Chat System Starter")
    print("=" * 50)
    
    success = starter.start(
        interface=args.interface,
        config_path=args.config,
        debug=args.debug
    )
    
    if not success:
        print("\n❌ System startup failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
