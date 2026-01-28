import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Hasher:
    @staticmethod
    def get_password_hash(password: str) -> str:
        # hash long password with SHA256
        password_bytes = password.encode('utf-8')
        sha_hash = hashlib.sha256(password_bytes).hexdigest()
        return pwd_context.hash(sha_hash)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        sha_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        return pwd_context.verify(sha_hash, hashed_password)
