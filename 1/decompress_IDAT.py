import zlib
import struct
import numpy as np

# decompresses a PNG image from a compressed IDAT stream
#   1 unpacks IDAT data (zlib / DEFLATE).
#   2 applies PNG filters (None, Sub, Up, Average, Paeth) restoring the original pixels in RGBA order
#   3 returns a numpy.ndarray with shape ``(height, width, 4)`` and ``dtype=uint8``

def decompressIDAT(IHDR_data: bytes, IDAT_data: bytes) -> np.ndarray:
    #1 IHDR parsing, verification of compression and filtration methods
    width, height, bitd, colort, compm, filterm, interlacem = struct.unpack('>IIBBBBB', IHDR_data)

    #PNG uses only one compression method (0 = DEFLATE) and filter (0), if another code then the file is unspecified


    #2 unpacking DEFLATE after the operation we have the entire image line by line with the filter byte added at the beginning of each line
    IDAT_data = zlib.decompress(IDAT_data)

    #3 preparation of the PaethPredictor RFC 2083 auxiliary predictor (filter no. 4)
    def PaethPredictor(a: int, b: int, c: int) -> int:
        p  = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        elif pb <= pc:
            return b
        else:
            return c

    #4 inverting filters
    Recon  = []  #reconstructed image bytes (flat list)
    bpp    = 4   #bytes per pixel – we assume 32-bit RGBA (8 b × 4 channels)
    stride = width * bpp  #number of bytes of one full pixel line without filter

    #auxiliary returning neighbors according to the PNG specification
    # a = pixel on the left, b = pixel above, c = pixel top left
    def a(r, c): return Recon[r * stride + c - bpp] if c >= bpp else 0
    def b(r, c): return Recon[(r - 1) * stride + c]     if r > 0 else 0
    def c(r, c): return Recon[(r - 1) * stride + c - bpp] if r > 0 and c >= bpp else 0

    i = 0  #index in the IDAT_data buffer
    for r in range(height):
        #first byte of each line = code of the filter used
        ftype = IDAT_data[i]
        i += 1

        #iterating over raw pixel bytes
        for c in range(stride):
            F = IDAT_data[i]  #byte after filter
            i += 1

            #inverting the filter according to 5 cases defined in PNG
            if ftype == 0:      #None
                val = F
            elif ftype == 1:    #Sub
                val = F + a(r, c)
            elif ftype == 2:    #Up
                val = F + b(r, c)
            elif ftype == 3:    #Average
                val = F + (a(r, c) + b(r, c)) // 2
            elif ftype == 4:    #Paeth
                val = F + PaethPredictor(a(r, c), b(r, c), c(r, c))
            else:
                raise Exception('unknown filter type')

            #keep only the last 8 bits (there could be an overflow sum >255)
            Recon.append(val & 0xFF)

    img = np.array(Recon, dtype=np.uint8).reshape((height, width, 4))
    return img