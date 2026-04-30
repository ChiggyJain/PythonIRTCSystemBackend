
"""
Users SQLAlchemy Repository
Implementation of UsersRepositoryBase
using SQLAlchemy async session.
"""

from typing import Any
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.models.users_models import Users
from app.domains.users.repository.base import UsersRepositoryBase
from app.common.utils.datetime import now_ist


class UsersSQLAlchemyRepository(UsersRepositoryBase):

    """
    SQLAlchemy implementation of UsersRepositoryBase
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    
    async def get_by_email(
        self,
        email: str,
    ) -> Users | None:

        stmt = select(Users).where(
            Users.email == email
        )
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    
    async def create_user(
        self,
        *,
        first_name: str,
        last_name: str,
        mobile: str,
        email: str,
        password: str,
        gender: str,
        profile: str
    ) -> Users:

        user = Users(
            first_name=first_name,
            last_name=last_name,
            mobile=mobile,
            email=email,
            password=password,
            gender=gender,
            profile=profile,
            status="A",
            created_at=now_ist(),
            updated_at=now_ist(),
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise
        await self.session.refresh(user)
        return user
    

    async def get_by_id(
        self,
        user_id: int,
    ) -> Users | None:

        stmt = select(Users).where(
            Users.id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    

    async def get_profile_snapshot_by_id(
        self,
        user_id: int,
    ) -> dict[str, Any] | None:

        # Select only profile fields needed by API response.
        stmt = select(
            Users.id.label("id"),
            Users.first_name.label("first_name"),
            Users.last_name.label("last_name"),
            Users.gender.label("gender"),
            Users.mobile.label("mobile"),
            Users.profile.label("profile"),
            Users.is_mobile_verified.label("is_mobile_verified"),
            Users.mobile_verified_last_datetime.label("mobile_verified_last_datetime"),
            Users.email.label("email"),
            Users.is_email_verified.label("is_email_verified"),
            Users.email_verified_last_datetime.label("email_verified_last_datetime"),
            
        ).where(
            Users.id == user_id
        )

        result = await self.session.execute(stmt)
        row = result.mappings().first()
        if not row:
            return None

        return dict(row)
