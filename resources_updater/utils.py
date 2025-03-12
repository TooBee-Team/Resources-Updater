from typing import TypeVar, Callable, List, Iterable
from mcdreforged.plugin.si.plugin_server_interface import ServerInterface

T = TypeVar('T')


class ConjunctionPredicateBuilder:
    def __init__(self):
        self.s: List[Callable[[T], bool]] = []

    def add(self, b: bool, p: Callable[[T], bool]):
        if b: self.s.append(p)
        return self

    def __pn(self, t: T):
        for p in self.s:
            if not p(t):
                return False
        return True

    def build(self) -> Callable[[T], bool]:
        match len(self.s):
            case 0: return lambda t: True
            case 1: return lambda t: self.s[0](t)
            case 2: return lambda t: self.s[0](t) and self.s[1](t)
            case 3: return lambda t: self.s[0](t) and self.s[1](t) and self.s[2](t)
            case 4: return lambda t: self.s[0](t) and self.s[1](t) and self.s[2](t) and self.s[3](t)
            case _: return lambda t: self.__pn(t)


class InsecurePathError(OSError):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


def tr(key: str, *args) -> str:
    return ServerInterface.get_instance().tr(f"modrinth_mods_updater.{key}", *args)
