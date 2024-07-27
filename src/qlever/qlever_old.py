#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# This is the `qlever` script (new version, written in Python).  It serves as a
# convenient command-line tool for all things QLever.  See the `README.md` file
# for how to use it.

import glob
import inspect
import json
import logging
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
import traceback
from configparser import ConfigParser, ExtendedInterpolation
from datetime import date, datetime

import pkg_resources
import psutil

from qlever.log import log

BLUE = "\033[34m"
RED = "\033[31m"
BOLD = "\033[1m"
NORMAL = "\033[0m"

# # Custom formatter for log messages.
# class CustomFormatter(logging.Formatter):
#     def format(self, record):
#         message = record.getMessage()
#         if record.levelno == logging.DEBUG:
#             return colored(message, "magenta")
#         elif record.levelno == logging.WARNING:
#             return colored(message, "yellow")
#         elif record.levelno in [logging.CRITICAL, logging.ERROR]:
#             return colored(message, "red")
#         else:
#             return message
#
#
# # Custom logger.
# log = logging.getLogger("qlever")
# log.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# handler.setFormatter(CustomFormatter())
# log.addHandler(handler)


# Helper function for tracking the order of the actions in class `Actions`.
def track_action_rank(method):
    method.rank = track_action_rank.counter
    track_action_rank.counter += 1
    return method
track_action_rank.counter = 0  # noqa: E305


# Abort the script.
def abort_script(error_code=1):
    log.info("")
    sys.exit(error_code)


# Show the available config names.
def show_available_config_names():
    # Get available config names from the Qleverfiles directory (which should
    # be in the same directory as this script).
    script_dir = os.path.dirname(__file__)
    try:
        qleverfiles_dir = os.path.join(script_dir, "Qleverfiles")
        config_names = [qleverfile_name.split(".")[1] for
                        qleverfile_name in os.listdir(qleverfiles_dir)]
        if not config_names:
            raise Exception(f"Directory \"{qleverfiles_dir}\" exists, but "
                            f"contains no Qleverfiles")
    except Exception as e:
        log.error(f"Could not find any Qleverfiles in \"{qleverfiles_dir}\" "
                  f"({e})")
        log.info("")
        log.info("Check that you have fully downloaded or cloned "
                 "https://github.com/ad-freiburg/qlever-control, and "
                 "not just the script itself")
        abort_script()
    # Show available config names.
    log.info(f"Available config names are: {', '.join(sorted(config_names))}")


# Show the available action names.
def show_available_action_names():
    log.info("You can now execute a sequence of actions, for example:")
    log.info("")
    log.info(f"{BLUE}qlever-old get-data index restart test-query ui {NORMAL}")
    log.info("")
    log.info(f"Available action names are: {', '.join(action_names)}")
    log.info("")
    log.info("To get autocompletion for these, run the following or "
             "add it to your `.bashrc`:")
    log.info("")
    log.info(f"{BLUE}eval \"$(qlever-old setup-autocompletion)\"{NORMAL}")


# We want to distinguish between exception that we throw intentionally and all
# others.
class ActionException(Exception):
    pass


