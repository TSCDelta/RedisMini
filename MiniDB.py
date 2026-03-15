import time
from typing import Dict, Optional, Any, List, Set, Union

class MiniDB:
    def __init__(self):
        self.strings: Dict[str, Any]       = {}
        self.expires: Dict[str, float]     = {}
        self.sets: Dict[str, Set[str]]     = {}
        self.lists: Dict[str, List[str]]   = {}

    def _is_expired(self, key: str) -> bool:
        if key in self.expires and time.time() > self.expires[key]:
            self._delete_key(key)
            return True
        return False

    def _delete_key(self, key: str):
        self.strings.pop(key, None)
        self.expires.pop(key, None)
        self.sets.pop(key, None)
        self.lists.pop(key, None)

    def _get_type(self, key: str) -> str:
        if self._is_expired(key):
            return "none"
        if key in self.strings:
            return "string"
        if key in self.sets:
            return "set"
        if key in self.lists:
            return "list"
        return "none"

    def set(self, key: str, value: str, ex: Optional[int] = None) -> str:
        if self._get_type(key) not in ("none", "string"):
            return "-WRONGTYPE Operation against a key holding the wrong kind of value"
        self.strings[key] = value
        if ex is not None and ex > 0:
            self.expires[key] = time.time() + ex
        else:
            self.expires.pop(key, None)
        return "OK"

    def get(self, key: str) -> Optional[str]:
        t = self._get_type(key)
        if t == "none":
            return None
        if t != "string":
            return "-WRONGTYPE"
        return self.strings.get(key)
    
    def mget(self, keys: List[str]) -> List[Optional[str]]:
        return [self.get(k) for k in keys]

    def mset(self, pairs: List[str]) -> str:
        if len(pairs) % 2 != 0:
            return "-ERR wrong number of arguments for MSET"
        for i in range(0, len(pairs), 2):
            self.set(pairs[i], pairs[i+1])
        return "OK"

    def delete(self, keys: List[str]) -> int:
        count = 0
        for k in keys:
            if self._get_type(k) != "none":
                self._delete_key(k)
                count += 1
        return count

    def flushall(self) -> str:
        self.strings.clear()
        self.expires.clear()
        self.sets.clear()
        self.lists.clear()
        return "OK"

    def flushdb(self) -> str:
        return self.flushall()

    def sadd(self, key: str, members: List[str]) -> int:
        if self._get_type(key) not in ("none", "set"):
            return "-WRONGTYPE"
        if key not in self.sets:
            self.sets[key] = set()
        added = 0
        for m in members:
            if m not in self.sets[key]:
                self.sets[key].add(m)
                added += 1
        return added

    def smembers(self, key: str) -> List[str]:
        if self._get_type(key) != "set":
            return "-WRONGTYPE"
        return list(self.sets.get(key, set()))

    def scard(self, key: str) -> int:
        if self._get_type(key) != "set":
            return "-WRONGTYPE"
        return len(self.sets.get(key, set()))

    def sismember(self, key: str, member: str) -> int:
        if self._get_type(key) != "set":
            return "-WRONGTYPE"
        return 1 if member in self.sets.get(key, set()) else 0

    def srem(self, key: str, members: List[str]) -> int:
        if self._get_type(key) != "set":
            return "-WRONGTYPE"
        s = self.sets.get(key)
        if not s:
            return 0
        removed = 0
        for m in members:
            if m in s:
                s.remove(m)
                removed += 1
        if not s:
            self.sets.pop(key, None)
        return removed

    def lpush(self, key: str, values: List[str]) -> int:
        if self._get_type(key) not in ("none", "list"):
            return "-WRONGTYPE"
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key][0:0] = values[::-1]
        return len(self.lists[key])

    def rpush(self, key: str, values: List[str]) -> int:
        if self._get_type(key) not in ("none", "list"):
            return "-WRONGTYPE"
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].extend(values)
        return len(self.lists[key])

    def llen(self, key: str) -> int:
        if self._get_type(key) != "list":
            return "-WRONGTYPE"
        return len(self.lists.get(key, []))

    def lrange(self, key: str, start: int, stop: int) -> List[str]:
        if self._get_type(key) != "list":
            return "-WRONGTYPE"
        lst = self.lists.get(key, [])
        if start < 0:
            start = max(0, len(lst) + start)
        if stop < 0:
            stop = len(lst) + stop
        stop = min(stop, len(lst) - 1) + 1
        return lst[start:stop]

    def lpop(self, key: str) -> Optional[str]:
        if self._get_type(key) != "list":
            return "-WRONGTYPE"
        lst = self.lists.get(key)
        if not lst:
            return None
        val = lst.pop(0)
        if not lst:
            self.lists.pop(key, None)
        return val

    def rpop(self, key: str) -> Optional[str]:
        if self._get_type(key) != "list":
            return "-WRONGTYPE"
        lst = self.lists.get(key)
        if not lst:
            return None
        val = lst.pop()
        if not lst:
            self.lists.pop(key, None)
        return val

    def handle_command(self, cmd_list: list) -> Any:
        if not cmd_list:
            return "-ERR empty command\r\n"

        cmd = str(cmd_list[0]).upper()

        try:
            if cmd == "PING":
                return "PONG"
            if cmd == "FLUSHALL" or cmd == "FLUSHDB":
                return self.flushall()
            if cmd == "DEL":
                return self.delete(cmd_list[1:])
            if cmd == "EXISTS":
                return sum(1 for k in cmd_list[1:] if self._get_type(k) != "none")

            if cmd == "SET":
                if len(cmd_list) < 3:
                    return "-ERR wrong number of arguments for SET"
                key, val = cmd_list[1], cmd_list[2]
                ex = None
                if len(cmd_list) >= 5 and cmd_list[3].upper() in ("EX", "PX"):
                    if cmd_list[3].upper() == "EX":
                        ex = int(cmd_list[4])
                return self.set(key, val, ex)

            if cmd == "GET":
                if len(cmd_list) != 2: return "-ERR wrong number of arguments for GET"
                val = self.get(cmd_list[1])
                return val

            if cmd == "MGET":
                return self.mget(cmd_list[1:])

            if cmd == "MSET":
                return self.mset(cmd_list[1:])

            if cmd == "SADD":
                if len(cmd_list) < 3: return "-ERR wrong number of arguments for SADD"
                return self.sadd(cmd_list[1], cmd_list[2:])

            if cmd == "SMEMBERS":
                if len(cmd_list) != 2: return "-ERR wrong number of arguments for SMEMBERS"
                return self.smembers(cmd_list[1])

            if cmd == "SCARD":
                if len(cmd_list) != 2: return "-ERR wrong number of arguments for SCARD"
                return self.scard(cmd_list[1])

            if cmd == "SISMEMBER":
                if len(cmd_list) != 3: return "-ERR wrong number of arguments for SISMEMBER"
                return self.sismember(cmd_list[1], cmd_list[2])

            if cmd == "SREM":
                if len(cmd_list) < 3: return "-ERR wrong number of arguments for SREM"
                return self.srem(cmd_list[1], cmd_list[2:])

            if cmd == "LPUSH":
                if len(cmd_list) < 3: return "-ERR wrong number of arguments for LPUSH"
                return self.lpush(cmd_list[1], cmd_list[2:])

            if cmd == "RPUSH":
                if len(cmd_list) < 3: return "-ERR wrong number of arguments for RPUSH"
                return self.rpush(cmd_list[1], cmd_list[2:])

            if cmd == "LLEN":
                if len(cmd_list) != 2: return "-ERR wrong number of arguments for LLEN"
                return self.llen(cmd_list[1])

            if cmd == "LRANGE":
                if len(cmd_list) != 4: return "-ERR wrong number of arguments for LRANGE"
                try:
                    start = int(cmd_list[2])
                    stop  = int(cmd_list[3])
                except ValueError:
                    return "-ERR value is not an integer"
                return self.lrange(cmd_list[1], start, stop)

            if cmd == "LPOP":
                if len(cmd_list) != 2: return "-ERR wrong number of arguments for LPOP"
                return self.lpop(cmd_list[1])

            if cmd == "RPOP":
                if len(cmd_list) != 2: return "-ERR wrong number of arguments for RPOP"
                return self.rpop(cmd_list[1])

            return f"-ERR unknown command '{cmd}'\r\n"

        except Exception as e:
            return f"-ERR {str(e)}\r\n"