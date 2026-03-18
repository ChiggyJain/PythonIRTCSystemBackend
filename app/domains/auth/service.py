
"""
Auth Token Service

Handles JWT + DB tokens
"""

from datetime import timedelta
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
from app.domains.auth.repository.base import (
    TokenRepositoryBase,
)
from app.common.cache.redis_cache import (
    build_cache_key,
    cache_set,
    build_cache_set_key,
    cache_set_add,
    cache_delete,
    cache_set_remove,
)


settings = get_settings()


class TokenService:

    def __init__(
        self,
        repo: TokenRepositoryBase,
    ):
        self.repo = repo


    async def create_tokens(
        self,
        *,
        user_id: int,
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
            access_token_row = await self.repo.create_token(
                user_id=user_id,
                token_hash="temp",
                token_type="access",
                expires_at=access_expire,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            
            refresh_token_row = await self.repo.create_token(
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
                token_id=access_token_row.id,
                against_token_type="refresh",
                against_token_id=refresh_token_row.id
            )

            refresh_token = create_refresh_token(
                user_id=user_id,
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

            # Single DB commit for whole token creation flow.
            await self.repo.db.commit()

            
        except Exception:
            await self.repo.rollback()
            raise

        # storing access-token-row-id into redis for respective user
        # key-value with expire seconds
        cacheKey = build_cache_key(f"auth:user:access:jti:{access_token_row.id}")
        await cache_set(key=cacheKey, value=user_id, ttl=access_expire_seconds)

        # storing all access-token-row-id into redis for respective user
        # set format
        cacheKey = build_cache_set_key(f"auth:user:access:index:{user_id}")
        await cache_set_add(cacheKey, str(access_token_row.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }


    async def revoke(
        self,
        token_id: int|str,
    ):

        try:
            await self.repo.revoke_token(int(token_id))
            await self.repo.commit()
        except Exception:
            await self.repo.rollback()
            raise

    
    async def get_access(
        self,
        token_id: int|str,
    ):

        return await self.repo.get_by_id(token_id)
    
    
    async def get_refresh(
        self,
        token_id: int|str,
    ):

        return await self.repo.get_by_id(token_id)
    

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

            # Revoke old pair in same transaction
            await self.repo.revoke_token(old_access_id)
            await self.repo.revoke_token(old_refresh_id)
            
            # Create new pair
            new_access_row = await self.repo.create_token(
                user_id=user_id,
                token_hash="temp",
                token_type="access",
                expires_at=access_expire,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            new_refresh_row = await self.repo.create_token(
                user_id=user_id,
                token_hash="temp",
                token_type="refresh",
                expires_at=refresh_expire,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            new_access_token = create_access_token(
                user_id=user_id,
                token_id=new_access_row.id,
                against_token_type="refresh",
                against_token_id=new_refresh_row.id,
            )

            new_refresh_token = create_refresh_token(
                user_id=user_id,
                token_id=new_refresh_row.id,
                against_token_type="access",
                against_token_id=new_access_row.id,
            )

            new_access_row.token_hash = build_token_hash(new_access_token)
            new_access_row.updated_at = now_time

            new_refresh_row.token_hash = build_token_hash(new_refresh_token)
            new_refresh_row.updated_at = now_time

            await self.repo.commit()

        except Exception:
            await self.repo.rollback()
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

