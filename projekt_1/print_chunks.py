import zlib
import struct
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

def printpCAL(data):
    pos = 0

    # 1. calibration name (null-terminated)
    cal_name_end = data.find(b'\x00', pos)
    cal_name = data[pos:cal_name_end].decode('latin-1', errors='replace')
    pos = cal_name_end + 1

    # 2. X0, X1 (8 bytes)
    x0, x1 = struct.unpack('>ii', data[pos:pos+8])
    pos += 8

    # 3. equation type and number of parameters (2 bytes)
    equation_type, num_params = struct.unpack('BB', data[pos:pos+2])
    pos += 2

    # 4. unit name (null-terminated)
    unit_end = data.find(b'\x00', pos)
    unit = data[pos:unit_end].decode('latin-1', errors='replace')
    pos = unit_end + 1

    params = []
    for i in range(num_params):
        if i < num_params - 1:
            param_end = data.find(b'\x00', pos)
            if param_end == -1:
                print(f"pCAL: [Warning] Null terminator missing for parameter {i+1}")
                param_end = len(data) 
        else:
            param_end = len(data)

        param_str = data[pos:param_end].decode('latin-1', errors='replace')
        try:
            param = float(param_str)
        except ValueError:
            param = param_str
        params.append(param)
        pos = param_end + 1

    print(f"  Name: {cal_name}")
    print(f"  X0: {x0}, X1: {x1}")
    print(f"  Equation type: {equation_type}")
    print(f"  Number of parameters: {num_params}")
    print(f"  Unit name: {unit}")
    print(f"  Parameters: {params}")

    
    # Print equation if we have enough parameters
    if equation_type == 0 and len(params) >= 2:
        print(f"  Equation: y = {params[0]} * x + {params[1]}")
    elif equation_type == 1 and len(params) >= 3:
        print(f"  Equation: y = {params[0]} * exp({params[1]} * x) + {params[2]}")
    elif equation_type == 2 and len(params) >= 3:
        print(f"  Equation: y = {params[0]} / ({params[1]} * x) + {params[2]}")


def printChunk(chunk):
    typ = chunk[0].decode()
    d = chunk[1]
    length = chunk[2]
    offset = chunk[3]
    print(f"{typ} length: {length}, offset: {offset}")
    if typ == 'IDAT':
        pass
    elif typ == 'IHDR':
        w, h, bitd, colort, compm, filterm, interlacem = struct.unpack('>IIBBBBB', d)
        print(f"  width={w}, height={h}, bit_depth={bitd}, color_type={colort}, compression={compm}, filter={filterm}, interlace={interlacem}")
    elif typ == 'gAMA':
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
        if len(d) == 6:
            r, g, b = struct.unpack('>HHH', d)
            print(f"  background RGB (16-bit) = ({r}, {g}, {b})")
        else:
            print(f"bKGD raw data (length={length})")
    elif typ == 'pHYs':
        x_ppu, y_ppu, unit = struct.unpack('>IIB', d)
        unit_descr = 'meter' if unit == 1 else 'unknown'
        print(f"  x_ppu={x_ppu}")
        print(f"  y_ppu={y_ppu}")
        print(f"  unit={unit} ({unit_descr})")
    elif typ == 'tEXt':
        try:
            key, val = d.split(b'\x00', 1)
            print(f"  key='{key.decode()}', text='{val.decode(errors='replace')}'")
        except Exception:
            print(f"tEXt raw data")
    elif typ == 'zTXt':
        try:
            key, rest = d.split(b'\x00', 1)
            comp_method = rest[0]
            compressed_text = rest[1:]
            text = zlib.decompress(compressed_text).decode(errors='replace') if comp_method == 0 else '<unsupported compression>'
            print(f"  key='{key.decode()}', text='{text}'")
        except Exception:
            print(f"zTXt raw data")
    elif typ == 'IEND':
        pass
    else:
        print(f"Unknown chunk type {typ}, raw data length {length}")