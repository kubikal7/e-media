#dodaje arbitralne dane tuż za ostatnim obowiązkowym chunkiem IEND w pliku PNG (data– bajty które chcemy dopisać za IEND)
def appendDataBehindIEND(file_path_read: str, file_path_save: str, data: bytes):

    with open(file_path_read, 'rb') as f:
        content = f.read()

    #1 walidacja podpisu PNG - prawidłowy PNG zaczyna się 8 bajtowym podpisem (jesli bez naglowka to plik nie PNG lub uszkodzony)
    # 89 50 4E 47 0D 0A 1A 0A
    if content[:8] != b'\x89PNG\r\n\x1a\n':
        raise Exception("To nie jest poprawny plik PNG")

    #2 wyszukanie chunka IEND, musimy odnaleźć bo obowiązkowy chunk (koniec pliku PNG)
    #rfind znajduje ostatnie wystąpienie,chroni przed fałszywymi trafieniami w danych obrazka (np litery "IEND" w skompresowanym IDAT)
    if b'IEND' not in content:
        raise Exception("Brak chunku IEND w pliku PNG")

    iend_index = content.rfind(b'IEND')

    #chunk ma strukture [4B length][4B 'IEND'][0B data][4B CRC]
    #3 obliczenie końca chunka IEND - koniec chunka = offset znaku 'I' + 4B typu + 4B CRC = +8 bajtow
    end_of_iend = iend_index + 8

    #4 oryginalną treść do (łącznie) chunka IEND i dokładamy swoje dane.
    new_content = content[:end_of_iend] + data
    with open(file_path_save, 'wb') as f:
        f.write(new_content)


    print(f"Added {len(data)} bytes behind IEND in file: {file_path_save}")
