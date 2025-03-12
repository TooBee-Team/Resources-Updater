from logging import Logger
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from mcdreforged.plugin.si.plugin_server_interface import PluginServerInterface

from .utils import InsecurePathError
from .config import Config, Handler, Resources
from .handler.modrinth import ModrinthHandler


def update(logger: Logger, handler: Handler):
    try:
        handler.handle(logger)
    except (InsecurePathError, FileNotFoundError) as e:
        logger.error(e)
    except Exception as e:
        logger.exception("Something went wrong when handling %s", handler.identifier(), exc_info=e)


def start(server: PluginServerInterface):
    from .config import static
    if not static.enable or not static.used_handlers():
        return
    #time = getattr(server, '_mcdr_server').config.watchdog_threshold
    #setattr(server, '_mcdr_server', 0)
    c = server._mcdr_server.config
    time = c.watchdog_threshold
    c.watchdog_threshold = 0

    # TODO: need ordering
    if not static.ask or input('Whether to update resources? (y/n)') == 'y':
        handlers = static.used_handlers()
        if static.concurrent:
            with ThreadPoolExecutor(max_workers=len(handlers)) as executor:
                executor.map(lambda x: update(server.logger, x), handlers)
        else:
            for handler in handlers:
                update(server.logger, handler)

    #setattr(server, '_mcdr_server', time)
    c.watchdog_threshold = time


def init(server: PluginServerInterface):
    from . import config
    Config.reg_used_handler(ModrinthHandler())
    config.static = server.load_config_simple(target_class=Config)
    config.working_dir = Path(server.get_mcdr_config()['working_directory'])
    if config.static.enable and config.static.disable_after_next_time:
        config.static.enable = False
        server.save_config_simple(config.static)


def on_load(server: PluginServerInterface, old):
    Config.register_handler(ModrinthHandler)
    server.register_event_listener('mcdr.mcdr_start', init)
    server.register_event_listener('mcdr.server_start_pre', start)
