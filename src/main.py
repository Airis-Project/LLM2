#!/usr/bin/env python3
"""
メインアプリケーションエントリーポイント
LLMコードアシスタントの起動とシステム初期化を管理
"""

import sys
import asyncio
import signal
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# コアシステムインポート
from src.core.logger import get_logger, setup_logging
from src.core.config_manager import get_config, ConfigManager
from src.core.event_system import get_event_system, Event

# LLMシステムインポート (新システム)
from src.llm import (
    get_llm_factory,
    LLMConfig,
    LLMProvider,
    create_llm_client,
    get_available_providers,
    DEFAULT_CONFIG
)

# UIシステムインポート
from src.ui.main_window import MainWindow
from src.ui.qt_app import create_qt_application

# サービスインポート
from src.services.llm_service import LLMService
from src.services.file_service import FileService
from src.services.project_service import ProjectService

# ユーティリティインポート
from src.utils.system_utils import SystemUtils
from src.utils.performance_monitor import PerformanceMonitor

logger = get_logger(__name__)

class ApplicationManager:
    """アプリケーション管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.config_manager: Optional[ConfigManager] = None
        self.llm_factory = None
        self.llm_client = None
        self.main_window: Optional[MainWindow] = None
        self.services = {}
        self.performance_monitor = PerformanceMonitor()
        self.event_system = get_event_system()
        
        # シグナルハンドラー設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def initialize_system(self) -> bool:
        """システム初期化"""
        try:
            logger.info("=== LLMコードアシスタント初期化開始 ===")
            
            # 1. ログシステム初期化
            setup_logging()
            logger.info("✅ ログシステム初期化完了")
            
            # 2. 設定管理初期化
            self.config_manager = get_config()
            logger.info("✅ 設定管理初期化完了")
            
            # 3. パフォーマンス監視開始
            self.performance_monitor.start_monitoring()
            logger.info("✅ パフォーマンス監視開始")
            
            # 4. LLMシステム初期化 (新システム)
            if not self._initialize_llm_system():
                return False
            
            # 5. サービス初期化
            if not self._initialize_services():
                return False
            
            # 6. イベントシステム初期化
            self._setup_event_handlers()
            logger.info("✅ イベントシステム初期化完了")
            
            logger.info("=== システム初期化完了 ===")
            return True
            
        except Exception as e:
            logger.error(f"システム初期化エラー: {e}")
            return False
    
    def _initialize_llm_system(self) -> bool:
        """LLMシステム初期化 (新ファクトリーシステム)"""
        try:
            logger.info("LLMシステム初期化開始...")
            
            # ファクトリー取得
            self.llm_factory = get_llm_factory()
            logger.info("✅ LLMファクトリー取得完了")
            
            # 利用可能プロバイダー確認
            available_providers = get_available_providers()
            logger.info(f"利用可能プロバイダー: {available_providers}")
            
            if not available_providers:
                logger.warning("利用可能なLLMプロバイダーがありません")
                logger.info("デモモードで継続します")
                return True
            
            # 設定からプロバイダー選択
            config = self.config_manager.get_section('llm', {})
            preferred_provider = config.get('preferred_provider', 'openai')
            
            # LLM設定作成
            llm_config = LLMConfig(
                model=config.get('model', 'gpt-3.5-turbo'),
                temperature=config.get('temperature', 0.7),
                max_tokens=config.get('max_tokens', 2048),
                timeout=config.get('timeout', 30.0),
                retry_count=config.get('retry_count', 3)
            )
            
            # プロバイダー別クライアント作成
            if preferred_provider in available_providers:
                try:
                    self.llm_client = create_llm_client(
                        preferred_provider, 
                        llm_config
                    )
                    logger.info(f"✅ {preferred_provider} クライアント作成完了")
                except Exception as e:
                    logger.warning(f"{preferred_provider} 初期化失敗: {e}")
                    # フォールバック処理
                    self.llm_client = self._create_fallback_client(available_providers, llm_config)
            else:
                logger.warning(f"設定されたプロバイダー '{preferred_provider}' が利用不可")
                self.llm_client = self._create_fallback_client(available_providers, llm_config)
            
            # 接続テスト
            if self.llm_client and self.llm_client.is_available():
                model_info = self.llm_client.get_model_info()
                logger.info(f"✅ LLM接続確認完了: {model_info.get('model', 'Unknown')}")
            else:
                logger.warning("LLM接続確認に失敗しました")
            
            return True
            
        except Exception as e:
            logger.error(f"LLMシステム初期化エラー: {e}")
            return False
    
    def _create_fallback_client(self, available_providers: list, config: LLMConfig):
        """フォールバッククライアント作成"""
        for provider in available_providers:
            try:
                client = create_llm_client(provider, config)
                logger.info(f"✅ フォールバック {provider} クライアント作成完了")
                return client
            except Exception as e:
                logger.warning(f"{provider} フォールバック失敗: {e}")
                continue
        
        logger.error("全てのプロバイダーでクライアント作成に失敗")
        return None
    
    def _initialize_services(self) -> bool:
        """サービス初期化"""
        try:
            logger.info("サービス初期化開始...")
            
            # LLMサービス
            self.services['llm'] = LLMService(self.llm_client)
            logger.info("✅ LLMサービス初期化完了")
            
            # ファイルサービス
            self.services['file'] = FileService()
            logger.info("✅ ファイルサービス初期化完了")
            
            # プロジェクトサービス
            self.services['project'] = ProjectService()
            logger.info("✅ プロジェクトサービス初期化完了")
            
            return True
            
        except Exception as e:
            logger.error(f"サービス初期化エラー: {e}")
            return False
    
    def _setup_event_handlers(self):
        """イベントハンドラー設定"""
        # LLM状態変更イベント
        self.event_system.subscribe('llm_status_changed', self._on_llm_status_changed)
        
        # LLMリクエスト完了イベント
        self.event_system.subscribe('llm_request_completed', self._on_llm_request_completed)
        
        # システムイベント
        self.event_system.subscribe('system_shutdown', self._on_system_shutdown)
    
    def _on_llm_status_changed(self, event: Event):
        """LLM状態変更ハンドラー"""
        data = event.data
        logger.info(f"LLM状態変更: {data['old_status']} -> {data['new_status']}")
    
    def _on_llm_request_completed(self, event: Event):
        """LLMリクエスト完了ハンドラー"""
        data = event.data
        if data['success']:
            logger.debug(f"LLMリクエスト成功: {data['tokens']}トークン, {data['response_time']:.2f}秒")
        else:
            logger.warning("LLMリクエスト失敗")
    
    def _on_system_shutdown(self, event: Event):
        """システムシャットダウンハンドラー"""
        logger.info("システムシャットダウン開始...")
        self.shutdown()
    
    def start_application(self) -> int:
        """アプリケーション開始"""
        try:
            # Qt アプリケーション作成
            app = create_qt_application()
            
            # メインウィンドウ作成
            self.main_window = MainWindow(
                llm_client=self.llm_client,
                services=self.services,
                config_manager=self.config_manager
            )
            
            # ウィンドウ表示
            self.main_window.show()
            logger.info("✅ メインウィンドウ表示完了")
            
            # アプリケーション実行
            logger.info("=== アプリケーション開始 ===")
            return app.exec()
            
        except Exception as e:
            logger.error(f"アプリケーション開始エラー: {e}")
            return 1
    
    def shutdown(self):
        """アプリケーション終了処理"""
        try:
            logger.info("=== アプリケーション終了処理開始 ===")
            
            # パフォーマンス監視停止
            if self.performance_monitor:
                self.performance_monitor.stop_monitoring()
                logger.info("✅ パフォーマンス監視停止")
            
            # サービス終了
            for name, service in self.services.items():
                if hasattr(service, 'shutdown'):
                    service.shutdown()
                    logger.info(f"✅ {name}サービス終了")
            
            # LLMクライアント終了
            if self.llm_client and hasattr(self.llm_client, '__exit__'):
                self.llm_client.__exit__(None, None, None)
                logger.info("✅ LLMクライアント終了")
            
            # 設定保存
            if self.config_manager:
                self.config_manager.save_config()
                logger.info("✅ 設定保存完了")
            
            logger.info("=== アプリケーション終了処理完了 ===")
            
        except Exception as e:
            logger.error(f"終了処理エラー: {e}")
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        logger.info(f"シグナル受信: {signum}")
        self.shutdown()
        sys.exit(0)

def main():
    """メイン関数"""
    try:
        # アプリケーション管理インスタンス作成
        app_manager = ApplicationManager()
        
        # システム初期化
        if not app_manager.initialize_system():
            logger.error("システム初期化に失敗しました")
            return 1
        
        # アプリケーション開始
        exit_code = app_manager.start_application()
        
        # 終了処理
        app_manager.shutdown()
        
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("ユーザーによる中断")
        return 0
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
