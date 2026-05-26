# Token Bucket Algorithm & Refill Math

## The Token Bucket Algorithm

The token bucket is a classic algorithm for rate limiting with burst support.

### Key Components

1. **Capacity**: Maximum tokens that can accumulate
2. **Refill Rate**: Tokens added per second
3. **Current Tokens**: Tokens available right now
4. **Last Refill**: Timestamp when tokens were last updated

### Example

```
Capacity: 10 tokens
Refill Rate: 1 token/second

Timeline:
─────────────────────────────────────────
Time    Event                   Tokens
─────────────────────────────────────────
T0      Initialize              10 (full)
T0      Request 1               9 (consume 1)
T0+0.1s Request 2               8
T0+0.2s Request 3               7
...
T0+1.0s Refill + Request 4      7 → 8 → 7 (added 1, consumed 1)
T0+2.0s 2 seconds idle          9 (added 2)
        Request 5               8
T0+20s  20 seconds idle         10 (clamped to capacity)
        Request 6               9
```

## Refill Calculation

The core calculation happens in the Lua script:

```lua
local time_elapsed = current_timestamp - last_refill
local tokens_to_add = time_elapsed * refill_rate
local new_tokens = math.min(capacity, current_tokens + tokens_to_add)
```

### Example Calculation

```
Setup:
- current_tokens: 2
- last_refill: 1000.0
- current_timestamp: 1005.3
- refill_rate: 0.1 tokens/second
- capacity: 10

Calculation:
- time_elapsed = 1005.3 - 1000.0 = 5.3 seconds
- tokens_to_add = 5.3 * 0.1 = 0.53 tokens
- new_tokens = min(10, 2 + 0.53) = min(10, 2.53) = 2.53

Result: 2.53 tokens available
```

## Capacity vs Burst

### Capacity Defines Burst Size

```
Refill Rate: 1 token/second (60 per minute steady-state)
Capacity: 10 tokens

Burst:
- Without refill, can make 10 requests immediately
- After burst, must wait ~1 second per request (1/refill_rate)

Steady State:
- After burst is exhausted, average rate is refill_rate per second
```

### Why Capacity Matters

Without capacity (only refill rate):
```
Refill Rate: 1 token/second
Request pattern: 1 request, wait 1 second, 1 request, wait 1 second...
```

With capacity:
```
Capacity: 100, Refill Rate: 1 token/second
Request pattern: Burst 100 requests immediately, then 1 per second average
```

## Different Rate Limit Scenarios

### Scenario 1: Strict Rate Limiting (no burst)

```
Capacity: 1
Refill Rate: 1/60 token/second (1 per minute)

Effect:
- At most 1 concurrent request
- After request, must wait ~60 seconds
- No burst possible
```

### Scenario 2: Normal API Rate Limiting

```
Capacity: 1000
Refill Rate: 10 tokens/second (600 per minute)

Effect:
- Can burst 1000 requests
- After burst, average 10 per second
- Good for normal traffic spikes
```

### Scenario 3: Login Rate Limiting

```
Capacity: 5
Refill Rate: 0.1 tokens/second (6 per minute)

Effect:
- Can attempt 5 logins in succession
- After 5 attempts, need to wait ~10 seconds for 1 more
- Good for preventing password brute force
```

### Scenario 4: Very Permissive

```
Capacity: 10000
Refill Rate: 100 tokens/second (6000 per minute)

Effect:
- Can burst 10000 requests
- After burst, average 100 per second
- Good for high-volume internal APIs
```

## Token Cost (Advanced)

Our implementation supports variable token cost:

```python
limiter.is_allowed(identifier="user:123", token_cost=5)
```

### Use Cases

```
Default: token_cost = 1
- Simple requests

token_cost = 5
- Expensive operations (bulk uploads, complex searches)
- Cost is proportional to resource consumption

token_cost = 0.1
- Very fast operations
- Allow 10 per token's worth
```

### Calculation with Variable Cost

```
Setup:
- Capacity: 100
- Refill Rate: 10 tokens/second
- Current Tokens: 50
- Token Cost: 5

Check:
- Is 50 >= 5? Yes
- Allow request
- Remaining: 50 - 5 = 45
```

## Time Precision

### Timestamp Resolution

The script uses float timestamps (seconds with decimal precision):

```lua
local current_timestamp = tonumber(ARGV[3])  -- Float: 1005.34567
```

This allows:
- Sub-second refill precision
- Smooth refill behavior
- Accurate burst calculation

### Floating Point Tokens

Tokens can be fractional:

```
Refill Rate: 0.1 tokens/second
After 5 seconds:
- Tokens to add: 5 * 0.1 = 0.5 tokens
- New tokens: 2 + 0.5 = 2.5 tokens
```

This prevents "quantization" where small refill rates would have jumpy behavior.

## Deny Case: retry_after Calculation

When a request is denied, the script calculates time until next token:

```lua
if new_tokens >= token_cost then
    allowed = 1
else
    allowed = 0
    local tokens_needed = token_cost - new_tokens
    retry_after = tokens_needed / refill_rate
end
```

### Example

