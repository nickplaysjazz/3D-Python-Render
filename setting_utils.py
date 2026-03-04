import configparser

from pathlib import Path

from error_handling import raise_error


def parse_ini(filename: str) -> configparser.ConfigParser:
    BASE_DIR = Path(__file__).resolve().parent
    config_path = BASE_DIR / filename
    if not config_path.exists():
        raise_error(Path(__file__).name, "Configuration file does not exist!")

    config = configparser.ConfigParser()
    config.read(config_path)
    if not config:
        raise_error(Path(__file__).name, "Unable to read configuration file!")

    return config


def read_settings(filename):

    try:
        settings = parse_ini(filename)
    except configparser.ParsingError as e:
        raise_error(
            Path(__file__).name, "Configuration file does not follow legal syntax", e
        )

    ret_dict = {}
    try:
        ret_dict["DISPLAY_WIDTH"] = settings.getint("Options", "DISPLAY_WIDTH")
        ret_dict["DISPLAY_HEIGHT"] = settings.getint("Options", "DISPLAY_HEIGHT")
        ret_dict["FOV"] = settings.getfloat("Options", "FOV")
        ret_dict["MOUSE_SENSITIVITY"] = settings.getfloat(
            "Options", "MOUSE_SENSITIVITY"
        )
        ret_dict["FPS"] = settings.getint("Options", "FPS")
    except ValueError as e:
        raise_error(Path(__file__).name, "Configuration file type mismatch error", e)
    except configparser.NoSectionError as e:
        raise_error(
            Path(__file__).name, "Configuration file does not follow expected syntax", e
        )

    return ret_dict
