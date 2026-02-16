#!/usr/bin/env python3
"""
AVR High Voltage Parallel Programmer (HVPP) Module
Port from C# to Python for cross-platform compatibility
"""

import serial
import serial.tools.list_ports
import time
import threading
from enum import Enum
from typing import Callable, Optional, TypedDict

# Debug messages control variable
DEBUG_PRINT = True


class ChipProperties(TypedDict):
    """Properties for each microcontroller chip"""
    chip_id: str
    flash_page_size: int
    flash_total_size: int
    eeprom_page_size: int
    eeprom_total_size: int


class HVPPCommand(Enum):
    """Commands supported by the HVPP programmer"""
    NONE = -1
    OPEN = 0
    READ_SIGNATURE = 1
    READ_FUSES = 2
    WRITE_LFUSE = 3
    WRITE_HFUSE = 4
    WRITE_EXT_FUSE = 5
    WRITE_LOCK_BYTE = 6
    CHIP_ERASE = 7
    READ_CALIBRATION_BYTE = 8
    READ_MEMORY = 9
    WRITE_MEMORY = 10
    LOG = 97
    END = 99


class AtmelHighVoltageParallelProgrammer:
    """Class for communicating with HVPP programmer via serial port"""

    BAUD_RATE = 57600

    # Chip properties database
    CHIP_PROPERTIES: dict[str, ChipProperties] = {
        "ATMEGA8(A)(L)": {
            "chip_id": "0008",
            "flash_page_size": 32,
            "flash_total_size": 1024,      # 1KB
            "eeprom_page_size": 4,
            "eeprom_total_size": 512        # 512 bytes
        },
        "ATMEGA48": {
            "chip_id": "0048",
            "flash_page_size": 32,
            "flash_total_size": 4096,       # 4KB
            "eeprom_page_size": 4,
            "eeprom_total_size": 256        # 256 bytes
        },
        "ATMEGA168(P)(PA)": {
            "chip_id": "0168",
            "flash_page_size": 64,
            "flash_total_size": 16384,      # 16KB
            "eeprom_page_size": 4,
            "eeprom_total_size": 512        # 512 bytes
        },
        "ATMEGA328(P)": {
            "chip_id": "0328",
            "flash_page_size": 64,
            "flash_total_size": 32768,      # 32KB
            "eeprom_page_size": 4,
            "eeprom_total_size": 1024       # 1KB
        },
        "ATTINY2313(V)": {
            "chip_id": "2313",
            "flash_page_size": 16,
            "flash_total_size": 2048,       # 2KB
            "eeprom_page_size": 4,
            "eeprom_total_size": 128        # 128 bytes
        },
        "ATMEGA1284(P)": {
            "chip_id": "1284",
            "flash_page_size": 128,
            "flash_total_size": 131072,     # 128KB
            "eeprom_page_size": 8,
            "eeprom_total_size": 4096       # 4KB
        }
    }

    def __init__(self, port: str, chip: str):
        """
        Initialize the HVPP programmer

        Args:
            port: Serial port name (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            chip: Target chip name
        """
        self.serial_port: Optional[serial.Serial] = None
        self.in_string = ""
        self.chip_name = chip

        # Get chip properties
        if chip not in self.CHIP_PROPERTIES:
            raise ValueError(f"Unknown chip: {chip}")

        self.chip_props = self.CHIP_PROPERTIES[chip]
        self.chip_id = self.chip_props["chip_id"]
        self.data_received_ready = False
        self.firmware_info = ""  # Stocker les infos du firmware

        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=self.BAUD_RATE,
                parity=serial.PARITY_NONE,
                bytesize=serial.EIGHTBITS,
                stopbits=serial.STOPBITS_TWO,
                timeout=0.1
            )
            if DEBUG_PRINT:
                print(f"Port {port} opened")

            # Clear buffers
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            if DEBUG_PRINT:
                print("Buffers cleared")

            # Wait for microcontroller startup message
            if DEBUG_PRINT:
                print("Waiting for µC startup message...")
            startup_received = False
            startup_timeout = time.time() + 10  # 10 secondes timeout
            startup_buffer = ""

            while time.time() < startup_timeout:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='replace')
                    startup_buffer += data
                    if DEBUG_PRINT:
                        print(f"Received at startup: '{data}'")

                    # Check if we received the complete message (with newline)
                    if "\n" in startup_buffer:
                        # Check the part before the comma
                        if startup_buffer.startswith("HVPP Configurator started"):
                            if DEBUG_PRINT:
                                print(f"Startup message received: '{startup_buffer.strip()}'")
                            # Extract info after the comma
                            if "," in startup_buffer:
                                self.firmware_info = startup_buffer.split(",", 1)[1].strip()
                            startup_received = True
                            break
                        else:
                            if DEBUG_PRINT:
                                print(f"Unexpected message: '{startup_buffer.strip()}'")
                time.sleep(0.1)

            if not startup_received:
                error_msg = f"Microcontroller did not send expected startup message. Received: '{startup_buffer.strip()}'"
                if DEBUG_PRINT:
                    print(error_msg)
                self.serial_port.close()
                raise RuntimeError(error_msg)

            if DEBUG_PRINT:
                print("Microcontroller ready to communicate")
        except Exception as ex:
            if DEBUG_PRINT:
                print(f"Port opening error: {ex}")
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            raise

    def close(self):
        """Close the serial port connection"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

    def programmer_communicate(
        self,
        cmd: HVPPCommand,
        parameters: str = "",
        progress_callback: Optional[Callable[[int, int], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> str:
        """
        Send a command to the programmer and receive response

        Args:
            cmd: Command to send
            parameters: Optional parameters for the command

        Returns:
            Response string from the programmer
        """
        result = ""

        if cmd == HVPPCommand.OPEN:
            if DEBUG_PRINT:
                print(f"Sending command 00{self.chip_id}")
            result = self._send_command("00", self.chip_id, 0)
        elif cmd == HVPPCommand.READ_SIGNATURE:
            result = self._send_command("01", "", 6)
        elif cmd == HVPPCommand.READ_FUSES:
            result = self._send_command("02", "", 11)
        elif cmd == HVPPCommand.WRITE_LFUSE:
            result = self._send_command("03", parameters, 0)
        elif cmd == HVPPCommand.WRITE_HFUSE:
            result = self._send_command("04", parameters, 0)
        elif cmd == HVPPCommand.WRITE_EXT_FUSE:
            result = self._send_command("05", parameters, 0)
        elif cmd == HVPPCommand.WRITE_LOCK_BYTE:
            result = self._send_command("06", "", 0)
        elif cmd == HVPPCommand.CHIP_ERASE:
            result = self._send_command("07", "", 0)
        elif cmd == HVPPCommand.READ_CALIBRATION_BYTE:
            result = self._send_command("08", "", 2)
        elif cmd == HVPPCommand.READ_MEMORY:
            # Parameters format: "memory_type:filename"
            # memory_type: "flash" or "eeprom"
            # filename: path to output file
            if DEBUG_PRINT:
                print(f"READ_MEMORY parameters: '{parameters}'")
            parts = parameters.split(":", 1)
            if len(parts) != 2:
                raise ValueError("Invalid READ_MEMORY parameters. Expected format: 'flash:filename' or 'eeprom:filename'")

            memory_type, filename = parts
            if DEBUG_PRINT:
                print(f"READ_MEMORY parsed -> memory_type='{memory_type}', filename='{filename}'")
            if memory_type.lower() == "flash":
                self._read_flash_memory(filename, progress_callback, stop_event)
                result = "0"  # Success
            elif memory_type.lower() == "eeprom":
                self._read_eeprom_memory(filename, progress_callback, stop_event)
                result = "0"  # Success
            else:
                raise ValueError(f"Unknown memory type: {memory_type}")
        elif cmd == HVPPCommand.WRITE_MEMORY:
            # Parameters format: "memory_type:filename"
            if DEBUG_PRINT:
                print(f"WRITE_MEMORY parameters: '{parameters}'")
            parts = parameters.split(":", 1)
            if len(parts) != 2:
                raise ValueError("Invalid WRITE_MEMORY parameters. Expected format: 'flash:filename' or 'eeprom:filename'")

            memory_type, filename = parts
            if DEBUG_PRINT:
                print(f"WRITE_MEMORY parsed -> memory_type='{memory_type}', filename='{filename}'")
            if memory_type.lower() == "flash":
                result = self._write_flash_memory(filename, progress_callback, stop_event)
            elif memory_type.lower() == "eeprom":
                result = self._write_eeprom_memory(filename, progress_callback, stop_event)
            else:
                raise ValueError(f"Unknown memory type: {memory_type}")
        elif cmd == HVPPCommand.LOG:
            result = self._send_command("97", "", 0)
        elif cmd == HVPPCommand.END:
            result = self._send_command("99", "", 1)

        return result

    def _send_command(self, cmd: str, data: str, expected_length: int) -> str:
        """
        Send command and wait for response

        Args:
            cmd: Command code
            data: Data to send with command
            expected_length: Expected response length

        Returns:
            Response string
        """
        self._send_data(cmd + data)
        if DEBUG_PRINT:
            print("Command sent")

        if expected_length == 0:
            # Wait with timeout
            return self._read_response_until_newline(timeout_seconds=5.0)

        # Wait until expected length received
        result = self._read_response(expected_length, timeout_seconds=5.0)
        if not self.data_received_ready and DEBUG_PRINT:
            print("Délai d'attente dépassé")
        return result

    def _send_data(self, data: str):
        """
        Send data to serial port

        Args:
            data: String data to send
        """
        try:
            if self.serial_port and self.serial_port.is_open:
                bytes_written = self.serial_port.write(data.encode('utf-8'))
                self.serial_port.flush()  # Force immediate write
                if DEBUG_PRINT:
                    print(f'Sending "{data}" ({bytes_written} bytes written)')
            else:
                if DEBUG_PRINT:
                    print("ERROR: Serial port not open")
        except Exception as ex:
            if DEBUG_PRINT:
                print(f"Data sending ERROR: {ex}")

    def _send_bytes(self, data: bytes):
        """Send raw bytes to serial port"""
        try:
            if self.serial_port and self.serial_port.is_open:
                bytes_written = self.serial_port.write(data)
                self.serial_port.flush()
                if DEBUG_PRINT:
                    print(f"Sending {bytes_written} raw bytes")
            else:
                if DEBUG_PRINT:
                    print("ERROR: Serial port not open")
        except Exception as ex:
            if DEBUG_PRINT:
                print(f"Raw data sending ERROR: {ex}")

    def _read_response(self, expected_length: int, timeout_seconds: float = 5.0) -> str:
        """Read response from serial port without sending a command.

        If response starts with '1 ' (error with message), wait for \r\n regardless of expected_length.
        """
        self.data_received_ready = False
        self.in_string = ""

        timeout = time.time() + timeout_seconds
        while not self.data_received_ready and len(self.in_string) < expected_length:
            if time.time() > timeout:
                print("Timeout waiting for response (no data received)")
                break
            self._read_data()

            time.sleep(0.005)

        return self.in_string

    def _read_response_until_newline(self, timeout_seconds: float = 5.0) -> str:
        """Read response from serial port until \r\n is received.

        This is the same algorithm as _send_command with expected_length=0.
        Used when we don't know the size of the response (e.g., error messages).
        """
        self.data_received_ready = False
        self.in_string = ""
        timeout = time.time() + timeout_seconds
        while not self.data_received_ready:
            if time.time() > timeout:
                if len(self.in_string) == 0:
                    self.in_string = "1 Timeout waiting for response (no data received)"
                    if DEBUG_PRINT:
                        print("Timeout waiting for response (no data received)")
                break
            self._read_data()
            time.sleep(0.3)

        return self.in_string

    def _read_data(self):
        """Read data from serial port"""
        try:
            if self.serial_port and self.serial_port.is_open:
                waiting = self.serial_port.in_waiting
                if waiting > 0:
                    in_data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='replace')
                    if DEBUG_PRINT:
                        print(f'Receiving "{in_data}" ({waiting} bytes)')
                    self.in_string += in_data

                    # Check for end of transmission
                    if "\r\n" in self.in_string:
                        self.in_string = self.in_string.replace("\0", "").replace("\r\n", "")
                        self.data_received_ready = True
                        if DEBUG_PRINT:
                            print(f"Complete data received: '{self.in_string}'")
                # else:
                #     if DEBUG_PRINT:
                #         print("No data waiting")
        except Exception as ex:
            if DEBUG_PRINT:
                print(f"ERROR in _read_data: {ex}")

    @staticmethod
    def get_available_ports():
        """
        Get list of available serial ports

        Returns:
            List of port names
        """
        ports = serial.tools.list_ports.comports()
        return sorted([port.device for port in ports])

    def _read_memory_page(
        self,
        page_size: int,
        page_number: int,
        memory_type: int,
        stop_event: Optional[threading.Event] = None,
    ) -> bytes:
        """
        Read a page of memory from the microcontroller

        Args:
            page_size: Size of the memory page (Flash = words, EEPROM = bytes)
            page_number: Page number to read
            memory_type: Type of memory (0x01 for Flash, 0x02 for EEPROM)

        Returns:
            Page data as bytes

        Raises:
            RuntimeError: If CRC check fails or communication error
        """
        # Format command: 09sspppptt
        # ss: page size in hex (2 digits)
        # pppp: page number in hex (4 digits)
        # tt: memory type in hex (2 digits)
        cmd = f"09{page_size:02X}{page_number:04X}{memory_type:02X}"

        if stop_event and stop_event.is_set():
            raise RuntimeError("Operation stopped")

        if DEBUG_PRINT:
            unit = "words" if memory_type == 0x01 else "bytes"
            print(
                f"Sending memory read command: {cmd} "
                f"(page_size={page_size} {unit}, page_number={page_number}, memory_type=0x{memory_type:02X})"
            )

        if DEBUG_PRINT:
            print("Clearing input buffer before read")
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.reset_input_buffer()

        # Send command
        self._send_data(cmd)

        # Wait for response:
        # Flash: page_size is in words -> 2 bytes per word
        # EEPROM: page_size is in bytes
        data_bytes = page_size * 2 if memory_type == 0x01 else page_size
        expected_bytes = data_bytes + 2
        data = b''
        timeout = time.time() + 5  # 5 second timeout

        if DEBUG_PRINT:
            print(f"Waiting for {expected_bytes} bytes (data + CRC)")

        while len(data) < expected_bytes:
            if stop_event and stop_event.is_set():
                raise RuntimeError("Operation stopped")
            if time.time() > timeout:
                if DEBUG_PRINT:
                    print(
                        f"Timeout while waiting for memory data. Received {len(data)}/{expected_bytes} bytes"
                    )
                raise RuntimeError(f"Timeout waiting for memory data. Received {len(data)}/{expected_bytes} bytes")

            if self.serial_port.in_waiting > 0:
                chunk = self.serial_port.read(self.serial_port.in_waiting)
                data += chunk
                if DEBUG_PRINT:
                    print(f"Received {len(chunk)} bytes, total: {len(data)}/{expected_bytes}")
            elif DEBUG_PRINT:
                print("No data waiting on serial port")

            time.sleep(0.01)

        # Extract page data and CRC
        page_data = data[:data_bytes]
        received_crc = int.from_bytes(data[data_bytes:data_bytes+2], byteorder='little')

        if DEBUG_PRINT:
            preview_len = min(16, len(page_data))
            preview_hex = " ".join(
                f"{byte_value:02X}" for byte_value in page_data[:preview_len]
            )
            print(f"Page data preview ({preview_len} bytes): {preview_hex}")

        # Calculate CRC-16
        calculated_crc = self._calculate_crc16(page_data)

        if DEBUG_PRINT:
            print(f"Received CRC: 0x{received_crc:04X}, Calculated CRC: 0x{calculated_crc:04X}")

        if received_crc != calculated_crc:
            raise RuntimeError(f"CRC check failed! Received: 0x{received_crc:04X}, Expected: 0x{calculated_crc:04X}")

        return page_data

    @staticmethod
    def _calculate_crc16(data: bytes) -> int:
        """
        Calculate CRC-16 (CCITT) checksum

        Args:
            data: Data bytes to calculate CRC for

        Returns:
            CRC-16 value
        """
        crc = 0

        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
                crc &= 0xFFFF

        return crc

    @staticmethod
    def _parse_intel_hex(filename: str) -> dict[int, int]:
        """Parse Intel HEX file into a memory map (address -> byte)."""
        memory: dict[int, int] = {}
        upper = 0

        with open(filename, "r") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                if not line.startswith(":"):
                    raise ValueError(f"Invalid HEX line {line_num}: missing ':'")

                raw = line[1:]
                if len(raw) < 10:
                    raise ValueError(f"Invalid HEX line {line_num}: too short")

                byte_count = int(raw[0:2], 16)
                addr = int(raw[2:6], 16)
                record_type = int(raw[6:8], 16)
                expected_len = 8 + byte_count * 2 + 2
                if len(raw) != expected_len:
                    raise ValueError(
                        f"Invalid HEX line {line_num}: length {len(raw)} does not match expected {expected_len}"
                    )
                data_str = raw[8:8 + byte_count * 2]
                checksum = int(raw[8 + byte_count * 2:8 + byte_count * 2 + 2], 16)

                # Calcule du checksum pour contrôler l'intégrité de la ligne
                calc = byte_count + ((addr >> 8) & 0xFF) + (addr & 0xFF) + record_type
                data_bytes = bytes.fromhex(data_str) if data_str else b""
                for byte_value in data_bytes:
                    calc += byte_value
                calc = (0x100 - (calc & 0xFF)) & 0xFF

                if calc != checksum:
                    raise ValueError(f"HEX checksum error on line {line_num}")

                match record_type:
                    case 0x00:
                        base_address = upper + addr
                        for byte_index, byte_value in enumerate(data_bytes):
                            memory[base_address + byte_index] = byte_value
                    case 0x01:
                        break
                    case 0x04:
                        if byte_count != 2:
                            raise ValueError(
                                f"Invalid extended linear address record at line {line_num}"
                            )
                        upper = int(data_str, 16) << 16
                    case 0x02:
                        if byte_count != 2:
                            raise ValueError(
                                f"Invalid extended segment address record at line {line_num}"
                            )
                        upper = int(data_str, 16) << 4
                    case _:
                        # Ignore other record types
                        continue

        return memory

    @staticmethod
    def _segment_page_data(page_bytes: int, offsets: list[int], values: dict[int, int]) -> list[tuple[int, bytes]]:
        """Build contiguous segments (offset, data) for a page."""
        segments: list[tuple[int, bytes]] = []
        if not offsets:
            return segments

        offsets.sort()
        start = offsets[0]
        current = [values[start]]
        prev = start

        for off in offsets[1:]:
            if off == prev + 1:
                current.append(values[off])
            else:
                segments.append((start, bytes(current)))
                start = off
                current = [values[off]]
            prev = off

        segments.append((start, bytes(current)))

        # Split segments if they exceed page boundary
        split_segments: list[tuple[int, bytes]] = []
        for start, data in segments:
            offset_index = 0
            while offset_index < len(data):
                current_offset = start + offset_index
                max_chunk_size = page_bytes - current_offset
                chunk = data[offset_index:offset_index + max_chunk_size]
                split_segments.append((current_offset, chunk))
                offset_index += len(chunk)

        return split_segments

    def _read_flash_memory(
        self,
        filename: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Read entire Flash memory and save to Intel HEX file

        Args:
            filename: Output file path

        Raises:
            RuntimeError: If read fails or CRC check fails
        """
        page_size = self.chip_props["flash_page_size"]
        total_size = self.chip_props["flash_total_size"]
        total_pages = total_size // (page_size * 2)

        if DEBUG_PRINT:
            print(
                f"Reading Flash: page_size={page_size} words, total_pages={total_pages}, "
                f"total_size={total_size} bytes, output='{filename}'"
            )

        # Read all pages
        if progress_callback:
            progress_callback(0, total_pages)
        all_data = bytearray()
        for page_num in range(total_pages):
            if stop_event and stop_event.is_set():
                raise RuntimeError("Operation stopped")
            page_data = self._read_memory_page(page_size, page_num, 0x01, stop_event)  # 0x01 = Flash
            all_data.extend(page_data)

            if progress_callback:
                progress_callback(page_num + 1, total_pages)

            if DEBUG_PRINT:
                print(f"Read Flash page {page_num + 1}/{total_pages}")

        # Write to Intel HEX file
        if DEBUG_PRINT:
            print(f"Writing Flash data to Intel HEX file: '{filename}'")
        self._write_intel_hex(filename, all_data)
        if DEBUG_PRINT:
            print("Flash read completed successfully")

    def _read_eeprom_memory(
        self,
        filename: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Read entire EEPROM memory and save to Intel HEX file

        Args:
            filename: Output file path

        Raises:
            RuntimeError: If read fails or CRC check fails
        """
        page_size = self.chip_props["eeprom_page_size"]
        total_size = self.chip_props["eeprom_total_size"]
        total_pages = total_size // page_size

        if DEBUG_PRINT:
            print(
                f"Reading EEPROM: page_size={page_size}, total_pages={total_pages}, "
                f"total_size={total_size}, output='{filename}'"
            )

        # Read all pages
        if progress_callback:
            progress_callback(0, total_pages)
        all_data = bytearray()
        for page_num in range(total_pages):
            if stop_event and stop_event.is_set():
                raise RuntimeError("Operation stopped")
            page_data = self._read_memory_page(page_size, page_num, 0x02, stop_event)  # 0x02 = EEPROM
            all_data.extend(page_data)

            if progress_callback:
                progress_callback(page_num + 1, total_pages)

            if DEBUG_PRINT:
                print(f"Read EEPROM page {page_num + 1}/{total_pages}")

        # Write to Intel HEX file
        if DEBUG_PRINT:
            print(f"Writing EEPROM data to Intel HEX file: '{filename}'")
        self._write_intel_hex(filename, all_data)
        if DEBUG_PRINT:
            print("EEPROM read completed successfully")

    def _write_flash_memory(
        self,
        filename: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> str:
        """Write Flash memory from an Intel HEX file.

        Returns:
            "0" on success, or firmware error response
        """
        page_words = self.chip_props["flash_page_size"]
        total_size = self.chip_props["flash_total_size"]
        return self._write_memory_from_hex(
            filename=filename,
            total_size=total_size,
            page_size=page_words,
            memory_type=0x01,
            memory_label="Flash",
            progress_callback=progress_callback,
            stop_event=stop_event,
        )

    def _write_eeprom_memory(
        self,
        filename: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> str:
        """Write EEPROM memory from an Intel HEX file.

        Returns:
            "0" on success, or firmware error response
        """
        page_bytes = self.chip_props["eeprom_page_size"]
        total_size = self.chip_props["eeprom_total_size"]
        return self._write_memory_from_hex(
            filename=filename,
            total_size=total_size,
            page_size=page_bytes,
            memory_type=0x02,
            memory_label="EEPROM",
            progress_callback=progress_callback,
            stop_event=stop_event,
        )

    def _write_memory_from_hex(
        self,
        filename: str,
        total_size: int,
        page_size: int,
        memory_type: int,
        memory_label: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> str:
        """Write memory from an Intel HEX file using page segments.

        Returns:
            "0" on success, or firmware error response
        """
        page_bytes = page_size * 2 if memory_type == 0x01 else page_size

        if DEBUG_PRINT:
            unit = "words" if memory_type == 0x01 else "bytes"
            print(
                f"Writing {memory_label}: page_size={page_size} {unit}, page_bytes={page_bytes}, "
                f"total_size={total_size} bytes, input='{filename}'"
            )

        memory = self._parse_intel_hex(filename)
        if not memory:
            raise RuntimeError("HEX file contains no data")

        out_of_range = [addr for addr in memory if addr < 0 or addr >= total_size]
        if out_of_range:
            first_addr = min(out_of_range)
            raise RuntimeError(
                f"HEX data contains address outside {memory_label} memory size: 0x{first_addr:06X}"
            )

        pages: dict[int, dict[int, int]] = {}
        for addr, value in memory.items():
            page_number = addr // page_bytes
            offset = addr % page_bytes
            pages.setdefault(page_number, {})[offset] = value

        total_pages = len(pages)
        if progress_callback:
            progress_callback(0, total_pages)

        for page_index, (page_number, values) in enumerate(sorted(pages.items())):
            if stop_event and stop_event.is_set():
                raise RuntimeError("Operation stopped")

            segments = self._segment_page_data(page_bytes, list(values.keys()), values)
            for offset, data in segments:
                response = self._write_memory_page(page_size, page_number, memory_type, offset, data)
                # Check response for each segment write
                if response != "0":
                    # Return first error encountered
                    return response

            if progress_callback:
                progress_callback(page_index + 1, total_pages)

            if DEBUG_PRINT:
                print(f"Wrote {memory_label} page {page_index + 1}/{total_pages}")

        if DEBUG_PRINT:
            print(f"{memory_label} write completed successfully")

        return "0"  # Success

    def _write_memory_page(
        self,
        page_size: int,
        page_number: int,
        memory_type: int,
        offset: int,
        data: bytes,
    ) -> str:
        """Write a page segment to memory with offset/length and CRC.

        Returns:
            "0" on success, or firmware error response (e.g., "1 Checksum invalide...")
        """
        if offset + len(data) > (page_size * 2 if memory_type == 0x01 else page_size):
            raise RuntimeError("Offset + length exceeds page size")

        if len(data) == 0:
            return "0"  # No data to write, return success

        # Command format: 10ssppppttooll
        # For Flash, firmware expects length in words; for EEPROM, in bytes
        write_length = len(data) // 2 if memory_type == 0x01 else len(data)

        if offset > 0xFF or write_length > 0xFF:
            raise RuntimeError("Offset/length must fit in one byte")

        cmd = f"10{page_size:02X}{page_number:04X}{memory_type:02X}{offset:02X}{write_length:02X}"

        if DEBUG_PRINT:
            unit = "words" if memory_type == 0x01 else "bytes"
            print(
                f"Writing memory page: cmd={cmd} (page_size={page_size} {unit}, page={page_number}, "
                f"offset={offset}, length={write_length} {unit}, data_bytes={len(data)})"
            )

        self._send_data(cmd)

        # Wait for firmware acknowledgment "+" before sending data
        ack = self._read_response_until_newline(timeout_seconds=5.0)

        if DEBUG_PRINT:
            print(f"Firmware acknowledgment: '{ack}'")

        # Check if firmware is ready (sends "+") or returned an error
        if ack != "+":
            # Firmware returned an error instead of acknowledgment
            if DEBUG_PRINT:
                print(f"Firmware error before data transmission: '{ack}'")
            return ack

        # Firmware is ready, send data and CRC
        if DEBUG_PRINT:
            preview_len = min(16, len(data))
            preview_hex = " ".join(f"{b:02X}" for b in data[:preview_len])
            print(f"Sending data ({len(data)} bytes), preview: {preview_hex}")

        self._send_bytes(data)
        crc = self._calculate_crc16(data)

        if DEBUG_PRINT:
            print(f"Calculated CRC: 0x{crc:04X}")
            crc_bytes = crc.to_bytes(2, byteorder="little")
            print(f"Sending CRC bytes (little-endian): {crc_bytes[0]:02X} {crc_bytes[1]:02X}")

        self._send_bytes(crc.to_bytes(2, byteorder="little"))

        # Read final response until \r\n (we don't know the size of error messages)
        response = self._read_response_until_newline(timeout_seconds=5.0)

        if DEBUG_PRINT:
            print(f"Write response: '{response}'")

        return response

    @staticmethod
    def _write_intel_hex(filename: str, data: bytearray) -> None:
        """
        Write data to Intel HEX format file

        Args:
            filename: Output file path
            data: Binary data to write
        """
        with open(filename, 'w') as f:
            bytes_per_line = 16
            extended_address = 0

            # Process data in chunks
            for offset in range(0, len(data), bytes_per_line):
                # Calculate current extended address (upper 16 bits)
                current_extended = (offset >> 16) & 0xFFFF

                # Write Extended Linear Address record if needed (for addresses > 64KB)
                if current_extended != extended_address:
                    extended_address = current_extended
                    # Format: :02000004XXXXCC
                    # 02 = byte count, 0000 = address, 04 = record type (extended linear address)
                    ext_addr_high = (extended_address >> 8) & 0xFF
                    ext_addr_low = extended_address & 0xFF
                    checksum = (0x02 + 0x00 + 0x00 + 0x04 + ext_addr_high + ext_addr_low) & 0xFF
                    checksum = (0x100 - checksum) & 0xFF
                    f.write(f":02000004{extended_address:04X}{checksum:02X}\n")

                # Get chunk of data
                chunk = data[offset:offset + bytes_per_line]
                byte_count = len(chunk)

                # Calculate address (lower 16 bits)
                address = offset & 0xFFFF

                # Record type: 00 = data
                record_type = 0x00

                # Calculate checksum
                checksum = byte_count + ((address >> 8) & 0xFF) + (address & 0xFF) + record_type
                for byte in chunk:
                    checksum += byte
                checksum = (0x100 - (checksum & 0xFF)) & 0xFF

                # Write data record
                hex_data = ''.join(f'{byte:02X}' for byte in chunk)
                f.write(f":{byte_count:02X}{address:04X}{record_type:02X}{hex_data}{checksum:02X}\n")

            # Write End Of File record
            f.write(":00000001FF\n")
