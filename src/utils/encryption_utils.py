# src/utils/encryption_utils.py
"""
暗号化ユーティリティ
データ暗号化・復号化に関する共通機能を提供
"""

import os
import base64
import hashlib
import re
import secrets
from typing import Optional, Union, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from ..core.logger import get_logger


class EncryptionMethod(Enum):
    """暗号化方式"""
    FERNET = "fernet"
    AES_256_GCM = "aes_256_gcm"
    AES_256_CBC = "aes_256_cbc"


@dataclass
class EncryptionResult:
    """暗号化結果"""
    encrypted_data: bytes
    salt: Optional[bytes] = None
    iv: Optional[bytes] = None
    tag: Optional[bytes] = None
    method: str = "fernet"


@dataclass
class KeyInfo:
    """キー情報"""
    key: bytes
    salt: bytes
    iterations: int
    method: str


class EncryptionUtils:
    """暗号化ユーティリティクラス"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        if not CRYPTOGRAPHY_AVAILABLE:
            self.logger.warning("cryptographyライブラリが利用できません。暗号化機能は制限されます。")
        
        # デフォルト設定
        self.default_iterations = 100000
        self.default_key_length = 32
        self.salt_length = 16
        self.iv_length = 16
    
    def _check_cryptography(self) -> bool:
        """cryptographyライブラリの利用可能性をチェック"""
        if not CRYPTOGRAPHY_AVAILABLE:
            self.logger.error("cryptographyライブラリが必要です。pip install cryptographyでインストールしてください。")
            return False
        return True
    
    def generate_key(self, password: str, salt: Optional[bytes] = None,
                    iterations: int = None) -> KeyInfo:
        """パスワードから暗号化キーを生成"""
        try:
            if not self._check_cryptography():
                raise RuntimeError("cryptographyライブラリが利用できません")
            
            if salt is None:
                salt = os.urandom(self.salt_length)
            
            if iterations is None:
                iterations = self.default_iterations
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.default_key_length,
                salt=salt,
                iterations=iterations,
                backend=default_backend()
            )
            
            key = kdf.derive(password.encode('utf-8'))
            
            return KeyInfo(
                key=key,
                salt=salt,
                iterations=iterations,
                method="pbkdf2"
            )
            
        except Exception as e:
            self.logger.error(f"キー生成エラー: {e}")
            raise
    
    def generate_fernet_key(self) -> bytes:
        """Fernetキーを生成"""
        try:
            if not self._check_cryptography():
                raise RuntimeError("cryptographyライブラリが利用できません")
            
            return Fernet.generate_key()
            
        except Exception as e:
            self.logger.error(f"Fernetキー生成エラー: {e}")
            raise
    
    def encrypt_fernet(self, data: Union[str, bytes], key: bytes) -> bytes:
        """Fernetを使用してデータを暗号化"""
        try:
            if not self._check_cryptography():
                raise RuntimeError("cryptographyライブラリが利用できません")
            
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(data)
            
            return encrypted_data
            
        except Exception as e:
            self.logger.error(f"Fernet暗号化エラー: {e}")
            raise
    
    def decrypt_fernet(self, encrypted_data: bytes, key: bytes) -> bytes:
        """Fernetを使用してデータを復号化"""
        try:
            if not self._check_cryptography():
                raise RuntimeError("cryptographyライブラリが利用できません")
            
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data)
            
            return decrypted_data
            
        except Exception as e:
            self.logger.error(f"Fernet復号化エラー: {e}")
            raise
    
    def encrypt_aes_gcm(self, data: Union[str, bytes], key: bytes,
                       associated_data: Optional[bytes] = None) -> EncryptionResult:
        """AES-GCMを使用してデータを暗号化"""
        try:
            if not self._check_cryptography():
                raise RuntimeError("cryptographyライブラリが利用できません")
            
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # IVを生成
            iv = os.urandom(12)  # GCMでは96ビット（12バイト）のIVを使用
            
            # 暗号化
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            
            if associated_data:
                encryptor.authenticate_additional_data(associated_data)
            
            encrypted_data = encryptor.update(data) + encryptor.finalize()
            
            return EncryptionResult(
                encrypted_data=encrypted_data,
                iv=iv,
                tag=encryptor.tag,
                method="aes_256_gcm"
            )
            
        except Exception as e:
            self.logger.error(f"AES-GCM暗号化エラー: {e}")
            raise
    
    def decrypt_aes_gcm(self, encrypted_data: bytes, key: bytes, iv: bytes,
                       tag: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """AES-GCMを使用してデータを復号化"""
        try:
            if not self._check_cryptography():
                raise RuntimeError("cryptographyライブラリが利用できません")
            
            # 復号化
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            
            if associated_data:
                decryptor.authenticate_additional_data(associated_data)
            
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            return decrypted_data
            
        except Exception as e:
            self.logger.error(f"AES-GCM復号化エラー: {e}")
            raise
    
    def encrypt_aes_cbc(self, data: Union[str, bytes], key: bytes) -> EncryptionResult:
        """AES-CBCを使用してデータを暗号化"""
        try:
            if not self._check_cryptography():
                raise RuntimeError("cryptographyライブラリが利用できません")
            
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # パディング
            padding_length = 16 - (len(data) % 16)
            padded_data = data + bytes([padding_length] * padding_length)
            
            # IVを生成
            iv = os.urandom(16)
            
            # 暗号化
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            return EncryptionResult(
                encrypted_data=encrypted_data,
                iv=iv,
                method="aes_256_cbc"
            )
            
        except Exception as e:
            self.logger.error(f"AES-CBC暗号化エラー: {e}")
            raise
    
    def decrypt_aes_cbc(self, encrypted_data: bytes, key: bytes, iv: bytes) -> bytes:
        """AES-CBCを使用してデータを復号化"""
        try:
            if not self._check_cryptography():
                raise RuntimeError("cryptographyライブラリが利用できません")
            
            # 復号化
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # パディング除去
            padding_length = padded_data[-1]
            decrypted_data = padded_data[:-padding_length]
            
            return decrypted_data
            
        except Exception as e:
            self.logger.error(f"AES-CBC復号化エラー: {e}")
            raise
    
    def encrypt_data(self, data: Union[str, bytes], password: str,
                    method: EncryptionMethod = EncryptionMethod.FERNET) -> Dict[str, Any]:
        """データを暗号化（メタデータ付き）"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            result_dict = {
                'method': method.value,
                'timestamp': int(os.times().elapsed * 1000)  # ミリ秒タイムスタンプ
            }
            
            if method == EncryptionMethod.FERNET:
                # パスワードからキーを生成
                key_info = self.generate_key(password)
                fernet_key = base64.urlsafe_b64encode(key_info.key)
                
                encrypted_data = self.encrypt_fernet(data, fernet_key)
                
                result_dict.update({
                    'data': base64.b64encode(encrypted_data).decode('utf-8'),
                    'salt': base64.b64encode(key_info.salt).decode('utf-8'),
                    'iterations': key_info.iterations
                })
                
            elif method == EncryptionMethod.AES_256_GCM:
                key_info = self.generate_key(password)
                result = self.encrypt_aes_gcm(data, key_info.key)
                
                result_dict.update({
                    'data': base64.b64encode(result.encrypted_data).decode('utf-8'),
                    'salt': base64.b64encode(key_info.salt).decode('utf-8'),
                    'iv': base64.b64encode(result.iv).decode('utf-8'),
                    'tag': base64.b64encode(result.tag).decode('utf-8'),
                    'iterations': key_info.iterations
                })
                
            elif method == EncryptionMethod.AES_256_CBC:
                key_info = self.generate_key(password)
                result = self.encrypt_aes_cbc(data, key_info.key)
                
                result_dict.update({
                    'data': base64.b64encode(result.encrypted_data).decode('utf-8'),
                    'salt': base64.b64encode(key_info.salt).decode('utf-8'),
                    'iv': base64.b64encode(result.iv).decode('utf-8'),
                    'iterations': key_info.iterations
                })
            
            return result_dict
            
        except Exception as e:
            self.logger.error(f"データ暗号化エラー: {e}")
            raise
    
    def decrypt_data(self, encrypted_dict: Dict[str, Any], password: str) -> bytes:
        """データを復号化（メタデータ付き）"""
        try:
            method = encrypted_dict.get('method', 'fernet')
            
            if method == 'fernet':
                # キーを再生成
                salt = base64.b64decode(encrypted_dict['salt'])
                iterations = encrypted_dict.get('iterations', self.default_iterations)
                key_info = self.generate_key(password, salt, iterations)
                fernet_key = base64.urlsafe_b64encode(key_info.key)
                
                encrypted_data = base64.b64decode(encrypted_dict['data'])
                decrypted_data = self.decrypt_fernet(encrypted_data, fernet_key)
                
            elif method == 'aes_256_gcm':
                # キーを再生成
                salt = base64.b64decode(encrypted_dict['salt'])
                iterations = encrypted_dict.get('iterations', self.default_iterations)
                key_info = self.generate_key(password, salt, iterations)
                
                encrypted_data = base64.b64decode(encrypted_dict['data'])
                iv = base64.b64decode(encrypted_dict['iv'])
                tag = base64.b64decode(encrypted_dict['tag'])
                
                decrypted_data = self.decrypt_aes_gcm(encrypted_data, key_info.key, iv, tag)
                
            elif method == 'aes_256_cbc':
                # キーを再生成
                salt = base64.b64decode(encrypted_dict['salt'])
                iterations = encrypted_dict.get('iterations', self.default_iterations)
                key_info = self.generate_key(password, salt, iterations)
                
                encrypted_data = base64.b64decode(encrypted_dict['data'])
                iv = base64.b64decode(encrypted_dict['iv'])
                
                decrypted_data = self.decrypt_aes_cbc(encrypted_data, key_info.key, iv)
            
            else:
                raise ValueError(f"サポートされていない暗号化方式: {method}")
            
            return decrypted_data
            
        except Exception as e:
            self.logger.error(f"データ復号化エラー: {e}")
            raise
    
    def encrypt_file(self, file_path: Union[str, Path], password: str,
                    output_path: Optional[Union[str, Path]] = None,
                    method: EncryptionMethod = EncryptionMethod.FERNET) -> Path:
        """ファイルを暗号化"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
            
            if output_path is None:
                output_path = file_path.with_suffix(file_path.suffix + '.encrypted')
            else:
                output_path = Path(output_path)
            
            # ファイルを読み込み
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # 暗号化
            encrypted_dict = self.encrypt_data(file_data, password, method)
            
            # メタデータを追加
            encrypted_dict['original_filename'] = file_path.name
            encrypted_dict['original_size'] = len(file_data)
            
            # 暗号化されたファイルを保存
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(encrypted_dict, f, indent=2)
            
            self.logger.info(f"ファイルを暗号化しました: {file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"ファイル暗号化エラー: {e}")
            raise
    
    def decrypt_file(self, encrypted_file_path: Union[str, Path], password: str,
                    output_path: Optional[Union[str, Path]] = None) -> Path:
        """ファイルを復号化"""
        try:
            encrypted_file_path = Path(encrypted_file_path)
            
            if not encrypted_file_path.exists():
                raise FileNotFoundError(f"暗号化ファイルが見つかりません: {encrypted_file_path}")
            
            # 暗号化されたファイルを読み込み
            with open(encrypted_file_path, 'r', encoding='utf-8') as f:
                encrypted_dict = json.load(f)
            
            # 復号化
            decrypted_data = self.decrypt_data(encrypted_dict, password)
            
            # 出力パスを決定
            if output_path is None:
                original_filename = encrypted_dict.get('original_filename', 'decrypted_file')
                output_path = encrypted_file_path.parent / original_filename
            else:
                output_path = Path(output_path)
            
            # 復号化されたファイルを保存
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            self.logger.info(f"ファイルを復号化しました: {encrypted_file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"ファイル復号化エラー: {e}")
            raise
    
    def calculate_hash(self, data: Union[str, bytes], algorithm: str = 'sha256') -> str:
        """データのハッシュ値を計算"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            if algorithm.lower() == 'md5':
                hash_obj = hashlib.md5(data)
            elif algorithm.lower() == 'sha1':
                hash_obj = hashlib.sha1(data)
            elif algorithm.lower() == 'sha256':
                hash_obj = hashlib.sha256(data)
            elif algorithm.lower() == 'sha512':
                hash_obj = hashlib.sha512(data)
            else:
                raise ValueError(f"サポートされていないハッシュアルゴリズム: {algorithm}")
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"ハッシュ計算エラー: {e}")
            raise
    
    def calculate_file_hash(self, file_path: Union[str, Path],
                          algorithm: str = 'sha256', chunk_size: int = 8192) -> str:
        """ファイルのハッシュ値を計算"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
            
            if algorithm.lower() == 'md5':
                hash_obj = hashlib.md5()
            elif algorithm.lower() == 'sha1':
                hash_obj = hashlib.sha1()
            elif algorithm.lower() == 'sha256':
                hash_obj = hashlib.sha256()
            elif algorithm.lower() == 'sha512':
                hash_obj = hashlib.sha512()
            else:
                raise ValueError(f"サポートされていないハッシュアルゴリズム: {algorithm}")
            
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"ファイルハッシュ計算エラー: {e}")
            raise
    
    def generate_secure_token(self, length: int = 32) -> str:
        """セキュアなトークンを生成"""
        try:
            return secrets.token_urlsafe(length)
        except Exception as e:
            self.logger.error(f"セキュアトークン生成エラー: {e}")
            raise
    
    def generate_secure_password(self, length: int = 16,
                                include_uppercase: bool = True,
                                include_lowercase: bool = True,
                                include_digits: bool = True,
                                include_symbols: bool = True) -> str:
        """セキュアなパスワードを生成"""
        try:
            import string
            
            characters = ""
            if include_lowercase:
                characters += string.ascii_lowercase
            if include_uppercase:
                characters += string.ascii_uppercase
            if include_digits:
                characters += string.digits
            if include_symbols:
                characters += "!@#$%^&*()_+-=[]{}|;:,.<>?"
            
            if not characters:
                raise ValueError("少なくとも1つの文字種類を含める必要があります")
            
            password = ''.join(secrets.choice(characters) for _ in range(length))
            return password
            
        except Exception as e:
            self.logger.error(f"セキュアパスワード生成エラー: {e}")
            raise
    
    def verify_password_strength(self, password: str) -> Dict[str, Any]:
        """パスワード強度を検証"""
        try:
            import string
            
            result = {
                'score': 0,
                'strength': 'very_weak',
                'feedback': [],
                'length': len(password),
                'has_uppercase': bool(re.search(r'[A-Z]', password)),
                'has_lowercase': bool(re.search(r'[a-z]', password)),
                'has_digits': bool(re.search(r'\d', password)),
                'has_symbols': bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password))
            }
            
            # 長さによる評価
            if result['length'] >= 12:
                result['score'] += 2
            elif result['length'] >= 8:
                result['score'] += 1
            else:
                result['feedback'].append('パスワードは8文字以上にしてください')
            
            # 文字種類による評価
            char_types = sum([
                result['has_uppercase'],
                result['has_lowercase'],
                result['has_digits'],
                result['has_symbols']
            ])
            result['score'] += char_types
            
            if not result['has_uppercase']:
                result['feedback'].append('大文字を含めることを推奨します')
            if not result['has_lowercase']:
                result['feedback'].append('小文字を含めることを推奨します')
            if not result['has_digits']:
                result['feedback'].append('数字を含めることを推奨します')
            if not result['has_symbols']:
                result['feedback'].append('記号を含めることを推奨します')
            
            # 繰り返しパターンのチェック
            if re.search(r'(.)\1{2,}', password):
                result['score'] -= 1
                result['feedback'].append('同じ文字の繰り返しは避けてください')
            
            # 強度判定
            if result['score'] >= 6:
                result['strength'] = 'very_strong'
            elif result['score'] >= 5:
                result['strength'] = 'strong'
            elif result['score'] >= 4:
                result['strength'] = 'medium'
            elif result['score'] >= 2:
                result['strength'] = 'weak'
            else:
                result['strength'] = 'very_weak'
            
            return result
            
        except Exception as e:
            self.logger.error(f"パスワード強度検証エラー: {e}")
            raise


# グローバルインスタンス
_encryption_utils: Optional[EncryptionUtils] = None


def get_encryption_utils() -> EncryptionUtils:
    """グローバル暗号化ユーティリティを取得"""
    global _encryption_utils
    if _encryption_utils is None:
        _encryption_utils = EncryptionUtils()
    return _encryption_utils
