"""
IUT implementation to hack HCI_Reset command

@author: Daniel Fajardo
"""

import logging
from typing import Dict, Union

from hci import BLECommands
from interfaces import Serial

log_iut = logging.getLogger("Bridge.IUT")


class IUT(BLECommands):
    """
    Class that implements a hack for the HCI Reset command
    """

    def __init__(self, device: Dict[str, Union[str, int, float]]):
        """
        Initializing the IUT
        """
        super().__init__(Serial(device))
        self.commands_black_list[(3, 3)] = self.reset

    def reset(self) -> bytes:
        """
        Implements the hack for the HCI Reset command
        """
        log_iut.debug("Sending Reset to IUT!")
        self.interface.write(b'01030C00')

        reply = self.interface.read()
        log_iut.debug(f"Reply from IUT {reply.hex()}")

        log_iut.debug("Hacking reply")
        reply = list(reply.hex())
        reply[7] = "5"
        reply = bytes("".join(reply), 'utf-8')

        log_iut.debug(f"Sending fake event {reply.decode()} to tester")

        return reply
