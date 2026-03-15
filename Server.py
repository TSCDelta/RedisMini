import asyncio
from enum import Enum, auto
from Parser import RESPParser
from Serializer import Serializer, SimpleString

parser = RESPParser()
serializer = Serializer()


class ParserState(Enum):
    SCANNING = auto()
    PARSING_ARRAY = auto()
    PARSING_BULK_PRIMARY = auto()
    PARSING_BULK_SECONDARY = auto()
    PARSING_SIMPLE = auto()
    COMPLETE = auto()


class SymbolType(Enum):
    ARRAY = '*'
    BULK_STRING = '$'
    INTEGER = ':'
    SIMPLE_STRING = '+'


class BulkStringPhase(Enum):
    FINDING_LENGTH = auto()
    READING_DATA = auto()


class StateMachine:
    def __init__(self):
        self.state = ParserState.SCANNING
        self.counter = 1
        self.counter_stack = []      
        self.await_buffer = ""
        self.raw_buffer = ""         

        self.bulk_phase = BulkStringPhase.FINDING_LENGTH
        self.bulk_length = 0
        self.foundry_index = 0

    def reset(self):
        self.state = ParserState.SCANNING
        self.counter = 1
        self.counter_stack = []
        self.await_buffer = ""
        self.raw_buffer = ""
        self.bulk_phase = BulkStringPhase.FINDING_LENGTH
        self.bulk_length = 0
        self.foundry_index = 0

    def _next_state(self):
        """Called after decrementing counter. Pops stack if inner array is done."""
        if self.counter > 0:
            return ParserState.SCANNING
        if self.counter_stack:
            self.counter = self.counter_stack.pop() - 1
            if self.counter > 0:
                return ParserState.SCANNING
        return ParserState.COMPLETE

    def process(self):
        while True:
            if self.state == ParserState.SCANNING:
                if not self.await_buffer:
                    return None

                if self.counter == 0:
                    self.state = ParserState.COMPLETE
                    continue

                first_char = self.await_buffer[0]

                if first_char == SymbolType.ARRAY.value:
                    self.state = ParserState.PARSING_ARRAY
                elif first_char == SymbolType.BULK_STRING.value:
                    if self.bulk_phase == BulkStringPhase.FINDING_LENGTH:
                        self.state = ParserState.PARSING_BULK_PRIMARY
                    else:
                        self.state = ParserState.PARSING_BULK_SECONDARY
                elif first_char in (SymbolType.INTEGER.value, SymbolType.SIMPLE_STRING.value):
                    self.state = ParserState.PARSING_SIMPLE
                else:
                    raise ValueError(f"Unknown symbol: {first_char}")

            elif self.state == ParserState.PARSING_ARRAY:
                delimiter_pos = self.await_buffer.find('\r\n')
                if delimiter_pos == -1:
                    return None

                try:
                    n = int(self.await_buffer[1:delimiter_pos])
                except ValueError:
                    raise ValueError("Invalid array length")

                consumed = self.await_buffer[:delimiter_pos + 2]
                self.raw_buffer += consumed
                self.await_buffer = self.await_buffer[delimiter_pos + 2:]

                if self.counter_stack or self.counter != 1:
                    self.counter_stack.append(self.counter)

                self.counter = n
                self.state = ParserState.SCANNING

            elif self.state == ParserState.PARSING_BULK_PRIMARY:
                delimiter_pos = self.await_buffer.find('\r\n')
                if delimiter_pos == -1:
                    return None

                try:
                    self.bulk_length = int(self.await_buffer[1:delimiter_pos])
                except ValueError:
                    raise ValueError("Invalid bulk string length")

                self.foundry_index = delimiter_pos + 2
                self.bulk_phase = BulkStringPhase.READING_DATA
                self.state = ParserState.PARSING_BULK_SECONDARY

            elif self.state == ParserState.PARSING_BULK_SECONDARY:
                data_end = self.foundry_index + self.bulk_length

                if len(self.await_buffer) < data_end:
                    return None
                if len(self.await_buffer) < data_end + 2:
                    return None
                if self.await_buffer[data_end:data_end + 2] != '\r\n':
                    raise ValueError("Bulk string not properly terminated")

                consumed = self.await_buffer[:data_end + 2]
                self.raw_buffer += consumed
                self.await_buffer = self.await_buffer[data_end + 2:]
                self.bulk_phase = BulkStringPhase.FINDING_LENGTH
                self.counter -= 1
                self.state = self._next_state()

            elif self.state == ParserState.PARSING_SIMPLE:
                delimiter_pos = self.await_buffer.find('\r\n')
                if delimiter_pos == -1:
                    return None

                consumed = self.await_buffer[:delimiter_pos + 2]
                self.raw_buffer += consumed
                self.await_buffer = self.await_buffer[delimiter_pos + 2:]
                self.counter -= 1
                self.state = self._next_state()

            elif self.state == ParserState.COMPLETE:
                raw = self.raw_buffer
                self.reset()
                return raw


def serialize_response(resp_value):
    if resp_value is None:
        return "$-1\r\n"
    if isinstance(resp_value, str) and resp_value.startswith('-'):
        return resp_value if resp_value.endswith("\r\n") else resp_value + "\r\n"
    if isinstance(resp_value, str) and resp_value in ("OK", "PONG"):
        return serializer.serialize(SimpleString(resp_value))
    return serializer.serialize(resp_value)


async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"New connection from {addr}")
    machine = StateMachine()

    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break

            message = data.decode(errors='ignore')
            print(f"Received from {addr}: {repr(message)}")
            machine.await_buffer += message

            while True:
                raw = machine.process()
                if raw is None:
                    break

                print(f"Raw RESP: {repr(raw)}")

                try:
                    resp_value = parser.execute(raw)
                except Exception as e:
                    resp_value = f"-ERR {e}"

                response = serialize_response(resp_value)
                print(f"Response: {repr(response)}")

                writer.write(response.encode())
                await writer.drain()

                if not machine.await_buffer:
                    break

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        print(f"Connection closed: {addr}")
        writer.close()
        await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 8888)
    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
