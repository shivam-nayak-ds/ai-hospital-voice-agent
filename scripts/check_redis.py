import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.db_pool import _db_cache_set, _db_cache_get

def main():
    test_key = "asha:test"
    test_val = "Redis is alive!"
    _db_cache_set(test_key, test_val, ttl=30)
    retrieved = _db_cache_get(test_key)
    print(f"Stored = {test_val!r}, Retrieved = {retrieved!r}")

if __name__ == "__main__":
    main()
