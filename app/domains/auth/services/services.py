
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.utils.logger import app_logger
from app.common.security.token_hash import (
    build_token_hash,
    is_token_hash_match,
)
from app.common.security.jwt import (
    create_access_token,
    create_refresh_token,
)
from app.common.utils.datetime import now_ist
from app.core.settings import get_settings
from app.domains.auth.repository.sqlalchemy_repo import TokenRepositorySQLAlchemy
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


settings = get_settings()


class TokenService:


    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.user_tokens_repo = TokenRepositorySQLAlchemy(db_session)


    async def create_tokens(
        self,
        *,
        user_id: int,
        user_profile: str = "User",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):

        # Single timestamp source for this flow
        now_time = now_ist()
        access_expire = now_time + timedelta(
            minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
        )
        access_expire_seconds = int(
            (access_expire - now_time).total_seconds()
        )
        refresh_expire = now_time + timedelta(
            days=settings.JWT_REFRESH_EXPIRE_DAYS
        )

        try:

            # Create rows first (flush-only) to get IDs.
            access_token_row = await self.user_tokens_repo.create_token(
                user_id=user_id,
                token_hash="temp",
                token_type="access",
                expires_at=access_expire,
                ip_address=ip_address,
                user_agent=user_agent,
            )  
            refresh_token_row = await self.user_tokens_repo.create_token(
                user_id=user_id,
                token_hash="temp",
                token_type="refresh",
                expires_at=refresh_expire,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            # Build JWTs with DB IDs.
            access_token = create_access_token(
                user_id=user_id,
                user_profile=user_profile,
                token_id=access_token_row.id,
                against_token_type="refresh",
                against_token_id=refresh_token_row.id
            )
            refresh_token = create_refresh_token(
                user_id=user_id,
                user_profile=user_profile,
                token_id=refresh_token_row.id,
                against_token_type="access",
                against_token_id=access_token_row.id
            )
            # Store only hashes.
            now_time = now_ist()
            access_token_row.token_hash = build_token_hash(access_token)
            access_token_row.updated_at = now_time
            refresh_token_row.token_hash = build_token_hash(refresh_token)
            refresh_token_row.updated_at = now_time

            # storing access-token-row-id into redis for respective user
            # key-value with expire seconds
            cacheKey = build_cache_key(f"auth:user:access:jti:{access_token_row.id}")
            await cache_set(key=cacheKey, value=user_id, ttl=access_expire_seconds)

            # storing all access-token-row-id into redis for respective user
            # set format
            cacheKey = build_cache_set_key(f"auth:user:access:index:{user_id}")
            await cache_set_add(cacheKey, str(access_token_row.id))

            return {
                "messages" : [f"Tokens generated successfully"],
                "access_token_id" : access_token_row.id,
                "access_token": access_token,
                "refresh_token_id" : refresh_token_row.id,
                "refresh_token": refresh_token,
                
            }

        except Exception as e:
            return {
                "messages" : [f"{str(e)}"],
                "access_token_id" : "",
                "access_token" : "",
                "refresh_token_id" : "",
                "refresh_token" : "",
            }

        


    async def revoke(
        self,
        token_id: int|str,
    ):

        try:
            await self.user_tokens_repo.revoke_token(int(token_id))
            await self.user_tokens_repo.commit()
        except Exception:
            await self.user_tokens_repo.rollback()
            raise

    
    async def get_access(
        self,
        token_id: int|str,
    ):

        return await self.user_tokens_repo.get_by_id(token_id)
    
    
    async def get_refresh(
        self,
        token_id: int|str,
    ):

        return await self.user_tokens_repo.get_by_id(token_id)
    

    def is_raw_token_matches_stored_hash(
        self,
        *,
        raw_token: str,
        stored_hash: str | None,
    ) -> bool:
        return is_token_hash_match(
            raw_token=raw_token,
            stored_hash=stored_hash,
        )
    

    async def rotate_tokens_by_refresh(
        self,
        *,
        user_id: int,
        user_profile: str = "User",
        current_access_token_id: int | str,
        current_refresh_token_id: int | str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:

        old_access_id = int(current_access_token_id)
        old_refresh_id = int(current_refresh_token_id)

        # Single timestamp source for this flow
        now_time = now_ist()

        access_expire = now_time + timedelta(
            minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
        )
        access_expire_seconds = int(
            (access_expire - now_time).total_seconds()
        )
        refresh_expire = now_time + timedelta(
            days=settings.JWT_REFRESH_EXPIRE_DAYS
        )

        try:

            # Revoke old toekn pair in same transaction
            await self.user_tokens_repo.revoke_token(old_access_id)
            await self.user_tokens_repo.revoke_token(old_refresh_id)
            
            # Create access token
            new_access_row = await self.user_tokens_repo.create_token(
                user_id=user_id,
                token_hash="temp",
                token_type="access",
                expires_at=access_expire,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            # Create refresh token
            new_refresh_row = await self.user_tokens_repo.create_token(
                user_id=user_id,
                token_hash="temp",
                token_type="refresh",
                expires_at=refresh_expire,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            new_access_token = create_access_token(
                user_id=user_id,
                user_profile=user_profile,
                token_id=new_access_row.id,
                against_token_type="refresh",
                against_token_id=new_refresh_row.id,
            )

            new_refresh_token = create_refresh_token(
                user_id=user_id,
                user_profile=user_profile,
                token_id=new_refresh_row.id,
                against_token_type="access",
                against_token_id=new_access_row.id,
            )

            new_access_row.token_hash = build_token_hash(new_access_token)
            new_access_row.updated_at = now_time

            new_refresh_row.token_hash = build_token_hash(new_refresh_token)
            new_refresh_row.updated_at = now_time

            await self._db_session.commit()

        except Exception:
            await self._db_session.rollback()
            raise

        # Cache cleanup for old access token
        old_access_key = build_cache_key(f"auth:user:access:jti:{old_access_id}")
        await cache_delete(key=old_access_key)

        user_access_index_key = build_cache_set_key(f"auth:user:access:index:{user_id}")
        await cache_set_remove(user_access_index_key, str(old_access_id))

        # Cache insert for new access token
        new_access_key = build_cache_key(f"auth:user:access:jti:{new_access_row.id}")
        await cache_set(key=new_access_key, value=user_id, ttl=access_expire_seconds)
        await cache_set_add(user_access_index_key, str(new_access_row.id))

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        }


    async def logout_by_token_pair(
        self,
        *,
        user_id: int,
        access_token_id: int | str,
        refresh_token_id: int | str,
    ) -> None:

        access_id = int(access_token_id)
        refresh_id = int(refresh_token_id)

        # Single DB transaction for both revokes
        try:
            await self.user_tokens_repo.revoke_token(access_id)
            await self.user_tokens_repo.revoke_token(refresh_id)
            await self._db_session.commit()
        except Exception:
            await self._db_session.rollback()
            raise

        # Cache cleanup: best-effort (DB already source of truth)
        access_cache_key = build_cache_key(f"auth:user:access:jti:{access_id}")
        user_access_index_key = build_cache_set_key(f"auth:user:access:index:{user_id}")

        try:
            await cache_delete(key=access_cache_key)
        except Exception as exc:
            app_logger.warning(
                f"logout cache_delete failed | key={access_cache_key} | error={str(exc)}"
            )

        try:
            await cache_set_remove(user_access_index_key, str(access_id))
        except Exception as exc:
            app_logger.warning(
                f"logout cache_set_remove failed | key={user_access_index_key} | access_id={access_id} | error={str(exc)}"
            )

    
    async def logout_from_all_devices_by_user_id(
        self,
        *,
        user_id: int,
    ) -> None:

        # Single DB transaction for both revokes
        try:
            await self.user_tokens_repo.revoke_token_by_user(user_id)
            await self._db_session.commit()
        except Exception:
            await self._db_session.rollback()
            raise


        # Cache cleanup as post-commit side-effect (best effort)
        user_index_key = build_cache_set_key(f"auth:user:access:index:{user_id}")
        try:
            access_jti_set = await cache_set_members(key=user_index_key)
            for access_jti in access_jti_set:
                access_key = build_cache_key(f"auth:user:access:jti:{access_jti}")
                try:
                    await cache_delete(key=access_key)
                except Exception as exc:
                    app_logger.warning(
                        f"logout_all_devices cache_delete failed | user_id={user_id} | key={access_key} | error={str(exc)}"
                    )
            try:
                await cache_set_delete(key=user_index_key)
            except Exception as exc:
                app_logger.warning(
                    f"logout_all_devices cache_set_delete failed | user_id={user_id} | key={user_index_key} | error={str(exc)}"
                )
        except Exception as exc:
            app_logger.error(
                f"logout_all_devices cache_cleanup failed | user_id={user_id} | error={str(exc)}"
            )
