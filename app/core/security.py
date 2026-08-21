import uuid
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from app.core.config import settings


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access"
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> tuple[str, str]:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": jti,
        "type": "refresh"
    })
    token = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti


def decode_token(token: str, secret_key: str) -> dict:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token signature or payload")
