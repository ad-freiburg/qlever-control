#!/usr/bin/python3

# This is the QLever script (new version, written in Python).

from configparser import ConfigParser, ExtendedInterpolation
from datetime import datetime, date
import os
import glob
import psutil
import re
import shlex
import subprocess
import sys
import time
import traceback

BLUE = "\033[34m"
RED = "\033[31m"
BOLD = "\033[1m"
NORMAL = "\033[0m"


class ActionException(Exception):
    pass


class Actions:

    def __init__(self):
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        self.config.read("Qleverfile.ini")
        self.name = self.config['DEFAULT']['name']
        self.yes_values = ["1", "true", "yes"]

        # Default values for options that are not mandatory in the Qleverfile.
        defaults = {
            "server": {
                "binary": "ServerMain",
                "num_threads": "8",
                "cache_max_size_gb": "5",
                "cache_max_size_gb_single_entry": "1",
                "cache_max_num_entries": "100",
                "with_text_index": "no",
                "only_pso_and_pos_permutations": "no",
                "no_patterns": "no",
            },
            "index": {
                "binary": "IndexBuilderMain",
                "with_text_index": "no",
                "only_pso_and_pos_permutations": "no",
                "no_patterns": "no",
            },
            "docker": {
                "image": f"qlever/qlever:{self.name}",
                "container_server": f"qlever.server.{self.name}",
                "container_indexer": f"qlever.indexer.{self.name}",
            },
        }
        for section in defaults:
            for option in defaults[section]:
                if not self.config[section].get(option):
                    self.config[section][option] = defaults[section][option]

        # Show some information (for testing purposes only).
        print(f"Parsed Qleverfile, sections are: "
              f"{', '.join(self.config.sections())}")
        print(f"Name of dataset: {self.config['DEFAULT']['name']}")
        # print(f"Get the data: {self.config['data']['get_data_cmd']}")

        # Check whether we are allowed to get the list of network connections.
        try:
            psutil.net_connections()
            self.net_connections_allowed = True
        except psutil.AccessDenied:
            self.net_connections_allowed = False

        # Check whether docker is installed by running `docker info`. If the
        # program does not return after 100ms, we assume that docker is not
        # installed.
        try:
            subprocess.run("docker info", shell=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=0.1)
            self.docker_installed = True
        except subprocess.TimeoutExpired:
            self.docker_installed = False

    def set_config(self, section, option, value):
        """
        Set a value in the config file (throws an exception if the
        section or option does not exist).
        """

        if not self.config.has_section(section):
            raise Exception(f"Section {section} does not exist in Qleverfile")
        if not self.config.has_option(section, option):
            raise Exception(f"Option {option} does not exist in section "
                            f"{section} in Qleverfile")
        self.config[section][option] = value

    def get_total_file_size(self, paths):
        """ Get the total size of all files in the given paths in GB. """

        total_size = 0
        for path in paths:
            for file in glob.glob(path):
                total_size += os.path.getsize(file)
        return total_size / 1e9

    def alive_check(self, port):
        """ Check if a QLever server is running on the given port. """

        message = "from the qlever script".replace(" ", "%20")
        curl_cmd = f"curl -s http://localhost:{port}/ping?msg={message}"
        exit_code = subprocess.call(curl_cmd, shell=True,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        return exit_code == 0

    def action_get_data(self, only_show=False):
        """ Get the data. """

        if not self.config['data']['get_data_cmd']:
            print(f"{RED}No GET_DATA_CMD specified in Qleverfile")
            return
        cmdline = self.config['data']['get_data_cmd']
        print(f"{BLUE}{cmdline}{NORMAL}")
        if not only_show:
            print()
            os.system(cmdline)
            total_file_size = self.get_total_file_size(
                self.config['index']['file_names'].split())
            print(f"Total file size: {total_file_size:.1f} GB")
            # os.system(f"ls -lh {self.config['index']['file_names']}")

    def action_index(self, only_show=False):
        """ Build a QLever index for the given dataset. """

        # Write settings.json file.
        with open(f"{self.name}.settings.json", "w") as f:
            f.write(self.config['index']['settings_json'])

        # Construct the command line based on the config file.
        index_config = self.config['index']
        cmdline = (f"{index_config['cat_files']} | {index_config['binary']}"
                   f" -F ttl -f -"
                   f" -i {self.name}"
                   f" -s {self.name}.settings.json")
        if index_config['only_pso_and_pos_permutations'] in self.yes_values:
            cmdline += " --only-pso-and-pos-permutations --no-patterns"
        if index_config['with_text_index'] in \
                ["from_text_records", "from_text_records_and_literals"]:
            cmdline += (f" -w {self.name}.wordsfile.tsv"
                        f" -d {self.name}.docsfile.tsv")
        if index_config['with_text_index'] in \
                ["from_literals", "from_text_records_and_literals"]:
            cmdline += " --text-words-from-literals"
        if 'stxxl_memory_gb' in index_config:
            cmdline += f" --stxxl-memory-gb {index_config['stxxl_memory_gb']}"
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
        print(f"{BLUE}{cmdline}{NORMAL}")
        if only_show:
            return
        print()

        # Check if index files (name.index.*) already exist.
        if glob.glob(f"{self.name}.index.*"):
            raise ActionException(
                    f"Index files for dataset {self.name} already exist, "
                    f"please delete them if you want to rebuild the index")

        # Run the command.
        os.system(cmdline)

    def action_start(self, only_show=False):
        """ Start the QLever server. """

        # Construct the command line based on the config file.
        server_config = self.config['server']
        cmdline = (f"{self.config['server']['binary']}"
                   f" -i {self.name}"
                   f" -j {server_config['num_threads']}"
                   f" -p {server_config['port']}"
                   f" -m {server_config['memory_for_queries_gb']}"
                   f" -c {server_config['cache_max_size_gb']}"
                   f" -e {server_config['cache_max_size_gb_single_entry']}"
                   f" -k {server_config['cache_max_num_entries']}")
        if server_config['access_token']:
            cmdline += f" -a {server_config['access_token']}"
        if server_config['only_pso_and_pos_permutations'] in self.yes_values:
            cmdline += " --only-pso-and-pos-permutations"
        if server_config['no_patterns'] in self.yes_values:
            cmdline += " --no-patterns"
        if server_config["with_text_index"] in \
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
                       f" {docker_config['image']}"
                       f" -c {shlex.quote(cmdline)}")
        else:
            cmdline = f"nohup {cmdline} &"

        # Show the command line (and exit if only_show is True).
        print(f"{BLUE}{cmdline}{NORMAL}")
        if only_show:
            return
        print()

        # Check if a QLever server is already running on this port.
        port = server_config['port']
        if self.alive_check(port):
            raise ActionException(
                    f"QLever server already running on port {port}")

        # Check if another process is already listening.
        if self.net_connections_allowed:
            if port in [conn.laddr.port for conn
                        in psutil.net_connections()]:
                raise ActionException(
                        f"Port {port} is already in use by another process")

        # Execute the command line.
        os.system(cmdline)

        # Tail the server log until the server is ready (note that the `exec`
        # is important to make sure that the tail process is killed and not
        # just the bash process).
        print(f"Follow {self.name}.server-log.txt until the server is ready"
              f" (Ctrl-C stops following the log, but not the server)")
        print()
        tail_cmd = f"exec tail -f {self.name}.server-log.txt"
        tail_proc = subprocess.Popen(tail_cmd, shell=True)
        while not self.alive_check(port):
            time.sleep(1)

        # Set the access token if specified.
        access_token = server_config['access_token']
        access_arg = f"--data-urlencode \"access-token={access_token}\""
        if self.config['data']['index_description']:
            desc = self.config['data']['index_description']
            curl_cmd = (f"curl -Gs http://localhost:{port}/api"
                        f" --data-urlencode \"index-description={desc}\""
                        f" {access_arg} > /dev/null")
            os.system(curl_cmd)
        if self.config['data']['text_description']:
            desc = self.config['data']['text_description']
            curl_cmd = (f"curl -Gs http://localhost:{port}/api"
                        f" --data-urlencode \"text-description={desc}\""
                        f" {access_arg} > /dev/null")
            os.system(curl_cmd)

        # Kill the tail process. Note: tail_proc.kill() does not work.
        tail_proc.terminate()

    def action_stop(self, only_show=False):
        """ Stop the QLever server. """

        docker_container_name = self.config['docker']['container_server']
        cmdline_regex = (f"{self.config['server']['binary']}"
                         f" -i [^ ]*{self.name}")
        print(f"{BLUE}Checking for Docker container with name "
              f"\"{docker_container_name}\" and for processes "
              f"matching: {cmdline_regex}{NORMAL}")
        if only_show:
            return
        print()

        # First check if there is docker container running.
        if self.docker_installed:
            docker_cmd = (f"docker stop {docker_container_name} && "
                          f"docker rm {docker_container_name}")
            try:
                subprocess.run(docker_cmd, shell=True, check=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                print(f"Docker container with name "
                      f"\"{docker_container_name}\" "
                      f"stopped and removed")
                return
            except Exception:
                pass

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
                if re.match(cmdline_regex, cmdline):
                    print(f"Found process {pinfo['pid']} from user "
                          f"{pinfo['username']} with command line: {cmdline}")
                    print()
                    try:
                        proc.kill()
                        print(f"{RED}Killed process {pinfo['pid']}{NORMAL}")
                    except Exception as e:
                        raise ActionException(
                                f"Could not kill process with PID "
                                f"{pinfo['pid']}: {e}")
                    return
            except psutil.NoSuchProcess:
                pass

        # No matching process found.
        raise ActionException("No matching Docker container or process found")

    def action_status(self, only_show=False):
        """ Show all QLever processes running on this machine. """

        cmdline_regex = f"^{self.config['server']['binary']}"
        print(f"{BLUE}All processes on this machine where "
              f"the command line matches: {cmdline_regex}"
              f" (using Python's psutil library){NORMAL}")
        print()
        if only_show:
            print(f"{BLUE}If executed, show processes using psutil{NORMAL}")
            return

        # Print the table headers
        num_processes_found = 0
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['pid', 'username', 'create_time',
                                        'memory_info', 'cmdline'])
            cmdline = " ".join(pinfo['cmdline']) if pinfo['cmdline'] else ""
            if not re.match(cmdline_regex, cmdline):
                continue
            if num_processes_found == 0:
                print("{:<8} {:<8} {:>5}  {:>5}  {}".format(
                    "PID", "USER", "START", "RSS", "COMMAND"))
            num_processes_found += 1
            pid = pinfo['pid']
            user = pinfo['username'] if pinfo['username'] else ""
            start_time = datetime.fromtimestamp(pinfo['create_time'])
            if start_time.date() == date.today():
                start_time = start_time.strftime("%H:%M")
            else:
                start_time = start_time.strftime("%b%d")
            rss = f"{pinfo['memory_info'].rss / 1e9:.0f} G"
            print("{:<8} {:<8} {:>5}  {:>5}  {}".format(
                pid, user, start_time, rss, cmdline))
        if num_processes_found == 0:
            print("No processes found")


