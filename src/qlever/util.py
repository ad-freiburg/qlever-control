from pathlib import Path


def get_total_file_size(patterns: list[str]) -> int:
    """
    Helper function that gets the total size of all files mathing the given
    patterns in bytes.
    """

    total_size = 0
    search_dir = Path.cwd()
    for pattern in patterns:
        for file in search_dir.glob(pattern):
            total_size += file.stat().st_size
    return total_size
