"""Check that the Windows DLL loads and APG matches the IERS reference case."""

from __future__ import annotations

import ctypes
from pathlib import Path
import sys


def main(path: Path) -> None:
    dll_path = path.resolve()
    dll = ctypes.CDLL(str(dll_path))
    apg = dll.apg_
    pointer = ctypes.POINTER(ctypes.c_double)
    apg.argtypes = [pointer] * 7
    apg.restype = None

    values = [
        ctypes.c_double(0.6274877539940092),
        ctypes.c_double(2.454994088489240),
        ctypes.c_double(0.2617993877991494),
        ctypes.c_double(0.8726646259971648),
        ctypes.c_double(),
        ctypes.c_double(),
        ctypes.c_double(),
    ]
    apg(*(ctypes.byref(value) for value in values))
    expected = (-0.9677190006296187757e-4, -0.1042668498001996791, 0.4662515377110782594e-1)
    actual = tuple(value.value for value in values[4:])
    for result, reference in zip(actual, expected):
        if abs(result - reference) > 1e-9:
            raise AssertionError(f"APG result {actual} differs from IERS reference {expected}")
    print(f"Loaded {dll_path}; APG reference case passed: {actual}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
