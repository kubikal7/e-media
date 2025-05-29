def appendDataBehindIEND(file_path_read, file_path_save, data: bytes):
    with open(file_path_read, 'rb') as f:
        content = f.read()

    if content[:8] != b'\x89PNG\r\n\x1a\n':
        raise Exception("To nie jest poprawny plik PNG")

    if b'IEND' not in content:
        raise Exception("Brak chunku IEND w pliku PNG")

    iend_index = content.rfind(b'IEND')
    end_of_iend = iend_index + 8

    new_content = content[:end_of_iend] + data

    with open(file_path_save, 'wb') as f:
        f.write(new_content)

    print(f"Added {len(data)} bytes behind IEND in file: {file_path_save}")
