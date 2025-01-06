# Global variables for the full configuration, set in `qlever_main.py`.
# For example, these are used by by `qlever config --show-qleverfile-config` or
# `qlever config --show-envvars`.
#
# NOTE 1: Most commands do not (and should not) use these: the `args` passed to
# the `execute` method of a command class is deliberately reduced to those
# arguments that are relevant for the command.
#
# NOTE 2: If we would define these in `config.py`, which seems like the natural
# place, we get a circular import error, because we need these in
# `qlever/commands/config.py`, which would have to import `config.py`, which
# imports `__init__.py`, which imports all the command modules.
qleverfile_path = None
qleverfile_config = None
envvars_config = None
