import requests
from requests.exceptions import ConnectionError  # noqa


def alive_check(port: int, host: str = "127.0.0.1") -> bool:
    """
    Check if a QLever server is already running on this port.
    """
    try:
        erg = requests.get(
            f"http://{host}:{port}/ping",
            params={"msg": "from the qlever script".replace(" ", "%20")},
            timeout=10,
        )
    except ConnectionError:
        return False
    # assert erg.text == "This QLever server is up and running\n"
    return erg.status_code == 200
