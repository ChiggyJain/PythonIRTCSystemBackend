
import json
from typing import (
    Any, Optional
)
from app.infrastructure.redis.client import get_redis



async def cache_get(
    key: str,
) -> Optional[Any]:

    redis = get_redis()
    value = await redis.get(key)
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return None


async def cache_set(
    key: str,
    value: Any,
    ttl: int = 300,
):

    redis = get_redis()
    if isinstance(value, str):
        data = value
    else:
        data = json.dumps(value)
    await redis.set(
        key,
        data,
        ex=ttl,
    )


async def cache_delete(
    key: str,
):

    redis = get_redis()
    await redis.delete(key)



async def cache_set_add(
    key: str,
    *members: str,
    ttl: int | None = None,
) -> int:
    
    if not members:
        return 0
    redis = get_redis()
    added = int(await redis.sadd(key, *members))
    # Optional TTL for auto cleanup.
    if ttl is not None:
        await redis.expire(key, ttl)
    return added


async def cache_set_members(
    key: str,
) -> set[str]:
    
    redis = get_redis()
    values = await redis.smembers(key)
    if not values:
        return set()
    return {str(v) for v in values}


async def cache_set_remove(
    key: str,
    *members: str,
) -> int:

    if not members:
        return 0
    redis = get_redis()
    return int(await redis.srem(key, *members))


async def cache_set_size(
    key: str,
) -> int:

    redis = get_redis()
    return int(await redis.scard(key))


async def cache_set_contains(
    key: str,
    member: str,
) -> bool:
    
    redis = get_redis()
    return bool(await redis.sismember(key, member))


async def cache_set_delete(
    key: str,
) -> int:
    
    redis = get_redis()
    return int(await redis.delete(key))



async def acquireBookingSeatLocksThroughRedis(allKeys, keyValue, ttlSeconds):

    lua_script = """
        local value = ARGV[1]
        local ttl = tonumber(ARGV[2])
        local insertedKeys = {}
        local failedKeys = {}
        for i = 1, #KEYS do
            local key = KEYS[i]
            local result = redis.call(
                "SET",
                key,
                value,
                "EX",
                ttl,
                "NX"
            )
            if not result then
                table.insert(failedKeys, key)
                for j = 1, #insertedKeys do
                    redis.call("DEL", insertedKeys[j])
                end
                return cjson.encode({
                    totalCntOfKeys = #KEYS,
                    insertedKeys = "",
                    failedKeys = table.concat(failedKeys, ","),
                    isSuccess = false
                })
            end
            table.insert(insertedKeys, key)
        end
        return cjson.encode({
            totalCntOfKeys = #KEYS,
            insertedKeys = table.concat(insertedKeys, ","),
            failedKeys = "",
            isSuccess = true
        })
    """

    redis = get_redis()
    response = await redis.eval(lua_script, len(allKeys), *allKeys, keyValue, ttlSeconds)
    response_dict = json.loads(response)
    return response_dict


async def releaseBookingSeatLocksThroughRedis(allKeys, keyValue):

    lua_script = """
        local value = ARGV[1]
        local releasedKeys = {}
        local failedKeys = {}
        for i = 1, #KEYS do
            local key = KEYS[i]
            local currentValue = redis.call("GET", key)
            if currentValue == value then
                redis.call("DEL", key)
                table.insert(releasedKeys, key)
            else
                table.insert(failedKeys, key)
            end
        end
        return cjson.encode({
            totalCntOfKeys = #KEYS,
            releasedKeys = table.concat(releasedKeys, ","),
            failedKeys = table.concat(failedKeys, ","),
            isSuccess = (#failedKeys == 0)
        })
    """

    redis = get_redis()
    response = await redis.eval(lua_script, len(allKeys), *allKeys, keyValue)
    response_dict = json.loads(response)
    return response_dict