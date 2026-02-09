import asyncio
from enum import Enum, auto

class ParserState(Enum):
    SCANNING = auto()
    PARSING_ARRAY = auto()
    PARSING_BULK_PRIMARY = auto()
    PARSING_BULK_SECONDARY = auto()
    PARSING_SIMPLE = auto()
    VALIDATING = auto()
    COMPLETE = auto()

class SymbolType(Enum):
    ARRAY = '*'
    BULK_STRING = '$'
    INTEGER = ':'
    SIMPLE_STRING = '+'

class BulkStringPhase(Enum):
    FINDING_LENGTH = auto()
    READING_DATA = auto()

class RESPParser:
    def __init__(self):
        self.state = ParserState.SCANNING
        self.counter = 1
        self.await_buffer = ""
        self.ready_buffer = []
        
        self.bulk_phase = BulkStringPhase.FINDING_LENGTH
        self.bulk_length = 0
        self.foundry_index = 0
    
    def reset(self):
        self.state = ParserState.SCANNING
        self.counter = 1
        self.await_buffer = ""
        self.ready_buffer = []
        self.bulk_phase = BulkStringPhase.FINDING_LENGTH
        self.bulk_length = 0
        self.foundry_index = 0
    
    def process(self):
        while True:
            if self.state == ParserState.SCANNING:
                if not self.await_buffer:
                    return None
                
                if self.counter == 0:
                    self.state = ParserState.VALIDATING
                    continue
                
                first_char = self.await_buffer[0]
                
                if first_char == SymbolType.ARRAY.value:
                    self.state = ParserState.PARSING_ARRAY
                
                elif first_char == SymbolType.BULK_STRING.value:
                    if self.bulk_phase == BulkStringPhase.FINDING_LENGTH:
                        self.state = ParserState.PARSING_BULK_PRIMARY
                    else:
                        self.state = ParserState.PARSING_BULK_SECONDARY
                
                elif first_char in [SymbolType.INTEGER.value, 
                                   SymbolType.SIMPLE_STRING.value]:
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
                
                self.counter = n
                self.await_buffer = self.await_buffer[delimiter_pos + 2:]
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
                
                terminator_pos = data_end
                
                if len(self.await_buffer) < terminator_pos + 2:
                    return None
                
                if self.await_buffer[terminator_pos:terminator_pos + 2] != '\r\n':
                    raise ValueError("Bulk string not properly terminated")
                
                extracted_string = self.await_buffer[self.foundry_index:data_end]
                
                if len(extracted_string) != self.bulk_length:
                    raise ValueError("Bulk string length mismatch")
                
                self.ready_buffer.append(extracted_string)
                self.counter -= 1
                self.await_buffer = self.await_buffer[terminator_pos + 2:]
                self.bulk_phase = BulkStringPhase.FINDING_LENGTH
                
                if self.counter > 0:
                    self.state = ParserState.SCANNING
                else:
                    self.state = ParserState.VALIDATING
            
            elif self.state == ParserState.PARSING_SIMPLE:
                delimiter_pos = self.await_buffer.find('\r\n')
                
                if delimiter_pos == -1:
                    return None
                
                symbol = self.await_buffer[0]
                value_str = self.await_buffer[1:delimiter_pos]
                
                if symbol == SymbolType.INTEGER.value:
                    try:
                        value = int(value_str)
                    except ValueError:
                        raise ValueError("Invalid integer format")
                else:
                    value = value_str
                
                self.ready_buffer.append(value)
                self.counter -= 1
                self.await_buffer = self.await_buffer[delimiter_pos + 2:]
                
                if self.counter > 0:
                    self.state = ParserState.SCANNING
                else:
                    self.state = ParserState.VALIDATING
            
            elif self.state == ParserState.VALIDATING:
                if self.counter != 0:
                    raise ValueError(f"Malformed command: counter={self.counter} at termination")
                
                self.state = ParserState.COMPLETE
            
            elif self.state == ParserState.COMPLETE:
                result = self.ready_buffer.copy()
                self.reset()
                return result

async def reading(reader):
    data = await reader.read(4096)
    if not data:
        return None
    message = data.decode()
    return message

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"New connection from {addr}")
    parser = RESPParser()
    
    try:
        while True:
            message = await reading(reader)
            
            if message is None:
                break
            
            print(f"Received from {addr}: {message}")
            
            parser.await_buffer += message
            
            while True:
                result = parser.process()
                
                if result is None:
                    break
                
                print(f"Parsed command: {result}")
                
                response = f"Echo: {result}\r\n"
                writer.write(response.encode())
                await writer.drain()
                
                if not parser.await_buffer:
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
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())