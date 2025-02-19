import os
from pathlib import Path

def create_dir_if_not_exists(dir_path: str|Path) -> None:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)