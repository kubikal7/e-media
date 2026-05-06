import zlib
import struct
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image 

from decompress_IDAT import decompressIDAT   #decopression IDAT to RGBA
from print_chunks      import printChunk      #nice writting metadata
from append_data_behind_iend import appendDataBehindIEND  #add at the end

#1 constants specific to the PNG format
PngSignature: bytes = b'\x89PNG\r\n\x1a\n'   #8-byte PNG header
critical = {b'IHDR', b'PLTE', b'IDAT', b'IEND'}   #4 critical chunks according to RFC 2083

#2 PNG file parser manually reads the PNG structure and returns the broken chunks + bytes after IEND
def readPNG(file_path):

    critical_chunks  = []
    ancillary_chunks = []

    with open(file_path, 'rb') as f:
        #validation
        if f.read(len(PngSignature)) != PngSignature:
            raise Exception('Invalid PNG Signature')

        #reading one chunk
        def read_chunk(stream):
            #chunk = [4B length][4B type][payload][4B CRC]
            chunk_length, chunk_type = struct.unpack('>I4s', stream.read(8))
            chunk_data = stream.read(chunk_length)
            chunk_crc, = struct.unpack('>I', stream.read(4))

            # CRC integrity protection, we calculate zlib.crc32(type + data) and compare
            calc_crc = zlib.crc32(chunk_data, zlib.crc32(chunk_type))
            if chunk_crc != calc_crc:
                raise Exception('chunk checksum failed')
            return chunk_type, chunk_data, chunk_length, chunk_crc

        #loop in chunks
        offset = len(PngSignature)
        while True:
            t, d, length, crc = read_chunk(f)

            #the division into critical and ancillary facilitates subsequent anonymization
            if t in critical:
                critical_chunks.append((t, d, length, offset, crc))
            else:
                ancillary_chunks.append((t, d, length, offset, crc))

            offset += 4 + 4 + length + 4
            if t == b'IEND':
                break  #end of PNG specification, only hidden bytes left

        #IEND check (steganography)
        f.seek(0, 2)
        file_size        = f.tell()
        bytes_after_iend = file_size - offset  #ile śmieci po IEND

    return critical_chunks, ancillary_chunks, bytes_after_iend

def printChunks(chunks):
    for chunk in chunks:
        printChunk(chunk)

#3 anonymization = throwing away ancillary chunks + any palette creates a PNG copy keeping only the minimum chunks
#    if the image is paletted (color_type == 3), PLTE must be
#    removing other ancillaries = no EXIF, texts, timestamp, i.e. pure graphics
def anonymize_png(chunks, out_path):
    color_type = None
    modified_IHDR = None

    for t, d, *_ in chunks:
        if t == b'IHDR':
            # Unpack IHDR (13 bytes)
            w, h, bitd, colort, compm, filterm, interlacem = struct.unpack('>IIBBBBB', d)
            color_type = colort
            # Set compression_method and filter_method to 0
            compm = 0
            filterm = 0
            # Pack back the modified IHDR
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
                # Save the modified IHDR instead of the original one
                o.write(struct.pack('>I', len(modified_IHDR)))
                o.write(b'IHDR')
                o.write(modified_IHDR)
                crc = zlib.crc32(modified_IHDR, zlib.crc32(b'IHDR'))
                o.write(struct.pack('>I', crc))
                continue
            if t == b'IEND':
                # Save the concatenated IDAT chunk before IEND
                if combined_idat_data:
                    combined_idat_data = zlib.decompress(combined_idat_data)
                    combined_idat_data = zlib.compress(combined_idat_data)
                    o.write(struct.pack('>I', len(combined_idat_data)))
                    o.write(b'IDAT')
                    o.write(combined_idat_data)
                    crc = zlib.crc32(combined_idat_data, zlib.crc32(b'IDAT'))
                    o.write(struct.pack('>I', crc))
                # now save IEND
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


#4 visualization of the FFT spectrum on a logarithmic scale - decomposes the image into spatial frequency components
#low frequencies are large spots of color, high frequencies are fine details/noise
def fourier(img):

    gray = img[...,:3].mean(axis=2)   #conversion to luminance
    F    = np.fft.fft2(gray)

    #we invert the transform and check the MSE
    recon = np.fft.ifft2(F).real     #IFFT returns complex and we take .real
    mse   = np.mean((gray - recon) ** 2)  #comparison with the original luminance
    print(f"[FFT-check] MSE between gray and IFFT(gray): {mse:.6e}")
    Fsh  = np.fft.fftshift(F)    #centralizing 0Hz
    mag  = 20 * np.log(np.abs(Fsh) + 1)     #log scale + log(0) avoidance

    plt.figure(figsize=(6, 6))
    plt.imshow(mag, cmap='gray')
    plt.title('FFT spectrum (log scale)')
    plt.axis('off')
    plt.show()

if __name__ == '__main__':
    file_path       = 'plik8.png'
    file_path_save  = 'behind_iend.png'
    file_anon       = 'anon.png'

    #parsing
    crit, anc, tail = readPNG(file_path)
    printChunks(anc)
    printChunks(crit)
    print(f'Bytes behind IEND: {tail}\n')

    _, IHDR_data, *_ = crit[0]   #IHDR is first critical
    IDAT_data = b''.join(d for t, d, *_ in crit if t == b'IDAT')
    img = decompressIDAT(IHDR_data, IDAT_data)

    #adding a marker after IEND
    
    appendDataBehindIEND(file_path, file_path_save, b'I am behind IEND')

    crit, anc, tail = readPNG(file_path_save)
    print('\n=== After adding data after IEND ===')
    printChunks(anc)
    printChunks(crit)
    print(f'Bytes behind IEND: {tail}\n')

    #anonymization
    anonymize_png(crit, file_anon)

    crit, anc, tail = readPNG(file_anon)
    print('\n=== After anonymization ===')
    printChunks(anc)
    printChunks(crit)
    print(f'Bytes behind IEND: {tail}\n')

    #decompression

    #FFT
    fourier(img)

    plt.imshow(img)
    plt.title('Decoded PNG')
    plt.axis('off')
    plt.show()