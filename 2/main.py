import PNG
import time
import ECB
import CBC
import os
import myRSA
from Crypto.PublicKey import RSA

if __name__ == "__main__":
    
    keys = myRSA.generate_rsa_keypair(2048)
    n, e = keys['public_key']
    _, d = keys['private_key']
    with open("rsa_keys.txt", "w") as f:
        f.write(f"{n}\n")
        f.write(f"{e}\n")
        f.write(f"{d}\n")
    '''
    with open("rsa_keys.txt", "r") as f:
        lines = f.readlines()
        n = int(lines[0].strip())
        e = int(lines[1].strip())
        d = int(lines[2].strip())

    
    '''
    '''
    # Tworzymy klucz
    key = RSA.construct((n, e))

    # Szyfrowanie "raw" przez bibliotekę (bez ręcznego pow())
    ciphertext = key._encrypt(int.from_bytes(b"1234567890123456", 'big'))
    cipher_bytes = ciphertext.to_bytes((key.size_in_bits() + 7) // 8, 'big')

    print("Długość zaszyfrowanych danych (bajty):", len(cipher_bytes))
    decrypted_int = key._decrypt(ciphertext)
    decrypted_bytes = decrypted_int.to_bytes((key.size_in_bits() + 7) // 8, 'big')
    print(f"Odszyfrowane dane: {decrypted_bytes.decode()}")
    print(f"Długość odszyfrowanych danych: {len(decrypted_bytes)} bajtów")
    '''
    file_path = 'plik11.png'

    crit, anc, tail = PNG.readPNG(file_path)
    start = time.time()
    encrypted_chunks, tail_encrypted = ECB.encrypt_IDAT_chunks_compressed(crit, e, n)
    end = time.time()
    print(f"Czas wykonania: {end-start:.4f} sekundy")
    PNG.write_modified_png("zaszyfrowany_compressed_ECB.png", crit, anc, encrypted_chunks, tail_encrypted+tail)

    crit, anc, tail = PNG.readPNG("zaszyfrowany_compressed_ECB.png")
    decrypted_chunks = ECB.decrypt_IDAT_chunks_compressed(crit, tail, d, n)
    end = time.time()
    print(f"Czas wykonania: {end-start:.4f} sekundy")
    PNG.write_modified_png("odszyfrowany_compressed_ECB.png", crit, anc, decrypted_chunks, b'')
    
    crit, anc, tail = PNG.readPNG(file_path)
    start = time.time()
    encrypted_chunks, tail_encrypted = ECB.encrypt_IDAT_chunks_after_decompressed(crit, e, n)
    end = time.time()
    print(f"Czas wykonania: {end-start:.4f} sekundy")
    PNG.write_modified_png("zaszyfrowany_decompressed_ECB.png", crit, anc, encrypted_chunks, tail_encrypted+tail)

    crit_chunks, anc_chunks, tail = PNG.readPNG("zaszyfrowany_decompressed_ECB.png")
    start = time.time()
    decrypted_idat_chunks = ECB.decrypt_IDAT_chunks_after_decompressed(crit_chunks, tail, d, n)
    end = time.time()
    print(f"Czas wykonania: {end-start:.4f} sekundy")
    PNG.write_modified_png("odszyfrowany_decompressed_ECB.png", crit_chunks, anc_chunks, decrypted_idat_chunks, b'')
    
    crit, anc, tail = PNG.readPNG(file_path)
    start = time.time()
    encrypted_idat_chunks, tail_encrypted = CBC.encrypt_IDAT_chunks_after_decompressed(crit, e, n, 1)
    end = time.time()
    print(f"Czas wykonania: {end-start:.4f} sekundy")
    PNG.write_modified_png("zaszyfrowany_decompressed_CBC.png", crit, anc, encrypted_idat_chunks, tail_encrypted+tail)

    crit, anc, tail = PNG.readPNG("zaszyfrowany_decompressed_CBC.png")
    start = time.time()
    encrypted_idat_chunks = CBC.decrypt_IDAT_chunks_after_decompressed(crit, tail, d, n)
    end = time.time()
    print(f"Czas wykonania: {end-start:.4f} sekundy")
    PNG.write_modified_png("odszyfrowany_decompressed_CBC.png", crit, anc, encrypted_idat_chunks, b'')
    