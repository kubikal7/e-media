import struct
import zlib

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

def remove_chunk(png_path, chunk_type_to_remove, out_path):
    chunks = read_chunks(png_path)
    chunk_type_to_remove = chunk_type_to_remove.encode('ascii') if isinstance(chunk_type_to_remove, str) else chunk_type_to_remove

    new_chunks = [c for c in chunks if c[0] != chunk_type_to_remove]

    with open(out_path, 'wb') as o:
        o.write(PngSignature)
        for t, d, length, crc in new_chunks:
            o.write(struct.pack('>I', length))
            o.write(t)
            o.write(d)
            o.write(crc)

    print(f"Chunk {chunk_type_to_remove.decode('ascii')} removed and saved to {out_path}")

remove_chunk('anon.png', 'IEND', 'test.png')
