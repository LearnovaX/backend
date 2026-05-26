# Race Condition Prevention

## The Problem

In a distributed system with multiple application instances, concurrent requests for the same rate limit can create race conditions:

### Naive GET/SET Approach (UNSAFE)

```python
# WRONG! This has race conditions:
current_tokens = redis.get(key)              # Time T1: Read 10 tokens
if current_tokens >= 1:
    redis.set(key, current_tokens - 1)       # Time T2: Write 9 tokens
    return True
return False
```

### Race Condition Example

```
Thread 1                              Thread 2
reads tokens = 10                     (concurrent read)
                                      reads tokens = 10 (race!)
check: 10 >= 1 ✓
                                      check: 10 >= 1 ✓
set tokens = 9                        set tokens = 9 (race!)
allow request                         allow request
    ↓
Both threads allowed! But should only allow 1.
Should have been: T1 = 9, T2 = denied
```

### Why This Happens

Redis is single-threaded, but network I/O and application logic are not. Between the time one client sends `GET` and `SET`, another client can make its own `GET` call. The second client sees the old value.

## The Solution: Redis Lua Scripts

### Lua Script Atomicity

Lua scripts are executed atomically by Redis:

```lua
-- REDIS RUNS THIS ENTIRE SCRIPT WITHOUT INTERRUPTION
local tokens = redis.call('GET', key)
if tokens >= 1 then
    redis.call('SET', key, tokens - 1)
    return 1  -- allowed
end
return 0  -- denied
```

**This is atomic**: Redis executes the entire script in one operation. No other clients can interleave their commands.

### How It Works

```
Client 1 evalsha                     Client 2 evalsha
    ↓                                    ↓
[Redis queue]
    ↓                                    ↓
Redis processes Client 1 script ← No interruption!
    ↓
Client 1 gets result
    ↓
Redis processes Client 2 script ← Now executes
    ↓
Client 2 gets result
```

Each `evalsha` call is a single atomic operation from Redis's perspective.

## Our Implementation's Atomicity

Our Lua script is more complex (token bucket with refill), but maintains atomicity:

```lua
-- All of this happens atomically in Redis:

-- 1. Get current state
local state = redis.call('HMGET', rate_limit_key, 'tokens', 'last_refill')
local current_tokens = tonumber(state[1]) or capacity
local last_refill = tonumber(state[2]) or current_timestamp

-- 2. Calculate
local time_elapsed = current_timestamp - last_refill
local tokens_to_add = time_elapsed * refill_rate
local new_tokens = math.min(capacity, current_tokens + tokens_to_add)

-- 3. Check and update
if new_tokens >= token_cost then
    -- Atomic read-modify-write
    redis.call('HMSET', rate_limit_key, 'tokens', tostring(remaining_tokens), ...)
    return {1, tostring(remaining_tokens), tostring(0)}
else
    redis.call('HMSET', rate_limit_key, 'tokens', tostring(new_tokens), ...)
    return {0, tostring(new_tokens), tostring(retry_after)}
end
```

### Why This is Safe

1. **No GET/SET Race**: State is read AND written within the same Lua execution
2. **No TOCTOU Bug**: Time-Of-Check (if new_tokens >= token_cost) and Time-Of-Use (update state) are atomic
3. **No Lost Updates**: All increments/decrements are serialized by Redis
4. **Calculation Accuracy**: Time calculations (elapsed, refill) happen server-side, consistent
5. **No Dirty Reads**: No other client can read partial state during update

## Proof of Correctness

### Scenario: 2 concurrent requests, capacity = 10

