
"""
Users Service
Business logic for users domain.
"""

from sqlalchemy.exc import IntegrityError
from app.core.exceptions import BaseAppException
from app.common.utils.password import (
    hash_password, 
    verify_password
)
from app.domains.users.repository.base import (
    UsersRepositoryBase,
)
from app.common.cache.redis_cache import (
    cache_get,
    cache_set,
    build_cache_key,
)
from app.common.cache.config import (
    CACHE_TTL_PROFILE,
    CACHE_KEY_USER_PROFILE,
)


class UsersService:
    """
    Users business logic
    """

    def __init__(
        self,
        repo: UsersRepositoryBase,
    ):
        self.repo = repo

    # ---------------------------------
    # signup user
    # ---------------------------------

    async def signup_user(
        self,
        *,
        first_name: str,
        last_name: str,
        mobile: str,
        email: str,
        password: str,
        gender: str,
    ):

        # -------------------------
        # check email exists
        # -------------------------

        existing = await self.repo.get_by_email(email)
        if existing:
            raise BaseAppException(
                messages=["Email already exists"],
                status_code=400,
            )

        # -------------------------
        # hash password
        # -------------------------

        hashed_password = hash_password(password)

        # -------------------------
        # create user
        # -------------------------

        try:

            user = await self.repo.create_user(
                first_name=first_name,
                last_name=last_name,
                mobile=mobile,
                email=email,
                password=hashed_password,
                gender=gender,
            )

        except IntegrityError:

            raise BaseAppException(
                messages=["Email already exists"],
                status_code=400,
            )

        return user
    


    # ---------------------------------
    # login user
    # ---------------------------------

    async def login_user(
        self,
        *,
        email: str,
        password: str,
    ):

        # -------------------------
        # get user
        # -------------------------

        user = await self.repo.get_by_email(email)

        # -------------------------
        # user not found
        # -------------------------

        if not user:
            raise BaseAppException(
                messages=[
                    "Invalid email or password"
                ],
                status_code=400,
            )

        # -------------------------
        # status check
        # -------------------------

        if user.status != "A":
            raise BaseAppException(
                messages=[
                    "User account inactive"
                ],
                status_code=403,
            )

        # -------------------------
        # verify password
        # -------------------------

        is_valid = verify_password(password, user.password,)
        if not is_valid:
            raise BaseAppException(
                messages=[
                    "Invalid email or password"
                ],
                status_code=400,
            )

        return user


    # ---------------------------------
    # profile details
    # ---------------------------------

    async def get_profile_details(
        self,
        user_id: int,
    ):

        # -------------------------
        # build cache key
        # -------------------------

        key = build_cache_key(
            CACHE_KEY_USER_PROFILE,
            user_id,
        )

        # -------------------------
        # try cache
        # -------------------------

        cached = await cache_get(key)
        if cached:
            return cached

        # -------------------------
        # DB fetch
        # -------------------------

        user = await self.repo.get_by_id(
            user_id
        )

        if not user:
            raise BaseAppException(
                messages=["User not found"],
                status_code=404,
            )

        data = {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "mobile": user.mobile,
            "gender": user.gender,
            "status": user.status,
        }

        # -------------------------
        # set cache
        # -------------------------

        await cache_set(
            key,
            data,
            ttl=CACHE_TTL_PROFILE,
        )

        return data