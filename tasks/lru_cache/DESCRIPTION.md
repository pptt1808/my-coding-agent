# Task: lru_cache (L4, data structure / algorithm)

Implement `LRUCache` in `src/lru.py` — a least-recently-used cache:
- `get(key)` returns the stored value, or `-1` if the key is absent; a
  successful `get` refreshes that key's recency;
- `put(key, value)` inserts or updates; inserting when at capacity evicts the
  **least recently used** key first;
- `put` on an existing key updates the value and refreshes recency (no eviction);
- if `capacity <= 0`, the cache stores nothing and `get` always returns `-1`;
- aim for O(1) average time per operation.

The hidden test suite covers these rules — make all tests pass before finishing.
