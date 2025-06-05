import zlib
import struct
import numpy as np

# dekompresuje obraz PNG ze skompresowanego strumienia IDAT
#   1 rozpakowuje dane IDAT (zlib / DEFLATE).
#   2 stosuje filtry PNG (None, Sub, Up, Average, Paeth) przywracając pierwotne piksele w kolejności RGBA
#   3 zwraca numpy.ndarray o kształcie ``(height, width, 4)`` oraz ``dtype=uint8``

def decompressIDAT(IHDR_data: bytes, IDAT_data: bytes) -> np.ndarray:
    #1 parsowanie IHDR, weryfikacja metod kompresji i filtracji
    width, height, bitd, colort, compm, filterm, interlacem = struct.unpack('>IIBBBBB', IHDR_data)

    #PNG używa tylko jednej metody kompresji (0 = DEFLATE) i filtra (0) jeśli inny kod to plik jest niespecyfikacyjny


    #2 rozpakowanie DEFLATE po operacji mamy cały obraz linia po lini z dodanym byte filtra na początku każdego wiersza
    IDAT_data = zlib.decompress(IDAT_data)

    #3 przygotowanie pomocniczego predyktora PaethPredictor RFC 2083 (filtr nr 4)
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

    #4 odwracanie filtrów
    Recon  = []  #zrekonstruowane bajty obrazu (flat list)
    bpp    = 4   #bytes per pixel – zakładamy 32-bit RGBA (8 b × 4 kanaly)
    stride = width * bpp  #liczba bajtów jednej pełnej linii pikseli bez filtra

    #pomocnicze zwracające sąsiadów wg specyfikacji PNG
    # a = piksel po lewej, b = piksel powyżej, c = piksel lewy górny
    def a(r, c): return Recon[r * stride + c - bpp] if c >= bpp else 0
    def b(r, c): return Recon[(r - 1) * stride + c]     if r > 0 else 0
    def c(r, c): return Recon[(r - 1) * stride + c - bpp] if r > 0 and c >= bpp else 0

    i = 0  #indeks w buforze IDAT_data
    for r in range(height):
        #pierwszy bajt każdej linii = kod zastosowanego filtra
        ftype = IDAT_data[i]
        i += 1

        #iteracja po surowych bajtach pikseli
        for c in range(stride):
            F = IDAT_data[i]  #bajt po filtrze
            i += 1

            #odwracamy filtr wg 5 przypadkow definiowanych w PNG
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

            #zachowujemy tylko ostatnie 8 bitów (mogła wystąpić nadmiarowa suma >255)
            Recon.append(val & 0xFF)

    img = np.array(Recon, dtype=np.uint8).reshape((height, width, 4))
    return img