
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.security.token_hash import (
    build_token_hash,
)
from app.common.security.jwt import (
    create_access_token,
    create_refresh_token,
)
from app.common.utils.datetime import now_ist
from app.core.settings import get_settings
from app.domains.auth.repository.sqlalchemy_repo import TokenRepositorySQLAlchemy


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
        refresh_expire_seconds = int(
            (refresh_expire - now_time).total_seconds()
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

            return {
                "messages" : [f"Tokens generated successfully"],
                "access_token_id" : access_token_row.id,
                "access_token": access_token,
                "access_expire_seconds" : access_expire_seconds,
                "refresh_token_id" : refresh_token_row.id,
                "refresh_token": refresh_token,
                "refresh_expire_seconds" : refresh_expire_seconds,                
            }

        except Exception as e:
            return {
                "messages" : [f"{str(e)}"],
                "access_token_id" : "",
                "access_token" : "",
                "access_expire_seconds" : "",
                "refresh_token_id" : "",
                "refresh_token" : "",
                "refresh_expire_seconds" : "",
            }

    