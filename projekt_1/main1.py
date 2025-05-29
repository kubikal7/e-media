import zlib
import struct
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from decompress_IDAT import decompressIDAT
from print_chunks import printChunk
from append_data_behind_iend import appendDataBehindIEND

PngSignature = b'\x89PNG\r\n\x1a\n'
critical = {b'IHDR', b'PLTE', b'IDAT', b'IEND'}

def readPNG(file_path):
    critical_chunks = []
    ancillary_chunks = []
    with open(file_path, 'rb') as f:
        if f.read(len(PngSignature)) != PngSignature:
            raise Exception('Invalid PNG Signature')

        def read_chunk(f):
            chunk_length, chunk_type = struct.unpack('>I4s', f.read(8))
            chunk_data = f.read(chunk_length)
            chunk_crc, = struct.unpack('>I', f.read(4))
            calc_crc = zlib.crc32(chunk_data, zlib.crc32(chunk_type))
            if chunk_crc != calc_crc:
                raise Exception('chunk checksum failed')
            return chunk_type, chunk_data, chunk_length, chunk_crc

        offset = len(PngSignature)
        while True:
            t, d, length, crc = read_chunk(f)
            #print(f"offset={offset}   type={t.decode()}   length={length}")

            if t in critical:
                critical_chunks.append((t, d, length, offset, crc))
            else:
                ancillary_chunks.append((t, d, length, offset, crc))

            offset += 4 + 4 + length + 4
            if(t.decode() == 'IEND'):
                break
        
        f.seek(0, 2)
        file_size = f.tell()
        bytes_after_iend = file_size - offset  
    
    return critical_chunks, ancillary_chunks, bytes_after_iend

def printChunks(chunks):
    for chunk in chunks:
        printChunk(chunk)

def anonymize_png(chunks, out_path):
    color_type = None
    for t, d, length, offset, crc in chunks:
        if t == b'IHDR':
            w, h, bitd, colort, compm, filterm, interlacem = struct.unpack('>IIBBBBB', d)
            color_type = colort
    if color_type is None:
        raise ValueError("IHDR chunk not found – cannot determine color type")
    with open(out_path, 'wb') as o:
        o.write(PngSignature)
        for t, d, length, offset, crc in chunks:
            if color_type != 3 and t == b'PLTE':
                continue
            o.write(struct.pack('>I', length))
            o.write(t)
            o.write(d)
            o.write(struct.pack('>I', crc))
    print(f"Saved anonymized PNG → {out_path}")


def fourier(img):
    gray = img[...,:3].mean(axis=2)
    F    = np.fft.fft2(gray)
    Fsh  = np.fft.fftshift(F)
    mag  = 20 * np.log(np.abs(Fsh) + 1)

    plt.figure(figsize=(6,6))
    plt.imshow(mag, cmap='gray')
    plt.title('FFT spectrum (log scale)')
    plt.axis('off')
    plt.show()

file_path = 'plik8.png'
file_path_save = 'behind_iend.png'
file_anon = 'anon.png'

critical_chunks, ancillary_chunks, bytes_after_iend = readPNG(file_path)
printChunks(ancillary_chunks)
printChunks(critical_chunks)
print(f"Bytes behind IEND: {bytes_after_iend}")

appendDataBehindIEND(file_path, file_path_save, b'Jestem za IEND')

critical_chunks, ancillary_chunks, bytes_after_iend = readPNG(file_path_save)
print("\n\n")
printChunks(ancillary_chunks)
printChunks(critical_chunks)
print(f"Bytes behind IEND: {bytes_after_iend}")

anonymize_png(critical_chunks, file_anon)

critical_chunks, ancillary_chunks, bytes_after_iend = readPNG(file_anon)
print("\n\n")
printChunks(ancillary_chunks)
printChunks(critical_chunks)
print(f"Bytes behind IEND: {bytes_after_iend}")

_, IHDR_data, _, _, _ = critical_chunks[0]
IDAT_data = b''.join(d for t,d, length, offset, crc in critical_chunks if t == b'IDAT')
img = decompressIDAT(IHDR_data, IDAT_data)

plt.imshow(img)
plt.title('Decoded PNG')
plt.axis('off')
plt.show()


fourier(img)