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

## Dependencies
- python (tested on 3.10)
- systemd
- pamd
- python-pam (tested with 2.0.2)
- Xorg/X11
- only tested with [qtile](https://github.com/qtile/qtile) wm so far

## Install
- No package manager support sorry :(
- download zip off github or clone repo
- copy contents of `./etc/` to `/etc/`
- symlink qdm.service to `/etc/systemd/system/qdm.service` (optionally alias display-manager.service)
- change envars to match your system

## Config
- all vaules in quotes
- default_session: the value of `name=` in the xsession .desktop file
- default_username: your username lowercase
- menu_color: [ansi](https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797) escape sequence in quotes ("\u001b[34m" = blue)
- install path and etc path are temporary
- xauth and mcookie paths. See xauth(1) man for more details

## TODO
- systemd/logind/pam vs not those
- default config files in `/etc/qdm/`
- wayland-session
