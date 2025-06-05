import struct
import zlib
import os

PngSignature = b'\x89PNG\r\n\x1a\n'

def read_chunks(png_path):
    with open(png_path, 'rb') as f:
        signature = f.read(8)
        if signature != PngSignature:
            raise ValueError("Not a valid PNG file")
        chunks = []
        while True:
            length_bytes = f.read(4)
            if not length_bytes:
                break
            length = struct.unpack('>I', length_bytes)[0]
            chunk_type = f.read(4)
            data = f.read(length)
            crc = f.read(4)
            chunks.append((chunk_type, data, length, crc))
        return chunks

def insert_plte_chunk(png_path, out_path='output_with_plte.png'):
    chunks = read_chunks(png_path)

    new_chunks = []
    plte_inserted = False

    # Przygotuj losowe dane PLTE - np. 3 kolory RGB
    # Każdy kolor to 3 bajty (R, G, B)
    plte_data = os.urandom(9)  # 3 kolory * 3 bajty

    for t, d, length, crc in chunks:
        new_chunks.append((t, d, length, crc))
        if t == b'IHDR' and not plte_inserted:
            # Po IHDR dodajemy PLTE
            length_plte = len(plte_data)
            crc_plte = zlib.crc32(plte_data, zlib.crc32(b'PLTE'))
            crc_plte_bytes = struct.pack('>I', crc_plte)
            new_chunks.append((b'PLTE', plte_data, length_plte, crc_plte_bytes))
            plte_inserted = True

    with open(out_path, 'wb') as o:
        o.write(PngSignature)
        for t, d, length, crc in new_chunks:
            o.write(struct.pack('>I', length))
            o.write(t)
            o.write(d)
            o.write(crc)

    print(f"Saved PNG with PLTE chunk after IHDR → {out_path}")

insert_plte_chunk('plik8.png', 'plik9.png')
