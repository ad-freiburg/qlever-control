import os
from docker.client import DockerClient
from docker.errors import (
    DockerException,
    NotFound,
    APIError,
    ContainerError,
    ImageNotFound,
)


def is_docker_installed(docker_host="unix://var/run/docker.sock") -> bool:
    """
    Check whether docker is installed on the specified host machine
    """
    try:
        d = DockerClient(base_url=docker_host)  # noqa
        print

    except DockerException as err:
        # docker.errors.DockerException:
        # Error while fetching server API version:
        # ('Connection aborted.',
        # FileNotFoundError(2, 'No such file or directory'))
        print(err)  # TODO: log warn
        return False
    return True


def docker_version() -> str:
    """
    Returns docker engine version
    """
    try:
        d = DockerClient()  # noqa
        return d.version().get("Components", [{}])[0].get("Version", "N/A")

    except DockerException as err:
        # docker.errors.DockerException:
        # Error while fetching server API version:
        # ('Connection aborted.',
        # FileNotFoundError(2, 'No such file or directory'))
        return "N/A"


def docker_run(container_indexer: str, image: str, cmdline: str) -> None:
    if not is_docker_installed():
        raise Exception("Docker Not Installed")  # TODO: too general

    pwd = os.getcwd()
    # always increase fds
    cmdline = "ulimit -Sn 1048576;" + cmdline
    try:
        d = DockerClient()
        d.containers.run(
            image=image,
            command=cmdline,
            auto_remove=True,
            tty=True,
            entrypoint="bash",
            name=container_indexer,
            volumes={
                "/etc/localtime": {"bind": "/etc/localtime", "mode": "ro"},
                pwd: {"bind": "/index", "mode": "rw"},
            },
        )
    except ImageNotFound as err:
        print(err)
    except ContainerError as err:
        print(err)
    except DockerException as err:
        print(err)


def docker_stop(container_name: str) -> None:
    try:
        d = DockerClient()
        c = d.containers.get(container_name)  # container name or ID
        c.stop()
        c.remove()
    except NotFound as err:
        print(err)  # TODO: use logger.error / warn
    except APIError as err:
        print(err)  # TODO: login?
    except DockerException as err:
        print(err)
