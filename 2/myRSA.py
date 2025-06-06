import sympy
from math import gcd

def generate_large_prime(bits):
    start = 2**(bits - 1)
    end = 2**bits - 1
    return sympy.randprime(start, end)

def generate_rsa_keypair(bits=2048):
    half_bits = bits // 2
    e = 834781

    while True:
        p = generate_large_prime(half_bits)
        q = generate_large_prime(half_bits)
        if p == q:
            continue

        n = p * q
        phi = (p - 1) * (q - 1)

        if gcd(e, phi) == 1:
            break 

    d = pow(e, -1, phi)

    return {
        "public_key": (n, e),
        "private_key": (n, d),
        "p": p,
        "q": q
    }

def encrypt(message_bytes, e, n):
    m = int.from_bytes(message_bytes, byteorder='big')
    #print(len(message_bytes))
    if m > n:
        raise ValueError("Message is too long to encypt by one block")
    return pow(m, e, n)

def decrypt(cipher_block, d, n):
    cipher_int = int.from_bytes(cipher_block, byteorder='big')
    return pow(cipher_int, d, n)

def ciphertext_to_block(cipher_int, key_length_bits):
    key_length_bytes = (key_length_bits + 7) // 8
    block = cipher_int.to_bytes(key_length_bytes, byteorder='big')
    return block
