import os
import time as _time
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from clickhouse_driver import Client

from configg import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_S

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

# Client ClickHouse per login
ch = Client(
    host=os.getenv("CLICKHOUSE_HOST", "clickhouse-server"),
    port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
    user=os.getenv("CLICKHOUSE_USER", "default"),
    password=os.getenv("CLICKHOUSE_PASSWORD", ""),
    database=os.getenv("CLICKHOUSE_DATABASE", "nearyou"),
)

def authenticate_user(username: str, password: str):
    q = "SELECT user_id, password FROM users WHERE username = %(u)s LIMIT 1"
    rows = ch.execute(q, {"u": username})
    if not rows:
        return None
    user_id, pw = rows[0]
    if pw != password:
        return None
    return {"user_id": user_id}

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = _time.time() + JWT_EXPIRATION_S
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token non valido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        return {"user_id": user_id}
    except JWTError:
        raise credentials_exception
