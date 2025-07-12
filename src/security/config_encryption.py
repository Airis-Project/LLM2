# src/security/config_encryption.py
"""
設定暗号化システム
機密設定データの暗号化・復号化機能
"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

# 暗号化ライブラリ
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from src.core.logger import get_logger

logger = get_logger(__name__)


class EncryptionMethod(Enum):
    """暗号化方式"""
    FERNET = "fernet"           # 対称暗号化
    RSA = "rsa"                 # 非対称暗号化
    AES_GCM = "aes_gcm"        # AES-GCM
    SIMPLE = "simple"           # 簡易暗号化（開発用）


class KeyDerivationMethod(Enum):
    """鍵導出方式"""
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"
    ARGON2 = "argon2"


@dataclass
class EncryptionConfig:
    """暗号化設定"""
    method: EncryptionMethod = EncryptionMethod.FERNET
    key_derivation: KeyDerivationMethod = KeyDerivationMethod.PBKDF2
    iterations: int = 100000
    salt_length: int = 32
    key_length: int = 32
    rsa_key_size: int = 2048
    password_min_length: int = 8


@dataclass
class EncryptedData:
    """暗号化データ"""
    data: str                    # 暗号化されたデータ（Base64）
    method: str                  # 暗号化方式
    salt: Optional[str] = None   # ソルト（Base64）
    iv: Optional[str] = None     # 初期化ベクトル（Base64）
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = {
            '_encrypted': True,
            'data': self.data,
            'method': self.method
        }
        
        if self.salt:
            result['salt'] = self.salt
        if self.iv:
            result['iv'] = self.iv
        if self.timestamp:
            result['timestamp'] = self.timestamp
        if self.metadata:
            result['metadata'] = self.metadata
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptedData':
        """辞書から作成"""
        return cls(
            data=data['data'],
            method=data['method'],
            salt=data.get('salt'),
            iv=data.get('iv'),
            timestamp=data.get('timestamp'),
            metadata=data.get('metadata')
        )


class ConfigEncryption:
    """設定暗号化管理クラス"""
    
    def __init__(self, config: EncryptionConfig = None):
        self.config = config or EncryptionConfig()
        
        # 暗号化キー管理
        self._master_key: Optional[bytes] = None
        self._key_cache: Dict[str, bytes] = {}
        
        # RSAキーペア
        self._rsa_private_key: Optional[rsa.RSAPrivateKey] = None
        self._rsa_public_key: Optional[rsa.RSAPublicKey] = None
        
        # キーファイルパス
        self.key_dir = Path("keys")
        self.key_dir.mkdir(parents=True, exist_ok=True)
        
        # 機密キー識別パターン
        self.sensitive_keys = {
            'api_key', 'password', 'token', 'secret', 'private_key',
            'access_token', 'refresh_token', 'client_secret', 'webhook_secret'
        }
        
        logger.info("設定暗号化システム初期化完了")
    
    def initialize_master_key(self, password: Optional[str] = None) -> bool:
        """マスターキー初期化"""
        try:
            if password:
                # パスワードベースのキー導出
                self._master_key = self._derive_key_from_password(password)
            else:
                # 環境変数またはキーファイルから読み込み
                self._master_key = self._load_or_generate_master_key()
            
            if self._master_key:
                logger.info("マスターキー初期化完了")
                return True
            else:
                logger.error("マスターキー初期化失敗")
                return False
                
        except Exception as e:
            logger.error(f"マスターキー初期化エラー: {e}")
            return False
    
    def _derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """パスワードから鍵導出"""
        if len(password) < self.config.password_min_length:
            raise ValueError(f"パスワードは{self.config.password_min_length}文字以上である必要があります")
        
        if salt is None:
            salt = os.urandom(self.config.salt_length)
        
        if self.config.key_derivation == KeyDerivationMethod.PBKDF2:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.config.key_length,
                salt=salt,
                iterations=self.config.iterations,
                backend=default_backend()
            )
            return kdf.derive(password.encode('utf-8'))
        
        else:
            raise NotImplementedError(f"未対応の鍵導出方式: {self.config.key_derivation}")
    
    def _load_or_generate_master_key(self) -> Optional[bytes]:
        """マスターキー読み込みまたは生成"""
        try:
            # 環境変数から読み込み
            env_key = os.getenv('CONFIG_MASTER_KEY')
            if env_key:
                return base64.b64decode(env_key)
            
            # キーファイルから読み込み
            key_file = self.key_dir / "master.key"
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    return f.read()
            
            # 新規生成
            master_key = Fernet.generate_key()
            
            # キーファイルに保存
            with open(key_file, 'wb') as f:
                f.write(master_key)
            
            # ファイル権限設定（Unix系のみ）
            if hasattr(os, 'chmod'):
                os.chmod(key_file, 0o600)
            
            logger.info(f"新しいマスターキーを生成: {key_file}")
            return master_key
            
        except Exception as e:
            logger.error(f"マスターキー処理エラー: {e}")
            return None
    
    def _get_fernet_cipher(self, key: Optional[bytes] = None) -> Fernet:
        """Fernet暗号化オブジェクト取得"""
        if key is None:
            key = self._master_key
        
        if key is None:
            raise ValueError("暗号化キーが設定されていません")
        
        return Fernet(key)
    
    def _initialize_rsa_keys(self) -> bool:
        """RSAキーペア初期化"""
        try:
            private_key_file = self.key_dir / "rsa_private.pem"
            public_key_file = self.key_dir / "rsa_public.pem"
            
            if private_key_file.exists() and public_key_file.exists():
                # 既存キー読み込み
                with open(private_key_file, 'rb') as f:
                    self._rsa_private_key = serialization.load_pem_private_key(
                        f.read(), password=None, backend=default_backend()
                    )
                
                with open(public_key_file, 'rb') as f:
                    self._rsa_public_key = serialization.load_pem_public_key(
                        f.read(), backend=default_backend()
                    )
            
            else:
                # 新規キーペア生成
                self._rsa_private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=self.config.rsa_key_size,
                    backend=default_backend()
                )
                self._rsa_public_key = self._rsa_private_key.public_key()
                
                # キーファイル保存
                with open(private_key_file, 'wb') as f:
                    f.write(self._rsa_private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                
                with open(public_key_file, 'wb') as f:
                    f.write(self._rsa_public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ))
                
                # ファイル権限設定
                if hasattr(os, 'chmod'):
                    os.chmod(private_key_file, 0o600)
                    os.chmod(public_key_file, 0o644)
                
                logger.info("新しいRSAキーペアを生成")
            
            return True
            
        except Exception as e:
            logger.error(f"RSAキー初期化エラー: {e}")
            return False
    
    def encrypt_value(self, value: Any, method: EncryptionMethod = None) -> EncryptedData:
        """値の暗号化"""
        try:
            if method is None:
                method = self.config.method
            
            # 値をJSON文字列に変換
            if isinstance(value, str):
                plain_text = value
            else:
                plain_text = json.dumps(value, ensure_ascii=False)
            
            plain_bytes = plain_text.encode('utf-8')
            
            if method == EncryptionMethod.FERNET:
                return self._encrypt_fernet(plain_bytes)
            
            elif method == EncryptionMethod.RSA:
                return self._encrypt_rsa(plain_bytes)
            
            elif method == EncryptionMethod.SIMPLE:
                return self._encrypt_simple(plain_bytes)
            
            else:
                raise NotImplementedError(f"未対応の暗号化方式: {method}")
                
        except Exception as e:
            logger.error(f"値暗号化エラー: {e}")
            raise
    
    def decrypt_value(self, encrypted_data: Union[EncryptedData, Dict[str, Any]]) -> Any:
        """値の復号化"""
        try:
            if isinstance(encrypted_data, dict):
                encrypted_data = EncryptedData.from_dict(encrypted_data)
            
            method = EncryptionMethod(encrypted_data.method)
            
            if method == EncryptionMethod.FERNET:
                plain_bytes = self._decrypt_fernet(encrypted_data)
            
            elif method == EncryptionMethod.RSA:
                plain_bytes = self._decrypt_rsa(encrypted_data)
            
            elif method == EncryptionMethod.SIMPLE:
                plain_bytes = self._decrypt_simple(encrypted_data)
            
            else:
                raise NotImplementedError(f"未対応の復号化方式: {method}")
            
            plain_text = plain_bytes.decode('utf-8')
            
            # JSON形式の場合はパース
            try:
                return json.loads(plain_text)
            except json.JSONDecodeError:
                return plain_text
                
        except Exception as e:
            logger.error(f"値復号化エラー: {e}")
            raise
    
    def _encrypt_fernet(self, data: bytes) -> EncryptedData:
        """Fernet暗号化"""
        cipher = self._get_fernet_cipher()
        encrypted_bytes = cipher.encrypt(data)
        
        return EncryptedData(
            data=base64.b64encode(encrypted_bytes).decode('ascii'),
            method=EncryptionMethod.FERNET.value,
            timestamp=datetime.now().isoformat()
        )
    
    def _decrypt_fernet(self, encrypted_data: EncryptedData) -> bytes:
        """Fernet復号化"""
        cipher = self._get_fernet_cipher()
        encrypted_bytes = base64.b64decode(encrypted_data.data)
        return cipher.decrypt(encrypted_bytes)
    
    def _encrypt_rsa(self, data: bytes) -> EncryptedData:
        """RSA暗号化"""
        if not self._rsa_public_key:
            if not self._initialize_rsa_keys():
                raise RuntimeError("RSAキーの初期化に失敗")
        
        # RSAは小さなデータのみ暗号化可能
        max_size = (self.config.rsa_key_size // 8) - 42  # OAEP padding考慮
        if len(data) > max_size:
            raise ValueError(f"RSA暗号化データサイズ制限: {max_size}バイト")
        
        encrypted_bytes = self._rsa_public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return EncryptedData(
            data=base64.b64encode(encrypted_bytes).decode('ascii'),
            method=EncryptionMethod.RSA.value,
            timestamp=datetime.now().isoformat()
        )
    
    def _decrypt_rsa(self, encrypted_data: EncryptedData) -> bytes:
        """RSA復号化"""
        if not self._rsa_private_key:
            if not self._initialize_rsa_keys():
                raise RuntimeError("RSAキーの初期化に失敗")
        
        encrypted_bytes = base64.b64decode(encrypted_data.data)
        return self._rsa_private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def _encrypt_simple(self, data: bytes) -> EncryptedData:
        """簡易暗号化（開発用）"""
        # XOR暗号化（セキュアではない）
        key = b"simple_key_for_development_only"
        encrypted = bytes(a ^ b for a, b in zip(data, (key * (len(data) // len(key) + 1))[:len(data)]))
        
        return EncryptedData(
            data=base64.b64encode(encrypted).decode('ascii'),
            method=EncryptionMethod.SIMPLE.value,
            timestamp=datetime.now().isoformat()
        )
    
    def _decrypt_simple(self, encrypted_data: EncryptedData) -> bytes:
        """簡易復号化（開発用）"""
        encrypted_bytes = base64.b64decode(encrypted_data.data)
        key = b"simple_key_for_development_only"
        return bytes(a ^ b for a, b in zip(encrypted_bytes, (key * (len(encrypted_bytes) // len(key) + 1))[:len(encrypted_bytes)]))
    
    def encrypt_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """設定全体の暗号化"""
        try:
            encrypted_config = {}
            
            for key, value in config_data.items():
                if self._should_encrypt_key(key, value):
                    # 機密データを暗号化
                    encrypted_value = self.encrypt_value(value)
                    encrypted_config[key] = encrypted_value.to_dict()
                elif isinstance(value, dict):
                    # ネストした辞書を再帰処理
                    encrypted_config[key] = self.encrypt_config(value)
                else:
                    # 通常データはそのまま
                    encrypted_config[key] = value
            
            # メタデータ追加
            encrypted_config['_encryption_info'] = {
                'encrypted_at': datetime.now().isoformat(),
                'method': self.config.method.value,
                'version': '1.0.0'
            }
            
            return encrypted_config
            
        except Exception as e:
            logger.error(f"設定暗号化エラー: {e}")
            raise
    
    def decrypt_config(self, encrypted_config: Dict[str, Any]) -> Dict[str, Any]:
        """設定全体の復号化"""
        try:
            decrypted_config = {}
            
            for key, value in encrypted_config.items():
                if key.startswith('_'):
                    # メタデータはスキップ
                    continue
                
                if isinstance(value, dict) and value.get('_encrypted'):
                    # 暗号化データを復号化
                    decrypted_value = self.decrypt_value(value)
                    decrypted_config[key] = decrypted_value
                elif isinstance(value, dict):
                    # ネストした辞書を再帰処理
                    decrypted_config[key] = self.decrypt_config(value)
                else:
                    # 通常データはそのまま
                    decrypted_config[key] = value
            
            return decrypted_config
            
        except Exception as e:
            logger.error(f"設定復号化エラー: {e}")
            raise
    
    def _should_encrypt_key(self, key: str, value: Any) -> bool:
        """キーの暗号化要否判定"""
        key_lower = key.lower()
        
        # 機密キーパターンチェック
        for sensitive_key in self.sensitive_keys:
            if sensitive_key in key_lower:
                return True
        
        # 値の内容チェック
        if isinstance(value, str):
            # 長い文字列でキーっぽいもの
            if len(value) > 20 and any(c.isalnum() for c in value):
                return True
        
        return False
    
    def is_encrypted_data(self, data: Any) -> bool:
        """暗号化データ判定"""
        return isinstance(data, dict) and data.get('_encrypted', False)
    
    def rotate_master_key(self, new_password: Optional[str] = None) -> bool:
        """マスターキーローテーション"""
        try:
            # 新しいキー生成
            if new_password:
                new_key = self._derive_key_from_password(new_password)
            else:
                new_key = Fernet.generate_key()
            
            # 古いキーをバックアップ
            old_key = self._master_key
            
            # 新しいキーを設定
            self._master_key = new_key
            
            # キーファイル更新
            key_file = self.key_dir / "master.key"
            backup_file = self.key_dir / f"master.key.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if key_file.exists():
                key_file.rename(backup_file)
            
            with open(key_file, 'wb') as f:
                f.write(new_key)
            
            if hasattr(os, 'chmod'):
                os.chmod(key_file, 0o600)
            
            logger.info("マスターキーローテーション完了")
            return True
            
        except Exception as e:
            logger.error(f"マスターキーローテーションエラー: {e}")
            # 失敗時は古いキーを復元
            if 'old_key' in locals():
                self._master_key = old_key
            return False
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """暗号化情報取得"""
        return {
            'method': self.config.method.value,
            'key_derivation': self.config.key_derivation.value,
            'iterations': self.config.iterations,
            'rsa_key_size': self.config.rsa_key_size,
            'master_key_initialized': self._master_key is not None,
            'rsa_keys_initialized': self._rsa_private_key is not None,
            'key_dir': str(self.key_dir)
        }


# グローバルインスタンス
_config_encryption_instance: Optional[ConfigEncryption] = None


def get_config_encryption() -> ConfigEncryption:
    """ConfigEncryptionのシングルトンインスタンスを取得"""
    global _config_encryption_instance
    if _config_encryption_instance is None:
        _config_encryption_instance = ConfigEncryption()
        _config_encryption_instance.initialize_master_key()
    return _config_encryption_instance


# 使用例とテスト
if __name__ == "__main__":
    def test_config_encryption():
        """設定暗号化テスト"""
        print("=== 設定暗号化テスト ===")
        
        try:
            encryption = ConfigEncryption()
            encryption.initialize_master_key()
            
            # テストデータ
            test_config = {
                'api_key': 'sk-test123456789',
                'password': 'secret_password',
                'normal_setting': 'normal_value',
                'nested': {
                    'token': 'access_token_123',
                    'public_data': 'not_secret'
                }
            }
            
            print(f"元データ: {test_config}")
            
            # 暗号化
            encrypted_config = encryption.encrypt_config(test_config)
            print(f"暗号化後: {encrypted_config}")
            
            # 復号化
            decrypted_config = encryption.decrypt_config(encrypted_config)
            print(f"復号化後: {decrypted_config}")
            
            # 検証
            print(f"データ一致: {test_config == decrypted_config}")
            
            # 暗号化情報
            info = encryption.get_encryption_info()
            print(f"暗号化情報: {info}")
            
        except Exception as e:
            print(f"テストエラー: {e}")
    
    test_config_encryption()
