import platform
from importlib.metadata import version
from pathlib import Path
from typing import Optional

import psutil

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log
from qlever.util import run_command, get_random_string, generate_heading, format_size, run_in_container


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

class SystemInfoCommand(QleverCommand):
    def __init__(self):
        pass

    def description(self) -> str:
        return "Gather some system info to help with troubleshooting"

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
