from backend.app.dao.base import BaseDAO
from  backend.app.auth.models import User, Role


class UsersDAO(BaseDAO):
    model = User


class RoleDAO(BaseDAO):
    model = Role
