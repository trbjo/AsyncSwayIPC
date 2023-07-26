import asyncio
import errno
import json
import os
import sys

import orjson

magic_string = "i3-ipc"
magic_string_len = len(magic_string)
payload_length_length = 4
payload_type_length = 4

message_types = {
    "RUN_COMMAND": 0,
    "GET_WORKSPACES": 1,
    "SUBSCRIBE": 2,
    "GET_OUTPUTS": 3,
    "GET_TREE": 4,
    "GET_MARKS": 5,
    "GET_BAR_CONFIG": 6,
    "GET_VERSION": 7,
    "GET_BINDING_MODES": 8,
    "GET_CONFIG": 9,
    "SEND_TICK": 10,
    "SYNC": 11,
    "GET_INPUTS": 100,
    "GET_SEATS": 101,
}

events = {
    b"\x80\x00\x00\x00": "workspace",
    b"\x80\x00\x00\x01": "output",
    b"\x80\x00\x00\x02": "mode",
    b"\x80\x00\x00\x03": "window",
    b"\x80\x00\x00\x04": "barconfig_update",
    b"\x80\x00\x00\x05": "binding",
    b"\x80\x00\x00\x06": "shutdown",
    b"\x80\x00\x00\x07": "tick",
    b"\x80\x00\x00\x14": "bar_state_update",
    b"\x80\x00\x00\x15": "input",
}


def parse_header(header):
    event = header[magic_string_len + payload_length_length : :]
    rev_byte_order = event[::-1]
    return events.get(rev_byte_order, "unknown")


class SwayIPCSocket:
    def __init__(self):
        self.socket = next(os.environ.get(socket) for socket in ["SWAYSOCK", "I3SOCK"])
        if not self.socket:
            raise EnvironmentError("Could not find the socket")

        self.reader: asyncio.StreamReader = None  # pyright: ignore
        self.writer: asyncio.StreamWriter = None  # pyright: ignore

    async def connect(self):
        self.reader, self.writer = await asyncio.open_unix_connection(path=self.socket)

    async def reconnect(self, source: str):
        print(f"Socket error due to {source}, trying to reconnect… ", end="")
        await self.close()
        await asyncio.sleep(1)  # Use asyncio.sleep for async sleep
        await self.connect()
        print("reacquired socket!")

    async def send(self, message_type, command=""):
        payload_length = len(command)
        payload_type = message_types[message_type.upper()]

        data = magic_string.encode()
        data += payload_length.to_bytes(payload_length_length, sys.byteorder)
        data += payload_type.to_bytes(payload_type_length, sys.byteorder)
        data += command.encode()

        try:
            self.writer.write(data)
            await self.writer.drain()
        except ConnectionResetError:
            await self.reconnect("ConnectionResetError, send")
            await self.send(message_type, command)

    async def receive_event(self) -> tuple[str, dict | list]:
        header = await self.reader.read(
            magic_string_len + payload_length_length + payload_type_length
        )
        event = parse_header(header)
        payload_length_bytes = header[
            magic_string_len : magic_string_len + payload_length_length
        ]
        payload_length = int.from_bytes(payload_length_bytes, sys.byteorder)
        try:
            raw_response = await self.reader.read(payload_length)
            resp_decoded = orjson.loads(raw_response)
            return event, resp_decoded
        except orjson.JSONDecodeError as e:
            await self.reconnect("JSONDecodeError")
            return "error", {"success": False, "parse_error": False, "error": e}

    async def close(self):
        if self.writer and not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()

    async def send_receive(self, message_type, command=""):
        while True:
            try:
                await self.send(message_type, command)
                _, response = await self.receive_event()
                return response
            except (OSError, ConnectionError):
                await self.reconnect(
                    f"send_receive, msg type: {message_type} {command}"
                )


class SwayIPCConnection:
    def __init__(self, num_command_sockets=5, reconnect_delay=1) -> None:
        self.reconnect_delay = reconnect_delay
        self._command_sockets = [SwayIPCSocket() for _ in range(num_command_sockets)]
        self._command_socket_queue = asyncio.Queue()

        for socket in self._command_sockets:
            self._command_socket_queue.put_nowait(socket)

        self._event_socket = SwayIPCSocket()

    async def connect(self) -> None:
        while True:
            try:
                for socket in self._command_sockets:
                    await socket.connect()
                await self._event_socket.connect()
                break
            except (OSError, ConnectionError) as e:
                if e.errno != errno.ECONNREFUSED:
                    raise
                print("Connection lost, trying to reconnect…")
                await asyncio.sleep(self.reconnect_delay)

    async def subscribe(self, events: list[str]) -> bool:
        await self._event_socket.send("SUBSCRIBE", json.dumps(events))
        _, response = await self._event_socket.receive_event()
        status = response["success"]  # pyright: ignore
        if not status:
            raise ConnectionError(f"Could subscribe with {events}, reply: {response}")
        return status

    async def send_receive_wrapper(self, message: str, command: str = ""):
        socket = await self._command_socket_queue.get()
        try:
            result = await socket.send_receive(message, command)
        finally:
            # Return the command socket to the pool
            self._command_socket_queue.put_nowait(socket)
        return result

    async def run_command(self, command: str):
        return await self.send_receive_wrapper("RUN_COMMAND", command)

    async def get_workspaces(self):
        return await self.send_receive_wrapper("GET_WORKSPACES")

    async def get_tree(self):
        return await self.send_receive_wrapper("GET_TREE")

    async def get_outputs(self):
        return await self.send_receive_wrapper("GET_OUTPUTS")

    async def listen(self) -> tuple[str, str]:
        while True:
            try:
                event, response = await self._event_socket.receive_event()
                subevent = response["change"]  # pyright: ignore
                return event, subevent
            except (OSError, ConnectionError):
                await self._event_socket.reconnect("eventlistener")

    async def close(self) -> None:
        for socket in self._command_sockets:
            await socket.close()
        await self._event_socket.close()
