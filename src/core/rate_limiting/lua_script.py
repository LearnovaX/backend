"""
Lua scripts for atomic token bucket operations in Redis.

The Lua script ensures that token refill, consumption, and state updates happen atomically,
preventing race conditions in distributed environments.
"""

# Redis Lua script for token bucket rate limiting
# This script is executed atomically on the Redis server
TOKEN_BUCKET_SCRIPT = """
-- KEYS:
--   [1] rate_limit_key: e.g., "rl:user:123" or "rl:ip:192.168.1.1"
--
-- ARGV:
--   [1] capacity: maximum tokens allowed (burst capacity)
--   [2] refill_rate: tokens per second
--   [3] current_timestamp: current Unix timestamp (float)
--   [4] token_cost: number of tokens to consume (default 1)
--
-- RETURNS:
--   {allowed, current_tokens, retry_after_seconds}
--   - allowed: 1 if request allowed, 0 if denied
--   - current_tokens: remaining tokens after this operation
--   - retry_after_seconds: seconds until next token available (0 if allowed)

local rate_limit_key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local current_timestamp = tonumber(ARGV[3])
local token_cost = tonumber(ARGV[4])

-- Expiration time for the rate limit key (2 hours)
local KEY_EXPIRY = 7200

-- Get current state from Redis
local state = redis.call('HMGET', rate_limit_key, 'tokens', 'last_refill')
local current_tokens = tonumber(state[1]) or capacity
local last_refill = tonumber(state[2]) or current_timestamp

-- Calculate time elapsed since last refill (in seconds)
local time_elapsed = math.max(0, current_timestamp - last_refill)

-- Calculate tokens to add: elapsed_time * refill_rate
local tokens_to_add = time_elapsed * refill_rate

-- Calculate new token count, clamped to capacity
local new_tokens = math.min(capacity, current_tokens + tokens_to_add)

-- Determine if request is allowed
local allowed = 0
local retry_after = 0
local remaining_tokens = new_tokens

if new_tokens >= token_cost then
    -- Allow request and consume tokens
    allowed = 1
    remaining_tokens = new_tokens - token_cost
else
    -- Deny request
    allowed = 0
    -- Calculate how long until we have a token available
    -- tokens_needed = token_cost - new_tokens
    -- time_needed = tokens_needed / refill_rate
    local tokens_needed = token_cost - new_tokens
    retry_after = tokens_needed / refill_rate
    remaining_tokens = new_tokens
end

-- Update state in Redis
redis.call('HMSET', rate_limit_key, 'tokens', tostring(remaining_tokens), 'last_refill', tostring(current_timestamp))

-- Set expiry to clean up old keys
redis.call('EXPIRE', rate_limit_key, KEY_EXPIRY)

-- Return result
return {allowed, tostring(remaining_tokens), tostring(retry_after)}
"""

# Alternative Lua script with support for refill reset on large time gaps
# Useful if you want to reset the bucket if Redis connection was lost for too long
TOKEN_BUCKET_WITH_RESET_SCRIPT = """
-- Same as TOKEN_BUCKET_SCRIPT but with optional reset if time gap is too large
-- ARGV[5] (optional): max_time_gap - if elapsed time > max_time_gap, reset bucket

local rate_limit_key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local current_timestamp = tonumber(ARGV[3])
local token_cost = tonumber(ARGV[4])
local max_time_gap = tonumber(ARGV[5]) or 3600  -- 1 hour default

local KEY_EXPIRY = 7200

local state = redis.call('HMGET', rate_limit_key, 'tokens', 'last_refill')
local current_tokens = tonumber(state[1]) or capacity
local last_refill = tonumber(state[2]) or current_timestamp

local time_elapsed = math.max(0, current_timestamp - last_refill)

-- If time gap is too large, assume bucket should be reset
if time_elapsed > max_time_gap then
    current_tokens = capacity
    time_elapsed = 0
end

local tokens_to_add = time_elapsed * refill_rate
local new_tokens = math.min(capacity, current_tokens + tokens_to_add)

local allowed = 0
local retry_after = 0
local remaining_tokens = new_tokens

if new_tokens >= token_cost then
    allowed = 1
    remaining_tokens = new_tokens - token_cost
else
    allowed = 0
    local tokens_needed = token_cost - new_tokens
    retry_after = tokens_needed / refill_rate
    remaining_tokens = new_tokens
end

redis.call('HMSET', rate_limit_key, 'tokens', tostring(remaining_tokens), 'last_refill', tostring(current_timestamp))
redis.call('EXPIRE', rate_limit_key, KEY_EXPIRY)

return {allowed, tostring(remaining_tokens), tostring(retry_after)}
"""


def get_token_bucket_script():
    """Returns the token bucket Lua script."""
    return TOKEN_BUCKET_SCRIPT


def get_token_bucket_script_with_reset():
    """Returns the token bucket Lua script with reset support."""
    return TOKEN_BUCKET_WITH_RESET_SCRIPT
