import os
import shutil
from pathlib import Path

from user_service import UserService


user_db = Path.cwd() / "test_user_db.json"
user_catalog = Path.cwd() / "test_users_dir"


def clean_env():
    try:
        os.remove(user_db)
        shutil.rmtree(user_catalog, ignore_errors=True)
    except OSError:
        pass


def test_user_service_new_user():
    clean_env()
    user_service = UserService(user_catalog, user_db)
    user_service.try_reg_user("admin", "admin")
    user = user_service.get_user("admin")
    assert user is not None
    clean_env()


def test_user_service_auth_user_fail():
    clean_env()
    user_service = UserService(user_catalog, user_db)
    user_service.try_reg_user("admin", "admin")
    assert user_service.auth_user("admin", "bad_pass") is False
    clean_env()


def test_user_service_auth_user_success():
    clean_env()
    user_service = UserService(user_catalog, user_db)
    user_service.try_reg_user("admin", "admin1234")
    assert user_service.auth_user("admin", "admin1234") is True
    clean_env()


def test_user_service_auth_add_file():
    clean_env()
    user_service = UserService(user_catalog, user_db)
    user_service.try_reg_user("admin", "admin1234")
    user_service.try_add_file("admin", "new_file")

    assert user_service.check_is_author("admin", "new_file") is True
    clean_env()
