"""
Bridge implementation to automate BLE devices

@author: Daniel Fajardo
"""

import binascii
import configparser
import logging
import os
import sys
import threading
import time
import traceback
from functools import wraps
from typing import Dict, Union

from hci import decode_hci
from interfaces import Serial

PATH = os.path.dirname(os.path.realpath(__file__))
LOG_FILE = os.path.join(PATH, "logs.log")
FORMATTER = logging.Formatter('%(asctime)s | %(name)-10s | %(lineno)-3s | %(levelname)-8s | %(message)s')

log = logging.getLogger("Bridge")
log.setLevel(logging.INFO)

fmt = FORMATTER

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(fmt)

file_handler = logging.FileHandler(LOG_FILE, mode='w')
file_handler.setFormatter(fmt)

log.addHandler(console_handler)
log.addHandler(file_handler)

sys.excepthook = lambda etype, value, tb: log.error(f"Uncaught exception!! \n"
                                                    f"{'- '.join(traceback.format_exception(etype, value, tb))}")


def own_excepthook(view):
    """
    Redirect any unexpected tracebacks (https://bugs.python.org/issue1230540)
    """

    @wraps(view)
    def run(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except:
            sys.excepthook(*sys.exc_info())

    return run


def synchronous(tester_conf, iut_conf, iut_implementation):
    """
    Synchronous solution: Events only can be caught if triggered by the tester.

    This solution can also be done without threads. In fact, it works as expected without them. However,
    it is used to introduce the asynchronous solution.
    """
    log.info("Running synchronous solution!")

    iut = iut_implementation.IUT(iut_conf)
    tester = Serial(tester_conf)

    @own_excepthook
    def listen_tester(stop):
        """
        Function to continuously listen the tester. It also invokes actions over the IUT if the commands_white_list
        are included in the commands_white_list white list.
        """
        while not stop.is_set():
            command = tester.read()
            if len(command) > 0:
                log.info(f"Tester -> IUT :: {command.hex()}")

                # Discard messages that are not commands_white_list
                ocf, ogf, length, data = decode_hci(command.hex()) if command[0] == 1 else [0, 0, 0, 0]

                # Check if it is in the list. Otherwise, discard
                if (ocf, ogf) in iut.commands_white_list:
                    ble_cmd = iut.commands_white_list[(ocf, ogf)]
                    event = ble_cmd(data) if length > 0 else ble_cmd()
                    log.info(f"IUT -> Tester :: {event.decode()}")
                    tester.write(event)

    stop_thread = threading.Event()
    listener_tester_thread = threading.Thread(name='listen_tester', target=listen_tester, daemon=True,
                                              args=(stop_thread,))

    listener_tester_thread.start()

    aux = None
    while aux != "q!":
        aux = input()

    stop_thread.set()
    log.info("Stop!")


def asynchronous(tester_conf, iut_conf, iut_implementation):
    """
    Asynchronous solution: Events can be caught at any time.
    """
    log.info("Running asynchronous solution!")

    iut = iut_implementation.IUT(iut_conf)
    tester = Serial(tester_conf)

    mutex = threading.Lock()  # To enable the hack!

    @own_excepthook
    def listen_iut(stop):
        """
        Function to continuously listen the IUT. It returns all events to the tester.
        """
        while not stop.is_set():
            mutex.acquire()
            event = binascii.hexlify(iut.interface.read())
            if len(event) > 0:
                log.info(f"IUT -> Tester :: {event.decode()}")
                tester.write(event)
            mutex.release()

            time.sleep(iut_config["timeout"] / 1000000)  # Ensuring fast replies by setting less priority to this thread

    @own_excepthook
    def listen_tester(stop):
        """
        Function to continuously listen the tester. It also invokes actions over the IUT if the commands_white_list
        are included in the commands_white_list black list. Otherwise, the command is send directly to the IUT,
        without any special processing.
        """
        while not stop.is_set():
            command = tester.read()
            if len(command) > 0:
                log.info(f"Tester -> IUT :: {command.hex()}")
                ocf, ogf, length, data = decode_hci(command.hex())
                if (ocf, ogf) in iut.commands_black_list:
                    mutex.acquire()
                    ble_cmd = iut.commands_black_list[(ocf, ogf)]
                    event = ble_cmd(data) if length > 0 else ble_cmd()
                    log.info(f"IUT -> Tester :: {event.decode()}")
                    tester.write(event)
                    mutex.release()
                else:
                    iut.interface.write(binascii.hexlify(command))

    stop_thread = threading.Event()

    listener_tester_thread = threading.Thread(name='listen_tester', target=listen_tester, daemon=True,
                                              args=(stop_thread,))
    listener_iut_thread = threading.Thread(name='listen_iut', target=listen_iut, daemon=True,
                                           args=(stop_thread,))

    listener_tester_thread.start()
    listener_iut_thread.start()

    aux = None
    while aux != "q!":
        aux = input()

    stop_thread.set()
    log.info("Stop!")


if __name__ == '__main__':
    # Read config from file
    config = configparser.ConfigParser()
    config.read(os.path.join(PATH, 'config.conf'))

    tester_config: Dict[str, Union[str, int, float]] = dict()
    tester_config["name"] = config.get("TESTER_CONFIGURATION", "TESTER_FRIENDLY_NAME")
    tester_config["port"] = config.get("TESTER_CONFIGURATION", "TESTER_COM_PORT")
    tester_config["baudrate"] = config.get("TESTER_CONFIGURATION", "TESTER_BAUD_RATE")
    tester_config["flowcontrol"] = int(config.get("TESTER_CONFIGURATION", "TESTER_FLOW_CONTROL"))
    tester_config["timeout"] = float(config.get("TESTER_CONFIGURATION", "TESTER_TIMEOUT"))

    iut_config: Dict[str, Union[str, int, float]] = dict()
    iut_config["name"] = config.get("IUT_CONFIGURATION", "IUT_FRIENDLY_NAME")
    iut_config["port"] = config.get("IUT_CONFIGURATION", "IUT_COM_PORT")
    iut_config["baudrate"] = config.get("IUT_CONFIGURATION", "IUT_BAUD_RATE")
    iut_config["flowcontrol"] = int(config.get("IUT_CONFIGURATION", "IUT_FLOW_CONTROL"))
    iut_config["timeout"] = float(config.get("IUT_CONFIGURATION", "IUT_TIMEOUT"))

    iut_implementation_file = config.get("IUT_IMPLEMENTATION", "FILENAME")
    ble_all_commands = int(config.get("IUT_IMPLEMENTATION", "BLE_ALL_COMMANDS"))

    hci_level = logging.DEBUG if int(config.get("LOGS", "HCI_DEBUG")) else logging.INFO
    iut_level = logging.DEBUG if int(config.get("LOGS", "IUT_DEBUG")) else logging.INFO
    int_level = logging.DEBUG if int(config.get("LOGS", "INT_DEBUG")) else logging.INFO

    logging.getLogger("Bridge.HCI").setLevel(hci_level)
    logging.getLogger("Bridge.IUT").setLevel(iut_level)
    logging.getLogger("Bridge.INT").setLevel(int_level)

    IUT_implementation = __import__(iut_implementation_file)

    if ble_all_commands:
        asynchronous(tester_config, iut_config, IUT_implementation)
    else:
        synchronous(tester_config, iut_config, IUT_implementation)