```
Setup:
- Capacity: 3
- Refill Rate: 0.1 tokens/second
- Current Tokens: 0.3
- Requesting: 1 token

Calculation:
- tokens_needed = 1 - 0.3 = 0.7 tokens
- time_needed = 0.7 / 0.1 = 7 seconds
- Return: denied, retry_after = 7 seconds

Meaning: Please retry in 7 seconds
```

## State Persistence

The script stores state in Redis:

```lua
redis.call('HMSET', rate_limit_key, 
    'tokens', tostring(remaining_tokens),
    'last_refill', tostring(current_timestamp)
)
redis.call('EXPIRE', rate_limit_key, KEY_EXPIRY)
```

### Benefits

- Survives application restarts
- Shared across multiple application instances
- Persistent rate limit state

### State Structure

```
Redis Key: "rl:default_authenticated:user:123"
Type: Hash
Fields:
  - "tokens": "2.5"         # Current token count (float as string)
  - "last_refill": "1005.3" # Timestamp (float as string)
TTL: 7200 seconds (2 hours)
```

### Why Hash + TTL

- Hash: Easy to store multiple values atomically
- TTL: Automatic cleanup of stale identifiers
- No manual garbage collection needed

## Edge Cases

### Case 1: Large Time Gap

```
Scenario: Application was restarted, Redis connection lost for 1 hour

Old State:
- tokens: 5
- last_refill: 1000.0

New Check at T=4600.0:
- time_elapsed = 4600 - 1000 = 3600 seconds!
- tokens_to_add = 3600 * 0.1 = 360 tokens
- new_tokens = min(10, 5 + 360) = 10 (clamped to capacity)

Without clamping:
- Bucket would suddenly have 365 tokens!
- Could allow huge burst

Clamping ensures:
- Bucket is "recharged" to capacity
- No unexpected burst
```

### Case 2: Tiny Time Gap

```
Scenario: Two rapid requests in quick succession

Request 1 at T=1000.0:
- Check: 10 >= 1 ✓
- Update: tokens=9, last_refill=1000.0

Request 2 at T=1000.001 (1 millisecond later):
- time_elapsed = 1000.001 - 1000.0 = 0.001
- tokens_to_add = 0.001 * 0.1 = 0.0001
- new_tokens = 9 + 0.0001 = 9.0001
- Check: 9.0001 >= 1 ✓
- Update: tokens=8.0001, last_refill=1000.001

Result: Correctly counted both requests, tiny refill between
```

### Case 3: Exactly at Boundary

```
Scenario: Exactly 1 token left

Current: 1.0 tokens
Request: 1 token

Check:
- Is 1.0 >= 1? Yes (floating point comparison)
- Allow request
- Remaining: 1.0 - 1 = 0.0
```

## Comparison: Fixed-Window vs Token Bucket

### Fixed-Window Counting (NAIVE - Don't Use)

```
Window size: 1 minute
Limit: 60 requests per window

Issue:
T=59s: 60 requests allowed
T=60s: Window resets
T=60.1s: 60 more requests allowed
Result: 120 requests in 1.1 seconds (2x limit!)
```

### Token Bucket (OUR IMPLEMENTATION)

```
Capacity: 60
Refill Rate: 1 token/second

Effect:
- Max 60 burst
- Average 1/second sustained
- No reset boundary issues
- Smooth rate limiting
```

## Mathematical Properties

### Sustained Rate

```
Capacity: C
Refill Rate: R tokens/second

After infinite time (bucket full):
- Sustainable rate = R tokens/second
- No more tokens than capacity (clamped)
- Steady state throughput = refill_rate
```

### Burst Allowance

```
Capacity: C
Refill Rate: R tokens/second

Burst duration = C / R seconds
Example:
- Capacity: 100
- Refill: 10 tokens/second
- Burst duration: 100 / 10 = 10 seconds
- Can burst at capacity rate for 10 seconds
```

### Recovery Time

```
After exhausting capacity, time to recover:
- Recovery time = Capacity / Refill Rate
- Example: Capacity=10, Rate=1/sec → 10 seconds to refill

After using N tokens:
- Time to recover = N / Refill Rate
```

## Configuring for Your Needs

### Calculate Refill Rate from Desired Throughput

```python
desired_requests_per_minute = 100
refill_rate = desired_requests_per_minute / 60  # = 1.67 tokens/second
capacity = 10  # Allow 10-token burst
```

### Calculate Burst Duration

```python
# Want 1-minute sustained rate of 60 req/min, 10-second burst
sustained_rate = 60 / 60  # = 1 token/second
burst_duration = 10  # seconds
capacity = sustained_rate * burst_duration  # = 10 tokens
refill_rate = sustained_rate  # = 1 token/second
```

### Safe Defaults

```python
# Conservative (prevent abuse)
capacity = 5
refill_rate = 0.1  # 6 requests per minute

# Balanced (normal API)
capacity = 1000
refill_rate = 10  # 600 requests per minute

# Permissive (high volume)
capacity = 10000
refill_rate = 100  # 6000 requests per minute
```

## Conclusion

The token bucket algorithm provides smooth, burst-friendly rate limiting. The key insight is:

- **Capacity** controls burst size
- **Refill Rate** controls sustained throughput
- **Clamping** prevents unbounded accumulation
- **Floating-point math** enables smooth refill

Together, these create a flexible, fair rate limiting system suitable for production APIs.
