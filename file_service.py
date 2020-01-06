import hashlib
import logging
from pathlib import Path
from typing import List, Tuple

from docengine import Doc


class FileService:
    """
    Performs all operations with files - loads, saves, applies patches
    """
    def __init__(self, users_dir):
        self.users_dir = users_dir
        self.patch_history = {}

    def register_patch(self, file_id, raw_patch) -> None:
        """
        Register document patch in patch history of the file with
        specified file id
        :param file_id: unique id of the file
        :param raw_patch: encoded patch
        :type file_id: str
        :type raw_patch: str
        """
        if file_id in self.patch_history:
            self.patch_history[file_id].append(raw_patch)

    def get_patches(self, username, filename) -> Tuple[str, List[str]] or None:
        """
        Load all patches for file of user from history. If no patches in
        history, try to load from disk. If there still no
        file patches available, return None.
        :param username: user login
        :param filename: file name
        :type username: str
        :type filename: str
        :return: unique file id and file patch history
        """
        file_id = self.get_file_id(username, filename)
        if file_id not in self.patch_history:
            file_path = self.users_dir / username / filename
            file_patches = self.try_load_file(file_path)
            if file_patches is not None:
                self.patch_history[file_id] = file_patches
            else:
                return None
        return file_id, self.patch_history[file_id]

    def save_file(self, username, filename) -> bool:
        """
        Save file of user to disk.
        :type username: str
        :type filename: str
        :return: True if success, if no file history loaded, or failed to save
        on disk, return False.
        """
        file_id = self.get_file_id(username, filename)
        file_path = self.users_dir / username / filename
        return (file_id in self.patch_history) and self.try_save_file(
            file_path, self.patch_history[file_id])

    @staticmethod
    def try_save_file(path, history) -> bool:
        """
        Try to save file of the user to the filesystem.
        Creates a new document, applies all the patches, then saves
        the resulting document's text to file.
        :param path: path to save
        :param history: patch history
        :type path: Path
        :type history: List[str]
        :return: True if successful, otherwise False
        """
        file_doc = Doc()
        file_doc.site = 0
        for patch in history:
            file_doc.apply_patch(patch)
        try:
            with open(path, 'w') as file:
                file.write(file_doc.text)
            return True
        except (OSError, IOError, FileNotFoundError):
            logging.info(f"Requested [{path}] was not found!")
            return False

    @staticmethod
    def try_load_file(path) -> List[str] or None:
        """
        Try to load file and return it as list of encoded patches
        :param path: path to file
        :type path: Path
        :return: list of file patches encoded to string
        """
        try:
            with open(path, 'r') as file:
                file_doc = Doc()
                file_doc.site = 0
                pos = 0
                result = []
                for line in file:
                    for char in line:
                        result.append(file_doc.insert(pos, char))
                        pos += 1
            return result
        except (OSError, IOError, FileNotFoundError):
            logging.info(f"Requested [{path}] was not found!")
            return None

    @staticmethod
    def get_file_id(username, filename) -> str:
        """
        Get unique id of user's file (user should be file owner)
        :param username: user login
        :param filename: file name
        :type username: str
        :type filename: str
        :return: Unique id of user's file
        """
        unique_name = username + "/#/" + filename
        return hashlib.sha224(unique_name.encode("utf-8")).hexdigest()
