
"""
Users Service
Business logic for users domain.
"""

from anyio import to_thread
from app.common.utils.logger import app_logger
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
        profile: str,
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
                profile=profile
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

        user = await self.repo.get_by_email(email)
        if not user:
            raise BaseAppException(
                messages=[
                    "Invalid email or password"
                ],
                status_code=400,
            )
        if user.status != "A":
            raise BaseAppException(
                messages=[
                    "User account inactive"
                ],
                status_code=403,
            )

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

        
        key = build_cache_key(CACHE_KEY_USER_PROFILE, user_id)
        cached = None
        try:
            cached = await cache_get(key)
        except Exception as exc:
            app_logger.warning(
                f"profile_details cache_get failed | user_id={user_id} | error={str(exc)}"
            )
        if cached:
            return cached

        profile = await self.repo.get_profile_snapshot_by_id(user_id=user_id)
        if not profile:
            raise BaseAppException(
                messages=["User not found"],
                status_code=404,
            )
        
        data = {
            "id": profile.get("id", 0),
            "first_name": profile.get("first_name", ""),
            "last_name": profile.get("last_name", ""),
            "gender": profile.get("gender", ""),
            "profile": profile.get("profile", "User"),
            "mobile": profile.get("mobile", ""),
            "is_mobile_verified": profile.get("is_mobile_verified", "N"),
            "mobile_verified_last_datetime": (
                str(profile.get("mobile_verified_last_datetime"))
                if profile.get("mobile_verified_last_datetime") is not None else ""
            ),
            "email": profile.get("email"),
            "is_email_verified": profile.get("is_email_verified", "N"),
            "email_verified_last_datetime": (
                str(profile.get("email_verified_last_datetime"))
                if profile.get("email_verified_last_datetime") is not None else ""
            ),            
        }

        try:
            await cache_set(key, data, ttl=CACHE_TTL_PROFILE)
        except Exception as exc:
            app_logger.warning(
                f"profile_details cache_set failed | user_id={user_id} | error={str(exc)}"
            )

        return data