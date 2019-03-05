"""
Interfaces implementation

@author: Daniel Fajardo
"""

import binascii
import logging
from abc import ABCMeta, abstractmethod
from typing import Dict, Union

import serial  # type: ignore

log_int = logging.getLogger("Bridge.INT")
log_int.setLevel(logging.DEBUG)


class InterfaceClass(metaclass=ABCMeta):
    """
    Base class for interfaces
    """

    @abstractmethod
    def __init__(self) -> None:
        """
        Initialize the device
        """
        pass

    @abstractmethod
    def read(self) -> bytes:
        """
        Method to read from the device
        """
        pass

    @abstractmethod
    def write(self, data: bytes) -> None:
        """
        Method to write to the device
        """
        pass


class Serial(InterfaceClass):
    """
    Serial implementation
    """

    def __init__(self, device: Dict[str, Union[str, int, float]]) -> None:
        """
        Initialize the device port
        """
        super().__init__()
        log_int.debug(f"Initializing serial device for {device['name']} :: Port: {device['port']} - Baud rate: "
                      f"{device['baudrate']} - Timeout: {device['timeout']} - RTS/CTS: {bool(device['flowcontrol'])}")
        self.device = serial.Serial(port=device['port'], baudrate=device['baudrate'],
                                    timeout=device['timeout'], rtscts=device['flowcontrol'])

    def read(self) -> bytes:
        """
        Read from the serial using the readline function.

        End line for readline is '\n', so if the data contains a '\n' character, it shall continue reading
        """
        line = self.device.readline()
        if len(line) > 0 and line[-1] == 10:
            line += self.device.readline()
        return line

    def write(self, data: bytes) -> None:
        """
        Write to the device
        """
        self.device.write(binascii.unhexlify(data))
