import zlib
import struct
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image 

from decompress_IDAT import decompressIDAT   #dekompresja IDAT na RGBA
from print_chunks      import printChunk      #ladne wypisywanie metadanych
from append_data_behind_iend import appendDataBehindIEND  #dodaj na koncu

#1 stale specyficzne dla formatu PNG
PngSignature: bytes = b'\x89PNG\r\n\x1a\n'   #8 bajtowy nagłówek PNG
critical = {b'IHDR', b'PLTE', b'IDAT', b'IEND'}   #4 krytyczne chunki wg RFC 2083

#2 parser pliku PNG recznie czyta strukturę PNG i zwraca rozbite chunki + bajty po IEND
def readPNG(file_path):

    critical_chunks  = []
    ancillary_chunks = []

    with open(file_path, 'rb') as f:
        #walidacja
        if f.read(len(PngSignature)) != PngSignature:
            raise Exception('Invalid PNG Signature')

        #odczyt jednego chunka
        def read_chunk(stream):
            #chunk = [4B length][4B type][payload][4B CRC]
            chunk_length, chunk_type = struct.unpack('>I4s', stream.read(8))
            chunk_data = stream.read(chunk_length)
            chunk_crc, = struct.unpack('>I', stream.read(4))

            # CRC zabezpieczenie integralności, obliczamy zlib.crc32(type + data) i porównujemy
            calc_crc = zlib.crc32(chunk_data, zlib.crc32(chunk_type))
            if chunk_crc != calc_crc:
                raise Exception('chunk checksum failed')
            return chunk_type, chunk_data, chunk_length, chunk_crc

        #petla po chnkach
        offset = len(PngSignature)
        while True:
            t, d, length, crc = read_chunk(f)

            #podział na critical i ancillary ułatwia późniejszą anonimizacje
            if t in critical:
                critical_chunks.append((t, d, length, offset, crc))
            else:
                ancillary_chunks.append((t, d, length, offset, crc))

            offset += 4 + 4 + length + 4
            if t == b'IEND':
                break  #koniec specyfikacji PNG dalej tyklko ukryte bajty

        #sprawdzenie za IEND (steganografia)
        f.seek(0, 2)
        file_size        = f.tell()
        bytes_after_iend = file_size - offset  #ile śmieci po IEND

    return critical_chunks, ancillary_chunks, bytes_after_iend

def printChunks(chunks):
    for chunk in chunks:
        printChunk(chunk)

#3 anonimizacja = wyrzucenie ancillary chunkow + ewentualnej palety tworzy kopię PNG z zachowaniem tylko minimum chunków
#    jeżeli obraz jest paletowy (color_type == 3), PLTE musi zostać
#    usunięcie innych ancillary = brak EXIF, tekstów, timestampa czyli czysta grafika
def anonymize_png(chunks, out_path):
    color_type = None
    modified_IHDR = None

    for t, d, *_ in chunks:
        if t == b'IHDR':
            # Rozpakuj IHDR (13 bajtów)
            w, h, bitd, colort, compm, filterm, interlacem = struct.unpack('>IIBBBBB', d)
            color_type = colort
            # Ustaw compression_method i filter_method na 0
            compm = 0
            filterm = 0
            # Spakuj z powrotem zmodyfikowany IHDR
            modified_IHDR = struct.pack('>IIBBBBB', w, h, bitd, colort, compm, filterm, interlacem)
            break
    if color_type is None:
        raise ValueError('IHDR chunk not found – cannot determine color_type')

    combined_idat_data = b''

    with open(out_path, 'wb') as o:
        o.write(PngSignature)
        for t, d, length, *_ in chunks:
            if color_type != 3 and t == b'PLTE':
                continue
            if t == b'IDAT':
                combined_idat_data += d
                continue
            if t == b'IHDR':
                # Zapisz zmodyfikowany IHDR zamiast oryginalnego
                o.write(struct.pack('>I', len(modified_IHDR)))
                o.write(b'IHDR')
                o.write(modified_IHDR)
                crc = zlib.crc32(modified_IHDR, zlib.crc32(b'IHDR'))
                o.write(struct.pack('>I', crc))
                continue
            if t == b'IEND':
                # Zapisz połączony chunk IDAT przed IEND
                if combined_idat_data:
                    combined_idat_data = zlib.decompress(combined_idat_data)
                    combined_idat_data = zlib.compress(combined_idat_data)
                    o.write(struct.pack('>I', len(combined_idat_data)))
                    o.write(b'IDAT')
                    o.write(combined_idat_data)
                    crc = zlib.crc32(combined_idat_data, zlib.crc32(b'IDAT'))
                    o.write(struct.pack('>I', crc))
                # Teraz zapisz IEND
                o.write(struct.pack('>I', length))
                o.write(t)
                o.write(d)
                o.write(struct.pack('>I', zlib.crc32(d, zlib.crc32(t))))
            elif t != b'IDAT':
                o.write(struct.pack('>I', length))
                o.write(t)
                o.write(d)
                o.write(struct.pack('>I', zlib.crc32(d, zlib.crc32(t))))
    print(f'Saved anonymized PNG → {out_path}')


#4 wizualizacja widma FFT w skali logarytmicznej - rozkłada obraz na składowe częstotliwości przestrzennej
#niskie częstotliwości to duże plamy koloru, wysokie to drobne detale/szum
def fourier(img):

    gray = img[...,:3].mean(axis=2)   #konwersja do luminancji
    F    = np.fft.fft2(gray)

    #odwracamy transformatę i sprawdzamy MSE
    recon = np.fft.ifft2(F).real     #IFFT zwraca złożone i bierzemy .real
    mse   = np.mean((gray - recon) ** 2)  #porównanie z oryginalną luminancją
    print(f"[FFT-check] MSE between gray and IFFT(gray): {mse:.6e}")
    Fsh  = np.fft.fftshift(F)    #centralizujemy 0Hz
    mag  = 20 * np.log(np.abs(Fsh) + 1)     #skala log + uniknięcie log(0)

    plt.figure(figsize=(6, 6))
    plt.imshow(mag, cmap='gray')
    plt.title('FFT spectrum (log scale)')
    plt.axis('off')
    plt.show()

if __name__ == '__main__':
    file_path       = 'odszyfrowany_decompressed.png'
    file_path_save  = 'behind_iend.png'
    file_anon       = 'anon.png'

    #parsowanie
    crit, anc, tail = readPNG(file_path)
    printChunks(anc)
    printChunks(crit)
    print(f'Bytes behind IEND: {tail}\n')

    _, IHDR_data, *_ = crit[0]   #IHDR to pierwszy critical
    IDAT_data = b''.join(d for t, d, *_ in crit if t == b'IDAT')
    img = decompressIDAT(IHDR_data, IDAT_data)

    #dopisujemy marker po IEND
    
    appendDataBehindIEND(file_path, file_path_save, b'Jestem za IEND')

    crit, anc, tail = readPNG(file_path_save)
    print('\n=== Po dopisaniu danych za IEND ===')
    printChunks(anc)
    printChunks(crit)
    print(f'Bytes behind IEND: {tail}\n')

    #anonimizacja
    anonymize_png(crit, file_anon)

    crit, anc, tail = readPNG(file_anon)
    print('\n=== Po anonimizacji ===')
    printChunks(anc)
    printChunks(crit)
    print(f'Bytes behind IEND: {tail}\n')

    #dekopmresacja

    #FFT
    fourier(img)

    plt.imshow(img)
    plt.title('Decoded PNG')
    plt.axis('off')
    plt.show()