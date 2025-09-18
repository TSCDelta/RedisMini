import asyncio
from Parser import RESPParser

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"New connection from {addr}")
    parser = RESPParser()

    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            message = data.decode()
            print(message)
            print(f"Received from {addr}: {message}")
            if message[0] == "*":
                decoded = parser.parse(message)
                print(type(decoded))
                print(decoded)  
                list_part, number = decoded
                response = f"Echo: {list_part}"
                writer.write(response.encode())
                await writer.drain()
            else:
                decoded = parser.parse(message)
                response = f"Echo: {decoded}"
                writer.write(response.encode())
                await writer.drain()
    except asyncio.CancelledError:
        pass
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

asyncio.run(main())
