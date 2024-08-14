from __future__ import annotations

import os

from qlever.qleverfile import Qleverfile


class EnvvarsException(Exception):
    pass


class Envvars:
    """
    Class for parsing environment variables with analogous names to those in
    the `Qleverfile` class, according to the schema `QLEVER_SECTION_VARIABLE`.
    For example, variable `PORT` in section `server` corresponds to the
    environment variable `QLEVER_SERVER_PORT`.
    """

    @staticmethod
    def envvar_name(section: str, name: str) -> str:
        """
        For a given section and variable name, return the environment variable
        name according to the schema described above.
        """
        return f"QLEVER_{section.upper()}_{name.upper()}"

    @staticmethod
    def read():
        """
        Check all environment variables that correspond to an entry in
        `Qleverfile.all_arguments()` according to the schema described above,
        and return a dictionary `config` with all the values found that way.
        For example, for `QLEVER_SERVER_PORT=8000`, there would be an entry
        `config['server']['port'] = 8000`.

        NOTE: If no environment variables was found at all, the method will
        return `None`. Otherwise, there will be an entry for each section, even
        if it is empty.
        """

        all_args = Qleverfile.all_arguments()
        config = {}
        num_envvars_found = 0
        for section, args in all_args.items():
            config[section] = {}
            for arg in args:
                envvar = Envvars.envvar_name(section, arg)
                if envvar in os.environ:
                    config[section][arg] = os.environ[envvar]
                    num_envvars_found += 1
        return config if num_envvars_found > 0 else None
