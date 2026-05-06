import zlib
import struct

#constants specific to the PNG format
PngSignature: bytes = b'\x89PNG\r\n\x1a\n'   #8-byte PNG header
critical = {b'IHDR', b'PLTE', b'IDAT', b'IEND'}   #4 critical chunks according to RFC 2083

#the PNG file parser manually reads the PNG structure and returns the broken chunks + bytes after IEND
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

        #loops in chunks
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

        f.seek(offset)
        tail_bytes = f.read()


    return critical_chunks, ancillary_chunks, tail_bytes

def write_modified_png(output_path, crit_chunks, anc_chunks, encrypted_idat_chunks, tail_data):
    with open(output_path, 'wb') as f:
        f.write(PngSignature)

        for t, d, length, offset, crc in crit_chunks:
            if t == b'IHDR' or t == b'PLTE':
                f.write(struct.pack('>I', length))
                f.write(t)
                f.write(d)
                f.write(struct.pack('>I', crc))

        for t, d, length, offset, crc in crit_chunks:
            if t == b'IDAT' and len(encrypted_idat_chunks)>0:
                encrypted_data = encrypted_idat_chunks.pop(0)
                new_length = len(encrypted_data)
                new_crc = zlib.crc32(encrypted_data, zlib.crc32(t))
                f.write(struct.pack('>I', new_length))
                f.write(t)
                f.write(encrypted_data)
                f.write(struct.pack('>I', new_crc))

        for t, d, length, offset, crc in anc_chunks:
            f.write(struct.pack('>I', length))
            f.write(t)
            f.write(d)
            f.write(struct.pack('>I', crc))

        for t, d, length, offset, crc in crit_chunks:
            if t == b'IEND':
                f.write(struct.pack('>I', length))
                f.write(t)
                f.write(d)
                f.write(struct.pack('>I', crc))

        if tail_data:
            f.write(tail_data)