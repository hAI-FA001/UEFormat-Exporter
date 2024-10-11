from __future__ import annotations

import struct
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import numpy.typing as npt

if TYPE_CHECKING:
    from types import TracebackType

R = TypeVar("R")


class FArchiveWriter:
    def __init__(self, path: Path) -> None:
        self.path = path if isinstance(path, Path) else Path(path)

    def __enter__(self) -> FArchiveWriter:
        self.file = open(self.path, "wb")
        return self
    
    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
    ) -> None:
        self.file.close()

    def tell(self) -> int:
        return self.file.tell()
    
    def seek(self, offset: int, whence: int = 0) -> None:
        self.file.seek(offset, whence)
    
    def write_bool(self, boolean: bool) -> int:
        number_bytes_written = self.file.write(struct.pack("?", boolean))
        return number_bytes_written
    
    def write_string(self, string: str) -> int:
        number_bytes_written = self.file.write(string.encode(encoding="utf-8"))
        return number_bytes_written
    
    def write_fstring(self, fstring: str) -> int:
        number_bytes_written = self.file.write(struct.pack("i", len(fstring)))
        number_bytes_written += self.file.write(fstring.encode(encoding="utf-8"))
        return number_bytes_written
    
    def write_int(self, integer: int) -> int:
        number_bytes_written = self.file.write(struct.pack("i", integer))
        return number_bytes_written
    
    def write_int_vector(self, int_vec: tuple[int, ...] | npt.NDArray) -> int:
        if type(int_vec) == npt.NDArray:
            int_vec = tuple(int_vec)
        number_bytes_written = self.file.write(struct.pack("I"*len(int_vec), *int_vec))
        return number_bytes_written
    
    def write_short(self, short: int) -> int:
        number_bytes_written = self.file.write(struct.pack("h", short))
        return number_bytes_written
    
    def write_byte(self, byte: bytes) -> int:
        number_bytes_written = self.file.write(struct.pack("c", byte))
        return number_bytes_written
    
    def write_float(self, float_value: float) -> int:
        number_bytes_written = self.file.write(struct.pack("f", float_value))
        return number_bytes_written
    
    def write_float_vector(self, float_vec: tuple[float, ...] | npt.NDArray) -> int:
        if type(float_vec) == npt.NDArray:
            float_vec = tuple(float_vec)
        number_bytes_written = self.file.write(struct.pack("f"*len(float_vec), *float_vec))
        return number_bytes_written
    
    def write_byte_vector(self, byte_vec: tuple[int, ...]) -> int:
        number_bytes_written = self.file.write(struct.pack("B"*len(byte_vec), *byte_vec))
        return number_bytes_written
    
    def pad(self, size: int) -> int:
        number_bytes_written = self.file.write(struct.pack("B"*size, *([0]*size)))
        return number_bytes_written