def parse_config():
    """ Parse the Qleverfile.ini file """
    config = ConfigParser(interpolation=ExtendedInterpolation())
    config.read("Qleverfile.ini")
    # config.write(sys.stdout)


if __name__ == "__main__":
    # Initalize actions.
    print()
    action_names = [_ for _ in dir(Actions) if _.startswith("action_")]
    action_names = [_.replace("action_", "") for _ in action_names]
    action_names = [_.replace("_", "-") for _ in action_names]
    actions = Actions()
    print(f"Actions available are: {', '.join(action_names)}")

    # Check if the last argument is "show" (if yes, remember it and remove it).
    only_show = True if len(sys.argv) > 1 and sys.argv[-1] == "show" else False
    if only_show:
        sys.argv = sys.argv[:-1]

    # Execute the actions specified on the command line.
    for action_name in sys.argv[1:]:
        # If the action is of the form section.key=value, set the config value.
        set_config_match = re.match(r"(\w+)\.(\w+)=(.*)", action_name)
        if set_config_match:
            section, option, value = set_config_match.groups()
            print()
            print(f"{BOLD}Setting config value: "
                  f"{section}.{option}={value}{NORMAL}")
            try:
                actions.set_config(section, option, value)
            except ValueError as err:
                print(f"{RED}{err}{NORMAL}")
                sys.exit(1)
            continue
        # If the action name does not exist, exit.
        if action_name not in action_names:
            print(f"{RED}Action \"{action_name}\" does not exist{NORMAL}")
            sys.exit(1)
        # Execute the action (or only show what would be executed).
        print()
        print(f"{BOLD}Action: \"{action_name}\"{NORMAL}")
        print()
        action = f"action_{action_name.replace('-', '_')}"
        try:
            getattr(actions, action)(only_show=only_show)
        except ActionException as err:
            # line = traceback.extract_tb(err.__traceback__)[-1].lineno
            print(f"{RED}{err}{NORMAL}")
            print()
            sys.exit(1)
        except Exception as err:
            line = traceback.extract_tb(err.__traceback__)[-1].lineno
            print(f"{RED}Error in Python script (line {line}: {err})"
                  f", stack trace follows:{NORMAL}")
            print()
            raise err
    print()
