# A script to make it so that with a keyboard shortcut I can jump to specific application windows,
# including specific windows of multi-window applications (e.g. Chrome).
# Gnome's built-in support for CMD-1 CMD-2 etc. is based on order of icons in the dash,
# which means CMD-2 may refer to something different each time, and there is no way to refer to 
# a specific window when icons are stacked.
#
# # As one-time setup, it may be necessary to run the following command to unmap Gnome's default capture
# of CMD-1...9 keys:
# for i in {0..9}; do dconf write "/org/gnome/shell/keybindings/switch-to-application-$i" "@as []"; done
# based on
# https://unix.stackexchange.com/questions/510375/super1-super2-super3-etc-keys-can-not-be-remapped-in-gnome
#
# Sample cron entries:
#
# USER=moshe
# XAUTHORITY=/run/user/1000/gdm/Xauthority
# DISPLAY=:0
# * * * * * /usr/bin/python3 /home/moshe/tools/manage_windows.py index >> /home/moshe/tools/manage_windows_cron.log 2>&1
#
# Finally use Autokey to map keyboard shortcuts to launch instances of the script, where each Autokey
# script is like:
# system.exec_command("python3 /path/to/manage_windows.py raise 2")

import argparse
import json
import os
import re
import subprocess

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(required=True, title="operations", dest="operation")
parser_index = subparsers.add_parser("index",
                                     help='Index the currently open windows. Intended to be called on an automated schedule.')
parser_raise = subparsers.add_parser("raise", help='Raise the specified window.')
parser_raise.add_argument("window_alias", help="Window alias as defined in manage_windows.json")
args = parser.parse_args()

config_path = "/home/" + os.environ["USER"] + "/.config/mjs_manage_windows/"

if not os.path.exists(config_path + "manage_windows.json"):
    print("No configuration file found. The file 'manage_windows.json' is required.")
    exit(1)

with open(config_path + "manage_windows.json") as config_file:
    app_config = json.load(config_file)

if not os.path.exists(config_path + "managed_windows.state"):
    window_state = {}
    with open(config_path + "managed_windows.state", "w") as state_file:
        json.dump(window_state, state_file)

with open(config_path + "managed_windows.state") as state_file:
    window_state = json.load(state_file)

if args.operation == "index":
    alias_to_id = {}

    window_list = subprocess.Popen(["wmctrl", "-lx"], stdout=subprocess.PIPE)

    for line in window_list.stdout:
        m = re.match(r"(?P<id>\S+)\s+\d+\s(?P<class>\S+)\s+\S+\s(?P<title>[^\n]+)", line.decode())
        if not m:
            continue

        for alias in app_config["WINDOW_TITLE_SUBSTRINGS"]:
            if alias in alias_to_id:
                continue
            for title_substring_option in app_config["WINDOW_TITLE_SUBSTRINGS"][alias]:
                if title_substring_option in m.group("title"):
                    alias_to_id[alias] = m.group("id")
                    break

    # print("After mapping config to currently running windows, we have:")
    # print(alias_to_id)

    # now merge this into whatever we've already persisted, using these new values
    # in place of whatever is there, but not removing entries that we don't have new values for
    for key in alias_to_id:
        window_state[key] = alias_to_id[key]

    with open(config_path + "managed_windows.state", "w") as state_file:
        json.dump(window_state, state_file)

elif args.operation == "raise":
    print(f"raising {args.window_alias}")
    if args.window_alias not in app_config["WINDOW_RAISE_BY_KEY"]:
        print(f"Requested key {args.window_alias} is not mapped, ignoring.")
        exit()

    # if app_config["WINDOW_RAISE_BY_KEY"][args.window_alias] not in app_config["WINDOW_TITLE_SUBSTRINGS"]:
    #     print(f"Requested key {args.window_alias} is not mapped to a window title, ignoring.")
    #     exit()

    print(f"States that we know of: {window_state}")
    if app_config["WINDOW_RAISE_BY_KEY"][args.window_alias] not in window_state:
        print(f"Current state unknown for window {app_config["WINDOW_RAISE_BY_KEY"][args.window_alias]}")
        exit()

    print(f"Raising {app_config["WINDOW_RAISE_BY_KEY"][args.window_alias]}")
    subprocess.Popen(["wmctrl", "-i", "-a", window_state[app_config["WINDOW_RAISE_BY_KEY"][args.window_alias]]])

print("Done, exiting.")