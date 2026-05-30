import os
import tempfile
from sornaris.cache import BisectCache, make_cache_key


def test_make_cache_key_format():
    k = make_cache_key("abc", "gpt-4", "ex1")
    assert k == "abc|gpt-4|ex1"


def test_set_and_get_memory():
    c = BisectCache()
    c.set("k1", 0.85)
    assert c.get("k1") == 0.85
    c.close()


def test_get_missing_returns_none():
    c = BisectCache()
    assert c.get("nope") is None
    c.close()


def test_has_true_false():
    c = BisectCache()
    c.set("k", 1.0)
    assert c.has("k") is True
    assert c.has("missing") is False
    c.close()


def test_overwrite_existing_key():
    c = BisectCache()
    c.set("k", 0.5)
    c.set("k", 0.9)
    assert c.get("k") == 0.9
    c.close()


def test_clear_removes_all():
    c = BisectCache()
    c.set("a", 1.0)
    c.set("b", 0.0)
    c.clear()
    assert c.get("a") is None
    assert c.get("b") is None
    c.close()


def test_disk_persistence():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        c1 = BisectCache(path)
        c1.set("persisted", 0.42)
        c1.close()
        c2 = BisectCache(path)
        assert c2.get("persisted") == 0.42
        c2.close()
    finally:
        os.unlink(path)


def test_context_manager_closes():
    with BisectCache() as c:
        c.set("k", 1.0)
        assert c.get("k") == 1.0


def test_close_twice_does_not_raise():
    c = BisectCache()
    c.close()
    c.close()


def test_value_is_float_after_get():
    c = BisectCache()
    c.set("k", 1)  # int input
    v = c.get("k")
    assert isinstance(v, float)
    assert v == 1.0
    c.close()
