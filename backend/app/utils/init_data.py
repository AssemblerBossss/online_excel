from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core import app_settings
from backend.app.models import User
from backend.app.schemas import SUserRegister, SUserFilter
from backend.app.utils import get_password_hash
from backend.app.repository import UserRepository


async def init_admin_user(session: AsyncSession):
    email = app_settings.admin_credentials.email
    password = app_settings.admin_credentials.password
    user_dao = UserRepository(session)

    existing_user = await user_dao.find_one_or_none(filters=SUserFilter(email=email))
    if existing_user:
        print(f"Admin user already exists: {email}")
        return

    hashed_password = get_password_hash(password)

    admin_user = User(
        email=email,
        hashed_password=hashed_password,
        role="admin",
        is_active=True,
        first_name="admin",
        last_name="admin",
    )

    session.add(admin_user)
    await session.commit()
    print(f"Admin user created: {email}")
