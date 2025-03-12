# Resources Updater

Automatically update your game resources before your game server is started. (Use the proxy server defined in mcdreforged config file if existing)

Until now only modrinth resources are supported.

## Requirements

- [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) requirement: `>=2.14.5`

## Config

In `config/resources_updater/config.json`, the default config is (handlers are omitted):

```json

{
    "enable": true,
    "disable_after_next_time": false,
    "ask": true,
    "concurrent": false,
    "timeout": 30.0,
    "handlers": {}
}
```

- `enable`: the plugin will check updating when it's true.
- `disable_after_next_time`: will set the above item to false after this checking.
- `ask`: whether to ask user to enter `y` for agreeing updating when mcdreforged is starting.
- `concurrent` whether to use concurrent threads to handle all the task, it's no use currently.
- `timeout` the seconds with which a connection can keep. You might need to increase it if a large file is downloaded.
- `handlers` a handler type - contents mapping, the key is the following subtitle, and see below for detailed values.

### modrinth

Check your resources from modrinth.

```json
{
    "game_versions": null,
    "hash_algorithm": "sha1",
    "resources_info": {
        "mods": {
            "archive_dir": "mods/old",
            "regex_match_pattern": "^.*\\.jar$",
            "blacklist": [],
            "whitelist": null,
            "loaders": []
        }
    }
}
```

- `game_version` is the list of version id of minecraft, `["1.21.4", "1.21.3"]` for example, use the latest version if not specified.
- `hash_algorithm` the hash algorithm to calculate the file hashes according to modrinth api standard, require `sha1` or `sha512`.
- `resources_info` specify a path - rules mapping, where the key points to which path (not recursive) under the working directory to handle, yet the above example means that `server/mods` will be chosen if working_dir is set to `server` in mcdreforged config.

Now explain the values in the value of `resources_info`

- `archive_dir` specify which path under the working directory to move the old files to.
- `whitelist` specify the list of allowed filenames to update, disabled if its value is null.
- `blacklist` specify the list of disallowed filenames to update, disabled if its value is empty.
- `regex_match_pattern` specify the regex pattern for matching the file name to update, disabled if its is null.
- `loaders` specify the list of loaders for updating, yet any loaders might be chosen if its empty. e.g., *fabric*, *neoforge* for mods; *minecraft* for datapacks; *paper*, *spigot*, *bukkit* for plugins; *iris*, *optifine* for shaders.