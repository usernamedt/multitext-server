import asyncio
import json
import unittest
from asyncio import Future, coroutine
from unittest import mock
from unittest.mock import MagicMock, Mock

import pytest
from websockets import ConnectionClosedError

from client_handler import ClientHandler
from docengine import Doc
from file_service import FileService


async def async_magic():
    pass


@unittest.mock.patch('client_handler.FileService')
@unittest.mock.patch('client_handler.UserService')
@pytest.mark.asyncio
async def test_client_handler_register(user_svc, file_svc):
    mock_client = MagicMock()
    raw_msg = bytes('{"username": "username", "password": "pass", '
                    '"filename": "", "type": "user_register"}', "utf-8")

    mock_client.__aiter__.return_value = [raw_msg]
    mock_client.return_value.send.return_value = Future()
    mock_client.return_value.send.return_value.set_result("123")
    user_svc.return_value.try_reg_user.return_value = True
    MagicMock.__await__ = lambda x: async_magic().__await__()

    user_svc_instance = user_svc.return_value()
    file_svc_instance = file_svc.return_value()
    client_handler = ClientHandler(user_svc_instance, file_svc_instance)

    await client_handler.handle_client(mock_client, None)
    response = mock_client.send.call_args.args[0]

    assert json.loads(response)["success"] is True


@unittest.mock.patch('client_handler.FileService')
@unittest.mock.patch('client_handler.UserService')
@pytest.mark.asyncio
async def test_client_handler_unauthorized(user_svc, file_svc):
    mock_client = MagicMock()
    raw_msg = bytes('{"username": "username", "password": "pass", '
                    '"filename": "xyz", "type": "file_request"}', "utf-8")
    mock_client.__aiter__.return_value = [raw_msg]
    mock_client.return_value.send.return_value = Future()
    mock_client.return_value.send.return_value.set_result("123")
    user_svc.auth_user.return_value = False
    MagicMock.__await__ = lambda x: async_magic().__await__()

    user_svc_instance = user_svc.return_value()
    user_svc_instance.auth_user.return_value = False
    file_svc_instance = file_svc.return_value()
    client_handler = ClientHandler(user_svc_instance, file_svc_instance)
    client_handler.active_authors.append(
        {"connection": mock_client, "current_file": None})

    await client_handler.handle_client(mock_client, None)
    response = mock_client.send.call_args.args[0]

    assert json.loads(response)["success"] is False


@unittest.mock.patch('client_handler.FileService')
@unittest.mock.patch('client_handler.UserService')
@pytest.mark.asyncio
async def test_client_handler_new_patch(user_svc, file_svc):
    mock_client = MagicMock()
    doc = Doc()
    patch = doc.insert(0, "A")
    file_id = FileService.get_file_id("r", "test")
    msg = {"username": "r", "password": "r", "filename": "test",
           "type": "patch", "content": patch, "file_id": file_id}
    raw_msg = json.dumps(msg).encode("utf-8")
    mock_client.__aiter__.return_value = [raw_msg]
    mock_client.return_value.send.return_value = Future()
    mock_client.return_value.send.return_value.set_result("123")
    user_svc.auth_user.return_value = False
    MagicMock.__await__ = lambda x: async_magic().__await__()

    user_svc_instance = user_svc.return_value()
    user_svc_instance.auth_user.return_value = True
    user_svc_instance.has_access.return_value = True
    file_svc_instance = file_svc.return_value()
    file_svc_instance.register_patch.return_value = None
    client_handler = ClientHandler(user_svc_instance, file_svc_instance)
    client_handler.active_authors.append(
        {"connection": mock_client, "current_file": file_id})

    await client_handler.handle_client(mock_client, None)
    response = mock_client.send.call_args.args[0]

    assert json.loads(response)["content"] == patch
