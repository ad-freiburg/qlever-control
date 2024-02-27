from __future__ import annotations

import subprocess
from pathlib import Path


def get_total_file_size(patterns: list[str]) -> int:
    """
    Helper function that gets the total size of all files mathing the given
    patterns in bytes.
    """

    total_size = 0
    search_dir = Path.cwd()
    for pattern in patterns:
        for file in search_dir.glob(pattern):
            total_size += file.stat().st_size
    return total_size


def run_command(cmd: str) -> bool:
    """
    Run the given command and throw an exception if something goes wrong or the
    command returns a non-zero exit code.
    """
    subprocess.run(cmd, shell=True, check=True,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def is_qlever_server_alive(port: str) -> bool:
    """
    Helper function that checks if a QLever server is running on the given
    port.
    """

    message = "from the qlever script".replace(" ", "%20")
    curl_cmd = f"curl -s http://localhost:{port}/ping?msg={message}"
    exit_code = subprocess.call(curl_cmd, shell=True,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    return exit_code == 0

def get_existing_index_files(basename: str) -> list[str]:
    """
    Helper function that returns a list of all index files for `basename` in
    the current working directory.
    """
    existing_index_files = []
    existing_index_files.extend(Path.cwd().glob(f"{basename}.index.*"))
    existing_index_files.extend(Path.cwd().glob(f"{basename}.text.*"))
    existing_index_files.extend(Path.cwd().glob(f"{basename}.vocabulary.*"))
    existing_index_files.extend(Path.cwd().glob(f"{basename}.meta-data.json"))
    existing_index_files.extend(Path.cwd().glob(f"{basename}.prefixes"))
    # Return only the file names, not the full paths.
    return [path.name for path in existing_index_files]
