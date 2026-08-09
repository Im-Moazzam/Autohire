from cryptography.fernet import Fernet

from app.core.config import settings

_fernet = Fernet(settings.token_encryption_key)


def encrypt_token(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt_token(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()
