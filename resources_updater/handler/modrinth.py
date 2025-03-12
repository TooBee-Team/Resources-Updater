import hashlib
from collections import deque
import re
from logging import Logger
from pathlib import Path
from typing import Optional

import requests
from mcdreforged.utils.request_utils import post_json
from typing_extensions import override

from ..config import Resources, Handler, working_dir, find_files_by_dir_path, ua


class ModrinthResources(Resources):
    loaders: list[str] = ['fabric']

    regex_match_pattern: Optional[re.Pattern[str]] = re.compile(r"^.*\.jar$")


class ModrinthHandler(Handler):
    resources_info: dict[str, ModrinthResources] = {'mods': ModrinthResources()}
    hash_algorithm: str = 'sha1'

    @staticmethod
    @override
    def identifier():
        return 'modrinth'

    @override
    def handle(self, logger: Logger):
        def post(hashes: list[str], loaders: list[str]) -> dict:
            url = "https://api.modrinth.com/v2/version_files/update"
            data = {
                "hashes": hashes,
                "loaders": loaders,
                "algorithm": self.hash_algorithm,
            }
            if self.game_versions is not None:
                data["game_versions"] = self.game_versions

            try:
                from ..config import static
                r = post_json(url, ua, data, timeout=static.timeout)[0]
                if r.status_code == 200:
                    return r.json()
                r.raise_for_status()
            except requests.RequestException as e:
                logger.exception('Something went wrong when posting updating url', exc_info=e)
            return {}

        sha512 = self.hash_algorithm == 'sha512'
        for dir_name, resources in self.resources_info.items():
            dir_path = working_dir / Path(dir_name)
            m = {calc_file_sha(file, sha512): file for file in find_files_by_dir_path(dir_path, resources)}
            json = post(list(m.keys()), resources.loaders)
            if json:
                update: deque[tuple[str, str, int, Path]] = deque()
                for key, value in json.items():
                    t = fetch_from_url(sha512, key, value)
                    if t is not None:
                        update.append(t + (m.pop(key),))
                        logger.info(str(update))
                resources.download(dir_path, update, logger)
                logger.info('Updating resources in %s from modrinth is completed.', str(dir_path))


def calc_file_sha(file_path: Path, sha512: bool) -> str:
    hasher = hashlib.sha512 if sha512 else hashlib.sha1()
    with open(file_path, 'rb') as f:
        while buf := f.read(16 * 1024):
            hasher.update(buf)
    return hasher.hexdigest()


def fetch_from_url(sha512: bool, hash1: str, obj: dict) -> Optional[tuple[str, str, int]]:
    files: list[dict] = obj['files']
    if files is None or not files:
        return None
    f: dict = files[0]
    if len(files) != 1:
        for file in files:
            if file['primary']:
                f = file
                break
    return (f['url'], f['filename'], f['size']) if hash1 != f['hashes']['sha512' if sha512 else 'sha1'] else None
