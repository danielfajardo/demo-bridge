"""
HCI base class and parser

@author: Daniel Fajardo
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Tuple, Dict, Union, Callable

from interfaces import InterfaceClass

log_hci = logging.getLogger("Bridge.HCI")


def decode_hci(data: str) -> Tuple[int, int, int, str]:
    """
    Returns decoded HCI packet
    """
    cmd = True if int(data[0:2], 16) == 1 else False
    return _parser_hci_cmd(data) if cmd else _parser_hci_acl_data(data)


def _parser_hci_cmd(data: str) -> Tuple[int, int, int, str]:
    """
    Returns decoded HCI Command packet
    """
    log_hci.debug(f"HCI Command!!")
    ocf = int(data[2:4], 16)
    ogf = int(data[4:6], 16) >> 2
    length = int(data[6:8], 16)
    data = data[8:]
    log_hci.debug(f"OCF: {ocf} - OGF: {ogf} - Length: {length} - Data: {data}")
    return ocf, ogf, length, data


def _parser_hci_acl_data(data: str) -> Tuple[int, int, int, str]:
    """
    Returns decoded HCI ACL Data packet
    """
    log_hci.debug(f"HCI ACL DATA!!")
    handle = int(data[4:6] + data[2:4], 16) & 0xEFF
    pb_bc_flag = int(data[4:6], 16) >> 4
    length = int(data[6:8], 16)
    data = data[8:]
    log_hci.debug(f"Handle: {handle} - PB/BC Flags: {pb_bc_flag} - Length: {length} - Data: {data}")
    return handle, pb_bc_flag, length, data


class RFCommands(metaclass=ABCMeta):
    """
    Base class for RF-PHY commands_white_list automation
    """

    commands_white_list: Dict[Tuple[int, int], Union[Callable[[], bytes], Callable[[str], bytes]]]

    def __init__(self, interface: InterfaceClass) -> None:
        """
        Initialize the interface and the commands_white_list dictionary with the pairs (OCF, OGF)
        that will invoke its related method
        """
        self.interface = interface
        self.commands_white_list = {(0x3, 3): self.reset,
                                    (0x1e, 8): self.transmitter_test,
                                    (0x1d, 8): self.receiver_test,
                                    (0x1f, 8): self.test_end,
                                    (0x34, 8): self.transmitter_test,
                                    (0x33, 8): self.receiver_test,
                                    (0x50, 8): self.transmitter_test,
                                    (0x4f, 8): self.receiver_test,
                                    }

    @abstractmethod
    def reset(self) -> bytes:
        """
        Implementation for the HCI Reset command
        """
        pass

    @abstractmethod
    def transmitter_test(self, parameters: str) -> bytes:
        """
        Implementation for any of the three HCI Transmitter Test command
        """
        pass

    @abstractmethod
    def receiver_test(self, parameters: str) -> bytes:
        """
        Implementation for any of the three HCI Receiver Test command
        """
        pass

    @abstractmethod
    def test_end(self) -> bytes:
        """
        Implementation for the HCI Test End command
        """
        pass


class BLECommands(metaclass=ABCMeta):
    """
    Base class for generic BLE commands_white_list automation
    """

    commands_black_list: Dict[Tuple[int, int], Union[Callable[[], bytes], Callable[[str], bytes]]]

    def __init__(self, interface: InterfaceClass) -> None:
        """
        Initialize the interface and the commands_white_list dictionary with the pairs (OCF, OGF)
        that will invoke its related method
        """
        self.interface = interface
        self.commands_black_list = {}
