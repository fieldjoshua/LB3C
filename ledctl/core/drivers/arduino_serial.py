"""
Arduino Serial LED Driver (Adalight protocol)

Streams RGB frames over USB serial to an Arduino (Nano/Uno/compatible)
running an Adalight-compatible sketch. The Arduino drives the physical
WS2811/WS2812 LEDs locally via FastLED or equivalent.

Adalight frame format (bytes):
    'A' 'd' 'a'        - magic word
    hi                 - (LED count - 1) high byte
    lo                 - (LED count - 1) low byte
    chk                - hi XOR lo XOR 0x55
    R0 G0 B0 ...       - RGB triples, one per LED

This protocol is the de facto standard supported by many sketches
(Adalight, Hyperion, Prismatik).
"""

import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from . import DeviceManager, OutputDevice

logger = logging.getLogger(__name__)

try:
    import serial
    from serial.tools import list_ports
    HAS_PYSERIAL = True
except ImportError:
    HAS_PYSERIAL = False
    logger.warning("pyserial not available - Arduino serial driver disabled")


class ArduinoSerialDevice(OutputDevice):
    """Arduino-over-USB LED driver using the Adalight protocol."""

    DEFAULT_BAUD = 500000
    # Long enough to cover Nano bootloader (~1.5s) + sketch start + banner.
    DEFAULT_HANDSHAKE_TIMEOUT = 4.0
    MAGIC = b"Ada"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        cfg = config.get("arduino", {})

        self.port: Optional[str] = cfg.get("port")  # None => autodetect
        self.baud: int = int(cfg.get("baud", self.DEFAULT_BAUD))
        self.width: int = int(cfg.get("width", 10))
        self.height: int = int(cfg.get("height", 10))
        self.count: int = int(cfg.get("count", self.width * self.height))
        self.pixel_order: str = cfg.get("pixel_order", "GRB").upper()
        self.wait_for_handshake: bool = bool(cfg.get("wait_for_handshake", True))
        self.reset_on_open: bool = bool(cfg.get("reset_on_open", True))
        self.map_file: Optional[str] = cfg.get("map_file")
        # Layout: "linear" | "serpentine". Serpentine == even rows L->R,
        # odd rows R->L (standard snake wiring for LED grids).
        self.layout: str = cfg.get("layout", "serpentine").lower()
        # Which row the serpentine starts flipped on. Set to 1 if your first
        # physical row runs right-to-left instead of left-to-right.
        self.serpentine_start_flipped: bool = bool(
            cfg.get("serpentine_start_flipped", False)
        )

        self.brightness: float = 1.0
        self._ser: Optional["serial.Serial"] = None
        self._lock = threading.Lock()
        self._header = self._build_header(self.count)
        self._tx_buf = bytearray(len(self._header) + self.count * 3)
        self._tx_buf[: len(self._header)] = self._header

        if self.map_file:
            self._load_pixel_map(self.map_file)
        else:
            self._generate_default_map()

    @classmethod
    def _build_header(cls, count: int) -> bytes:
        n = max(0, count - 1)
        hi = (n >> 8) & 0xFF
        lo = n & 0xFF
        chk = hi ^ lo ^ 0x55
        return cls.MAGIC + bytes([hi, lo, chk])

    def _load_pixel_map(self, map_file: str) -> None:
        try:
            with open(map_file, "r") as f:
                self.pixel_map = json.load(f)
            logger.info(f"Loaded pixel map from {map_file}")
        except Exception as e:
            logger.error(f"Failed to load pixel map: {e}")
            self._generate_default_map()

    def _generate_default_map(self) -> None:
        self.pixel_map = []
        if self.layout == "serpentine":
            for led_idx in range(self.count):
                row = led_idx // self.width
                col_in_row = led_idx % self.width
                flip = (row % 2 == 1) ^ self.serpentine_start_flipped
                x = (self.width - 1 - col_in_row) if flip else col_in_row
                y = row
                self.pixel_map.append({"x": x, "y": y})
        else:
            for i in range(self.count):
                x = i % self.width
                y = i // self.width
                self.pixel_map.append({"x": x, "y": y})

    @staticmethod
    def list_serial_ports() -> List[Dict[str, str]]:
        """Return available serial ports (device, description, hwid)."""
        if not HAS_PYSERIAL:
            return []
        return [
            {"device": p.device, "description": p.description or "", "hwid": p.hwid or ""}
            for p in list_ports.comports()
        ]

    @staticmethod
    def autodetect_port() -> Optional[str]:
        """Pick the most likely Arduino serial port.

        Looks for common USB-serial bridges used on Nano clones: CH340, CP210x,
        FTDI, and the ATmega16U2 on genuine Unos.
        """
        if not HAS_PYSERIAL:
            return None
        candidates = []
        for p in list_ports.comports():
            hay = f"{p.description} {p.manufacturer or ''} {p.hwid or ''}".lower()
            score = 0
            if "arduino" in hay:
                score += 10
            if any(k in hay for k in ("ch340", "ch341", "wch")):
                score += 8
            if "cp210" in hay:
                score += 7
            if "ftdi" in hay or "ft232" in hay:
                score += 6
            if "usb" in hay and "serial" in hay:
                score += 3
            if score > 0:
                candidates.append((score, p.device))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]

    def open(self) -> None:
        if not HAS_PYSERIAL:
            raise RuntimeError("pyserial not installed (pip install pyserial)")
        if self.is_open:
            return

        port = self.port or self.autodetect_port()
        if not port:
            raise RuntimeError(
                "No Arduino serial port configured or autodetected. "
                "Set arduino.port in config or plug in the device."
            )

        try:
            # dtr toggle resets most Arduinos; writeTimeout guards against
            # a wedged USB stack stalling the whole animation pipeline.
            self._ser = serial.Serial(
                port=port,
                baudrate=self.baud,
                timeout=1.0,
                write_timeout=1.0,
                dsrdtr=False,
            )
            if self.reset_on_open:
                self._ser.setDTR(False)
                time.sleep(0.1)
                self._ser.reset_input_buffer()
                self._ser.setDTR(True)
                # Bootloader takes ~1.5s after the DTR pulse, then the sketch
                # emits its 'Ada\n' banner exactly once. Don't flush again
                # below or we lose it.

            if self.wait_for_handshake:
                self._await_ready()
            else:
                self._ser.reset_input_buffer()

            self.port = port
            self.is_open = True
            logger.info(
                f"Arduino serial opened on {port} @ {self.baud} baud, "
                f"{self.count} LEDs ({self.width}x{self.height})"
            )
        except Exception as e:
            if self._ser is not None:
                try:
                    self._ser.close()
                except Exception:
                    pass
                self._ser = None
            raise RuntimeError(f"Cannot open Arduino on {port}: {e}") from e

    def _await_ready(self) -> None:
        """Wait for the sketch's 'Ada\\n' ready banner (if it emits one).

        Not all sketches send this. We wait best-effort and move on.
        """
        deadline = time.monotonic() + self.DEFAULT_HANDSHAKE_TIMEOUT
        buf = bytearray()
        while time.monotonic() < deadline:
            chunk = self._ser.read(64) if self._ser else b""
            if chunk:
                buf.extend(chunk)
                if b"Ada" in buf:
                    logger.info("Arduino sketch handshake received")
                    return
            else:
                time.sleep(0.05)
        logger.info("No Adalight handshake banner seen (continuing anyway)")

    def close(self) -> None:
        if not self.is_open:
            return
        try:
            self._send_black()
        except Exception:
            pass
        try:
            if self._ser:
                self._ser.close()
        finally:
            self._ser = None
            self.is_open = False
            logger.info("Arduino serial closed")

    def set_brightness(self, value: float) -> None:
        self.brightness = max(0.0, min(1.0, float(value)))
        logger.debug(f"Arduino brightness set to {self.brightness:.2f}")

    def _reorder(self, r: int, g: int, b: int) -> Tuple[int, int, int]:
        order = self.pixel_order
        if order == "RGB":
            return r, g, b
        if order == "GRB":
            return g, r, b
        if order == "BGR":
            return b, g, r
        if order == "BRG":
            return b, r, g
        if order == "GBR":
            return g, b, r
        if order == "RBG":
            return r, b, g
        return r, g, b  # unknown -> pass-through

    def draw_rgb_frame(
        self,
        width: int,
        height: int,
        rgb_data: List[Tuple[int, int, int]],
    ) -> None:
        if not self.is_open or self._ser is None:
            raise RuntimeError("Device not open")
        if len(rgb_data) != width * height:
            raise ValueError(
                f"RGB data size mismatch: expected {width*height}, got {len(rgb_data)}"
            )

        b_mul = self.brightness
        buf = self._tx_buf
        off = len(self._header)

        for led_idx in range(self.count):
            mapping = self.pixel_map[led_idx] if led_idx < len(self.pixel_map) else None
            if mapping is None:
                buf[off:off + 3] = b"\x00\x00\x00"
                off += 3
                continue
            x = mapping.get("x", 0)
            y = mapping.get("y", 0)
            if 0 <= x < width and 0 <= y < height:
                r, g, b = rgb_data[y * width + x]
                if b_mul < 1.0:
                    r = int(r * b_mul)
                    g = int(g * b_mul)
                    b = int(b * b_mul)
                r, g, b = self._reorder(r, g, b)
                buf[off] = r & 0xFF
                buf[off + 1] = g & 0xFF
                buf[off + 2] = b & 0xFF
            else:
                buf[off] = 0
                buf[off + 1] = 0
                buf[off + 2] = 0
            off += 3

        with self._lock:
            try:
                self._ser.write(buf)
            except serial.SerialTimeoutException:
                logger.warning("Serial write timed out; flushing and continuing")
                self._ser.reset_output_buffer()

    def _send_black(self) -> None:
        if not self._ser:
            return
        buf = bytearray(self._header) + bytes(self.count * 3)
        with self._lock:
            self._ser.write(buf)


DeviceManager.register_device("ARDUINO", ArduinoSerialDevice)
