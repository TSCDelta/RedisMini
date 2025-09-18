# Mini Redis

A lightweight Redis implementation in Python using asyncio. Because sometimes you need a key-value store and Redis feels like overkill.

## Features

- **Core Commands**: `GET`, `SET`, `DEL`, `FLUSH`
- **Batch Operations**: `MGET`, `MSET` for multiple key operations
- **TTL Support**: Set expiration timestamps on keys
- **AOF Persistence**: Append-Only File for command replay and data recovery
- **Async I/O**: Built with asyncio for concurrent client handling

## Quick Start

```bash
python mini_redis.py
```

Connect with any Redis client or telnet:
```bash
telnet localhost 6379
```

## Commands

```redis
SET mykey "hello world"
GET mykey
DEL mykey
MSET key1 "value1" key2 "value2"
MGET key1 key2
SET session:123 "user_data" EX 3600  # expires in 1 hour
FLUSH  # clear everything
```

## Architecture

- **asyncio server** handles multiple clients concurrently
- **In-memory storage** with TTL expiration checking
- **AOF logging** writes commands to disk for replay on restart
- **Command parser** handles Redis protocol basics

## Implementation Details

This project implements Redis core functionality to demonstrate key-value store fundamentals and async networking patterns. The codebase focuses on clarity and educational value while maintaining functional completeness for basic use cases.

## Limitations

- Single-node operation (no clustering)
- Limited to string data types
- Basic Redis protocol subset
- No authentication or security features
- Simplified persistence model

The implementation prioritizes understanding core concepts over feature completeness.
