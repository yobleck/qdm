# QDM
Is a terminal user interface(TUI) display/login manager written in Python(3.10) for Linux,

featuring the ability to choose between different desktop environments(DE)

and window managers(WM) via `/usr/share/xsessions/*.desktop` files.

QDM also supports multiple user login options and ASCII art style animations.

The UI is shamelessly ripped from [Ly](https://github.com/fairyglade/ly) another TUI DM.

The reason QDM exists is because Ly's large (too large for such a simple program IMO)

codebase is no longer being actively maintained.

QDM is a hobby project and security is not my strong suit so feel free to critique that.

## Config Format
    - vt #
    Which virtual terminal is being used. Currently for display purposes only.
    Actual value is controlled by the systemd service unit.

    - xsessions
    A list of DEs/WMs whre each one is a list with wo items `["display name", "startup command"]`.
    The first option is default.

    - usernames
    A list of usernames. Valid options can be found with `cat /etc/passwd`.
    The first option is default.

