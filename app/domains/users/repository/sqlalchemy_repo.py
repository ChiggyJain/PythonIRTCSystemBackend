
"""
Users SQLAlchemy Repository

Implementation of UsersRepositoryBase
using SQLAlchemy async session.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.models import Users
from app.domains.users.repository.base import UsersRepositoryBase
from app.common.utils.datetime import now_ist


class UsersSQLAlchemyRepository(UsersRepositoryBase):
    """
    SQLAlchemy implementation of UsersRepositoryBase
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------------------------------
    # get_by_email
    # ---------------------------------

    async def get_by_email(
        self,
        email: str,
    ) -> Users | None:

        stmt = select(Users).where(
            Users.email == email
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    # ---------------------------------
    # create_user
    # ---------------------------------

    async def create_user(
        self,
        *,
        first_name: str,
        last_name: str,
        mobile: str,
        email: str,
        password: str,
        gender: str,
    ) -> Users:

        user = Users(
            first_name=first_name,
            last_name=last_name,
            mobile=mobile,
            email=email,
            password=password,
            gender=gender,
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