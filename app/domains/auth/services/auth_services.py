
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import BaseAppException
from app.common.security.token_decoder import (
    get_current_user_details_from_refresh_token
)
from app.core.exceptions import BaseAppException
from app.domains.auth.services.token_services import TokenService
from app.core.response import (
    standardize_response, 
)
from app.common.cache.redis_cache import (
    cache_delete,
    cache_set,
    cache_set_remove,
    cache_set_delete,
    cache_set_members,
    cache_set_add,
)
from app.common.security.token_hash import (
    is_token_hash_match,
)

class AuthService:


    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session

    

    async def rotate_tokens_by_refresh(self, payload: dict):
        
        try:
            
            # extracted parameters data
            refresh_token = payload.get("refresh_token", None)
            ip_address = payload.get("ip_address", None)
            user_agent = payload.get("user_agent", None)

            # Decode refresh token payload  
            user_details_from_refresh_token = await get_current_user_details_from_refresh_token(refresh_token)

            user_profile = user_details_from_refresh_token.get("profile", "User")
            user_id = int(user_details_from_refresh_token.get("sub"))
            access_token_id = int(user_details_from_refresh_token.get("against_token_id"))
            refresh_token_id = int(user_details_from_refresh_token.get("jti"))
            
            # token services
            token_services = TokenService(self._db_session)

            # fetching refresh-token details
            async with self._db_session.begin():
                access_token_row = await token_services.user_tokens_repo.get_by_id(access_token_id)
                refresh_token_row = await token_services.user_tokens_repo.get_by_id(refresh_token_id)

            # access token row validations
            if access_token_row and access_token_row.token_type != "access":
                return standardize_response(
                    status_code=401,
                    messages=["Invalid linked access token type"],
                )
    
            # refresh token row validations
            if not refresh_token_row:
                return standardize_response(
                    status_code=401,
                    messages=["Refresh token not found"]
                )
            if refresh_token_row.token_type != "refresh":
                return standardize_response(
                    status_code=401,
                    messages=["Invalid refresh token type"],
                )
            if int(refresh_token_row.user_id) != user_id:
                return standardize_response(
                    status_code=401,
                    messages=["Refresh token user mismatch"],
                )
            if refresh_token_row.revoked:
                return standardize_response(
                    status_code=401,
                    messages=["Refresh token already revoked"]
                )

            if not is_token_hash_match(
                raw_token=refresh_token, stored_hash=refresh_token_row.token_hash,
            ):
                return standardize_response(
                    status_code=401,
                    messages=["Invalid refresh token"],
                )
            

            # revoking all token pairs 
            # creating new token pairs
            async with self._db_session.begin():
                await token_services.user_tokens_repo.revoke_token(access_token_id)
                await token_services.user_tokens_repo.revoke_token(refresh_token_id)
                new_token_rsp = await token_services.create_tokens(
                    user_id=user_id,
                    user_profile=user_profile,
                    ip_address=ip_address,
                    user_agent=user_agent
                )

            # removing old tokens from cache
            old_access_key = f"user:access:jti:{access_token_id}"
            await cache_delete(key=old_access_key)
            user_access_index_key = f"user:access:index:{user_id}"
            await cache_set_remove(user_access_index_key, str(access_token_id))

            # cache insert for new access token
            new_access_key = f"user:access:jti:{new_token_rsp["access_token_id"]}"
            await cache_set(key=new_access_key, value=user_id, ttl=new_token_rsp["access_expire_seconds"])
            await cache_set_add(user_access_index_key, str(new_token_rsp["access_token_id"]))

            return standardize_response(
                status_code=200,
                messages=["Token refreshed successfully"],
                data={
                    "access_token" : new_token_rsp["access_token"],
                    "refresh_token" : new_token_rsp["refresh_token"]
                },
            )

        except BaseAppException as e:
            raise e
        
        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"],
            )


    async def logout_by_token_pair(self, payload: dict, user_details_from_access_token: dict):

        try:
            
            token_services = TokenService(self._db_session)

            # Decode refresh token payload
            refresh_token = payload["refresh_token"]
            user_details_from_refresh_token = await get_current_user_details_from_refresh_token(refresh_token)

            # Extract and normalize ids
            access_user_id = int(user_details_from_access_token.get("sub"))
            access_token_id = int(user_details_from_access_token.get("jti"))

            refresh_user_id = int(user_details_from_refresh_token.get("sub"))
            refresh_token_id = int(user_details_from_refresh_token.get("jti"))
            refresh_against_access_id = int(user_details_from_refresh_token.get("against_token_id"))

            # Token pair binding checks
            if access_user_id != refresh_user_id:
                return standardize_response(
                    status_code=401,
                    messages=["User-ID of access and refresh token mismatch"],
                )
            if access_token_id != refresh_against_access_id:
                return  standardize_response(
                    status_code=401,
                    messages=["Access-Token-ID is not match against refresh token"],
                )
            
            # fetching access-token and refresh-token row details
            async with self._db_session.begin():
                access_token_row = await token_services.user_tokens_repo.get_by_id(access_token_id)
                refresh_token_row = await token_services.user_tokens_repo.get_by_id(refresh_token_id)

            # Access token row validations    
            if not access_token_row:
                return standardize_response(
                    status_code=401,
                    messages=["Access token not found"],
                )
            if access_token_row.token_type != "access":
                return standardize_response(
                    status_code=401,
                    messages=["Invalid access token type"],
                ) 
            if int(access_token_row.user_id) != access_user_id:
                return standardize_response(
                    status_code=401,
                    messages=["User-ID is not match with stored access-token user-id"],
                )  

            # Refresh row validations
            if not refresh_token_row:
                return standardize_response(
                    status_code=401,
                    messages=["Refresh token not found"],
                )
            if refresh_token_row.token_type != "refresh":
                return standardize_response(
                    status_code=401,
                    messages=["Invalid refresh token type"],
                )
            if int(refresh_token_row.user_id) != refresh_user_id:
                return standardize_response(
                    status_code=401,
                    messages=["User-ID is not match with stored refresh-token user-id"],
                )
            if refresh_token_row.revoked:
                return standardize_response(
                    status_code=401,
                    messages=["Refresh token already revoked"],
                ) 
            
            if not is_token_hash_match(
                raw_token = refresh_token, stored_hash = refresh_token_row.token_hash,
            ):
                return standardize_response(
                    status_code=401,
                    messages=["Invalid refresh token"],
                )
            
            # revoking access and refresh tokens from db level
            async with self._db_session.begin():
                await token_services.user_tokens_repo.revoke_token(access_token_id)
                await token_services.user_tokens_repo.revoke_token(refresh_token_id)
            
            # removing from cache
            access_cache_key = f"user:access:jti:{access_token_id}"
            user_access_index_key = f"user:access:index:{access_user_id}"
            await cache_delete(key=access_cache_key)
            await cache_set_remove(user_access_index_key, str(access_token_id))
            
            return standardize_response(
                status_code=200,
                messages=["Logout successful from current active device session"],
            )
        
        except BaseAppException as e:
            raise e
        
        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"],
            )
        

    async def logout_from_all_devices_by_user_id(self, payload: dict, user_details_from_access_token: dict):

        try:
            
            token_services = TokenService(self._db_session)

            # Decode refresh token payload
            refresh_token = payload["refresh_token"]
            user_details_from_refresh_token = await get_current_user_details_from_refresh_token(refresh_token)

            # Extract and normalize ids
            access_user_id = int(user_details_from_access_token.get("sub"))
            access_token_id = int(user_details_from_access_token.get("jti"))

            refresh_user_id = int(user_details_from_refresh_token.get("sub"))
            refresh_token_id = int(user_details_from_refresh_token.get("jti"))
            refresh_against_access_id = int(user_details_from_refresh_token.get("against_token_id"))

            # Token pair binding checks
            if access_user_id != refresh_user_id:
                return standardize_response(
                    status_code=401,
                    messages=["User-ID of access and refresh token mismatch"],
                )
            if access_token_id != refresh_against_access_id:
                return  standardize_response(
                    status_code=401,
                    messages=["Access-Token-ID is not match against refresh token"],
                )
            
            # fetching access-token and refresh-token row details
            async with self._db_session.begin():
                access_token_row = await token_services.user_tokens_repo.get_by_id(access_token_id)
                refresh_token_row = await token_services.user_tokens_repo.get_by_id(refresh_token_id)

            # Access token row validations    
            if not access_token_row:
                return standardize_response(
                    status_code=401,
                    messages=["Access token not found"],
                )
            if access_token_row.token_type != "access":
                return standardize_response(
                    status_code=401,
                    messages=["Invalid access token type"],
                ) 
            if int(access_token_row.user_id) != access_user_id:
                return standardize_response(
                    status_code=401,
                    messages=["User-ID is not match with stored access-token user-id"],
                )  

            # Refresh row validations
            if not refresh_token_row:
                return standardize_response(
                    status_code=401,
                    messages=["Refresh token not found"],
                )
            if refresh_token_row.token_type != "refresh":
                return standardize_response(
                    status_code=401,
                    messages=["Invalid refresh token type"],
                )
            if int(refresh_token_row.user_id) != refresh_user_id:
                return standardize_response(
                    status_code=401,
                    messages=["User-ID is not match with stored refresh-token user-id"],
                )
            if refresh_token_row.revoked:
                return standardize_response(
                    status_code=401,
                    messages=["Refresh token already revoked"],
                ) 
            
            if not is_token_hash_match(
                raw_token = refresh_token, stored_hash = refresh_token_row.token_hash,
            ):
                return standardize_response(
                    status_code=401,
                    messages=["Invalid refresh token"],
                )
            
            # revoking all access and refresh tokens from db level
            async with self._db_session.begin():
                await token_services.user_tokens_repo.revoke_token_by_user(access_user_id)
            
            # removing from cache
            user_index_key = f"user:access:index:{access_user_id}"
            access_jti_set = await cache_set_members(key=user_index_key)
            for access_jti in access_jti_set:
                access_key = f"user:access:jti:{access_jti}"
                await cache_delete(key=access_key)
            await cache_set_delete(key=user_index_key)
            
            return standardize_response(
                status_code=200,
                messages=["Logout successful from all active devices session"],
            )
        
        except BaseAppException as e:
            raise e
        
        except Exception as e:
            return standardize_response(
                status_code=500,
                messages=[f"{str(e)}"],
            )


    