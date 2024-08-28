from __future__ import annotations

import os
import platform
from typing import Tuple, Optional

import psutil
import pathlib

from qlever.command import QleverCommand
from qlever.containerize import Containerize
from qlever.log import log

from importlib.metadata import version

from qlever.util import run_command, get_random_string


def run_in_container(cmd: str, args) -> Optional[str]:
   if args.system in Containerize.supported_systems():
       if not args.server_container:
           args.server_container = get_random_string(20)
       run_cmd = Containerize().containerize_command(
           cmd,
           args.system, "run --rm -it --entrypoint \"\" ",
           args.image,
           args.server_container,
           volumes=[("$(pwd)", "/index")],
           working_directory="/index")
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
        return ("Please additionally attach the output of this command when creating issues to help with debugging.")

    def should_have_qleverfile(self) -> bool:
        return True

    def relevant_qleverfile_arguments(self) -> dict[str: list[str]]:
        return {"runtime": ["system", "image", "server_container"]}

    def additional_arguments(self, subparser) -> None:
        pass

    def execute(self, args) -> bool:
        # List of standard major/minor numbers: https://www.kernel.org/doc/html/latest/admin-guide/devices.html
        log.info("="*20+"Basic"+"="*20)
        log.info(f"qlever-control: {version('qlever')}")
        system = platform.system()
        if system == "Linux":
            info = platform.freedesktop_os_release()
            log.info(f"OS: {platform.system()} - {platform.machine()} - {info['PRETTY_NAME']}")
        else:
            log.info(f"OS: {platform.system()} - {platform.machine()}")
        log.info(f"Host: {platform.node()}")
        psutil.virtual_memory().total / (1000**3)
        log.info(f"RAM: {round(psutil.virtual_memory().total / (1024.0**3), 1)} GB total, {round(psutil.virtual_memory().available / (1024.0**3), 1)} GB available")
        # TODO: add cpu model
        log.info(f"CPU: {psutil.cpu_count(logical=False)}/{psutil.cpu_count(logical=True)} @ {psutil.cpu_freq().max/1000} GHz")

        cwd = pathlib.Path.cwd()
        #partitions = psutil.disk_partitions()
        #for partition in partitions:
        #    try:
        #        partition_usage = psutil.disk_usage(partition.mountpoint)
        #        log.info(
        #            f"{partition.device} @ {partition.mountpoint} is {partition.fstype} => {format_size(partition_usage.free)} / {format_size(partition_usage.total)}")
        #    except PermissionError:
        #        # this can be catched due to the disk that
        #        # isn't ready
        #        log.info(
        #            f"{partition.device} @ {partition.mountpoint} is {partition.fstype} => couldn't determine disk usage")
        def perm2str(oct: int) -> str:
            values = [(4, "r"), (2, "w"), (1, "x")]
            res = ""
            for value,letter in values:
               if oct & value:
                   res += letter
               else:
                   res += "-"
            return res
        def extract_permissions(stat: os.stat_result) -> Tuple[str, str, str]:
            perms = stat.st_mode % 0o1000 # The top bits are the type
            return perm2str((perms >> 6) % 0o10), perm2str((perms >> 3) % 0o10), perm2str(perms % 0o10)
        log.info(f"CWD: {cwd}")
        # Determine the disk on which . resides on print its metadata.
        major, minor = (cwd.stat().st_dev >> 8) & 0xfff, cwd.stat().st_dev & 0xff
        dev_name = run_command(f". /sys/dev/block/{major}:{minor}/uevent && echo -n $DEVNAME", return_output=True)
        partition = [partition for partition in psutil.disk_partitions() if partition.device == f"/dev/{dev_name}"]
        assert len(partition) == 1
        partition = partition[0]
        disk_usage = psutil.disk_usage(str(cwd))
        log.info(
            f"Disk space in . ({partition.device} @ {partition.mountpoint} is {partition.fstype}): {format_size(disk_usage.free)} / {format_size(disk_usage.total)}")
        # User/Group on host and in container
        log.info(f"User/Group on host: {run_command('id', return_output=True).strip()}")
        if args.system in Containerize.supported_systems():
            log.info(f"User/Group in container: {run_in_container('id', args).strip()}")
        # Permissions of files on host and in container
        log.info("="*20+"Permissions of files (on host)"+"="*20)
        log.info(run_command("ls -lanh", return_output=True).strip())
        if args.system in Containerize.supported_systems():
            log.info("="*20+"Permissions of files (in container)"+"="*20)
            log.info(run_in_container("ls -lanh", args).strip())
        # Qleverfile
        # TODO: output the effective qlever file using primites from #57
        log.info("="*20+"Qleverfile"+"="*20)
        log.info(run_command("cat Qleverfile", return_output=True).strip())
        #relevant_files = {}
        #for file in cwd.iterdir():
        #    relevant_files[file] = extract_permissions(file.stat())
        #inverted = {}
        #for k,v in relevant_files.items():
        #    if v in inverted:
        #        inverted[v].append(k)
        #    else:
        #        inverted[v] = [k]
        #if len(inverted) == 1:
        #    log.info(f"All files have permission: {inverted.items()[0]:02o}")
        #else:
        #    for perm, files in inverted.items():
        #        log.info(f"{perm} (#{len(files)}): {[file.name for file in files]}")
        return True

