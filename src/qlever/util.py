from __future__ import annotations

import secrets
import re
import shlex
import shutil
import string
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from qlever.log import log


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


def run_command(cmd: str, return_output: bool = False,
                show_output: bool = False) -> Optional[str]:
    """
    Run the given command and throw an exception if the exit code is non-zero.
    If `get_output` is `True`, return what the command wrote to `stdout`.

    NOTE: The `set -o pipefail` ensures that the exit code of the command is
    non-zero if any part of the pipeline fails (not just the last part).

    TODO: Find the executable for `bash` in `__init__.py`.
    """
    subprocess_args = {
        "executable": shutil.which("bash"),
        "shell": True,
        "text": True,
        "stdout": None if show_output else subprocess.PIPE,
        "stderr": subprocess.PIPE
    }
    result = subprocess.run(f"set -o pipefail; {cmd}", **subprocess_args)
    # If the exit code is non-zero, throw an exception. If something was
    # written to `stderr`, use that as the exception message. Otherwise, use a
    # generic message (which is also what `subprocess.run` does with
    # `check=True`).
    # log.debug(f"Command `{cmd}` returned the following result")
    # log.debug("")
    # log.debug(f"exit code: {result.returncode}")
    # log.debug(f"stdout: {result.stdout}")
    # log.debug(f"stderr: {result.stderr}")
    # log.debug("")
    if result.returncode != 0:
        if len(result.stderr) > 0:
            raise Exception(result.stderr.replace("\n", " ").strip())
        else:
            raise Exception(
                    f"Command failed with exit code {result.returncode}"
                    f" but nothing written to stderr")
    # Optionally, return what was written to `stdout`.
    if return_output:
        return result.stdout


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


def get_curl_cmd_for_sparql_query(
        query: str, port: int,
        host: str = "localhost",
        media_type: str = "application/sparql-results+qlever",
        verbose: bool = False,
        pinresult: bool = False,
        access_token: Optional[str] = None,
        send: Optional[int] = None) -> str:
    """
    Get curl command for given SPARQL query.
    """
    curl_cmd = (f"curl -s http://{host}:{port}"
                f" -H \"Accept: {media_type}\" "
                f" --data-urlencode query={shlex.quote(query)}")
    if pinresult and access_token is not None:
        curl_cmd += " --data-urlencode pinresult=true"
        curl_cmd += f" --data-urlencode access_token={access_token}"
    if send is not None:
        curl_cmd += f" --data-urlencode send={send}"
    if verbose:
        curl_cmd += " --verbose"
    return curl_cmd


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


def show_process_info(psutil_process, cmdline_regex, show_heading=True):
    """
    Helper function that shows information about a process if information
    about the process can be retrieved and the command line matches the
    given regex (in which case the function returns `True`). The heading is
    only shown if `show_heading` is `True` and the function returns `True`.
    """

    # Helper function that shows a line of the process table.
    def show_table_line(pid, user, start_time, rss, cmdline):
        log.info(f"{pid:<8} {user:<8} {start_time:>5}  {rss:>5} {cmdline}")

    try:
        pinfo = psutil_process.as_dict(
                attrs=['pid', 'username', 'create_time',
                       'memory_info', 'cmdline'])
        # Note: pinfo[`cmdline`] is `None` if the process is a zombie.
        cmdline = " ".join(pinfo['cmdline'] or [])
        if len(cmdline) == 0 or not re.search(cmdline_regex, cmdline):
            return False
        pid = pinfo['pid']
        user = pinfo['username'] if pinfo['username'] else ""
        start_time = datetime.fromtimestamp(pinfo['create_time'])
        if start_time.date() == date.today():
            start_time = start_time.strftime("%H:%M")
        else:
            start_time = start_time.strftime("%b%d")
        rss = f"{pinfo['memory_info'].rss / 1e9:.0f}G"
        if show_heading:
            show_table_line("PID", "USER", "START", "RSS", "COMMAND")
        show_table_line(pid, user, start_time, rss, cmdline)
        return True
    except Exception as e:
        log.error(f"Could not get process info: {e}")
        return False


def get_random_string(length: int) -> str:
    """
    Helper function that returns a randomly chosen string of the given
    length. Take the current time as seed.
    """
    characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))
