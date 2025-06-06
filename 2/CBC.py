import myRSA
import struct
import zlib
import os
from Crypto.PublicKey import RSA

def xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))

def encrypt_IDAT_chunks_after_decompressed(crit_chunks, e, n, choise):
    print("\nENCRYPT CBC:")
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

    initial_iv = os.urandom(max_data_size)
    prev_cipher_block = initial_iv

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
            length_byte = len(block).to_bytes(1, 'big')
            if len(block) < max_data_size:
                block = block.ljust(max_data_size, b'\x00')
            
            xored_block = xor_bytes(block, prev_cipher_block)
            if choise == 0:
                c_int = myRSA.encrypt(xored_block, e, n)
            else:
                key = RSA.construct((n, e))
                c_int = key._encrypt(int.from_bytes(xored_block, 'big'))
            c_bytes = c_int.to_bytes(key_size_bytes, byteorder='big')
            encrypted_line += length_byte + c_bytes

            prev_cipher_block = c_bytes

        encrypted_main = encrypted_line[:stride]
        encrypted_tail = encrypted_line[stride:]

        encrypted_blocks.append(encrypted_main)

        tail_blocks.append(len(encrypted_tail).to_bytes(1, 'big') + encrypted_tail)

    print()

    iv_encrypted_int = myRSA.encrypt(initial_iv, e, n)
    iv_encrypted_block = iv_encrypted_int.to_bytes(key_size_bytes, byteorder='big')

    encrypted_data_all = zlib.compress(b''.join(encrypted_blocks))
    tail_blocks_joined = b''.join(tail_blocks)
    tail = iv_encrypted_block+len(tail_blocks_joined).to_bytes(4, byteorder='big') + tail_blocks_joined

    encrypted_chunks_final = [encrypted_data_all]

    print(f"[ENCRYPT_IDAT_CBC] Tail data length: {len(tail)}")

    return encrypted_chunks_final, tail

def decrypt_IDAT_chunks_after_decompressed(crit_chunks, tail, d, n):
    print("\nDECRYPT CBC:")
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
    max_data_size = key_size_bytes - 1

    encrypted_idat_data = zlib.decompress(
        b''.join(d for (t, d, l, *_ ) in crit_chunks if t == b'IDAT')
    )

    if len(tail) >= key_size_bytes+4:
        tail_length = int.from_bytes(tail[key_size_bytes:key_size_bytes+4], byteorder='big')
        tail_data = tail[key_size_bytes+4:key_size_bytes+4 + tail_length]
    else:
        tail_data = tail

    tail_lines = []
    idx = 0
    for _ in range(height):
        if idx + 1 > len(tail_data):
            raise ValueError("Tail data truncated")
        tail_len = int.from_bytes(tail_data[idx:idx+1], 'big')
        idx += 1
        tail_bytes = tail_data[idx:idx+tail_len]
        if len(tail_bytes) != tail_len:
            raise ValueError("Tail data length mismatch")
        tail_lines.append(tail_bytes)
        idx += tail_len

    decrypted_lines = []

    initial_iv_encrypted_block = tail[:key_size_bytes]
    initial_iv_block = myRSA.decrypt(initial_iv_encrypted_block, d, n).to_bytes(max_data_size, byteorder='big')
    prev_cipher_block = initial_iv_block

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

            decrypted_int = myRSA.decrypt(c_bytes, d, n)

            decrypted_block = decrypted_int.to_bytes(max_data_size, byteorder='big')

            plain_block = xor_bytes(decrypted_block, prev_cipher_block)

            decrypted_line += plain_block[:block_len]

            prev_cipher_block = c_bytes

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