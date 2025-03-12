import re
from io import StringIO
from logging import Logger
from pathlib import Path
from threading import Lock
from abc import ABC, abstractmethod
from typing import Optional, Final, TypeVar, final, Iterable

import requests
from mcdreforged.plugin.si.plugin_server_interface import PluginServerInterface
from mcdreforged.utils.request_utils import get_direct
from typing_extensions import Self, override

from mcdreforged.api.utils.serializer import Serializable
from mcdreforged.utils.types.json_like import JsonLike
from .utils import InsecurePathError, ConjunctionPredicateBuilder


ua = 'ResourcesUpdater'


class Resources(Serializable):
    archive_dir: Optional[str] = None
    regex_match_pattern: Optional[re.Pattern[str]] = None
    blacklist: list[str] = []
    whitelist: Optional[list[str]] = None

    def download(self, dir_path: Path, update: Iterable[tuple[str, str, int, Path]], logger: Logger):
        sb = StringIO()
        sb.write("The following resources will be updated:\n")
        for t in update:
            sb.write("%s -> %s (%d KB)\n" % (t[3].name, t[1], t[2] >> 10))
        sb.write('Start to update......')
        logger.info(sb.getvalue())

        if self.archive_dir is None:
            archive_dir_path = working_dir
        else:
            archive_dir_path = working_dir / self.archive_dir

        dir_path.mkdir(0o755, True, True)
        for info in update:
            response = get_direct(info[0], ua, timeout=static.timeout)
            response.raise_for_status()
            size = int(response.headers.get('content-length', 0))

            if size != info[2] and info[2] >= 0:
                logger.warning(
                    "The downloaded file %s in size of %d cannot match the size from its meta info: %d bytes,\n\
                    which download url is %s", info[1], size, info[2], info[0])

            target_path = (dir_path / info[1])
            temp_path = target_path.with_suffix('.tmp')
            archive_dir_path.mkdir(0o755, True, True)

            try:
                with temp_path.open('wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                info[3].replace(archive_dir_path / info[3].name)
                temp_path.rename(target_path)
            except requests.exceptions.RequestException as e:
                logger.exception("Failed to download file from %s", info[0], exc_info=e)
                temp_path.unlink(True)


R = TypeVar('R', bound=Resources)


class Handler(Serializable, ABC):
    __instance = None
    resources_info: dict[str, R] = {}
    game_versions: Optional[list[str]] = None

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super().__new__(cls, *args, **kwargs)
        return cls.__instance

    @staticmethod
    @abstractmethod
    def identifier() -> str: pass

    @abstractmethod
    def handle(self, logger: Logger): pass

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)


H = TypeVar('H', bound=Handler)


@final
class Config(Serializable):
    __lock: Final[Lock] = Lock()
    __reg_handlers: Final[dict[str, type[H]]] = {}

    enable: bool = True
    disable_after_next_time: bool = False
    ask: bool = True
    concurrent: bool = False
    timeout: float = 10.0
    __used_handlers: set[Handler] = set()

    @classmethod
    def register_handler(cls, handler: type[H]) -> bool:
        with cls.__lock:
            name = handler.identifier()
            if name in cls.__reg_handlers:
                return False
            else:
                cls.__reg_handlers[handler.identifier()] = handler
                return True

    @override
    def serialize(self) -> JsonLike:
        temp: dict = super().serialize()
        temp['handlers'] = {value.identifier(): value.serialize() for value in self.__used_handlers}
        return temp

    @classmethod
    @override
    def deserialize(cls: type[Self], data: dict, **kwargs) -> Self:
        f = kwargs.pop('redundancy_callback')
        o = super().deserialize(data, **kwargs)
        kwargs['redundancy_callback'] = f
        g = (cls.__handlers[k].deserialize(v, **kwargs) for k, v in data['handlers'].items())
        o.__used_handlers = frozenset(g)
        return o

    @override
    def copy(self, *, deep: bool = True) -> Self:
        other: Self = super().copy(deep=deep)
        g = (x.copy() for x in self.__used_handlers)
        other.__used_handlers = set(g).copy()
        return other

    # Do not use @property to avoid being identified by super().serialize method
    def used_handlers(self) -> set[Handler]:
        return self.__used_handlers

    @classmethod
    def reg_used_handler(cls, s: Handler):
        cls.__used_handlers.add(s)


static: Config
working_dir: Path = Path('server')


def find_files_by_dir_path(target_dir: Path, r: Resources) -> Iterable[Path]:
    if working_dir.resolve() not in target_dir.resolve().parents:
        raise InsecurePathError('Insecure path %s, which is out of working directory' % target_dir.resolve())
    if not target_dir.is_dir():
        raise FileNotFoundError('Directory %s does not exist' % target_dir.resolve())

    pattern = r.regex_match_pattern
    if pattern is not None:
        regex = re.compile(pattern)
    predicate = (ConjunctionPredicateBuilder()
                 .add(r.whitelist is not None, lambda s: s in r.whitelist)
                 .add(r.blacklist, lambda s: s not in r.blacklist)
                 .add(pattern is not None, lambda s: regex.match(s))
                 .build())

    files = [file for file in target_dir.iterdir() if file.is_file()]
    return filter(lambda file: predicate(file.name), files)
