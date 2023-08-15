import asyncio
import os
import sys
from collections import defaultdict
from typing import AsyncGenerator

import orjson

JSONValue = (
    bool
    | str
    | None
    | float
    | dict[str, "JSONInnerValue"]
    | list[dict[str, "JSONInnerValue"]]
)
JSONInnerValue = JSONValue | list[dict[str, JSONValue]]
JSONDict = dict[str, JSONValue]
JSONList = list[JSONDict]

magic_string = "i3-ipc"
magic_len = len(magic_string)
magic_enc = magic_string.encode()
payload_len_len = 4  # length of payload length
payload_type_len = 4  # length of payload type
header_len = magic_len + payload_len_len + payload_type_len

_events = {
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
        self.lock = asyncio.Lock()
        self.reader: asyncio.StreamReader = None  # pyright: ignore
        self.writer: asyncio.StreamWriter = None  # pyright: ignore

    async def connect(self):
        socket_path = next(os.environ.get(socket) for socket in ["SWAYSOCK", "I3SOCK"])
        if not socket_path:
            raise EnvironmentError("Could not find the socket")
        self.reader, self.writer = await asyncio.open_unix_connection(path=socket_path)

    async def reconnect(self, error_message: str):
        print(f"{error_message}, trying to reconnect… ", end="")
        await self.close()
        await asyncio.sleep(1)
        await self.connect()
        print("reacquired socket")

    async def send(self, payload_type: int, command=b""):
        if not self.writer:  # first time calling, create socket
            await self.connect()

        payload_length = len(command)

        data = magic_enc
        data += payload_length.to_bytes(payload_len_len, sys.byteorder)
        data += payload_type.to_bytes(payload_type_len, sys.byteorder)
        data += command

        self.writer.write(data)
        await self.writer.drain()

    async def receive(self) -> JSONDict | JSONList:
        header = await self.reader.read(header_len)
        payload_length_bytes = header[magic_len : magic_len + payload_len_len]
        payload_length = int.from_bytes(payload_length_bytes, sys.byteorder)

        raw_response = await self.reader.read(payload_length)
        return orjson.loads(raw_response)

    async def receive_event(self) -> tuple[str, JSONDict]:
        header = await self.reader.read(header_len)

        event_bytes = header[magic_len + payload_len_len : :]
        event_int = int.from_bytes(event_bytes, byteorder=sys.byteorder)
        event_human = _events.get(event_int, "unknown")

        payload_length_bytes = header[magic_len : magic_len + payload_len_len]
        payload_length = int.from_bytes(payload_length_bytes, sys.byteorder)

        raw_response = await self.reader.read(payload_length)
        return event_human, orjson.loads(raw_response)

    async def close(self):
        if self.writer and not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()

    async def send_receive(self, payload_type: int, command=b"") -> JSONDict | JSONList:
        async with self.lock:  # ensure only one coroutine is in this block at a time
            await self.send(payload_type, command)
            return await self.receive()


class SwayIPCConnection:
    def __init__(self) -> None:
        self.sockets = defaultdict(lambda: SwayIPCSocket())

    async def run_command(self, c: str) -> list[dict[str, bool | str]]:
        return await self.sockets["run_command"].send_receive(0, c.encode())

    async def get_workspaces(self) -> JSONList:
        return await self.sockets["get_workspaces"].send_receive(1)  # pyright:ignore

    async def get_outputs(self) -> JSONList:
        return await self.sockets["get_outputs"].send_receive(3)  # pyright: ignore

    async def get_tree(self) -> JSONDict:
        return await self.sockets["get_tree"].send_receive(4)  # pyright:ignore

    async def get_marks(self):
        return await self.sockets["get_marks"].send_receive(5)

    async def get_bar_config(self):
        return await self.sockets["get_bar_config"].send_receive(6)

    async def get_version(self):
        return await self.sockets["get_version"].send_receive(7)

    async def get_binding_modes(self):
        return await self.sockets["get_binding_modes"].send_receive(8)

    async def get_config(self):
        return await self.sockets["get_config"].send_receive(9)

    async def send_tick(self):
        return await self.sockets["send_tick"].send_receive(10)

    async def get_inputs(self):
        return await self.sockets["get_inputs"].send_receive(100)

    async def get_seats(self):
        return await self.sockets["get_seats"].send_receive(101)

    async def subscribe(
        self, events: list[str]
    ) -> AsyncGenerator[tuple[str, str, JSONDict], None]:
        if not all(r in _events.values() for r in events):
            raise ValueError("invalid payload")

        socket = self.sockets["subscribe"]
        if not (await socket.send_receive(2, orjson.dumps(events))).get("success"):
            raise ConnectionError(f"Could not subscribe with {events}")

        while True:
            try:
                event, payload = await socket.receive_event()
                yield event, payload.get("change", "run"), payload
            except orjson.JSONDecodeError as e:
                await socket.reconnect(str(e))
                await socket.send_receive(2, orjson.dumps(events))
            except asyncio.exceptions.CancelledError:
                await self.close(["subscribe"])
                raise asyncio.exceptions.CancelledError

    async def close(self, socket_names: list[str] | None = None):
        if socket_names is None:
            socket_names = list(self.sockets.keys())

        for name in socket_names:
            socket = self.sockets.pop(name)
            await socket.close()