# This class contains all the action :-)
class Actions:

    def __init__(self):
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        # Check if the Qleverfile exists.
        if not os.path.isfile("Qleverfile"):
            log.setLevel(logging.INFO)
            log.info("")
            log.error("The qlever script needs a \"Qleverfile\" "
                      "in the current directory, but I could not find it")
            log.info("")
            log.info("Run `qlever-old setup-config <config name>` to create a "
                     "pre-filled Qleverfile")
            log.info("")
            show_available_config_names()
            abort_script()
        files_read = self.config.read("Qleverfile")
        if not files_read:
            log.error("ConfigParser could not read \"Qleverfile\"")
            abort_script()
        self.name = self.config['data']['name']
        self.yes_values = ["1", "true", "yes"]

        # Defaults for [server] that carry over from [index].
        for option in ["with_text_index", "only_pso_and_pos_permutations",
                       "use_patterns"]:
            if option in self.config['index'] and \
                    option not in self.config['server']:
                self.config['server'][option] = \
                    self.config['index'][option]

        # Default values for options that are not mandatory in the Qleverfile.
        defaults = {
            "general": {
                "log_level": "info",
                "pid": "0",
                "example_queries_url": (f"https://qlever.cs.uni-freiburg.de/"
                                        f"api/examples/"
                                        f"{self.config['ui']['config']}"),
                "example_queries_limit": "10",
                "example_queries_send": "0",
            },
            "index": {
                "binary": "IndexBuilderMain",
                "with_text_index": "false",
                "only_pso_and_pos_permutations": "false",
                "use_patterns": "true",
            },
            "server": {
                "port": "7000",
                "binary": "ServerMain",
                "num_threads": "8",
                "cache_max_size": "5G",
                "cache_max_size_single_entry": "1G",
                "cache_max_num_entries": "100",
                "with_text_index": "false",
                "only_pso_and_pos_permutations": "false",
                "timeout": "30s",
                "use_patterns": "true",
                "url": f"http://localhost:{self.config['server']['port']}",
            },
            "docker": {
                "image": "adfreiburg/qlever",
                "container_server": f"qlever.server.{self.name}",
                "container_indexer": f"qlever.indexer.{self.name}",
            },
            "ui": {
                "port": "7000",
                "image": "adfreiburg/qlever-ui",
                "container": "qlever-ui",
                "url": "https://qlever.cs.uni-freiburg.de/api",

            }
        }
        for section in defaults:
            # If the section does not exist, create it.
            if not self.config.has_section(section):
                self.config[section] = {}
            # If an option does not exist, set it to the default value.
            for option in defaults[section]:
                if not self.config[section].get(option):
                    self.config[section][option] = defaults[section][option]

        # If the log level was not explicitly set by the first command-line
        # argument (see below), set it according to the Qleverfile.
        if log.level == logging.NOTSET:
            log_level = self.config['general']['log_level'].upper()
            try:
                log.setLevel(getattr(logging, log_level))
            except AttributeError:
                log.error(f"Invalid log level: \"{log_level}\"")
                abort_script()

        # Show some information (for testing purposes only).
        log.debug(f"Parsed Qleverfile, sections are: "
                  f"{', '.join(self.config.sections())}")

        # Check specifics of the installation.
        self.check_installation()

    def check_installation(self):
        """
        Helper function that checks particulars of the installation and
        remembers them so that all actions execute without errors.
        """

        # Handle the case Systems like macOS do not allow
        # psutil.net_connections().
        try:
            psutil.net_connections()
            self.net_connections_enabled = True
        except Exception as e:
            self.net_connections_enabled = False
            log.debug(f"Note: psutil.net_connections() failed ({e}),"
                      f" will not scan network connections for action"
                      f" \"start\"")

        # Check whether docker is installed and works (on MacOS 12, docker
        # hangs when installed without GUI, hence the timeout).
        try:
            completed_process = subprocess.run(
                    ["docker", "info"], timeout=0.5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if completed_process.returncode != 0:
                raise Exception("docker info failed")
            self.docker_enabled = True
        except Exception:
            self.docker_enabled = False
            print("Note: `docker info` failed, therefore"
                  " docker.USE_DOCKER=true not supported")

    def set_config(self, section, option, value):
        """
        Helper function that sets a value in the config file (and throws an
        exceptionon if the section or option does not exist).
        """

        if not self.config.has_section(section):
            log.error(f"Section [{section}] does not exist in Qleverfile")
            abort_script()
        if not self.config.has_option(section, option):
            log.error(f"Option {option.upper()} does not exist in section "
                      f"[{section}] in Qleverfile")
            abort_script()
        self.config[section][option] = value

    def get_total_file_size(self, paths):
        """
        Helper function that gets the total size of all files in the given
        paths in GB.
        """

        total_size = 0
        for path in paths:
            for file in glob.glob(path):
                total_size += os.path.getsize(file)
        return total_size / 1e9

    def alive_check(self, port):
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

    def show_process_info(self, psutil_process,
                          cmdline_regex, show_heading=True):
        """
        Helper function that shows information about a process if information
        about the process can be retrieved and the command line matches the
        given regex (in which case the function returns `True`). The heading is
        only shown if `show_heading` is `True` and the function returns `True`.
        """

        def show_table_line(pid, user, start_time, rss, cmdline):
            log.info(f"{pid:<8} {user:<8} {start_time:>5}  {rss:>5} {cmdline}")
        try:
            pinfo = psutil_process.as_dict(
                    attrs=['pid', 'username', 'create_time',
                           'memory_info', 'cmdline'])
            cmdline = " ".join(pinfo['cmdline'])
            if not re.search(cmdline_regex, cmdline):
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
            log.debug(f"Could not get process info: {e}")
            return False

    def show(self, action_description, only_show):
        """
        Helper function that shows the command line or description of an
        action, together with an explanation.
        """

        log.info(f"{BLUE}{action_description}{NORMAL}")
        log.info("")
        if only_show:
            log.info("You called \"qlever-old ... show\", therefore the "
                     "action is only shown, but not executed (omit the "
                     "\"show\" to execute it)")

    @staticmethod
    @track_action_rank
    def action_setup_config(config_name="default"):
        """
        Setup a pre-filled Qleverfile in the current directory.
        """

        # log.info(f"{BLUE}Creating a pre-filled Qleverfile{NORMAL}")
        # log.info("")

        # If there is already a Qleverfile in the current directory, exit.
        if os.path.isfile("Qleverfile"):
            log.error("Qleverfile already exists in current directory")
            log.info("")
            log.info("If you want to create a new Qleverfile using "
                     "`qlever-old setup-config`, delete the existing "
                     "Qleverfile first")
            abort_script()

        # Get the directory of this script and copy the Qleverfile for `config`
        # to the current directory.
        script_dir = os.path.dirname(os.path.realpath(__file__))
        qleverfile_path = os.path.join(script_dir,
                                       f"Qleverfiles/Qleverfile.{config_name}")
        if not os.path.isfile(qleverfile_path):
            log.error(f"File \"{qleverfile_path}\" does not exist")
            log.info("")
            abort_script()
        try:
            shutil.copy(qleverfile_path, "Qleverfile")
        except Exception as e:
            log.error(f"Could not copy \"{qleverfile_path}\""
                      f" to current directory: {e}")
            abort_script()
        log.info(f"Created Qleverfile for config \"{config_name}\""
                 f" in current directory")
        log.info("")
        if config_name == "default":
            log.info("Since this is the default Qleverfile, you need to "
                     "edit it before you can continue")
            log.info("")
            log.info("Afterwards, run `qlever` without arguments to see "
                     "which actions are available")
        else:
            show_available_action_names()
        log.info("")

    @track_action_rank
    def action_show_config(self, only_show=False):
        """
        Action that shows the current configuration including the default
        values for options that are not set explicitly in the Qleverfile.
        """

        print(f"{BLUE}Showing the current configuration, including default"
              f" values for options that are not set explicitly in the"
              f" Qleverfile{NORMAL}")
        for section in self.config.sections():
            print()
            print(f"[{section}]")
            max_option_length = max([len(option) for option in
                                     self.config[section]])
            for option in self.config[section]:
                print(f"{option.upper().ljust(max_option_length)} = "
                      f"{self.config[section][option]}")

        print()

    @track_action_rank
    def action_get_data(self, only_show=False):
        """
        Action that gets the data according to GET_DATA_CMD.
        """

        # Construct the command line.
        if not self.config['data']['get_data_cmd']:
            log.error(f"{RED}No GET_DATA_CMD specified in Qleverfile")
            return
        get_data_cmd = self.config['data']['get_data_cmd']

        # Show it.
        self.show(get_data_cmd, only_show)
        if only_show:
            return

        # Execute the command line.
        subprocess.run(get_data_cmd, shell=True)
        total_file_size = self.get_total_file_size(
            self.config['index']['file_names'].split())
        print(f"Total file size: {total_file_size:.1f} GB")

    @track_action_rank
    def action_index(self, only_show=False):
        """
        Action that builds a QLever index according to the settings in the
        [index] section of the Qleverfile.
        """

        # Construct the command line based on the config file.
        index_config = self.config['index']
        cmdline = (f"{index_config['cat_files']} | {index_config['binary']}"
                   f" -F ttl -f -"
                   f" -i {self.name}"
                   f" -s {self.name}.settings.json")
        if index_config['only_pso_and_pos_permutations'] in self.yes_values:
            cmdline += " --only-pso-and-pos-permutations --no-patterns"
        if not index_config['use_patterns'] in self.yes_values:
            cmdline += " --no-patterns"
        if index_config['with_text_index'] in \
                ["from_text_records", "from_text_records_and_literals"]:
            cmdline += (f" -w {self.name}.wordsfile.tsv"
                        f" -d {self.name}.docsfile.tsv")
        if index_config['with_text_index'] in \
                ["from_literals", "from_text_records_and_literals"]:
            cmdline += " --text-words-from-literals"
        if 'stxxl_memory' in index_config:
            cmdline += f" --stxxl-memory {index_config['stxxl_memory']}"
        cmdline += f" | tee {self.name}.index-log.txt"

        # If the total file size is larger than 10 GB, set ulimit (such that a
        # large number of open files is allowed).
        total_file_size = self.get_total_file_size(
                self.config['index']['file_names'].split())
        if total_file_size > 10:
            cmdline = f"ulimit -Sn 1048576; {cmdline}"

        # If we are using Docker, run the command in a Docker container.
        # Here is how the shell script does it:
        if self.config['docker']['use_docker'] in self.yes_values:
            docker_config = self.config['docker']
            cmdline = (f"docker run -it --rm -u $(id -u):$(id -g)"
                       f" -v /etc/localtime:/etc/localtime:ro"
                       f" -v $(pwd):/index -w /index"
                       f" --entrypoint bash"
                       f" --name {docker_config['container_indexer']}"
                       f" {docker_config['image']}"
                       f" -c {shlex.quote(cmdline)}")

        # Show the command line.
        self.show(f"Write value of config variable index.SETTINGS_JSON to "
                  f"file {self.name}.settings.json\n"
                  f"{cmdline}", only_show)
        if only_show:
            return

        # When docker.USE_DOCKER=false, check if the binary for building the
        # index exists and works.
        if self.config['docker']['use_docker'] not in self.yes_values:
            try:
                check_binary_cmd = f"{self.config['index']['binary']} --help"
                subprocess.run(check_binary_cmd, shell=True, check=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                log.error(f"Running \"{check_binary_cmd}\" failed ({e}), "
                          f"set index.BINARY to a different binary or "
                          f"set docker.USE_DOCKER=true")
                abort_script()

        # Check if index files (name.index.*) already exist.
        if glob.glob(f"{self.name}.index.*"):
            raise ActionException(
                    f"Index files \"{self.name}.index.*\" already exist, "
                    f"please delete them if you want to rebuild the index")

        # Write settings.json file and run the command.
        with open(f"{self.name}.settings.json", "w") as f:
            f.write(self.config['index']['settings_json'])
        subprocess.run(cmdline, shell=True)

    @track_action_rank
    def action_remove_index(self, only_show=False):
        """
        Action that removes the index files.
        """

        # List of all the index files (not all of them need to be there).
        index_fileglobs = (f"{self.name}.index.*",
                           f"{self.name}.patterns.*",
                           f"{self.name}.prefixes",
                           f"{self.name}.meta-data.json",
                           f"{self.name}.vocabulary.*")

        # Show the command line.
        self.show(f"Remove index files {', '.join(index_fileglobs)}",
                  only_show)
        if only_show:
            return

        # Remove the index files.
        files_removed = []
        total_file_size = 0
        for index_fileglob in index_fileglobs:
            for filename in glob.glob(index_fileglob):
                if os.path.isfile(filename):
                    total_file_size += os.path.getsize(filename)
                    os.remove(filename)
                    files_removed.append(filename)
        if files_removed:
            log.info(f"Removed the following index files of total size "
                     f"{total_file_size / 1e9:.1f} GB:")
            log.info("")
            log.info(", ".join(files_removed))
        else:
            log.info("None of the listed index files found, nothing removed")

    @track_action_rank
    def action_start(self, only_show=False):
        """
        Action that starts the QLever server according to the settings in the
        [server] section of the Qleverfile. If a server is already running, the
        action reports that fact and does nothing.
        """

        # Construct the command line based on the config file.
        server_config = self.config['server']
        cmdline = (f"{self.config['server']['binary']}"
                   f" -i {self.name}"
                   f" -j {server_config['num_threads']}"
                   f" -p {server_config['port']}"
                   f" -m {server_config['memory_for_queries']}"
                   f" -c {server_config['cache_max_size']}"
                   f" -e {server_config['cache_max_size_single_entry']}"
                   f" -k {server_config['cache_max_num_entries']}")
        if server_config['timeout']:
            cmdline += f" -s {server_config['timeout']}"
        if server_config['access_token']:
            cmdline += f" -a {server_config['access_token']}"
        if server_config['only_pso_and_pos_permutations'] in self.yes_values:
            cmdline += " --only-pso-and-pos-permutations"
        if not server_config['use_patterns'] in self.yes_values:
            cmdline += " --no-patterns"
        if server_config['with_text_index'] in \
                ["from_text_records",
                 "from_literals",
                 "from_text_records_and_literals"]:
            cmdline += " -t"
        cmdline += f" > {self.name}.server-log.txt 2>&1"

        # If we are using Docker, run the command in a docker container.
        if self.config['docker']['use_docker'] in self.yes_values:
            docker_config = self.config['docker']
            cmdline = (f"docker run -d --restart=unless-stopped"
                       f" -u $(id -u):$(id -g)"
                       f" -it -v /etc/localtime:/etc/localtime:ro"
                       f" -v $(pwd):/index"
                       f" -p {server_config['port']}:{server_config['port']}"
                       f" -w /index"
                       f" --entrypoint bash"
                       f" --name {docker_config['container_server']}"
                       f" --init"
                       f" {docker_config['image']}"
                       f" -c {shlex.quote(cmdline)}")
        else:
            cmdline = f"nohup {cmdline} &"

        # Show the command line.
        self.show(cmdline, only_show)
        if only_show:
            return

        # When docker.USE_DOCKER=false, check if the binary for starting the
        # server exists and works.
        if self.config['docker']['use_docker'] not in self.yes_values:
            try:
                check_binary_cmd = f"{self.config['server']['binary']} --help"
                subprocess.run(check_binary_cmd, shell=True, check=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                log.error(f"Running \"{check_binary_cmd}\" failed ({e}), "
                          f"set server.BINARY to a different binary or "
                          f"set docker.USE_DOCKER=true")
                abort_script()

        # Check if a QLever server is already running on this port.
        port = server_config['port']
        if self.alive_check(port):
            raise ActionException(
                    f"QLever server already running on port {port}")

        # Check if another process is already listening.
        if self.net_connections_enabled:
            if port in [conn.laddr.port for conn
                        in psutil.net_connections()]:
                raise ActionException(
                        f"Port {port} is already in use by another process")

        # Execute the command line.
        subprocess.run(cmdline, shell=True,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        # Tail the server log until the server is ready (note that the `exec`
        # is important to make sure that the tail process is killed and not
        # just the bash process).
        log.info(f"Follow {self.name}.server-log.txt until the server is ready"
                 f" (Ctrl-C stops following the log, but not the server)")
        log.info("")
        tail_cmd = f"exec tail -f {self.name}.server-log.txt"
        tail_proc = subprocess.Popen(tail_cmd, shell=True)
        while not self.alive_check(port):
            time.sleep(1)

        # Set the access token if specified.
        access_token = server_config['access_token']
        access_arg = f"--data-urlencode \"access-token={access_token}\""
        if "index_description" in self.config['data']:
            desc = self.config['data']['index_description']
            curl_cmd = (f"curl -Gs http://localhost:{port}/api"
                        f" --data-urlencode \"index-description={desc}\""
                        f" {access_arg} > /dev/null")
            log.debug(curl_cmd)
            subprocess.run(curl_cmd, shell=True)
        if "text_description" in self.config['data']:
            desc = self.config['data']['text_description']
            curl_cmd = (f"curl -Gs http://localhost:{port}/api"
                        f" --data-urlencode \"text-description={desc}\""
                        f" {access_arg} > /dev/null")
            log.debug(curl_cmd)
            subprocess.run(curl_cmd, shell=True)

        # Kill the tail process. NOTE: `tail_proc.kill()` does not work.
        tail_proc.terminate()

    @track_action_rank
    def action_stop(self, only_show=False, fail_if_not_running=True):
        """
        Action that stops the QLever server according to the settings in the
        [server] section of the Qleverfile. If no server is running, the action
        does nothing.
        """

        # Show action description.
        docker_container_name = self.config['docker']['container_server']
        cmdline_regex = (f"ServerMain.* -i [^ ]*{self.name}")
        self.show(f"Checking for process matching \"{cmdline_regex}\" "
                  f"and for Docker container with name "
                  f"\"{docker_container_name}\"", only_show)
        if only_show:
            return

        # First check if there is docker container running.
        if self.docker_enabled:
            docker_cmd = (f"docker stop {docker_container_name} && "
                          f"docker rm {docker_container_name}")
            try:
                subprocess.run(docker_cmd, shell=True, check=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                log.info(f"Docker container with name "
                         f"\"{docker_container_name}\" "
                         f"stopped and removed")
                return
            except Exception as e:
                log.debug(f"Error running \"{docker_cmd}\": {e}")

        # Check if there is a process running on the server port using psutil.
        #
        # NOTE: On MacOS, some of the proc's returned by psutil.process_iter()
        # no longer exist when we try to access them, so we just skip them.
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(
                        attrs=['pid', 'username', 'create_time',
                               'memory_info', 'cmdline'])
                cmdline = " ".join(pinfo['cmdline'])
            except Exception as err:
                log.debug(f"Error getting process info: {err}")
            if re.match(cmdline_regex, cmdline):
                log.info(f"Found process {pinfo['pid']} from user "
                         f"{pinfo['username']} with command line: {cmdline}")
                print()
                try:
                    proc.kill()
                    log.info(f"Killed process {pinfo['pid']}")
                except Exception as e:
                    raise ActionException(
                            f"Could not kill process with PID "
                            f"{pinfo['pid']}: {e}")
                return

        # No matching process found.
        message = "No matching process or Docker container found"
        if fail_if_not_running:
            raise ActionException(message)
        else:
            log.info(f"{message}, so nothing to stop")

    @track_action_rank
    def action_restart(self, only_show=False):
        """
        Action that restarts the QLever server.
        """

        # Show action description.
        self.show("Stop running server if found, then start new server",
                  only_show)
        if only_show:
            return

        # Do it.
        self.action_stop(only_show=only_show, fail_if_not_running=False)
        log.info("")
        self.action_start()

    @track_action_rank
    def action_log(self, only_show=False):
        """
        Action that shows the server log.
        """

        # Show action description.
        log_cmd = f"tail -f -n 50 {self.name}.server-log.txt"
        self.show(log_cmd, only_show)
        if only_show:
            return

        # Do it.
        log.info(f"Follow {self.name}.server-log.txt (Ctrl-C stops"
                 f" following the log, but not the server)")
        log.info("")
        subprocess.run(log_cmd, shell=True)

    @track_action_rank
    def action_status(self, only_show=False):
        """
        Action that shows all QLever processes running on this machine.

        TODO: Also show the QLever-related docker containers.
        """

        # Show action description.
        cmdline_regex = "(ServerMain|IndexBuilderMain)"
        # cmdline_regex = f"(ServerMain|IndexBuilderMain).*{self.name}"
        self.show(f"{BLUE}Show all processes on this machine where "
                  f"the command line matches {cmdline_regex}"
                  f" using Python's psutil library", only_show)
        if only_show:
            return

        # Show the results as a table.
        num_processes_found = 0
        for proc in psutil.process_iter():
            show_heading = num_processes_found == 0
            process_shown = self.show_process_info(proc, cmdline_regex,
                                                   show_heading=show_heading)
            if process_shown:
                num_processes_found += 1
        if num_processes_found == 0:
            print("No processes found")

    @track_action_rank
    def action_index_stats(self, only_show=False):
        """
        Action that provides a breakdown of the time needed for building the
        index, based on the log file of th index build.
        """

        log_file_name = self.config['data']['name'] + ".index-log.txt"
        log.info(f"{BLUE}Breakdown of the time for building the index, "
                 f"based on the timestamps for key lines in "
                 f"\"{log_file_name}{NORMAL}\"")
        log.info("")
        if only_show:
            return

        # Read the content of `log_file_name` into a list of lines.
        try:
            with open(log_file_name, "r") as f:
                lines = f.readlines()
        except Exception as e:
            raise ActionException(f"Could not read log file {log_file_name}: "
                                  f"{e}")
        current_line = 0

        # Helper lambda that finds the next line matching the given `regex`,
        # starting from `current_line`, and extracts the time. Returns a tuple
        # of the time and the regex match object. If a match is found,
        # `current_line` is updated to the line after the match. Otherwise,
        # `current_line` will be one beyond the last line, unless
        # `line_is_optional` is true, in which case it will be the same as when
        # the function was entered.
        def find_next_line(regex, line_is_optional=False):
            nonlocal lines
            nonlocal current_line
            current_line_backup = current_line
            # Find starting from `current_line`.
            while current_line < len(lines):
                line = lines[current_line]
                current_line += 1
                timestamp_regex = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
                timestamp_format = "%Y-%m-%d %H:%M:%S"
                regex_match = re.search(regex, line)
                if regex_match:
                    try:
                        return datetime.strptime(
                                re.match(timestamp_regex, line).group(),
                                timestamp_format), regex_match
                    except Exception as e:
                        raise ActionException(
                                f"Could not parse timestamp of form "
                                f"\"{timestamp_regex}\" from line "
                                f" \"{line.rstrip()}\" ({e})")
            # If we get here, we did not find a matching line.
            if line_is_optional:
                current_line = current_line_backup
            return None, None

        # Find the lines matching th key_lines_regex and extract the time
        # information from them.
        overall_begin, _ = find_next_line(r"INFO:\s*Processing")
        merge_begin, _ = find_next_line(r"INFO:\s*Merging partial vocab")
        convert_begin, _ = find_next_line(r"INFO:\s*Converting triples")
        perm_begin_and_info = []
        while True:
            perm_begin, _ = find_next_line(r"INFO:\s*Creating a pair", True)
            if perm_begin is None:
                break
            _, perm_info = find_next_line(r"INFO:\s*Writing meta data for"
                                          r" ([A-Z]+ and [A-Z]+)", True)
            # if perm_info is None:
            #     break
            perm_begin_and_info.append((perm_begin, perm_info))
        convert_end = (perm_begin_and_info[0][0] if
                       len(perm_begin_and_info) > 0 else None)
        normal_end, _ = find_next_line(r"INFO:\s*Index build completed")
        text_begin, _ = find_next_line(r"INFO:\s*Adding text index", True)
        text_end, _ = find_next_line(r"INFO:\s*DocsDB done", True)
        # print("DEBUG:", len(perm_begin_and_info), perm_begin_and_info)
        # print("DEBUG:", overall_begin)
        # print("DEBUG:", normal_end)

        # Check whether at least the first phase is done.
        if overall_begin is None:
            raise ActionException("Missing line that index build has started")
        if overall_begin and not merge_begin:
            raise ActionException("According to the log file, the index build "
                                  "has started, but is still in its first "
                                  "phase (parsing the input)")

        # Helper lambda that shows the duration for a phase (if the start and
        # end timestamps are available).
        def show_duration(heading, start_end_pairs):
            nonlocal unit
            num_start_end_pairs = 0
            diff_seconds = 0
            for start, end in start_end_pairs:
                if start and end:
                    diff_seconds += (end - start).total_seconds()
                    num_start_end_pairs += 1
            if num_start_end_pairs > 0:
                if unit == "h":
                    diff = diff_seconds / 3600
                elif unit == "min":
                    diff = diff_seconds / 60
                else:
                    diff = diff_seconds
                log.info(f"{heading:<23} : {diff:>5.1f} {unit}")

        # Get the times of the various phases (hours or minutes, depending on
        # how long the first phase took).
        unit = "h"
        if merge_begin and overall_begin:
            parse_duration = (merge_begin - overall_begin).total_seconds()
            if parse_duration < 200:
                unit = "s"
            elif parse_duration < 3600:
                unit = "min"
        show_duration("Parse input", [(overall_begin, merge_begin)])
        show_duration("Build vocabularies", [(merge_begin, convert_begin)])
        show_duration("Convert to global IDs", [(convert_begin, convert_end)])
        for i in range(len(perm_begin_and_info)):
            perm_begin, perm_info = perm_begin_and_info[i]
            perm_end = perm_begin_and_info[i + 1][0] if i + 1 < len(
                    perm_begin_and_info) else normal_end
            perm_info_text = (perm_info.group(1).replace(" and ", " & ")
                              if perm_info else f"#{i + 1}")
            show_duration(f"Permutation {perm_info_text}",
                          [(perm_begin, perm_end)])
        show_duration("Text index", [(text_begin, text_end)])
        if text_begin and text_end:
            log.info("")
            show_duration("TOTAL index build time",
                          [(overall_begin, normal_end),
                           (text_begin, text_end)])
        elif normal_end:
            log.info("")
            show_duration("TOTAL index build time",
                          [(overall_begin, normal_end)])

    @track_action_rank
    def action_test_query(self, only_show=False):
        """
        Action that sends a simple test SPARQL query to the server.
        """

        # Construct the curl command.
        query = "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
        headers = ["Accept: text/tab-separated-values",
                   "Content-Type: application/sparql-query"]
        curl_cmd = (f"curl -s {self.config['server']['url']} "
                    f"-H \"{headers[0]}\" -H \"{headers[1]}\" "
                    f"--data \"{query}\"")

        # Show it.
        self.show(curl_cmd, only_show)
        if only_show:
            return

        # Execute it.
        subprocess.run(curl_cmd, shell=True)

    @track_action_rank
    def action_ui(self, only_show=False):
        """
        Action that starts the QLever UI with the server according to the
        Qleverfile as backend.
        """

        # Construct commands.
        host_name = socket.getfqdn()
        server_url = f"http://{host_name}:{self.config['server']['port']}"
        docker_rm_cmd = f"docker rm -f {self.config['ui']['container']}"
        docker_pull_cmd = f"docker pull {self.config['ui']['image']}"
        docker_run_cmd = (f"docker run -d -p {self.config['ui']['port']}:7000 "
                          f"--name {self.config['ui']['container']} "
                          f"{self.config['ui']['image']} ")
        docker_exec_cmd = (f"docker exec -it "
                           f"{self.config['ui']['container']} "
                           f"bash -c \"python manage.py configure "
                           f"{self.config['ui']['config']} "
                           f"{server_url}\"")

        # Show them.
        self.show("\n".join([docker_rm_cmd, docker_pull_cmd, docker_run_cmd,
                             docker_exec_cmd]), only_show)
        if only_show:
            return

        # Execute them.
        try:
            subprocess.run(docker_rm_cmd, shell=True,
                           stdout=subprocess.DEVNULL)
            subprocess.run(docker_pull_cmd, shell=True,
                           stdout=subprocess.DEVNULL)
            subprocess.run(docker_run_cmd, shell=True,
                           stdout=subprocess.DEVNULL)
            subprocess.run(docker_exec_cmd, shell=True,
                           stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            raise ActionException(f"Failed to start the QLever UI {e}")
        log.info(f"The QLever UI should now be up at "
                 f"http://{host_name}:{self.config['ui']['port']}")
        log.info("You can log in as QLever UI admin with username and "
                 "password \"demo\"")

    @track_action_rank
    def action_cache_stats_and_settings(self, only_show=False):
        """
        Action that shows the cache statistics and settings.
        """

        # Construct the two curl commands.
        cache_stats_cmd = (f"curl -s {self.config['server']['url']} "
                           f"--data-urlencode \"cmd=cache-stats\"")
        cache_settings_cmd = (f"curl -s {self.config['server']['url']} "
                              f"--data-urlencode \"cmd=get-settings\"")

        # Show them.
        self.show("\n".join([cache_stats_cmd, cache_settings_cmd]), only_show)
        if only_show:
            return

        # Execute them.
        try:
            cache_stats = subprocess.check_output(cache_stats_cmd, shell=True)
            cache_settings = subprocess.check_output(cache_settings_cmd,
                                                     shell=True)

            # Print the key-value pairs of the stats JSON in tabular form.
            def print_json_as_tabular(raw_json):
                key_value_pairs = json.loads(raw_json).items()
                max_key_len = max([len(key) for key, _ in key_value_pairs])
                for key, value in key_value_pairs:
                    if isinstance(value, int) or re.match(r"^\d+$", value):
                        value = "{:,}".format(int(value))
                    if re.match(r"^\d+\.\d+$", value):
                        value = "{:.2f}".format(float(value))
                    log.info(f"{key.ljust(max_key_len)} : {value}")
            print_json_as_tabular(cache_stats)
            log.info("")
            print_json_as_tabular(cache_settings)
        except Exception as e:
            raise ActionException(f"Failed to get cache stats and settings: "
                                  f"{e}")

    @track_action_rank
    def action_clear_cache(self, only_show=False):
        """
        Action that clears the cache (unpinned entries only).
        """

        # Construct the curl command.
        clear_cache_cmd = (f"curl -s {self.config['server']['url']} "
                           f"--data-urlencode \"cmd=clear-cache\"")

        # Show it.
        self.show(clear_cache_cmd, only_show)
        if only_show:
            return

        # Execute it.
        try:
            subprocess.run(clear_cache_cmd, shell=True,
                           stdout=subprocess.DEVNULL)
            print("Cache cleared (only unpinned entries)")
            print()
            self.action_cache_stats_and_settings(only_show)
        except Exception as e:
            raise ActionException(f"Failed to clear the cache: {e}")

    @track_action_rank
    def action_clear_cache_complete(self, only_show=False):
        """
        Action that clears the cache completely (both pinned and unpinned
        entries).
        """

        # Construct the curl command.
        access_token = self.config['server']['access_token']
        clear_cache_cmd = (f"curl -s {self.config['server']['url']} "
                           f"--data-urlencode \"cmd=clear-cache-complete\" "
                           f"--data-urlencode \"access-token={access_token}\"")

        # Show it.
        self.show(clear_cache_cmd, only_show)
        if only_show:
            return

        # Execute it.
        try:
            subprocess.run(clear_cache_cmd, shell=True,
                           stdout=subprocess.DEVNULL)
            print("Cache cleared (both pinned and unpinned entries)")
            print()
            self.action_cache_stats_and_settings(only_show)
        except Exception as e:
            raise ActionException(f"Failed to clear the cache: {e}")

    @track_action_rank
    def action_autocompletion_warmup(self, only_show=False):
        """
        Action that pins the autocompletion queries from `ui.config` to the
        cache.
        """

        # Construct curl command to obtain the warmup queries.
        #
        # TODO: This is the access token expected by Django in views.py, where
        # it is currently set to dummy value. Find a sound yet simple mechanism
        # for this.
        access_token_ui = "top-secret"
        config_name = self.config["ui"]["config"]
        warmup_url = f"{self.config['ui']['url']}/warmup/{config_name}"
        curl_cmd = (f"curl -s {warmup_url}/queries?token={access_token_ui}")

        # Show it.
        self.show(f"Pin warmup queries obtained via: {curl_cmd}", only_show)
        if only_show:
            return

        # Get the queries.
        try:
            queries = subprocess.check_output(curl_cmd, shell=True)
        except subprocess.CalledProcessError as e:
            raise ActionException(f"Failed to get warmup queries ({e})")

        # Iterate over them and pin them to the cache. Give a more generous
        # timeout (which requires an access token).
        header = "Accept: application/qlever-results+json"
        first = True
        timeout = "300s"
        access_token = self.config["server"]["access_token"]
        for description, query in [line.split("\t") for line in
                                   queries.decode("utf-8").split("\n")]:
            if first:
                first = False
            else:
                log.info("")
            log.info(f"{BOLD}Pin query: {description}{NORMAL}")
            pin_cmd = (f"curl -s {self.config['server']['url']}/api "
                       f"-H \"{header}\" "
                       f"--data-urlencode query={shlex.quote(query)} "
                       f"--data-urlencode timeout={timeout} "
                       f"--data-urlencode access-token={access_token} "
                       f"--data-urlencode pinresult=true "
                       f"--data-urlencode send=0")
            clear_cache_cmd = (f"curl -s {self.config['server']['url']} "
                               f"--data-urlencode \"cmd=clear-cache\"")
            log.info(pin_cmd)
            # Launch query and show the `resultsize` of the JSON response.
            try:
                result = subprocess.check_output(pin_cmd, shell=True)
                json_result = json.loads(result.decode("utf-8"))
                # Check if the JSON has a key "exception".
                if "exception" in json_result:
                    raise Exception(json_result["exception"])
                log.info(f"Result size: {json_result['resultsize']:,}")
                log.info(clear_cache_cmd)
                subprocess.check_output(clear_cache_cmd, shell=True,
                                        stderr=subprocess.DEVNULL)
            except Exception as e:
                log.error(f"Query failed: {e}")

    @track_action_rank
    def action_example_queries(self, only_show=False):
        """
        Action that shows the example queries from `ui.config`.
        """

        # Construct curl command to obtain the example queries.
        config_general = self.config["general"]
        example_queries_url = config_general["example_queries_url"]
        example_queries_limit = int(config_general["example_queries_limit"])
        example_queries_send = int(config_general["example_queries_send"])
        curl_cmd = f"curl -s {example_queries_url}"

        # Show what the action does.
        self.show(f"Launch example queries obtained via: {curl_cmd}\n"
                  f"SPARQL endpoint: {self.config['server']['url']}\n"
                  f"Clearing the cache before each query\n"
                  f"Using send={example_queries_send} and limit="
                  f"{example_queries_limit}",
                  only_show)
        if only_show:
            return

        # Get the queries.
        try:
            queries = subprocess.check_output(curl_cmd, shell=True)
        except subprocess.CalledProcessError as e:
            raise ActionException(f"Failed to get example queries ({e})")

        # Launch the queries one after the other and for each print: the
        # description, the result size, and the query processing time.
        count = 0
        total_time_seconds = 0.0
        total_result_size = 0
        for description, query in [line.split("\t") for line in
                                   queries.decode("utf-8").splitlines()]:
            # Launch query and show the `resultsize` of the JSON response.
            clear_cache_cmd = (f"curl -s {self.config['server']['url']} "
                               f"--data-urlencode cmd=clear-cache")
            query_cmd = (f"curl -s {self.config['server']['url']} "
                         f"-H \"Accept: application/qlever-results+json\" "
                         f"--data-urlencode query={shlex.quote(query)} "
                         f"--data-urlencode send={example_queries_send}")
            try:
                subprocess.run(clear_cache_cmd, shell=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                start_time = time.time()
                result = subprocess.check_output(query_cmd, shell=True)
                time_seconds = time.time() - start_time
                json_result = json.loads(result.decode("utf-8"))
                if "exception" in json_result:
                    raise Exception(json_result["exception"])
                result_size = int(json_result["resultsize"])
                result_string = f"{result_size:>14,}"
            except Exception as e:
                time_seconds = 0.0
                result_size = 0
                result_string = (f"{RED}        FAILED{NORMAL}"
                                 f" {RED}({e}){NORMAL}")

            # Print description, time, result in tabular form.
            log.debug(query)
            if (len(description) > 60):
                description = description[:57] + "..."
            log.info(f"{description:<60}  {time_seconds:6.2f} s  "
                     f"{result_string}")
            count += 1
            total_time_seconds += time_seconds
            total_result_size += result_size
            if count == example_queries_limit:
                break

        # Print total time.
        log.info("")
        description = (f"TOTAL   for {count} "
                       f"{'query' if count == 1 else 'queries'}")
        log.info(f"{description:<60}  {total_time_seconds:6.2f} s  "
                 f"{total_result_size:>14,}")
        description = (f"AVERAGE for {count} "
                       f"{'query' if count == 1 else 'queries'}")
        log.info(f"{description:<60}  {total_time_seconds / count:6.2f} s  "
                 f"{round(total_result_size / count):>14,}")

    @track_action_rank
    def action_memory_profile(self, only_show=False):
        """
        Action that prints the memory usage of a process (specified via
        `general.PID`) to a file `<PID>.memory-usage.tsv`.
        """

        # Show what the action does.
        self.show("Poll memory usage of the given process every second "
                  "and print it to a file", only_show)
        if only_show:
            return

        # Show process information.
        if "pid" not in self.config["general"]:
            raise ActionException("PID must be specified via general.PID")
        try:
            pid = int(self.config["general"]["pid"])
            proc = psutil.Process(pid)
        except Exception as e:
            raise ActionException(f"Could not obtain information for process "
                                  f"with PID {pid} ({e})")
        self.show_process_info(proc, "", show_heading=True)
        log.info("")

        # As long as the process exists, poll memory usage once per second and
        # print it to the screen as well as to a file `<PID>.memory-usage.tsv`.
        file = open(f"{pid}.memory-usage.tsv", "w")
        seconds = 0
        while proc.is_running():
            # Get memory usage in bytes and print as <timestamp>\t<size>, with
            # the timestand in the usual logger format (second precision).
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            memory_usage_gb = f"{proc.memory_info().rss / 1e9:.1f}"
            log.info(f"{timestamp}\t{memory_usage_gb}")
            file.write(f"{timestamp}\t{memory_usage_gb}\n")
            time.sleep(1)
            seconds += 1
            if seconds % 60 == 0:
                file.flush()
        file.close()

    @track_action_rank
    def action_memory_profile_show(self, only_show=False):
        """
        Action that shows a plot of the memory profile produce with action
        `memory_profile`.
        """

        # Construct gnuplot command.
        if "pid" not in self.config["general"]:
            raise ActionException("PID must be specified via general.PID")
        pid = int(self.config["general"]["pid"])
        gnuplot_script = (f"set datafile separator \"\t\"; "
                          f"set xdata time; "
                          f"set timefmt \"%Y-%m-%d %H:%M:%S\"; "
                          f"set xlabel \"Time\"; "
                          f"set ylabel \"Memory Usage\"; "
                          f"set grid; "
                          f"plot \"{pid}.memory-usage.tsv\" "
                          f"using 1:2 with lines; "
                          f"pause -1")
        gnuplot_cmd = f"gnuplot -e {shlex.quote(gnuplot_script)}"

        # Show it.
        self.show(gnuplot_cmd, only_show)
        if only_show:
            return

        # Launch gnuplot.
        try:
            subprocess.check_output(gnuplot_cmd, shell=True)
        except subprocess.CalledProcessError as e:
            raise ActionException(f"Failed to launch gnuplot ({e})")


def setup_autocompletion_cmd():
    """
    Print the command for setting up autocompletion for the qlever.py script.

    TODO: Currently works for bash only.
    """

    # Get methods that start wth "action_" from the Actions class, sorted by
    # their appearance in the class (see the `@track_action_rank` decorator).
    methods = inspect.getmembers(Actions, predicate=inspect.isfunction)
    methods = [m for m in methods if m[0].startswith("action_")]
    action_names = sorted([m[0] for m in methods],
                          key=lambda m: getattr(Actions, m).rank)
    action_names = [_.replace("action_", "") for _ in action_names]
    action_names = [_.replace("_", "-") for _ in action_names]
    action_names = " ".join(action_names)

    # Add config settings to the list of possible actions for autocompletion.
    action_names += " docker.USE_DOCKER=true docker.USE_DOCKER=false"
    action_names += " index.BINARY=IndexBuilderMain"
    action_names += " server.BINARY=ServerMain"

    # Return multiline string with the command for setting up autocompletion.
    return f"""\
_qlever_old_completion() {{
  local cur=${{COMP_WORDS[COMP_CWORD]}}
  COMPREPLY=( $(compgen -W "{action_names}" -- $cur) )
}}
complete -o nosort -F _qlever_old_completion qlever-old
"""


# Get all action names.
action_names = [_ for _ in dir(Actions) if _.startswith("action_")]
action_names = [_.replace("action_", "") for _ in action_names]
action_names = [_.replace("_", "-") for _ in action_names]


def main():
    # Get the version.
    try:
        version = pkg_resources.get_distribution("qlever").version
    except Exception as e:
        log.error(f"Could not determine package version: {e}")
        version = "unknown"
    # If the script is called without argument, say hello and provide some
    # help to get started.
    if len(sys.argv) == 1 or \
            (len(sys.argv) == 2 and sys.argv[1] == "help") or \
            (len(sys.argv) == 2 and sys.argv[1] == "--help") or \
            (len(sys.argv) == 2 and sys.argv[1] == "-h"):
        log.info("")
        log.info(f"{BOLD}Hello, I am the OLD qlever script"
                 f" (version {version}){NORMAL}")
        log.info("")
        if os.path.exists("Qleverfile"):
            log.info("I see that you already have a \"Qleverfile\" in the "
                     "current directory, so you are ready to start")
            log.info("")
            show_available_action_names()
        else:
            log.info("You need a Qleverfile in the current directory, which "
                     "you can create as follows:")
            log.info("")
            log.info(f"{BLUE}qlever-old setup-config <config name>{NORMAL}")
            log.info("")
            show_available_config_names()
            log.info("")
            log.info("If you omit <config name>, you get a default Qleverfile")
        log.info("")
        return

    # If there is only argument `setup-autocompletion`, call the function
    # `Actions.setup_autocompletion()` above and exit.
    if len(sys.argv) == 2 and sys.argv[1] == "setup-autocompletion":
        log.setLevel(logging.ERROR)
        print(setup_autocompletion_cmd())
        sys.exit(0)

    # If the first argument sets the log level, deal with that immediately (so
    # that it goes into effect before we do anything else). Otherwise, set the
    # log level to `NOTSET` (which will signal to the Actions class that it can
    # take the log level from the config file).
    log.setLevel(logging.NOTSET)
    if len(sys.argv) > 1:
        set_log_level_match = re.match(r"general.log_level=(\w+)",
                                       sys.argv[1], re.IGNORECASE)
        if set_log_level_match:
            log_level = set_log_level_match.group(1).upper()
            sys.argv = sys.argv[1:]
            try:
                log.setLevel(getattr(logging, log_level))
                log.debug("")
                log.debug(f"Log level set to {log_level}")
                log.debug("")
            except AttributeError:
                log.error(f"Invalid log level: \"{log_level}\"")
                abort_script()

    # Helper function that executes an action.
    def execute_action(actions, action_name, **kwargs):
        log.info("")
        log.info(f"{BOLD}Action \"{action_name}\"{NORMAL}")
        log.info("")
        action = f"action_{action_name.replace('-', '_')}"
        try:
            getattr(actions, action)(**kwargs)
        except ActionException as err:
            print(f"{RED}{err}{NORMAL}")
            abort_script()
        except Exception as err:
            line = traceback.extract_tb(err.__traceback__)[-1].lineno
            print(f"{RED}Error in Python script (line {line}: {err})"
                  f", stack trace follows:{NORMAL}")
            print()
            raise err

    # If `setup-config` is among the command-line arguments, it must the first
    # one, followed by at most one more argument.
    if "setup-config" in sys.argv:
        if sys.argv.index("setup-config") > 1:
            log.setLevel(logging.ERROR)
            log.error("Action `setup-config` must be the first argument")
            abort_script()
        if len(sys.argv) > 3:
            log.setLevel(logging.ERROR)
            log.error("Action `setup-config` must be followed by at most one "
                      "argument (the name of the desied configuration)")
            abort_script()
        log.setLevel(logging.INFO)
        config_name = sys.argv[2] if len(sys.argv) == 3 else "default"
        execute_action(Actions, "setup-config", config_name=config_name)
        return

    actions = Actions()
    # log.info(f"Actions available are: {', '.join(action_names)}")
    # Show the log level as string.
    # log.info(f"Log level: {logging.getLevelName(log.getEffectiveLevel())}")

    # Check if the last argument is "show" (if yes, remember it and remove it).
    only_show = True if len(sys.argv) > 1 and sys.argv[-1] == "show" else False
    if only_show:
        sys.argv = sys.argv[:-1]

    # Initalize actions.
    # Execute the actions specified on the command line.
    for action_name in sys.argv[1:]:
        # If the action is of the form section.key=value, set the config value.
        set_config_match = re.match(r"(\w+)\.(\w+)=(.*)", action_name)
        if set_config_match:
            section, option, value = set_config_match.groups()
            log.info(f"Setting config value: {section}.{option}={value}")
            try:
                actions.set_config(section, option, value)
            except ValueError as err:
                log.error(err)
                abort_script()
            continue
        # If the action name does not exist, exit.
        if action_name not in action_names:
            log.error(f"Action \"{action_name}\" does not exist, available "
                      f"actions are: {', '.join(action_names)}")
            abort_script()
        # Execute the action (or only show what would be executed).
        execute_action(actions, action_name, only_show=only_show)
    log.info("")


if __name__ == "__main__":
    main()
