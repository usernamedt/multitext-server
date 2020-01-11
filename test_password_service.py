from password_service import PasswordService


def test_password_diff_hash():
    good_pass = "123"
    good_pass_hash = PasswordService.hash_password(good_pass)
    strong_pass = "1234"
    strong_pass_hash = PasswordService.hash_password(strong_pass)
    assert good_pass_hash != strong_pass_hash


def test_password_verify_fail():
    good_pass = "123"
    good_pass_hash = PasswordService.hash_password(good_pass)
    bad_pass = "1234"
    assert not PasswordService.verify_password(good_pass_hash, bad_pass)


def test_password_verify_ok():
    good_pass = "123"
    good_pass_hash = PasswordService.hash_password(good_pass)
    assert PasswordService.verify_password(good_pass_hash, good_pass)
