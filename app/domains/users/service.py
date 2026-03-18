
"""
Users Service
Business logic for users domain.
"""

from anyio import to_thread
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
        
        # bcrypt hashing is CPU-heavy; run in worker thread
        # to avoid blocking async event loop under concurrency.
        hashed_password = await to_thread.run_sync(hash_password, password)

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

        """
        is_valid = verify_password(password, user.password,)
        if not is_valid:
            raise BaseAppException(
                messages=[
                    "Invalid email or password"
                ],
                status_code=400,
            )
        """

        # bcrypt verify is CPU-bound; run it in thread worker
        # so FastAPI event loop remains responsive under concurrency.
        is_valid = await to_thread.run_sync(verify_password, password, user.password)
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

        key = build_cache_key(CACHE_KEY_USER_PROFILE, user_id)

        # -------------------------
        # try cache
        # -------------------------

        cached = await cache_get(key)
        if cached:
            return cached

        # -------------------------
        # DB fetch
        # -------------------------

        user = await self.repo.get_by_id(user_id=user_id)

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
            "is_email_verified" : user.is_email_verified,
            "email_verified_last_datetime" : str(user.email_verified_last_datetime) if user.email_verified_last_datetime!=None else "",
            "mobile": user.mobile,
            "gender": user.gender
        }

        # -------------------------
        # set cache
        # -------------------------

        await cache_set(key, data, ttl=CACHE_TTL_PROFILE,)

        return data