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

def modify_ihdr_and_save(png_path, new_ihdr_params, out_path='test.png'):
    chunks = read_chunks(png_path)

    # Modify IHDR
    new_chunks = []
    for t, d, length, _ in chunks:
        if t == b'IHDR':
            # Unpack original IHDR
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack('>IIBBBBB', d)
            # Apply modifications (if provided)
            width = new_ihdr_params.get('width', width)
            height = new_ihdr_params.get('height', height)
            bit_depth = new_ihdr_params.get('bit_depth', bit_depth)
            color_type = new_ihdr_params.get('color_type', color_type)
            compression = new_ihdr_params.get('compression', compression)
            filter_method = new_ihdr_params.get('filter', filter_method)
            interlace = new_ihdr_params.get('interlace', interlace)
            new_data = struct.pack('>IIBBBBB', width, height, bit_depth, color_type, compression, filter_method, interlace)
            crc = struct.pack('>I', zlib.crc32(new_data, zlib.crc32(b'IHDR')))
            new_chunks.append((b'IHDR', new_data, len(new_data), crc))
        else:
            crc = struct.pack('>I', zlib.crc32(d, zlib.crc32(t)))
            new_chunks.append((t, d, length, crc))

    # Write new PNG
    with open(out_path, 'wb') as o:
        o.write(PngSignature)
        for t, d, length, crc in new_chunks:
            o.write(struct.pack('>I', length))
            o.write(t)
            o.write(d)
            o.write(crc)
    print(f"Modified PNG saved as: {out_path}")

modify_ihdr_and_save('plik11.png', {
    'interlace': 10
})
