#add arbitrary data just after the last mandatory IEND chunk in the PNG file (data – bytes we want to append after IEND)
def appendDataBehindIEND(file_path_read: str, file_path_save: str, data: bytes):

    with open(file_path_read, 'rb') as f:
        content = f.read()

    #1 PNG signature validation - a valid PNG starts with an 8-byte signature (if there is no header, the file is not PNG or is corrupted)
    # 89 50 4E 47 0D 0A 1A 0A
    if content[:8] != b'\x89PNG\r\n\x1a\n':
        raise Exception("To nie jest poprawny plik PNG")

    #2 searching for the IEND chunk, we need to find the mandatory chunk (end of the PNG file)
    #rfind finds the last occurrence, protects against false positives in image data (e.g. the letters "IEND" in compressed IDAT)
    if b'IEND' not in content:
        raise Exception("Brak chunku IEND w pliku PNG")

    iend_index = content.rfind(b'IEND')

    #chunk has the structure [4B length][4B 'IEND'][0B data][4B CRC]
    #3 end of chunk calculation IEND - end of chunk = offset of 'I' character + 4B type + 4B CRC = +8 bytes
    end_of_iend = iend_index + 8

    #4 original content to (total) IEND chunk and add your data.
    new_content = content[:end_of_iend] + data
    with open(file_path_save, 'wb') as f:
        f.write(new_content)


    print(f"Added {len(data)} bytes behind IEND in file: {file_path_save}")
