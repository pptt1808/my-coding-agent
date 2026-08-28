class LRUCache:
    """Least-recently-used cache. get() returns -1 for missing keys.

    Must support O(1) average get/put. Implement it.
    """

    def __init__(self, capacity: int):
        raise NotImplementedError

    def get(self, key: int) -> int:
        raise NotImplementedError

    def put(self, key: int, value: int) -> None:
        raise NotImplementedError
