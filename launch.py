#!/usr/bin/env python3
import argparse
import asyncio
import logging
import socket
from pathlib import Path

import websockets

from file_service import FileService
from client_handler import ClientHandler
from user_service import UserService

logging.basicConfig(filename=".log", level=logging.DEBUG,
                    format='%(asctime)s %(message)s')


class ServerLauncher:
    """
    Launches a new multi user text editor server instance
    listening on ip and port specified
    """
    listen_ip = "localhost"
    listen_port = 8080
    users_dir = "users"

    def __init__(self):
        parser = argparse.ArgumentParser(
            description='Multi text editor server launcher')

        parser.add_argument('-i', '--ip', type=str,
                            help='ip address for server to listen',
                            required=False, default=self.listen_ip)
        parser.add_argument('-p', '--port', type=int,
                            help='port for server to listen',
                            required=False, default=self.listen_port)
        parser.add_argument('-d', '--dir', type=str,
                            help='users files directory (relative path)',
                            required=False, default=self.users_dir)

        args = parser.parse_args()
        self.listen_ip = args.ip
        self.listen_port = args.port
        self.host = (self.listen_ip, self.listen_port)
        self.users_dir = args.dir
        file_service = FileService(Path.cwd() / self.users_dir)
        user_service = UserService(Path.cwd() / self.users_dir)
        self.client_handler = ClientHandler(user_service, file_service)

    def run(self) -> None:
        """
        Run a server
        """
        try:
            start_server = websockets.serve(self.client_handler.handle_client,
                                            *self.host,
                                            max_size=None, ping_timeout=100)
            print(f"Launched on {self.listen_ip}:{self.listen_port}")
            asyncio.get_event_loop().run_until_complete(start_server)
            asyncio.get_event_loop().run_forever()
        except socket.gaierror:
            print(f'Error launching on {self.listen_ip}:{self.listen_port}.\n'
                  f'Will exit now')


if __name__ == "__main__":
    launcher = ServerLauncher()
    launcher.run()
