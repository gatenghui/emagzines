# -*- coding: utf-8 -*-
"""保证 scripts/*.ps1 是 UTF-8 with BOM。

Windows PowerShell 5.1 读取无 BOM 的 .ps1 时按 ANSI(GBK) 解码，中文会变成乱码甚至语法错误。
每次双击 bat 都会静默跑一遍这个脚本，幂等，无输出。
"""
import pathlib
import sys

base = pathlib.Path(__file__).resolve().parent
fixed = 0
for p in base.glob("*.ps1"):
    data = p.read_bytes()
    if not data.startswith(b"\xef\xbb\xbf"):
        p.write_bytes(b"\xef\xbb\xbf" + data)
        fixed += 1
if "--verbose" in sys.argv:
    print(f"BOM fixed: {fixed}")
