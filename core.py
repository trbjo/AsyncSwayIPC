import asyncio
import errno
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
    0x80000000: "workspace",
    0x80000001: "output",
    0x80000002: "mode",
    0x80000003: "window",
    0x80000004: "barconfig_update",
    0x80000005: "binding",
    0x80000006: "shutdown",
    0x80000007: "tick",
    0x80000014: "bar_state_update",
    0x80000015: "input",
}


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
        await asyncio.sleep(1)
        await self.connect()
        print("reacquired socket")

    async def send(self, message_type, command=b""):
        payload_length = len(command)
        payload_type = message_types[message_type.upper()]

        data = magic_string.encode()
        data += payload_length.to_bytes(payload_length_length, sys.byteorder)
        data += payload_type.to_bytes(payload_type_length, sys.byteorder)
        data += command

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

        payload_length_bytes = header[
            magic_string_len : magic_string_len + payload_length_length
        ]
        payload_length = int.from_bytes(payload_length_bytes, sys.byteorder)

        try:
            raw_response = await self.reader.read(payload_length)
            resp_decoded = orjson.loads(raw_response)

            event_bytes = header[magic_string_len + payload_length_length : :]
            event_int = int.from_bytes(event_bytes, byteorder=sys.byteorder)
            event_human = events.get(event_int, "unknown")

            return event_human, resp_decoded

        except orjson.JSONDecodeError:
            await self.reconnect("JSONDecodeError")
            return "error", []

    async def close(self):
        if self.writer and not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()

    async def send_receive(self, message_type, command=""):
        while True:
            try:
                await self.send(message_type, command.encode())
                _, response = await self.receive_event()
                return response
            except (OSError, ConnectionError):
                await self.reconnect(
                    f"send_receive, msg type: {message_type} {command}"
                )


class SwayIPCConnection:
    def __init__(self, reconnect_delay=1) -> None:
        self.reconnect_delay = reconnect_delay
        self._sockets = [SwayIPCSocket() for _ in range(5)]

    async def connect(self) -> None:
        while True:
            try:
                for socket in self._sockets:
                    await socket.connect()
                break
            except (OSError, ConnectionError) as e:
                if e.errno != errno.ECONNREFUSED:
                    raise
                print("Connection lost, trying to reconnect…")
                await asyncio.sleep(self.reconnect_delay)

    async def subscribe(self, events: list[str]) -> bool:
        await self._sockets[0].send("SUBSCRIBE", orjson.dumps(events))
        _, response = await self._sockets[0].receive_event()
        status = response["success"]  # pyright: ignore
        if not status:
            raise ConnectionError(f"Could subscribe with {events}, reply: {response}")
        return status

    async def run_command(self, command: str):
        return await self._sockets[1].send_receive("RUN_COMMAND", command)

    async def get_workspaces(self):
        return await self._sockets[2].send_receive("GET_WORKSPACES")

    async def get_tree(self):
        return await self._sockets[3].send_receive("GET_TREE")

    async def get_outputs(self):
        return await self._sockets[4].send_receive("GET_OUTPUTS")

    async def listen(self) -> tuple[str, str, dict]:
        while True:
            try:
                event, response = await self._sockets[0].receive_event()
                subevent = response["change"]  # pyright: ignore
                return event, subevent, response  # pyright: ignore
            except (OSError, ConnectionError):
                await self._sockets[0].reconnect("eventlistener")

    async def close(self) -> None:
        for socket in self._sockets:
            await socket.close()
