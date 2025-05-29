import zlib
import struct
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

def decompressIDAT(IHDR_data, IDAT_data):
    width, height, bitd, colort, compm, filterm, interlacem = struct.unpack('>IIBBBBB', IHDR_data)
    if compm != 0:    raise Exception('invalid compression method')
    if filterm != 0: raise Exception('invalid filter method')

    IDAT_data = zlib.decompress(IDAT_data)

    def PaethPredictor(a,b,c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        elif pb <= pc:
            return b
        else:
            return c

    Recon = []
    bpp = 4
    stride = width * bpp
    def a(r,c): return Recon[r*stride + c - bpp] if c >= bpp else 0
    def b(r,c): return Recon[(r-1)*stride + c] if r > 0 else 0
    def c(r,c): return Recon[(r-1)*stride + c - bpp] if r > 0 and c >= bpp else 0

    i = 0
    for r in range(height):
        ftype = IDAT_data[i]; i += 1
        for c in range(stride):
            F = IDAT_data[i]; i += 1
            if ftype == 0:
                val = F
            elif ftype == 1:
                val = F + a(r,c)
            elif ftype == 2:
                val = F + b(r,c)
            elif ftype == 3:
                val = F + (a(r,c) + b(r,c)) // 2
            elif ftype == 4:
                val = F + PaethPredictor(a(r,c), b(r,c), c(r,c))
            else:
                raise Exception('unknown filter type')
            Recon.append(val & 0xff)

    img = np.array(Recon, dtype=np.uint8).reshape((height, width, 4))
    return img