```
Time    Client 1                           Client 2
─────────────────────────────────────────────────────
T0      Start request
T1      evalsha("RL:U:123", capacity=10,  Start request
        refill=1, now=1000)
T2      Redis receives evalsha1
        Lock all operations for this key
        Read: tokens=10, last_refill=990
        Calculate: new_tokens=10 (min(10, 10+10*1))
        Check: 10 >= 1 ✓
        Update: tokens=9, last_refill=1000
        Release lock
        Return: allowed=1, remaining=9
                                           evalsha2("RL:U:123", ...)
T3                                         Redis receives evalsha2
                                           Lock all operations
                                           Read: tokens=9 (not 10!)
                                           Calculate: new_tokens=9
                                           Check: 9 >= 1 ✓
                                           Update: tokens=8
                                           Release lock
                                           Return: allowed=1, remaining=8
T4      Client 1 returns allowed
                                           Client 2 returns allowed
Result: Both allowed, tokens: 10 → 9 → 8 ✓ CORRECT
```

### Counter-example: GET/SET Approach (Wrong)

```
Time    Client 1                           Client 2
─────────────────────────────────────────────────────
T0      GET RL:U:123
T1      Receive: 10                        GET RL:U:123
T2      Check: 10 >= 1 ✓                   Receive: 10 (RACE!)
T3      SET RL:U:123 = 9                   Check: 10 >= 1 ✓
T4      Return allowed                     SET RL:U:123 = 9 (RACE!)
T5                                         Return allowed
Result: Both allowed, tokens: 10 → 9 (lost decrement!)
        Should be: 10 → 9 → 8 ✗ WRONG
```

## Additional Safety Features

### 1. Timestamp Handling

Our script uses server-side timestamp from application:

```lua
local current_timestamp = tonumber(ARGV[3])  -- From application
```

This prevents clock skew issues between clients. But we still pass it from application for consistency.

### 2. Large Time Gap Reset

Optional: If time gap > max_time_gap, reset bucket:

```lua
local time_elapsed = current_timestamp - last_refill
if time_elapsed > max_time_gap then
    current_tokens = capacity  -- Reset
    time_elapsed = 0
end
```

Handles scenarios where Redis connection was lost and reconnected much later.

### 3. Clamping to Capacity

```lua
local new_tokens = math.min(capacity, current_tokens + tokens_to_add)
```

Prevents tokens from growing unbounded.

### 4. Expiry

```lua
redis.call('EXPIRE', rate_limit_key, KEY_EXPIRY)  -- 2 hours
```

Prevents stale keys from accumulating forever.

## Comparison: Redis Patterns

### Pattern 1: Naive Increment (UNSAFE)

```python
tokens = redis.get(key)
if tokens < capacity:
    redis.incr(key)
    return True
```

**Problem**: TOCTOU race between GET and INCR

### Pattern 2: INCR with Overflow Check (PARTIAL)

```python
if redis.incr(key) <= capacity:
    return True
redis.decr(key)
return False
```

**Problem**: Still has race for refill logic

### Pattern 3: Lua Script (SAFE)

```python
redis.evalsha(script, 1, key, capacity, refill_rate, now, cost)
```

**Advantage**: Fully atomic, handles all edge cases

## Testing Atomicity

Our test suite includes:

1. **Single-threaded rapid requests**
   - 5 rapid requests with capacity=3
   - Expected: 3 allowed, 2 denied
   - Tests sequential atomicity

2. **Multi-threaded concurrent requests**
   - ThreadPoolExecutor with 4 workers
   - 20 concurrent requests with capacity=10
   - Expected: exactly 10 allowed, 10 denied
   - Tests concurrent atomicity

3. **Multiple limiter instances**
   - 2 RateLimiter instances (simulating 2 app servers)
   - Consume tokens from instance 1
   - Read state from instance 2
   - Expected: shared state is consistent
   - Tests distributed atomicity

## Conclusion

The Lua script approach provides **true atomicity** that GET/SET patterns cannot achieve. This ensures correct distributed rate limiting across multiple application instances.

**Key Insight**: In Redis, Lua scripts are the only way to achieve atomic multi-step operations. Use them for any operation that requires consistency across multiple commands.
