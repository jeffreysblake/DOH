"""
Color constants for terminal output
"""

try:
    from colorama import init, Fore, Style

    init(autoreset=True)

    class Colors:
        """Color constants for terminal output"""

        RED = Fore.RED
        GREEN = Fore.GREEN
        YELLOW = Fore.YELLOW
        BLUE = Fore.BLUE
        BOLD = Style.BRIGHT
        RESET = Style.RESET_ALL

except ImportError:
    # Fallback for environments without colorama
    class Colors:
        RED = ""
        GREEN = ""
        YELLOW = ""
        BLUE = ""
        BOLD = ""
        RESET = ""
