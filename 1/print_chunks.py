import zlib
import struct
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

# dekoduje i wypisuje zawartość chunka pCAL (pixel calibration)
#     chunk jest opcjonalny i opisuje sposób przeliczania wartości
#     pikseli (np temperatury) na jednostki fizyczne
#
#     Struktura(RFC 2083):
#       <name>\0 – ASCII, nazwa kalibracji
#       X0, X1 – dwa int32 określające zakres osi X
#       eq_type, n_par – typ równania (0-4) i liczba parametrów
#       <unit>\0 – ASCII, nazwa jednostki
#       <param_1>\0… – n_par parametrów (ASCII)

def printpCAL(data):
    pos = 0

    #1 nazwa kalibracji (null-terminated ASCII)
    cal_name_end = data.find(b'\x00', pos)
    cal_name = data[pos:cal_name_end].decode('latin-1', errors='replace')
    pos = cal_name_end + 1  #przeskakujemy nullbyte
    x0, x1 = struct.unpack('>ii', data[pos:pos+8])
    pos += 8
    equation_type, num_params = struct.unpack('BB', data[pos:pos+2])
    pos += 2

    #2 jednostka fizyczna (null terminated)
    unit_end = data.find(b'\x00', pos)
    unit = data[pos:unit_end].decode('latin-1', errors='replace')
    pos = unit_end + 1

    #3 kolejne parametry (ASCII)
    params = []
    for i in range(num_params):
        #dla wszystkich oprócz ostatniego szukamy kolejnego nullbyte
        if i < num_params - 1:
            param_end = data.find(b'\x00', pos)
            if param_end == -1:         #uszkodzony plik
                print(f"pCAL: [Warning] Null terminator missing for parameter {i+1}")
                param_end = len(data)
        else:
            param_end = len(data)     #ostatni parametr do końca

        param_str = data[pos:param_end].decode('latin-1', errors='replace')
        #próbujemy sparsowac liczbowo jak się nie da zostawiamy string
        try:
            param = float(param_str)
        except ValueError:
            param = param_str
        params.append(param)
        pos = param_end + 1       #+1 aby pominac nullbyte

    print(f"  Name: {cal_name}")
    print(f"  X0: {x0}, X1: {x1}")
    print(f"  Equation type: {equation_type}")
    print(f"  Number of parameters: {num_params}")
    print(f"  Unit name: {unit}")
    print(f"  Parameters: {params}")

    if equation_type == 0 and len(params) >= 2:
        print(f"  Equation: y = {params[0]} * x + {params[1]}")
    elif equation_type == 1 and len(params) >= 3:
        print(f"  Equation: y = {params[0]} * exp({params[1]} * x) + {params[2]}")
    elif equation_type == 2 and len(params) >= 3:
        print(f"  Equation: y = {params[0]} / ({params[1]} * x) + {params[2]}")


#4 pretty printer dla dowolnego chunka PNG wypisuje metadane pojedynczego chunka odczytanego w main.readPNG()
def printChunk(chunk):

    typ = chunk[0].decode()  #4 znakowy identyfikator (IHDR, IDAT, …)
    d = chunk[1]      #payload
    length = chunk[2]
    offset = chunk[3]

    print(f"{typ} length: {length}, offset: {offset}")

    #obowiązkowe critical chunks
    if typ == 'IDAT':
        return

    if typ == 'IHDR':
        w, h, bitd, colort, compm, filterm, interlacem = struct.unpack('>IIBBBBB', d)
        print(f"  width={w}, height={h}, bit_depth={bitd}, color_type={colort}, "
              f"compression={compm}, filter={filterm}, interlace={interlacem}")
        return
    
    if typ == 'PLTE':
        # PLTE to paleta kolorów: lista 3-bajtowych kolorów RGB
        n_colors = len(d) // 3
        for i in range(n_colors):
            r, g, b = d[i*3:i*3+3]
            print(f"    Color {i}: R={r} G={g} B={b}")
        return

    #wybrane anicllary chunks
    if typ == 'gAMA':
        gamma, = struct.unpack('>I', d)
        print(f"  gamma={gamma/100000.0}")

    elif typ == 'sBIT':
        print(f"  significant bits per channel = {list(d)}")

    elif typ == 'pCAL':
        printpCAL(d)

    elif typ == 'tIME':
        y, mo, day, h, mi, s = struct.unpack('>HBBBBB', d)
        print(f"  {y:04}-{mo:02}-{day:02} {h:02}:{mi:02}:{s:02}")

    elif typ == 'bKGD':
        #zależnie od color-type: 1, 2 lub 6 bajtów, najczesciej 6 (RGB-16-bit)
        if len(d) == 6:
            r, g, b = struct.unpack('>HHH', d)
            print(f"  background RGB (16-bit) = ({r}, {g}, {b})")
        else:
            print(f"  bKGD raw data (length={length})")

    elif typ == 'pHYs':
        x_ppu, y_ppu, unit = struct.unpack('>IIB', d)
        unit_descr = 'meter' if unit == 1 else 'unknown'
        print(f"  x_ppu={x_ppu}\n  y_ppu={y_ppu}\n  unit={unit} ({unit_descr})")

    elif typ == 'tEXt':
        #niekompresowany tekst: key\0value
        try:
            key, val = d.split(b'\x00', 1)
            print(f"  key='{key.decode()}', text='{val.decode(errors='replace')}'")
        except ValueError:
            print("  [Malformed tEXt] – raw dump suppressed")

    elif typ == 'zTXt':
        #tekst skompresowany zlib i trzeba rozpakować
        try:
            key, rest = d.split(b'\x00', 1)
            comp_method = rest[0]
            compressed_text = rest[1:]
            text = zlib.decompress(compressed_text).decode(errors='replace')
            print(f"  key='{key.decode()}', text='{text}'")
        except Exception:
            print("  zTXt raw data (parse error)")

    elif typ == 'IEND':
        #żadnych dodatkowych danych.
        pass

    else:
        print(f"  Unknown chunk type {typ}, raw data length {length}")