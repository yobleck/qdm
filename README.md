# QDM
QDM is a terminal user interface(TUI) display/login manager written in Python(3.10) for Linux.

## Features
    - choose between different desktop environments(DE)
      and window managers(WM) via `/usr/share/xsessions/*.desktop` files
      (TODO: wayland-session and bash shell).

    - multiple user login options via `/etc/passwd`

    - ASCII art style animations.

## Why
This DM is heavily inspired by/shamelessly ripped off of [Ly](https://github.com/fairyglade/ly) another TUI DM.
<br>The reason QDM exists is because Ly's code base is not as actively maintained as before 
and relies on a number of unwieldy/unnecessary dependencies.

QDM is a hobby project and security is not my strong suit so feel free to critique that.

## TODO Config Format
    - default session

    - default username

    - menu color

    - systemd/logind/pam vs not those

