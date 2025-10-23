from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12, deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def authenticate_user(user, password):
    if (
        not user
        or verify_password(plain_password=password, hashed_password=user.password)
        is False
    ):
        return None
    return user
