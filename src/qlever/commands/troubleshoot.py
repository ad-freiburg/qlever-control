import platform
from importlib.metadata import version
from pathlib import Path
from typing import Optional

import psutil

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command, get_random_string


def generate_heading(text: str, total_width: int = 50) -> str:
    text_length = len(text)
    delimiter_space = total_width - text_length - 2
    if delimiter_space <= 0:
        raise ValueError("Text is too long for the specified width.")
    left_delimiter = delimiter_space // 2
    right_delimiter = delimiter_space - left_delimiter
    heading = f"{'=' * left_delimiter} {text} {'=' * right_delimiter}"
    return heading


def get_partition(dir: Path):
    """
    Returns the partition on which `dir` resides. May return None.
    """
    # The first partition that whose mountpoint is a parent of `dir` is
    # returned. Sort the partitions by the length of the mountpoint to ensure
    # that the result is correct. Assume there are partitions with mountpoint
    # `/` and `/home`. This ensures that `/home/foo` is detected as being in the
    # partition with mountpoint `/home`.
    partitions = sorted(
        psutil.disk_partitions(), key=lambda part: len(part.mountpoint), reverse=True
    )
    for partition in partitions:
        if dir.is_relative_to(partition.mountpoint):
            return partition
    return None


def run_in_container(cmd: str, args) -> Optional[str]:
    """
    Run an arbitrary command in the qlever container and return its output.
    """
    if args.system in Containerize.supported_systems():
        if not args.server_container:
            args.server_container = get_random_string(20)
        run_cmd = Containerize().containerize_command(
            cmd,
            args.system,
            'run --rm -it --entrypoint "" ',
            args.image,
            args.server_container,
            volumes=[("$(pwd)", "/index")],
            working_directory="/index",
        )
        return run_command(run_cmd, return_output=True)


def format_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor


class TroubleshootCommand(QleverCommand):
    def __init__(self):
        pass

    def description(self) -> str:
        return (
            "Please additionally attach the output of this command when "
            "creating issues to help with debugging."
        )

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {"runtime": ["system", "image", "server_container"]}

    def additional_arguments(self, subparser) -> None:
        pass

    def execute(self, args) -> bool:
        log.info(generate_heading("General Info"))
        system = platform.system()
        is_linux = system == "Linux"
        is_mac = system == "Darwin"
        is_windows = system == "Windows"
        if is_windows:
            log.warn("Only limited information is gathered on Windows.")
        log.info(f"qlever-control: {version('qlever')}")
        if is_linux:
            info = platform.freedesktop_os_release()
            log.info(f"OS: {platform.system()} ({info['PRETTY_NAME']})")
        else:
            log.info(f"OS: {platform.system()}")
        log.info(f"Arch: {platform.machine()}")
        log.info(f"Host: {platform.node()}")
        psutil.virtual_memory().total / (1000**3)
        log.info(
            f"RAM: {psutil.virtual_memory().total / (1024.0 ** 3):.1f} GB total, {psutil.virtual_memory().available / (1024.0 ** 3):.1f} GB available"
        )
        log.info(
            f"CPU: {psutil.cpu_count(logical=False)} Cores, {psutil.cpu_count(logical=True)} Threads @ {psutil.cpu_freq().max / 1000:.2f} GHz"
        )

        cwd = Path.cwd()
        log.info(f"CWD: {cwd}")
        # Free and total size of the partition on which the current working
        # directory resides.
        disk_usage = psutil.disk_usage(str(cwd))
        partition = get_partition(cwd)
        log.info(
            f"Disk space in . ({partition.device} @ {partition.mountpoint} is {partition.fstype}): {format_size(disk_usage.free)} free / {format_size(disk_usage.total)} total"
        )
        # User/Group on host and in container
        if is_linux or is_mac:
            log.info(
                f"User/Group on host: {run_command('id', return_output=True).strip()}"
            )
        elif is_windows:
            log.info(
                f"User/Group on host: {run_command('whoami /all', return_output=True).strip()}"
            )
        if args.system in Containerize.supported_systems():
            log.info(
                f"User/Group in container: " f"{run_in_container('id', args).strip()}"
            )

        # Qleverfile
        log.info(generate_heading("Qleverfile"))
        qleverfile = cwd / "Qleverfile"
        if qleverfile.exists():
            # TODO: output the effective qlever file using primites from #57
            log.info(qleverfile.read_text())
        else:
            log.info("No Qleverfile found")
        return True
