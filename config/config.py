import tomllib
import tomli_w
from pathlib import Path

PATH = Path("config/config.toml")

DEFAULT_DATA = {
    "console": {"force_color": True},
    "monitor": {
        "interval": 5,
        "load": True,
        "cpu": True,
        "ram": True,
        "disk": True,
        "io": False,
        "verbose": False,
    },
    "network": {"requests": 5, "dtype": "A", "sockets": False, "no_trace": False},
    "ai": {"format": "hybrid", "verbosity": "normal", "auto_fix": False},
}


def create_config_file(path: Path) -> None:
    try:
        with open(path, "wb") as config:
            tomli_w.dump(DEFAULT_DATA, config)
            print(f"Created config file at {Path.home()}")
    except Exception as e:
        print(f"Could not create config.toml file: {e}")


def load_config_file(path: Path) -> dict:
    if not path.exists():
        print("Config file does not exist, creating new config file...")
        create_config_file(path)
        return DEFAULT_DATA

    with open(path, "rb") as config:
        data = tomllib.load(config)

    if not data:
        print("Config file is empty, creating new config file...")
        create_config_file(path)
        return DEFAULT_DATA

    return data


if __name__ == "__main__":
    """
    Run this file for a default config.toml file
    """
    try:
        load_config_file(PATH)
        print(f"Loaded config file at {PATH}")
    except Exception:
        create_config_file()
