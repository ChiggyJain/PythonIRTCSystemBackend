
from fastapi import (
    Depends, Header
)
from app.core.exceptions import BaseAppException
from app.common.security.jwt import decode_token
from app.common.cache.redis_cache import (
    cache_get
)


async def get_current_user_id_from_access_token(
    authorization: str | None = Header(
        default=None
    ),
):

    if not authorization:
        raise BaseAppException(
            messages=["Authorization header missing"],
            status_code=401,
        )

    if not authorization.startswith("Bearer "):
        raise BaseAppException(
            messages=["Invalid authorization header"],
            status_code=401,
        )

    token = authorization.split(" ")[1]
    payload = decode_token(token) 
    if not payload:
        raise BaseAppException(
            messages=["Invalid token"],
            status_code=401,
        )
    if payload.get("type") != "access":
        raise BaseAppException(
            messages=["Invalid token type"],
            status_code=401,
        )

    user_id = payload.get("sub")
    jti = payload.get("jti")
    user_id_from_access_token_cache = await cache_get(key=f"user:access:jti:{jti}")
    if user_id_from_access_token_cache ==  None:
        raise BaseAppException(
            messages=["Access-Token (User-ID) is not found in stored cache"],
            status_code=401,
        )
    if int(user_id) != int(user_id_from_access_token_cache):
        raise BaseAppException(
            messages=["Access-Token (User-ID) is not matched with stored cache"],
            status_code=401,
        )
       
    return int(user_id)



async def get_current_user_details_from_access_token(
    authorization: str | None = Header(
        default=None
    ),
):

    if not authorization:
        raise BaseAppException(
            status_code=401,
            messages=["Authorization header missing"],
        )
    if not authorization.startswith("Bearer "):
        raise BaseAppException(
            status_code=401,
            messages=["Invalid authorization header"],
        )

    token = authorization.split(" ")[1]
    payload = decode_token(token)  
    if not payload:
        raise BaseAppException(
            status_code=401,
            messages=["Invalid token"],
        )
    if payload.get("type") != "access":
        raise BaseAppException(
            status_code=401,
            messages=["Invalid token type"],
        )
    
    user_id = payload.get("sub")
    jti = payload.get("jti")
    user_id_from_access_token_cache = await cache_get(key=f"user:access:jti:{jti}")
    if user_id_from_access_token_cache == None:
        raise BaseAppException(
            status_code=401,
            messages=["Invalid access token. Access token is not available into cache"],
        )
    if int(user_id)!=int(user_id_from_access_token_cache):
        raise BaseAppException(
            status_code=401,
            messages=["Access-Token (User-ID) is not matched with stored cache"],
        )       
    return payload



async def get_current_user_id_from_refresh_token(
    refresh_token: str,
):

    # decode the refresh token
    payload = decode_token(refresh_token)
    if not payload:
        raise BaseAppException(
            status_code=401,
            messages=["Invalid refresh token"],
        )
    if payload.get("type") != "refresh":
        raise BaseAppException(
            status_code=401,
            messages=["Invalid refresh token type"],
        )

    user_id = payload.get("sub")
    return int(user_id)


async def get_current_user_details_from_refresh_token(
    refresh_token: str,
):

    # decode the refresh token
    payload = decode_token(refresh_token)
    if not payload:
        raise BaseAppException(
            status_code=401,
            messages=["Invalid refresh token"],
        )
    if payload.get("type")!="refresh":
        raise BaseAppException(
            status_code=401,
            messages=["Invalid refresh token type"],
        )
    return payload



async def get_current_admin_user_details_from_access_token(
    user_details_from_access_token: dict = Depends(get_current_user_details_from_access_token),
):
    
    profile = str(user_details_from_access_token.get("profile") or "").strip()
    if profile != "Admin":
        raise BaseAppException(
            status_code=403,
            messages=["Only admin user can access this API"],            
        )
    return user_details_from_access_token

















