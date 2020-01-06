import asyncio
import json
import logging
from functools import lru_cache

from websockets import ConnectionClosedError, WebSocketServerProtocol

from file_service import FileService
from user_service import UserService


class ClientHandler:
    """
    Handles all incoming requests from clients
    """

    def __init__(self, user_service: UserService, file_service: FileService):
        self.active_authors = []
        self.user_service = user_service
        self.file_service = file_service

    async def handle_new_patch(self, file_id, content, raw_patch) -> None:
        """
        Handle new patch from client
        :type file_id: str
        :type content: str
        :type raw_patch: bytes
        """
        self.file_service.register_patch(file_id, content)
        filename_authors = [user for user in self.active_authors if
                            user["current_file"] == file_id]
        # asyncio wait doesn't accept an empty list
        if filename_authors:
            await asyncio.wait([user["connection"].send(raw_patch) for user in
                                filename_authors])

    async def handle_send_file(self, filename, username, ws) -> None:
        """
        Send requested file to the user
        :type filename: str
        :type username: str
        :type ws: WebSocketServerProtocol
        """
        response = {"type": "file_request_response"}
        file_id, file_patches = self.file_service.get_patches(username,
                                                              filename)
        if file_patches is None:
            await self.msg_send({**response, "success": False}, ws)

        self.assign_file(file_id, ws)
        logging.info(f"[{username}] Sending known patches history...")
        await self.msg_send({**response, "success": True, "file_id": file_id,
                             "content": file_patches}, ws)

    async def handle_save_file(self, filename, username, ws) -> None:
        """
        Save requested file
        :type filename: str
        :type username: str
        :type ws: WebSocketServerProtocol
        """
        success = self.file_service.save_file(username, filename)
        await self.msg_send({"type": "save_file_response",
                             "success": success}, ws)

    async def handle_share_file(self, owner, share_user, filename, ws) -> None:
        """
        Share owner's file to share_user
        :type owner: str
        :type share_user: str
        :type filename: str
        :type ws: WebSocketServerProtocol
        """
        res = self.user_service.try_grant_access(owner, share_user, filename)
        await self.msg_send({"type": "file_share_response",
                             "success": res}, ws)

    async def handle_create_file(self, filename: str, username: str, ws) -> \
            None:
        """
        Create requested file for specified user
        :type filename: str
        :type username: str
        :type ws: WebSocketServerProtocol
        """
        response = {"type": "create_file_response"}
        logging.info(f"Creating file {filename}")

        if self.user_service.try_add_file(username, filename):
            message = {**response, "success": True,
                       "content": f"Successfully created {filename}"}
        else:
            message = {**response, "success": False,
                       "content": f"Failed to create {filename}"}

        await self.msg_send(message, ws)
        self.is_authorized.cache_clear()

    async def handle_all_files(self, username, ws) -> None:
        """
        Send a list of all files of user
        :type username: str
        :type ws: WebSocketServerProtocol
        """
        all_files = {
            "shared_files": self.user_service.get_shared_files(username),
            "files": self.user_service.get_owned_files(username)}

        await self.msg_send({"type": "all_files_response",
                             "content": all_files}, ws)

    def assign_file(self, file_id, ws) -> None:
        """
        Set current working file id of specified
        websocket to the provided one. It means that websocket is currently
        editing file with specified file id.
        :type file_id: str
        :type ws: WebSocketServerProtocol
        """
        author = next((element for element in self.active_authors if
                       element["connection"] == ws), None)
        if author:
            author["current_file"] = file_id
            logging.info(f"Assigned {file_id} to {author}")

    def authorize_message(self, message: dict) -> bool:
        """
        Verify that message is authorized to request action that is
        specified inside it.
        :type message: dict
        :return True if authorized, otherwise False
        """
        username: str = message.get("username")
        password: str = message.get("password")
        filename: str = message.get("filename")
        req_type: str = message.get("type")
        owner_name: str = message.get("owner")
        return self.is_authorized(username, password, filename, owner_name,
                                  req_type)

    async def handle_new_client(self, auth_data, ws) -> None:
        """
        Process newly joined websocket - log in / register
        :param auth_data: message received from websocket
        :type auth_data: Dict
        :type ws: WebSocketServerProtocol
        """
        logging.info(f"[register] New client joined: {ws}")
        action = None
        if auth_data["type"] == "user_register":
            action = self.user_service.try_reg_user
        elif auth_data["type"] == "user_login":
            action = self.user_service.auth_user

        if action and action(auth_data["username"], auth_data["password"]):
            await self.send_authorized_response(ws)
            self.is_authorized.cache_clear()
            self.active_authors.append(
                {"connection": ws, "current_file": None})
            logging.info("[register] Main author procedure: Done")
        else:
            await self.send_unauthorized_response(ws)

    @lru_cache(maxsize=128)
    def is_authorized(self, username, password, filename, owner_name,
                      req_type) -> bool:
        """
        Check if specified credentials combination is legit.
        :param username: user login
        :param password: user password (provided one)
        :param filename: filename to access
        :param owner_name: owner user login (if shared doc)
        :param req_type: type of the request
        :type username: str
        :type password: str
        :type filename: str
        :type owner_name: str
        :type req_type: str
        :return: True if legit, False if not legit
        """
        # if message does not contain required parts, reject
        if not username or not password:
            return False
        # if failed to authorize user, reject
        if not self.user_service.auth_user(username, password):
            return False
        if owner_name and self.user_service.has_access(owner_name, username,
                                                       filename):
            return True
        # if user has no permission for filename, reject
        if req_type in ["create_file_request", "all_files_request"]:
            return True
        if self.user_service.check_is_author(username, filename):
            return True
        return False

    @staticmethod
    def get_file_owner(data) -> str:
        """
        Check if request has file owner specified, if owner is specified
        then return it, otherwise consider username as original owner.
        :type data: dict
        :return: owner login
        """
        return data.get("username") if not data.get("owner") else data["owner"]

    async def send_unauthorized_response(self, ws) -> None:
        """
        Send "unauthorized" response to the client. It indicates that
        there was an error in credentials.
        :type ws: WebSocketServerProtocol
        """
        await self.msg_send({"type": "auth_response", "success": False,
                             "content": "Auth failure"}, ws)

    async def send_authorized_response(self, ws) -> None:
        """
        Send "authorized" response to the client.
        It indicates that provided credentials are legit.
        :type ws: WebSocketServerProtocol
        """
        await self.msg_send({"type": "auth_response", "success": True,
                             "content": "Auth success."}, ws)

    @staticmethod
    async def msg_send(message, ws) -> None:
        """
        Encode and send message to the websocket
        :type message: dict
        :type ws: WebSocketServerProtocol
        """
        encoded_message = json.dumps(message).encode("utf-8")
        await ws.send(encoded_message)

    async def handle_message(self, message, ws) -> None:
        """
        Determine message type and provide it
        to the corresponding handler method.
        :type message: bytes
        :type ws: WebSocketServerProtocol
        """
        data = json.loads(message.decode("utf-8"))
        msg_type = data["type"]
        owner_name = self.get_file_owner(data)

        if msg_type in ["user_register", "user_login"]:
            await self.handle_new_client(data, ws)

        elif not self.authorize_message(data):
            await self.send_unauthorized_response(ws)

        elif msg_type == "all_files_request":
            await self.handle_all_files(data["username"], ws)

        elif msg_type == "file_request":
            await self.handle_send_file(data["filename"], owner_name,
                                        ws)

        elif msg_type == "patch":
            await self.handle_new_patch(
                data["file_id"], data["content"], message)

        elif msg_type == "create_file_request":
            await self.handle_create_file(
                data["filename"], data["username"], ws)

        elif msg_type == "save_file_request":
            await self.handle_save_file(data["filename"], owner_name,
                                        ws)

        elif msg_type == "file_share_request":
            await self.handle_share_file(owner_name,
                                         data["share_user"],
                                         data["filename"], ws)
        else:
            logging.info("unsupported event: {}", data)

    async def unregister(self, ws) -> None:
        """
        Remove websocket from active authors list
        :type ws: WebSocketServerProtocol
        """
        author = next((author for author in self.active_authors if author[
            "connection"] == ws), None)
        self.active_authors.remove(author)

    async def handle_client(self, ws, _) -> None:
        """
        Websocket connection handler.
        :type ws: WebSocketServerProtocol
        :type _: Any
        """
        logging.info(f'New client {ws}')
        logging.info(' ({} existing clients)'.format(len(self.active_authors)))
        try:
            async for message in ws:
                await self.handle_message(message, ws)
        except (ConnectionResetError, ConnectionClosedError):
            logging.info(f"Client {ws} seems to gone away")
        finally:
            await self.unregister(ws)
