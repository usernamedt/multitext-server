import logging
import os
from typing import List

from tinydb import Query, TinyDB
from tinydb.operations import set

from password_service import PasswordService


class UserService:
    """
    Provides functionality to interact with user database,
    create new users, add/delete/index files, check permissions for owned
    and shared files opening
    """

    def __init__(self, users_dir, db_name='users.json'):
        db = TinyDB(db_name)
        self.users = db.table('users')
        self.users_dir = users_dir
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.cleanup()
        self.index()

    def cleanup(self) -> None:
        """
        Remove files that do not exist on disk from database
        """
        all_users = self.users.all()
        for user in all_users:
            for file in user["files"]:
                if not (self.users_dir / user["name"] / file).is_file():
                    logging.info(f"Removed non-existing file {file}.")
                    user["files"].remove(file)
            for owner in user["shared_files"].keys():
                for file in user["shared_files"][owner]:
                    if not (self.users_dir / owner / file).is_file():
                        logging.info(f"Removed non-existing file {file}.")
                        user["shared_files"][owner].remove(file)
        self.users.write_back(all_users)

    def index(self) -> None:
        """
        Index files on disk and if there are new files,
        assign them to the users
        """
        all_users = self.users.all()
        for user in all_users:
            # if no directory, create one
            (self.users_dir / user["name"]).mkdir(parents=True, exist_ok=True)
            for filename in os.listdir(self.users_dir / user["name"]):
                if filename not in user["files"]:
                    user["files"].append(filename)
        self.users.write_back(all_users)

    def try_add_file(self, username, file) -> bool:
        """
        Try to add file to user collection
        :param username: user login
        :param file: file name
        :type username: str
        :type file: str
        :return: True if successful, otherwise False
        """
        if (self.users_dir / username / file).is_file():
            return False
        # if no directory, create one
        (self.users_dir / username).mkdir(parents=True, exist_ok=True)

        with open(self.users_dir / username / file, 'w'):
            pass
        logging.info(f"File {file} created successfully")

        exist_user = self.get_user(username)
        exist_user["files"].append(file)
        self.__save_field(username, 'files', exist_user["files"])
        return True

    def try_reg_user(self, username, password) -> bool:
        """
        Try to register user in database
        :param username: user login
        :param password: user password
        :type username: str
        :type password: str
        :return: True if successful, otherwise False
        """
        if self.get_user(username):
            return False
        pass_hash = PasswordService.hash_password(password)
        self.users.insert({"name": username,
                           "pass_hash": pass_hash,
                           "files": [],
                           "shared_files": {}})
        return True

    def get_user(self, username) -> dict:
        """
        Get user from database by username
        :param username: user login
        :type username: str
        :return: user entity
        """
        User = Query()
        return self.users.get(User.name == username)

    def auth_user(self, username, password) -> bool:
        """
        Authenticate user
        :param username: user login
        :param password: provided password
        :type username: str
        :type password: str
        :return: True if successful, otherwise False
        """
        exist_user = self.get_user(username)
        if not exist_user:
            return False
        return PasswordService.verify_password(exist_user["pass_hash"],
                                               password)

    def check_is_author(self, username, filename) -> bool:
        """
        Check if user owns a file with specified filename
        :param username: user login
        :param filename: file name
        :type username: str
        :type filename: str
        :return: True if user owns a file, otherwise False
        """
        exist_user = self.get_user(username)
        return filename in exist_user["files"]

    def has_access(self, owner, username, filename) -> bool:
        """
        Check if user has access to shared file
        :param owner: file owner
        :param username: user login
        :param filename: file name
        :type owner: str
        :type username: str
        :type filename: str
        :return: True if user has access, otherwise False
        """
        user = self.get_user(username)
        return (owner in user["shared_files"].keys()) and (
                filename in user["shared_files"][owner])

    def try_grant_access(self, owner, username, filename) -> bool:
        """
        Try to grant access for user to the file owned by
        specified owner
        :param owner: login of the file owner
        :param username: user login
        :param filename: file name
        :type owner: str
        :type username: str
        :type filename: str
        :return: True if operation succeeded, otherwise False
        """
        if username == owner:
            return False
        user = self.get_user(username)
        if user is None:
            return False
        if not user["shared_files"].get(owner):
            user["shared_files"][owner] = []
        if filename not in user["shared_files"][owner]:
            user["shared_files"][owner].append(filename)
        self.__save_field(username, 'shared_files', user["shared_files"])
        return True

    def __save_field(self, username, field_name, value) -> None:
        """
        Set field of user entity to the value provided
        :param username: user login
        :param field_name: user's field name
        :param value: value to set
        :type username: str
        :type field_name: str
        :type value: Any
        """
        User = Query()
        logging.info(f"Updating {username} field {field_name} with value "
                     f"{value}")
        self.users.update(set(field_name, value), User.name == username)

    def get_shared_files(self, username) -> List[dict]:
        """
        Get list of files shared with user
        :param username: user login
        :type username: str
        :return: List of dictionaries, with owners as keys and files as items
        """
        user = self.get_user(username)
        return user["shared_files"]

    def get_owned_files(self, username) -> List[str]:
        """
        Get list of filenames owned by user
        :param username: user login
        :type username: str
        :return: List of filenames owned by user
        """
        user = self.get_user(username)
        return user["files"]
