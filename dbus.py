# https://www.programcreek.com/python/example/1862/dbus.Interface
# https://wiki.python.org/moin/DbusExamples
# https://trstringer.com/python-systemd-dbus/
# https://www.freedesktop.org/wiki/Software/systemd/dbus/
# https://www.freedesktop.org/wiki/Software/systemd/logind/
# https://systemd-devel.freedesktop.narkive.com/zb2cP969/create-a-new-logind-session-from-a-systemd-user-unit
import dbus

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

    login_obj = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
    login_interface = dbus.Interface(login_obj, "org.freedesktop.login1.Manager")

    # pid = os.fork()
    # if pid > 0:
    # Create session is supposed to be called by PAM, but hell if I can figure out how to
    # to interface with it. TODO see python-pam source code
    # TODO type, desktop, tty etc. should be input from config values
    # whats the proper way to handle seat0
    info = login_interface.CreateSession(
                                        1000,  # uid
                                        pid,  # pid
                                        "login",  # service
                                        "x11",  # type
                                        "user",  # class
                                        "qtile",  # desktop
                                        "seat0",  # seat_id
                                        3,  # vtnr
                                        "tty3",  # tty
                                        ":1",  # display
                                        False,  # remote
                                        "yobleck",  # remote_user
                                        "yobleck",  # remote_host
                                        [],  # properties
                                        )

    with open("/home/yobleck/qdm/test.log", "a") as f:
        f.write("pid: " + str(pid) + "\n")
        f.write(str(info) + "\n")  # TODO turn this into envars
        f.write(str(login_interface.ListSessions()) + "\n")
