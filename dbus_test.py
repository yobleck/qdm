# https://www.programcreek.com/python/example/1862/dbus.Interface
# https://wiki.python.org/moin/DbusExamples
# https://trstringer.com/python-systemd-dbus/
# https://www.freedesktop.org/wiki/Software/systemd/dbus/
# https://www.freedesktop.org/wiki/Software/systemd/logind/
# https://systemd-devel.freedesktop.narkive.com/zb2cP969/create-a-new-logind-session-from-a-systemd-user-unit
import dbus
import os

# TODO if this file is small enough just move it over to the main file or auth.py?

""" Testing
bus = dbus.SessionBus()  # SystemBus() requires root

# Introspect notifications
obj = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
interface = dbus.Interface(obj, dbus_interface="org.freedesktop.DBus.Introspectable")  # DBus.Properties
print(interface.Introspect())
print("########################################")


systemd_obj = bus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")

# Introspects systemd1
sys_interface = dbus.Interface(systemd_obj, "org.freedesktop.DBus.Introspectable")
print(sys_interface.Introspect("org.freedesktop.systemd1"))
print("########################################")

# List all properties of systemd
sys_interface2 = dbus.Interface(systemd_obj, "org.freedesktop.DBus.Properties")
print(sys_interface2.GetAll("org.freedesktop.systemd1.Manager"))
print("########################################")
# Get specific property
print(sys_interface2.GetAll("org.freedesktop.systemd1.Manager")["Version"])
print("########################################")

# Execute method on systemd1.Manager
sys_interface3 = dbus.Interface(systemd_obj, "org.freedesktop.systemd1.Manager")
print(sys_interface3.GetUnitFileState("pulseaudio.service"))
print(sys_interface3.GetUnitProcesses("pulseaudio.service"))
"""

def sys_test(pid: int) -> None:
    bus = dbus.SystemBus()

    #systemd_obj = bus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")
    #systemd_interface = dbus.Interface(systemd_obj, "org.freedesktop.systemd1.Manager")  # org.freedesktop.DBus.Properties
    
    login_obj = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
    login_interface = dbus.Interface(login_obj, "org.freedesktop.login1.Manager")
    
    #pid = os.fork()
    #if pid > 0:
    # Create session is supposed to be called by PAM, but hell if I can figure out how to
    # to interface with it. TODO see python-pam source code
    # TODO type, desktop, tty etc. should be input from config values
    # whats the proper way to handle seat0
    login_interface.CreateSession(1000,  # uid
                                pid,  # pid
                                "login",  # service
                                "x11",  # type
                                "user",  # class
                                "qtile",  # desktop
                                "seat0",  # seat_id
                                3,  # vtnr
                                "tty3",  #tty
                                ":1",  # display
                                False, # remote
                                "yobleck",  # remote_user
                                "yobleck",  # remote_host
                                []  # properties
                                )
    
    with open("/home/yobleck/qdm/test.log", "a") as f:
        #f.write(str(systemd_interface.GetAll("org.freedesktop.systemd1.Manager")))
        #f.write(str(systemd_interface.ListUnitFiles()))
        f.write("pid: " + str(pid) + "\n")
        f.write(str(login_interface.ListSessions()) + "\n")
    
    # TODO remove this
    """elif pid == 0:
        os.setuid(1000)
        os.putenv("QT_QPA_PLATFORMTHEME", "qt5ct")
        os.putenv("XCURSOR_THEME", "breeze_cursors")
        os.putenv("XDG_RUNTIME_DIR", "/run/user/1000")  # This should be set by pam_systemd.so
        os.putenv("XDG_SEAT", "seat0")
        os.putenv("XDG_VTNR", "3")
        os.putenv("XDG_SESSION_CLASS", "user")
        os.putenv("XDG_SESSION_TYPE", "tty")
        os.putenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")
        os.putenv("HOME", "/home/yobleck")
        os.putenv("PWD", "/home/yobleck")
        os.chdir("/home/yobleck")
        os.putenv("USER", "yobleck")
        os.putenv("LOGNAME", "yobleck")
        os.putenv("TERM", "xterm-256color")
        os.putenv("DISPLAY", ":1")
        
        os.putenv("XAUTHORITY", "/home/yobleck/.qdm_xauth")
        os.system("/usr/bin/xauth add :1 . `/usr/bin/mcookie`")
        
        os.system("startx /usr/bin/qtile start")"""
    
