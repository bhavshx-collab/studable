"""
Studable API — Lua scripts for atomic Redis operations.

Scripts are registered with Redis once at startup and called by their SHA.
Using EVALSHA instead of EVAL avoids resending the script body each time.

Available scripts
-----------------
ATOMIC_QUEUE_JOIN
    Atomically checks that a user is not already in a queue before adding them.
    Keys:  KEYS[1] = queue key (ZSET),  KEYS[2] = request hash key
    Args:  ARGV[1] = user_id,  ARGV[2] = timestamp (score),
           ARGV[3] = mode,     ARGV[4] = ttl_seconds

ATOMIC_MATCH_RESERVE
    Pops the best candidate from the queue (excluding the requesting user)
    and sets a reservation key atomically to prevent double-matching.
    Keys:  KEYS[1] = queue key (ZSET),  KEYS[2] = reserved key prefix
    Args:  ARGV[1] = requesting_user_id,  ARGV[2] = ttl_seconds (reservation)
    Returns: candidate_user_id or empty string
"""

from __future__ import annotations

# ── Script sources ─────────────────────────────────────────────────────────────

ATOMIC_QUEUE_JOIN_SRC = """
local queue_key   = KEYS[1]
local req_key     = KEYS[2]
local user_id     = ARGV[1]
local score       = tonumber(ARGV[2])
local mode        = ARGV[3]
local ttl         = tonumber(ARGV[4])

-- Already in this queue?
local existing = redis.call('ZSCORE', queue_key, user_id)
if existing then
    return {0, 'already_queued'}
end

-- Add to sorted set (score = timestamp so FIFO ordering)
redis.call('ZADD', queue_key, score, user_id)

-- Store request metadata with TTL
redis.call('HMSET', req_key,
    'mode',      mode,
    'status',    'QUEUED',
    'joined_at', tostring(score),
    'match_id',  ''
)
redis.call('EXPIRE', req_key, ttl)

return {1, 'ok'}
"""

ATOMIC_MATCH_RESERVE_SRC = """
local queue_key      = KEYS[1]
local reserved_prefix = KEYS[2]
local requesting_uid = ARGV[1]
local ttl            = tonumber(ARGV[2])

-- Get all candidates ordered by wait time (ascending score = longest wait first)
local candidates = redis.call('ZRANGE', queue_key, 0, -1)

for _, uid in ipairs(candidates) do
    if uid ~= requesting_uid then
        -- Check not already reserved
        local res_key = reserved_prefix .. uid
        local already = redis.call('EXISTS', res_key)
        if already == 0 then
            -- Remove from queue and set reservation
            redis.call('ZREM', queue_key, uid)
            redis.call('SET', res_key, requesting_uid, 'EX', ttl)
            return uid
        end
    end
end

return ''
"""

# ── Loader ─────────────────────────────────────────────────────────────────────

_SHA_CACHE: dict[str, str] = {}


async def load_script(redis, name: str, src: str) -> str:
    """Upload *src* to Redis and return its SHA (cached after first call)."""
    if name not in _SHA_CACHE:
        sha = await redis.script_load(src)
        _SHA_CACHE[name] = sha
    return _SHA_CACHE[name]


async def run_atomic_queue_join(
    redis,
    queue_key: str,
    req_key: str,
    user_id: str,
    score: float,
    mode: str,
    ttl: int,
) -> tuple[bool, str]:
    """
    Atomically join the matching queue.

    Returns (success, reason).
    """
    sha = await load_script(redis, "queue_join", ATOMIC_QUEUE_JOIN_SRC)
    result = await redis.evalsha(sha, 2, queue_key, req_key, user_id, score, mode, ttl)
    success = int(result[0]) == 1
    reason = result[1].decode() if isinstance(result[1], bytes) else str(result[1])
    return success, reason


async def run_atomic_match_reserve(
    redis,
    queue_key: str,
    reserved_prefix: str,
    requesting_uid: str,
    ttl: int,
) -> str | None:
    """
    Atomically pop a candidate and reserve them.

    Returns candidate user_id or None.
    """
    sha = await load_script(redis, "match_reserve", ATOMIC_MATCH_RESERVE_SRC)
    result = await redis.evalsha(
        sha, 2, queue_key, reserved_prefix, requesting_uid, ttl
    )
    if isinstance(result, bytes):
        result = result.decode()
    return result if result else None
