from database.db_readiness import is_db_ready


def test_is_db_ready_from_bundle() -> None:
    assert is_db_ready({"status": "up", "migrations": {"aligned": True}}) is True
    assert is_db_ready({"status": "down", "migrations": {"aligned": True}}) is False
    assert is_db_ready({"status": "up", "migrations": {"aligned": False}}) is False
    assert is_db_ready({"status": "down", "migrations": {"aligned": False}}) is False
