"""
IUT implementation to communicate using HCI with an IUT supporting 2-wires protocol

@author: Daniel Fajardo
"""

import binascii
import logging
from typing import Dict, Union

from hci import RFCommands
from interfaces import Serial

log_iut = logging.getLogger("Bridge.IUT")


class IUT(RFCommands):
    """
    Class that implements the translation from HCI to 2-wires protocol and vice versa
    """

    def __init__(self, device: Dict[str, Union[str, int, float]]) -> None:
        """
        Initializing the IUT
        """
        super().__init__(Serial(device))

    def reset(self) -> bytes:
        """
        Implementation for HCI Reset
        """
        log_iut.debug("Sending Reset to IUT")
        self.interface.write(b'0000')

        reply = binascii.hexlify(self.interface.read())
        log_iut.debug(f"Reply from IUT: {reply.decode()}")

        status = b'00' if reply == b'0000' else b'1f'

        return b'040e0401030c' + status

    def transmitter_test(self, parameters: str) -> bytes:
        """
        Implementation for HCI Transmitter Test v1 and v2
        """
        failed = 0  # To control the global status of the commands_white_list
        log_iut.debug(f"Transmitter test parameters: {parameters}")

        # 2-wires does not support all payload packet types defined in HCI
        payload_type_map = {0: 0,
                            1: 1,
                            2: 2,
                            4: 3,
                            }

        hci_channel = int(parameters[0:2], 16)
        packet_length = int(parameters[2:4], 16)
        payload_type = payload_type_map.get(int(parameters[4:6], 16), 3)

        if len(parameters) / 2 == 4:
            tx_test_version = 2
            phy = int(parameters[6:8], 16)

            test_setup_phy = int(f"00{2:06b}{phy:06b}{0:02b}", 2) \
                .to_bytes(length=2, byteorder='big')
            log_iut.debug(f"Sending Test Setup PHY to IUT: {test_setup_phy.hex()}")
            self.interface.write(binascii.hexlify(test_setup_phy))

            reply = binascii.hexlify(self.interface.read())
            log_iut.debug(f"Reply from IUT: {reply.decode()}")

            failed += 1 if reply != b'0000' else 0
        elif len(parameters) / 2 > 4:
            tx_test_version = 3
            log_iut.warning("Transmitter Test v3 not implemented")
        else:
            tx_test_version = 1

        if packet_length > 63:
            test_setup_length = int(f"00{1:06b}{(packet_length & 0xC0) >> 4:08b}", 2) \
                .to_bytes(length=2, byteorder='big')
            log_iut.debug(f"Sending Test Setup Length to IUT: {test_setup_length.hex()}")
            self.interface.write(binascii.hexlify(test_setup_length))

            reply = binascii.hexlify(self.interface.read())
            log_iut.debug(f"Reply from IUT: {reply.decode()}")

            failed += 1 if reply != b'0000' else 0

        tx_test_cmd = int(f"10{hci_channel:06b}{packet_length & 0x3F:06b}{payload_type:02b}", 2) \
            .to_bytes(length=2, byteorder='big')
        log_iut.debug(f"Sending TX Test to IUT: {tx_test_cmd.hex()}")
        self.interface.write(binascii.hexlify(tx_test_cmd))

        reply = binascii.hexlify(self.interface.read())
        log_iut.debug(f"Reply from IUT: {reply.decode()}")

        failed += 1 if reply != b'0000' else 0
        status = b'00' if not failed else b'01'
        log_iut.debug(f"Status: {status.decode()}")

        event = {1: b'040E04011E20',
                 2: b'040E04013420',
                 3: b'040E04014f20',
                 }

        return event[tx_test_version] + status

    def receiver_test(self, parameters: str) -> bytes:
        """
        Implementation for HCI Receiver Test v1 and v2
        """
        failed = 0  # To control the global status of the commands_white_list
        hci_channel = int(parameters[0:2], 16)

        if len(parameters) / 2 == 3:
            rx_test_version = 2
            phy = int(parameters[2:4], 16)
            mod_index = int(parameters[4:6], 16)

            test_setup_phy = int(f"00{2:06b}{phy:06b}{0:02b}", 2) \
                .to_bytes(length=2, byteorder='big')
            log_iut.debug(f"Sending Test Setup PHY to IUT: {test_setup_phy.hex()}")
            self.interface.write(binascii.hexlify(test_setup_phy))

            reply = binascii.hexlify(self.interface.read())
            log_iut.debug(f"Reply from IUT: {reply.decode()}")

            failed += 1 if reply != b'0000' else 0

            test_setup_mod = int(f"00{3:06b}{mod_index:06b}{0:02b}", 2) \
                .to_bytes(length=2, byteorder='big')
            log_iut.debug(f"Sending Test Setup Mod to IUT: {test_setup_mod.hex()}")
            self.interface.write(binascii.hexlify(test_setup_mod))

            reply = binascii.hexlify(self.interface.read())
            log_iut.debug(f"Reply from IUT: {reply.decode()}")

            failed += 1 if reply != b'0000' else 0
        elif len(parameters) / 2 > 3:
            rx_test_version = 3
            log_iut.warning("Receiver Test v3 not implemented")
        else:
            rx_test_version = 1

        rx_test_cmd = int(f"01{hci_channel:06b}{0:06b}{0:02b}", 2) \
            .to_bytes(length=2, byteorder='big')
        log_iut.debug(f"Sending RX Test to IUT: {rx_test_cmd.hex()}")
        self.interface.write(binascii.hexlify(rx_test_cmd))

        reply = binascii.hexlify(self.interface.read())
        log_iut.debug(f"Reply from IUT: {reply.decode()}")

        failed += 1 if reply != b'0000' else 0
        status = b'00' if not failed else b'01'
        log_iut.debug(f"Status: {status.decode()}")

        event = {1: b'040E04011d20',
                 2: b'040E04013320',
                 3: b'040E04015020',
                 }

        return event[rx_test_version] + status

    def test_end(self) -> bytes:
        """
        Implementation for HCI Test End
        """
        log_iut.debug("Sending Test End to IUT")
        self.interface.write(b'c000')

        reply = self.interface.read()
        log_iut.debug(f"Reply from IUT: {reply.hex()}")

        reply_int = int.from_bytes(reply, byteorder='big')
        is_report = reply_int >> 15
        if is_report:
            status = b'00'
            num_packets_int = reply_int & 0x7FF
            num_packets = binascii.hexlify(num_packets_int.to_bytes(length=2, byteorder='little'))
            log_iut.debug(f"Num packets: {num_packets_int}")
        else:
            status = b'01'
            num_packets = b'0000'
            log_iut.debug("Test End failed")

        event = b'040E06011F20' + status + num_packets if status == b'00' else b'040E04011F20' + status

        return event
