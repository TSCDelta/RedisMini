import asyncio

async def tcp_client():
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888)
    print("Connected to server!")

    try:
        while True:
            message = input("Message to server: ")
            message = message.replace('\\r\\n', '\r\n')
            writer.write(message.encode())
            await writer.drain()
            data = await reader.read(1024)
            print(f"Server says: {data.decode()}")
    except KeyboardInterrupt:
        print("Closing connection...")
    finally:
        writer.close()
        await writer.wait_closed()

asyncio.run(tcp_client())
