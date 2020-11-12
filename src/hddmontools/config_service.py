from injectable import injectable
from pathlib import Path
import json

@injectable(singleton=True)
class ConfigService:

    @property
    def data(self):
        return self._data

    def __init__(self):
        self._data = None
        self._path = Path(__file__).parent / '../config/config.json'
        try:
            with self._path.open() as fd:
                self._data = json.load(fd)
        except FileNotFoundError:
            print(f"Warning! No config file exists at {self._path}!")
            print("Be sure to specify configuration either environment variables or cmd line arguments!")
            print("A config file should be used as a fallback!")
            self._data = {}
        except json.JSONDecodeError as e:
            print(f"There was an error while parsing {self._path}!")
            print(str(e))
            self._data = {}

    def override_env_var(self):
        pass