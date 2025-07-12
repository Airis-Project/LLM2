# src/core/singleton.py
"""
シングルトンパターン実装
スレッドセーフなシングルトンベースクラス
"""

import threading
from typing import Dict, Any, Type, Optional
from abc import ABCMeta

from src.core.logger import get_logger

logger = get_logger(__name__)

class Singleton:
    """シングルトンパターンの基底クラス"""
    _instances = {}
    
    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__new__(cls)
        return cls._instances[cls]

class SingletonMeta(type):
    """シングルトンメタクラス"""
    
    _instances: Dict[Type, Any] = {}
    _lock: threading.Lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        """インスタンス作成制御"""
        if cls not in cls._instances:
            with cls._lock:
                # ダブルチェックロッキング
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
                    logger.debug(f"シングルトンインスタンス作成: {cls.__name__}")
        
        return cls._instances[cls]
    
    def clear_instance(cls):
        """インスタンスクリア（テスト用）"""
        with cls._lock:
            if cls in cls._instances:
                del cls._instances[cls]
                logger.debug(f"シングルトンインスタンスクリア: {cls.__name__}")


class Singleton(metaclass=SingletonMeta):
    """シングルトンベースクラス"""
    
    def __init__(self, *args, **kwargs):
        """初期化（サブクラスで_initializedフラグを使用推奨）"""
        pass
    
    @classmethod
    def get_instance(cls) -> 'Singleton':
        """インスタンス取得"""
        return cls()
    
    @classmethod
    def clear_instance(cls):
        """インスタンスクリア"""
        cls.__class__.clear_instance(cls)


class ThreadSafeSingleton:
    """スレッドセーフシングルトン（デコレータ用）"""
    
    def __init__(self, cls):
        self._cls = cls
        self._instance = None
        self._lock = threading.Lock()
    
    def __call__(self, *args, **kwargs):
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._cls(*args, **kwargs)
                    logger.debug(f"ThreadSafeSingletonインスタンス作成: {self._cls.__name__}")
        
        return self._instance
    
    def clear_instance(self):
        """インスタンスクリア"""
        with self._lock:
            self._instance = None
            logger.debug(f"ThreadSafeSingletonインスタンスクリア: {self._cls.__name__}")


def singleton(cls):
    """シングルトンデコレータ"""
    return ThreadSafeSingleton(cls)


# 使用例とテスト
if __name__ == "__main__":
    def test_singleton():
        """シングルトンテスト"""
        print("=== シングルトンテスト ===")
        
        # メタクラス版テスト
        class TestClass1(Singleton):
            def __init__(self):
                if hasattr(self, '_initialized'):
                    return
                self.value = "test1"
                self._initialized = True
        
        instance1 = TestClass1()
        instance2 = TestClass1()
        
        print(f"メタクラス版同一インスタンス: {instance1 is instance2}")
        print(f"値: {instance1.value}")
        
        # デコレータ版テスト
        @singleton
        class TestClass2:
            def __init__(self):
                self.value = "test2"
        
        instance3 = TestClass2()
        instance4 = TestClass2()
        
        print(f"デコレータ版同一インスタンス: {instance3 is instance4}")
        print(f"値: {instance3.value}")
        
        # クリアテスト
        TestClass1.clear_instance()
        instance5 = TestClass1()
        print(f"クリア後新インスタンス: {instance1 is not instance5}")
    
    test_singleton()
