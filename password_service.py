import binascii
import hashlib
import os


class PasswordService:
    """
    Provides methods to hash a password and to verify if
    password hash corresponds to the provided password.
    """
    @staticmethod
    def hash_password(password) -> str:
        """
        Hash provided password.
        :type password: str
        """
        salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
        pass_hash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                        salt, 100000)
        pass_hash = binascii.hexlify(pass_hash)
        return (salt + pass_hash).decode('ascii')

    @staticmethod
    def verify_password(hashed_password, password) -> bool:
        """
        Verify previously hashed password to match the provided one
        :type password: str
        :type hashed_password: str
        """
        salt = hashed_password[:64]
        hashed_password = hashed_password[64:]
        pass_hash = hashlib.pbkdf2_hmac('sha512',
                                        password.encode('utf-8'),
                                        salt.encode('ascii'), 100000)
        pass_hash = binascii.hexlify(pass_hash).decode('ascii')
        return pass_hash == hashed_password
