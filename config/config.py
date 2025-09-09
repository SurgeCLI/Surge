import tomllib
import tomli_w
from pathlib import Path
import pathlib

def load_config_file(path: Path) -> dict:
    with open(path, 'rb') as config:
        data = tomllib.load(config)
    if not data:
        raise EOFError('Config file is empty, will create a new config file.')
    return data

if __name__ == '__main__':
    """
    Run this file for a default config.toml file
    """
    try:
        PATH = Path('config/config.toml')
        load_config_file(PATH)
        print(f'Loaded config file at {PATH}')

    except Exception:
        default_data = {
            'console': {'force_color': True, 'theme': 'default'}, 
            'monitor': {'interval': 5, 'load': True, 'cpu': True, 
            'ram': True, 'disk': True, 'io': False, 'verbose': False}, 
            'network': {'requests': 5, 'dtype': 'A', 'sockets': False, 'no_trace': False}, 
            'ai': {'format': 'hybrid', 'verbosity': 'normal', 'auto_fix': False}
        }

        try:
            if Path.cwd().name == 'Surge':
                with open(PATH, 'wb') as config:
                    tomli_w.dump(default_data, config)
                    print(f'Created config file at {pathlib.Path}')
        except Exception as e:
            print(f'Could not create config.toml file: {e}')