
from anyio import to_thread
from passlib import exc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.common.utils.logger import app_logger
from app.core.exceptions import BaseAppException
from app.core.response import (
    success_response, 
    error_response,
    exception_response
)
from app.common.utils.password import (
    hash_password, 
    verify_password
)
from app.domains.users.repository.sqlalchemy_repo import (
    UsersSQLAlchemyRepository
)
from app.common.cache.redis_cache import (
    cache_get,
    cache_set,
    build_cache_key,
)
from app.common.cache.redis_cache import (
    build_cache_key,
    cache_set,
    build_cache_set_key,
    cache_set_add,
    cache_delete,
    cache_set_remove,
    cache_set_delete,
    cache_set_members,
)
from app.common.cache.config import (
    CACHE_TTL_PROFILE,
    CACHE_KEY_USER_PROFILE,
)
from app.domains.auth.services.token_services import TokenService


class UsersService:

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.users_repo = UsersSQLAlchemyRepository(db_session)


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

            async with self._db_session.begin():
                user = await self.users_repo.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    mobile=mobile,
                    email=email,
                    password=hashed_password,
                    gender=gender,
                    profile=profile
                )

            return success_response(
                status_code=200,
                messages=["User created successfully"],
                data={
                    "userId": user.id,
                    "userEmail": user.email,
                },
            )
        
        except IntegrityError as e:
            return error_response(
                status_code=400,
                messages=["Email already exists"],
                data=None
            )
        except Exception as e:
            return exception_response(
                status_code=500,
                messages=[f"{str(e)}"],
                data=None
            )
        
    
    async def login_user(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):

        try:
            
            async with self._db_session.begin():
                user = await self.users_repo.get_by_email(email)

            if not user:
                return error_response(
                    status_code=400,
                    messages=[
                        "Invalid email or password"
                    ],
                )
            if user.status!="A":
                return error_response(
                    status_code=403,
                    messages=[
                        "User account inactive"
                    ],
                )

            # bcrypt verify is CPU-bound; run it in thread worker
            # so FastAPI event loop remains responsive under concurrency.
            is_valid = await to_thread.run_sync(verify_password, password, user.password)
            if not is_valid:
                return error_response(
                    status_code=400,
                    messages=[
                        "Invalid email or password"
                    ],
                )
            
            # token service
            token_service = TokenService(self._db_session)

            # creating tokens
            async with self._db_session.begin():
                token_rsp = await token_service.create_tokens(
                    user_id=user.id,
                    user_profile=user.profile,
                    ip_address=ip_address,
                    user_agent=user_agent
                )

            if token_rsp["access_token"]!="" and token_rsp["refresh_token"]!="":

                # storing access-token-row-id into redis for respective user
                # key-value with expire seconds
                cacheKey = f"user:access:jti:{token_rsp["access_token_id"]}"
                await cache_set(key=cacheKey, value=user.id, ttl=token_rsp["access_expire_seconds"])

                # storing all access-token-row-id into redis for respective user
                # set format
                cacheKey = build_cache_set_key(f"user:access:index:{user.id}")
                await cache_set_add(cacheKey, str(token_rsp["access_token_id"]))
                
                return success_response(
                    status_code=200,
                    messages=["Login successful"],
                    data={
                        "tokens" : {
                            "access_token" : token_rsp["access_token"],
                            "refresh_token" : token_rsp["refresh_token"]
                        }
                    },
                )
            
            else:
                return error_response(
                    status_code=400,
                    messages=token_rsp["messages"],
                    data=None
                )
        
        except Exception as e:
            return exception_response(
                status_code=500,
                messages=[f"{str(e)}"],
                data=None
            )
    

    async def get_profile_details(
        self,
        user_id: int,
    ):
        
        # extracting user profile data from redis-cache
        key = build_cache_key(CACHE_KEY_USER_PROFILE, user_id)
        cached = None
        try:
            cached = await cache_get(key)
        except Exception as exc:
            app_logger.warning(
                f"User profile details cache get failed | user_id={user_id} | error={str(exc)}"
            )
        if cached:
            return success_response(
                status_code=200,
                messages=["User profile details found successfully"],
                data=cached,
            )

        # fetching user profile data from db
        async with self._db_session.begin():
            profile = await self.users_repo.get_profile_snapshot_by_id(user_id=user_id)
            if not profile:
                return error_response(
                    status_code=404,
                    messages=["User profile details not found"],
                )
        
        # preparing user profile data for returning the response
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

        # storing user profile data into redis-cache
        try:
            await cache_set(key, data, ttl=CACHE_TTL_PROFILE)
        except Exception as exc:
            app_logger.warning(
                f"profile_details cache_set failed | user_id={user_id} | error={str(exc)}"
            )

        return success_response(
            status_code=200,
            messages=["User profile details found successfully"],
            data=data,
        )