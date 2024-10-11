from __future__ import annotations
from typing import TYPE_CHECKING

from .writer import FArchiveWriter

if TYPE_CHECKING:
    from collections.abc import Callable


def write_byte_size_wrapper(ar: FArchiveWriter, fn: Callable[[FArchiveWriter], int]):
    pos_before = ar.tell()
    ar.pad_with_int(1)

    total_bytes_written = fn(ar)
    pos_after = ar.tell()
    
    ar.seek(pos_before)
    ar.write_int(total_bytes_written)
    ar.seek(pos_after)

    return total_bytes_written + 4  # add 4 cuz total_bytes_written itself takes 4 bytes
