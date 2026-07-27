from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files


def get_version() -> str:
    try:
        return version("clavis")
    except PackageNotFoundError:
        return "unknown"


def version_text(command: str = "clavis") -> str:
    return f"{command} {get_version()}"


def about_text() -> str:
    banner = files("clavis").joinpath("assets/clavis.txt").read_text(encoding="utf-8").rstrip()
    return (
        f"{banner}\n\n"
        f"{version_text()}\n"
        "Control Layer for Acquisition-board Validation and Interface Services\n"
        "Apache-2.0\n"
        "https://github.com/claus-92/clavis"
    )
