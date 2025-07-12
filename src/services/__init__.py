# src/services/__init__.py
"""
LLM Code Assistant サービス層統合モジュール
全てのサービスクラスの統合管理とファクトリ機能を提供
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

# サービスクラスのインポート
from .file_service import FileService, create_file_service
from .project_service import ProjectService, create_project_service

# 設定管理とコアモジュール
#from src.core.config_manager import ConfigManager
from src.core.exceptions import (
    LLMCodeAssistantError,
    ConfigError,
    FileServiceError,
    ProjectServiceError
)
def ConfigManager(*args, **kwargs):
    from ..core.config_manager import ConfigManager
    return ConfigManager(*args, **kwargs)


class ServiceManager:
    """
    サービス統合管理クラス
    全てのサービスのライフサイクル管理と依存関係の解決を行う
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        サービスマネージャーの初期化
        
        Args:
            config_manager: 設定管理インスタンス
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # サービスインスタンス
        self._file_service: Optional[FileService] = None
        self._project_service: Optional[ProjectService] = None
        
        # 初期化フラグ
        self._initialized = False
        self._services_started = False
        
        self.logger.info("ServiceManager 初期化完了")
    
    async def initialize(self) -> bool:
        """
        サービスマネージャーの初期化
        
        Returns:
            bool: 初期化成功フラグ
        """
        try:
            if self._initialized:
                self.logger.warning("ServiceManager は既に初期化済みです")
                return True
            
            # 設定の検証
            await self._validate_configuration()
            
            # サービスの初期化順序（依存関係に基づく）
            await self._initialize_file_service()
            await self._initialize_project_service()
            
            self._initialized = True
            self.logger.info("ServiceManager 初期化完了")
            return True
            
        except Exception as e:
            self.logger.error(f"ServiceManager 初期化エラー: {e}")
            await self.cleanup()
            raise LLMCodeAssistantError(f"サービス初期化に失敗しました: {e}")
    
    async def start_services(self) -> bool:
        """
        全サービスの開始
        
        Returns:
            bool: 開始成功フラグ
        """
        try:
            if not self._initialized:
                raise LLMCodeAssistantError("ServiceManager が初期化されていません")
            
            if self._services_started:
                self.logger.warning("サービスは既に開始済みです")
                return True
            
            # ファイルサービスの開始
            if self._file_service:
                await self._file_service.initialize()
            
            # プロジェクトサービスの開始
            if self._project_service:
                await self._project_service.initialize()
            
            self._services_started = True
            self.logger.info("全サービス開始完了")
            return True
            
        except Exception as e:
            self.logger.error(f"サービス開始エラー: {e}")
            raise LLMCodeAssistantError(f"サービスの開始に失敗しました: {e}")
    
    async def stop_services(self) -> bool:
        """
        全サービスの停止
        
        Returns:
            bool: 停止成功フラグ
        """
        try:
            if not self._services_started:
                self.logger.info("サービスは既に停止済みです")
                return True
            
            # プロジェクトサービスの停止（依存関係の逆順）
            if self._project_service:
                await self._project_service.close()
            
            # ファイルサービスの停止
            if self._file_service:
                await self._file_service.cleanup()
            
            self._services_started = False
            self.logger.info("全サービス停止完了")
            return True
            
        except Exception as e:
            self.logger.error(f"サービス停止エラー: {e}")
            return False
    
    async def restart_services(self) -> bool:
        """
        全サービスの再起動
        
        Returns:
            bool: 再起動成功フラグ
        """
        try:
            self.logger.info("サービス再起動開始")
            
            # 停止
            await self.stop_services()
            
            # 設定の再読み込み
            await self.config_manager.reload_config()
            
            # 再開始
            await self.start_services()
            
            self.logger.info("サービス再起動完了")
            return True
            
        except Exception as e:
            self.logger.error(f"サービス再起動エラー: {e}")
            return False
    
    # === サービスアクセサ ===
    
    @property
    def file_service(self) -> FileService:
        """ファイルサービスの取得"""
        if not self._file_service:
            raise LLMCodeAssistantError("FileService が初期化されていません")
        return self._file_service
    
    @property
    def project_service(self) -> ProjectService:
        """プロジェクトサービスの取得"""
        if not self._project_service:
            raise LLMCodeAssistantError("ProjectService が初期化されていません")
        return self._project_service
    
    # === サービス状態管理 ===
    
    def is_initialized(self) -> bool:
        """初期化状態の確認"""
        return self._initialized
    
    def is_services_started(self) -> bool:
        """サービス開始状態の確認"""
        return self._services_started
    
    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態の取得"""
        return {
            'initialized': self._initialized,
            'services_started': self._services_started,
            'file_service': {
                'available': self._file_service is not None,
                'initialized': self._file_service.is_initialized() if self._file_service else False
            },
            'project_service': {
                'available': self._project_service is not None,
                'current_project': self._project_service.get_current_project().name if 
                                 self._project_service and self._project_service.get_current_project() else None
            }
        }
    
    # === ヘルスチェック ===
    
    async def health_check(self) -> Dict[str, Any]:
        """サービスヘルスチェック"""
        health_status = {
            'overall': 'healthy',
            'services': {},
            'timestamp': None
        }
        
        try:
            from datetime import datetime
            health_status['timestamp'] = datetime.now().isoformat()
            
            # ファイルサービスのヘルスチェック
            if self._file_service:
                try:
                    file_health = await self._file_service.health_check()
                    health_status['services']['file_service'] = file_health
                except Exception as e:
                    health_status['services']['file_service'] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
                    health_status['overall'] = 'degraded'
            
            # プロジェクトサービスのヘルスチェック
            if self._project_service:
                try:
                    # 簡易ヘルスチェック
                    project_health = {
                        'status': 'healthy',
                        'recent_projects_count': len(self._project_service.get_recent_projects()),
                        'current_project': self._project_service.get_current_project() is not None
                    }
                    health_status['services']['project_service'] = project_health
                except Exception as e:
                    health_status['services']['project_service'] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
                    health_status['overall'] = 'degraded'
            
            # 全体的な健康状態の判定
            unhealthy_services = [
                name for name, status in health_status['services'].items()
                if status.get('status') == 'unhealthy'
            ]
            
            if unhealthy_services:
                health_status['overall'] = 'unhealthy'
                health_status['unhealthy_services'] = unhealthy_services
            
        except Exception as e:
            health_status['overall'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status
    
    # === プライベートメソッド ===
    
    async def _validate_configuration(self):
        """設定の検証"""
        try:
            # 必要な設定の存在確認
            required_sections = ['file_service', 'project_service']
            
            for section in required_sections:
                if not self.config_manager.has_section(section):
                    raise ConfigError(f"必要な設定セクションが見つかりません: {section}")
            
            # ディレクトリの存在確認と作成
            await self._ensure_directories()
            
        except Exception as e:
            self.logger.error(f"設定検証エラー: {e}")
            raise
    
    async def _ensure_directories(self):
        """必要なディレクトリの確保"""
        try:
            # データディレクトリ
            data_dir = Path(self.config_manager.get('app.data_directory', 'data'))
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # バックアップディレクトリ
            backup_dir = Path(self.config_manager.get('file_service.backup_directory', 'data/backups'))
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # プロジェクトデータディレクトリ
            projects_dir = Path(self.config_manager.get('project_service.projects_directory', 'data/projects'))
            projects_dir.mkdir(parents=True, exist_ok=True)
            
            # テンプレートディレクトリ
            templates_dir = Path(self.config_manager.get('project_service.templates_directory', 'data/templates'))
            templates_dir.mkdir(parents=True, exist_ok=True)
            
        except Exception as e:
            self.logger.error(f"ディレクトリ作成エラー: {e}")
            raise
    
    async def _initialize_file_service(self):
        """ファイルサービスの初期化"""
        try:
            self._file_service = create_file_service(self.config_manager)
            self.logger.debug("FileService 初期化完了")
            
        except Exception as e:
            self.logger.error(f"FileService 初期化エラー: {e}")
            raise FileServiceError(f"ファイルサービスの初期化に失敗しました: {e}")
    
    async def _initialize_project_service(self):
        """プロジェクトサービスの初期化"""
        try:
            if not self._file_service:
                raise LLMCodeAssistantError("FileService が初期化されていません")
            
            self._project_service = create_project_service(
                self.config_manager, 
                self._file_service
            )
            self.logger.debug("ProjectService 初期化完了")
            
        except Exception as e:
            self.logger.error(f"ProjectService 初期化エラー: {e}")
            raise ProjectServiceError(f"プロジェクトサービスの初期化に失敗しました: {e}")
    
    async def cleanup(self):
        """クリーンアップ処理"""
        try:
            await self.stop_services()
            
            # サービスインスタンスのクリア
            self._file_service = None
            self._project_service = None
            
            self._initialized = False
            self._services_started = False
            
            self.logger.info("ServiceManager クリーンアップ完了")
            
        except Exception as e:
            self.logger.error(f"ServiceManager クリーンアップエラー: {e}")


# === ファクトリ関数 ===

def create_service_manager(config_manager: ConfigManager) -> ServiceManager:
    """
    サービスマネージャーのインスタンス作成
    
    Args:
        config_manager: 設定管理インスタンス
        
    Returns:
        ServiceManager: サービスマネージャーインスタンス
    """
    return ServiceManager(config_manager)


# === 便利関数 ===

async def initialize_services(config_manager: ConfigManager) -> ServiceManager:
    """
    サービスの一括初期化と開始
    
    Args:
        config_manager: 設定管理インスタンス
        
    Returns:
        ServiceManager: 初期化済みサービスマネージャー
    """
    service_manager = create_service_manager(config_manager)
    await service_manager.initialize()
    await service_manager.start_services()
    return service_manager


def get_available_services() -> List[str]:
    """利用可能なサービス一覧の取得"""
    return [
        'file_service',
        'project_service'
    ]


def get_service_dependencies() -> Dict[str, List[str]]:
    """サービス依存関係の取得"""
    return {
        'file_service': [],  # 依存なし
        'project_service': ['file_service']  # ファイルサービスに依存
    }


# === モジュールレベルエクスポート ===

__all__ = [
    # サービスクラス
    'FileService',
    'ProjectService',
    
    # サービス管理
    'ServiceManager',
    
    # ファクトリ関数
    'create_service_manager',
    'create_file_service',
    'create_project_service',
    
    # 便利関数
    'initialize_services',
    'get_available_services',
    'get_service_dependencies'
]


# === バージョン情報 ===
__version__ = '1.0.0'
__author__ = 'LLM Code Assistant'
__description__ = 'サービス層統合モジュール'
