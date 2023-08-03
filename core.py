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
        self.lock = asyncio.Lock()
        self.reader: asyncio.StreamReader
        self.writer: asyncio.StreamWriter

    async def connect(self):
        self.socket = next(os.environ.get(socket) for socket in ["SWAYSOCK", "I3SOCK"])
        if not self.socket:
            raise EnvironmentError("Could not find the socket")
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
        async with self.lock:  # ensure only one coroutine is in this block at a time
            while True:
                try:
                    await self.send(message_type, command.encode())
                except (OSError, ConnectionError):
                    await self.reconnect(
                        f"send_receive send, msg type: {message_type} {command}"
                    )
                    continue
                try:
                    _, response = await self.receive_event()
                    return response
                except (OSError, ConnectionError):
                    await self.reconnect(
                        f"send_receive receive, msg type: {message_type} {command}"
                    )


class SwayIPCConnection:
    def __init__(self, reconnect_delay=1) -> None:
        self.reconnect_delay = reconnect_delay

    async def _create_socket(self) -> SwayIPCSocket:
        socket = SwayIPCSocket()
        await socket.connect()
        return socket

    async def run_command(self, command: str):
        if not hasattr(self, "_run_socket"):
            self._run_socket = await self._create_socket()
        return await self._run_socket.send_receive("RUN_COMMAND", command)

    async def get_workspaces(self):
        if not hasattr(self, "_workspace_socket"):
            self._workspace_socket = await self._create_socket()
        return await self._workspace_socket.send_receive("GET_WORKSPACES")

    async def subscribe(self, events: list[str]) -> bool:
        self._listen_socket = await self._create_socket()
        await self._listen_socket.send("SUBSCRIBE", orjson.dumps(events))
        _, response = await self._listen_socket.receive_event()
        status = response.get("success")  # pyright: ignore
        if not status:
            raise ConnectionError(f"Could subscribe with {events}, reply: {response}")
        return status

    async def get_outputs(self):
        if not hasattr(self, "_output_socket"):
            self._output_socket = await self._create_socket()
        return await self._output_socket.send_receive("GET_OUTPUTS")

    async def get_tree(self):
        if not hasattr(self, "_tree_socket"):
            self._tree_socket = await self._create_socket()
        return await self._tree_socket.send_receive("GET_TREE")

    async def get_marks(self):
        if not hasattr(self, "_marks_socket"):
            self._marks_socket = await self._create_socket()
        return await self._marks_socket.send_receive("GET_MARKS")

    async def get_bar_config(self):
        if not hasattr(self, "_config_socket"):
            self._config_socket = await self._create_socket()
        return await self._config_socket.send_receive("GET_BAR_CONFIG")

    async def get_version(self):
        if not hasattr(self, "_version_socket"):
            self._version_socket = await self._create_socket()
        return await self._version_socket.send_receive("GET_VERSION")

    async def get_binding_modes(self):
        if not hasattr(self, "_binding_modes_socket"):
            self._binding_modes_socket = await self._create_socket()
        return await self._binding_modes_socket.send_receive("GET_BINDING_MODES")

    async def get_config(self):
        if not hasattr(self, "_config_socket"):
            self._config_socket = await self._create_socket()
        return await self._config_socket.send_receive("GET_CONFIG")

    async def send_tick(self):
        if not hasattr(self, "_tick_socket"):
            self._tick_socket = await self._create_socket()
        return await self._tick_socket.send_receive("SEND_TICK")

    async def get_inputs(self):
        if not hasattr(self, "_input_socket"):
            self._input_socket = await self._create_socket()
        return await self._input_socket.send_receive("GET_INPUTS")

    async def get_seats(self):
        if not hasattr(self, "_seats_socket"):
            self._seats_socket = await self._create_socket()
        return await self._seats_socket.send_receive("GET_INPUTS")

    async def listen(self) -> tuple[str, str, dict]:
        while True:
            try:
                event, payload = await self._listen_socket.receive_event()
                change = payload.get("change", "run")  # pyright: ignore
                return event, change, payload  # pyright: ignore
            except (OSError, ConnectionError):
                await self._listen_socket.reconnect("eventlistener")

    async def close(self):
        for attr_name in dir(self):
            if attr_name.endswith("_socket"):
                socket = getattr(self, attr_name)
                await socket.close()
                setattr(self, attr_name, None)
