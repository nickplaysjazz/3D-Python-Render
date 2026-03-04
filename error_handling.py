import sys


def raise_error(filename: str, text: str, exception: Exception = None) -> None:
    """
    Prints an error statement then halts execution of code.

    filename: Name of file where error occurred. Preferred usage is `Path(__file__).name` with pathlib library imported.

    text: Text displayed with error.

    exception: (Optional) Exception to be printed with error.
    """
    RED_TEXT = "\033[31m"
    RESET_TEXT = "\033[0m"

    if exception is not None:
        print(f"{RED_TEXT}!! ERROR !! {filename} : {text}:\n\t{exception}{RESET_TEXT}")
    else:
        print(f"{RED_TEXT}!! ERROR !! {filename} : {text}{RESET_TEXT}")

    sys.exit(1)


def raise_warning(filename: str, text: str) -> None:
    """
    Prints a warning statement then continues execution of code.

    filename: Name of file where warning occurred. Preferred usage is `Path(__file__).name` with pathlib library imported.

    text: Text displayed with warning.
    """
    LIGHT_RED = "\033[91m"
    RESET = "\033[0m"

    print(f"{LIGHT_RED}! WARNING ! {filename} : {text}{RESET}")

    return
