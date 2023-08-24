#!/usr/bin/python3

# For each action, we have the following:
#
# 1. The name of the action
# 2. The commands that are actually run as part of the action
# 3. The part of those commands shown to the user (on demand, show full command)

import sys
from configparser import ConfigParser, ExtendedInterpolation
import psutil
from datetime import datetime, date


class Actions:

    def __init__(self):
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        self.config.read("Qleverfile.ini")
        self.server_binary = "ServerMain"

    def action_status(self):
        """ Show all QLever processes running on this machine. """

        # Print the table headers
        print("{:<8} {:<8} {:>5}  {:>5}  {}".format("PID", "USER", "START", "RSS", "COMMAND"))
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['pid', 'username', 'create_time', 'memory_info', 'cmdline'])
            cmdline = " ".join(pinfo['cmdline']) if pinfo['cmdline'] else ""
            if not cmdline.startswith(self.server_binary):
                continue
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


def parse_config():
    """ Parse the Qleverfile.ini file """
    config = ConfigParser(interpolation=ExtendedInterpolation())
    config.read("Qleverfile.ini")
    print(config.sections())
    print(config["DEFAULT"]["db"])
    print(config["data"]["get_data_cmd"])
    # config.write(sys.stdout)


if __name__ == "__main__":
    parse_config()
    # Get all function names from class Action starting with "action_".
    actions = [_.replace("action_", "") for _ in dir(Actions)
               if not _.startswith("__")]
    print(actions)

    # Iterate over all arguments and call the corresponding function.
    for action in sys.argv[1:]:
        if action not in actions:
            print(f"Unknown action: {action}")
            sys.exit(1)
        print("Running action: ", action)
        print()
        getattr(Actions(), f"action_{action}")()
