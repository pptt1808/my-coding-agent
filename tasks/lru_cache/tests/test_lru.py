from src.lru import LRUCache


def test_basic_put_get():
    c = LRUCache(2)
    c.put(1, 10)
    c.put(2, 20)
    assert c.get(1) == 10
    assert c.get(2) == 20
    assert c.get(3) == -1


def test_evicts_lru():
    c = LRUCache(2)
    c.put(1, 10)
    c.put(2, 20)
    c.put(3, 30)  # evicts 1
    assert c.get(1) == -1
    assert c.get(2) == 20
    assert c.get(3) == 30


def test_get_refreshes_recency():
    c = LRUCache(2)
    c.put(1, 10)
    c.put(2, 20)
    assert c.get(1) == 10  # 1 is now most recent
    c.put(3, 30)           # evicts 2
    assert c.get(2) == -1
    assert c.get(1) == 10


def test_update_existing_key_no_eviction():
    c = LRUCache(2)
    c.put(1, 10)
    c.put(2, 20)
    c.put(1, 99)
    assert c.get(1) == 99
    assert c.get(2) == 20


def test_zero_capacity():
    c = LRUCache(0)
    c.put(1, 10)
    assert c.get(1) == -1
