# -*- coding: utf-8 -*-
"""Diem khoi chay ung dung.

    python run.py

Chi can Python 3.10+ voi tkinter (co san trong ban cai Python tren Windows).
Khong can cai them bat ky goi nao.
"""

import sys

if sys.version_info < (3, 10):
    raise SystemExit("Can Python 3.10 tro len. Ban dang dung %s."
                     % sys.version.split()[0])

try:
    import tkinter  # noqa: F401
except ImportError:
    raise SystemExit(
        "Khong tim thay tkinter.\n"
        "Tren Windows: cai lai Python va tick 'tcl/tk and IDLE'.\n"
        "Tren Ubuntu/Debian: sudo apt install python3-tk")

from psat.ui import main

if __name__ == "__main__":
    main()
