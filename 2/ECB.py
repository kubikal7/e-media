import RSA
import struct
import zlib

def encrypt_IDAT_chunks_compressed(crit_chunks, e, n):
    print("\nENCRYPT ECB COMPRESSED:")
    key_size_bytes = ((n.bit_length() + 7) // 8)
    max_data_size = key_size_bytes - 1

    all_idat_data = b''.join(d for (t, d, length, *_) in crit_chunks if t == b'IDAT')

    blocks = [all_idat_data[i:i+max_data_size] for i in range(0, len(all_idat_data), max_data_size)]

    encrypted_blocks = []
    for i, block in enumerate(blocks):
        print(f"\r{(i/len(blocks))*100:.2f}%", end='', flush=True)
        c_int = RSA.encrypt(block, e, n)
        c_bytes = c_int.to_bytes(key_size_bytes, byteorder='big')
        length_byte = len(block).to_bytes(1, 'big') 
        encrypted_blocks.append(length_byte + c_bytes)
    print()

    encrypted_data_all = b''.join(encrypted_blocks)

    idat_lengths = [length for (t, d, length, *_) in crit_chunks if t == b'IDAT']
    encrypted_chunks_final = []
    idx = 0
    for i, length in enumerate(idat_lengths):
        chunk_data = encrypted_data_all[idx:idx+length]
        encrypted_chunks_final.append(chunk_data)
        idx += length

    tail = encrypted_data_all[idx:]
    tail_len = len(tail)
    tail_final = tail_len.to_bytes(4, byteorder='big') + tail
    print(f"[ENCRYPT_IDAT] Tail data length: {len(tail_final)}")

    return encrypted_chunks_final, tail_final

def decrypt_IDAT_chunks_compressed(crit_chunks, tail_data, d, n):
    print("\nDECRYPT ECB COMPRESSED:")
    key_size_bytes = ((n.bit_length() + 7) // 8 ) + 1

    idat_chunks = [(t, d_chunk, length) for (t, d_chunk, length, *_ ) in crit_chunks if t == b'IDAT']
    encrypted_data = b''.join(d_chunk for _, d_chunk, _ in idat_chunks)

    if len(tail_data) >= 4:
        tail_length = int.from_bytes(tail_data[:4], byteorder='big')
        tail_encrypted = tail_data[4:4+tail_length]
        encrypted_data += tail_encrypted

    blocks = [encrypted_data[i:i+key_size_bytes] for i in range(0, len(encrypted_data), key_size_bytes)]

    decrypted_data = b''
    for i, block in enumerate(blocks):
        print(f"\r{(i/len(blocks))*100:.2f}%", end='', flush=True)
        length=block[0]
        block=block[1:]
        c_int = int.from_bytes(block, byteorder='big')
        m_bytes = RSA.decrypt(c_int, d, n)
        m_bytes = m_bytes.to_bytes(length, byteorder='big')
        decrypted_data += m_bytes
    print()

    decrypted_chunks = []
    idx = 0
    for _, _, length in idat_chunks:
        chunk_data = decrypted_data[idx:idx+length]
        decrypted_chunks.append(chunk_data)
        idx += length

    return decrypted_chunks

def encrypt_IDAT_chunks_after_decompressed(crit_chunks, e, n):
    print("\nENCRYPT ECB DECOMPRESSED:")
    ihdr_chunk = None
    for t, d, length, *_ in crit_chunks:
        if t == b'IHDR':
            ihdr_chunk = d
            break
    if ihdr_chunk is None:
        raise ValueError("IHDR chunk not found")

    width, height = struct.unpack(">II", ihdr_chunk[:8])

    key_size_bytes = ((n.bit_length() + 7) // 8)
    max_data_size = key_size_bytes - 1

    all_idat_data = b''.join(d for (t, d, length, *_) in crit_chunks if t == b'IDAT')

    decompressed = zlib.decompress(all_idat_data)

    bpp = 4
    stride = width * bpp + 1 

    encrypted_blocks = []
    tail_blocks = []

    for i in range(height):
        start = i * stride
        end = start + stride
        scanline = decompressed[start:end]
        print(f"\r{(end/(height*stride))*100:.2f}%", end='', flush=True)

        filter_byte = scanline[0]
        line_data = scanline[1:]

        blocks = [line_data[j:j+max_data_size] for j in range(0, len(line_data), max_data_size)]

        encrypted_line = b''
        encrypted_line += filter_byte.to_bytes(1, 'big')

        for block in blocks:
            c_int = RSA.encrypt(block, e, n)
            c_bytes = c_int.to_bytes(key_size_bytes, byteorder='big')
            length_byte = len(block).to_bytes(1, 'big')
            encrypted_line += length_byte + c_bytes

        encrypted_main = encrypted_line[:stride]
        encrypted_tail = encrypted_line[stride:]

        encrypted_blocks.append(encrypted_main)

        tail_blocks.append(len(encrypted_tail).to_bytes(2, 'big') + encrypted_tail)

    print()

    encrypted_data_all = zlib.compress(b''.join(encrypted_blocks))
    tail_blocks_joined = b''.join(tail_blocks)
    tail = len(tail_blocks_joined).to_bytes(4, byteorder='big') + tail_blocks_joined
    
    encrypted_chunks_final = [encrypted_data_all]

    print(f"[ENCRYPT_IDAT] Tail data length: {len(tail)}")

    return encrypted_chunks_final, tail

def decrypt_IDAT_chunks_after_decompressed(crit_chunks, tail, d, n):
    print("\nDECRYPT ECB DECOMPRESSED:")
    ihdr_chunk = None
    for t, d_chunk, length, *_ in crit_chunks:
        if t == b'IHDR':
            ihdr_chunk = d_chunk
            break
    if ihdr_chunk is None:
        raise ValueError("IHDR not found")

    width, height = struct.unpack(">II", ihdr_chunk[:8])
    bpp = 4  # RGBA
    stride = width * bpp + 1

    key_size_bytes = ((n.bit_length() + 7) // 8)
    encrypted_idat_data = zlib.decompress(
        b''.join(d for (t, d, l, *_ ) in crit_chunks if t == b'IDAT')
    )
    
    if len(tail) >= 4:
        tail_length = int.from_bytes(tail[:4], byteorder='big')
        tail_data = tail[4:4 + tail_length]
    else:
        tail_data = b''

    
    tail_lines = []
    idx = 0
    for _ in range(height):
        if idx + 2 > len(tail_data):
            raise ValueError("Tail data truncated")
        tail_len = int.from_bytes(tail_data[idx:idx+2], 'big')
        idx += 2
        tail_bytes = tail_data[idx:idx+tail_len]
        if len(tail_bytes) != tail_len:
            raise ValueError("Tail data length mismatch")
        tail_lines.append(tail_bytes)
        idx += tail_len

    decrypted_lines = []

    for i in range(height):
        start = i * stride
        end = start + stride
        encrypted_main = encrypted_idat_data[start:end]
        full_encrypted = encrypted_main + tail_lines[i]
        print(f"\r{(end/(height*stride))*100:.2f}%", end='', flush=True)

        pos = 0
        filter_byte = full_encrypted[pos]
        pos += 1

        decrypted_line = b''

        while pos < len(full_encrypted):
            block_len = full_encrypted[pos]
            pos += 1
            c_bytes = full_encrypted[pos:pos + key_size_bytes]
            pos += key_size_bytes
            c_int = int.from_bytes(c_bytes, 'big')
            m_bytes = RSA.decrypt(c_int, d, n)
            decrypted_block = m_bytes.to_bytes(block_len, byteorder='big')
            decrypted_line += decrypted_block

        full_line = bytes([filter_byte]) + decrypted_line
        decrypted_lines.append(full_line)

    print()

    recompressed = zlib.compress(b''.join(decrypted_lines))

    idat_lengths = [l for (t, d, l, *_ ) in crit_chunks if t == b'IDAT']
    decrypted_chunks = []
    idx = 0
    for length in idat_lengths:
        chunk_data = recompressed[idx:idx+length]
        decrypted_chunks.append(chunk_data)
        idx += length

    return decrypted_chunks
