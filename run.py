import subprocess
import os
import sys
import zlib
import logging
import argparse
import struct


parser = argparse.ArgumentParser(description='A tutorial of argparse!')
parser.add_argument("-d", default='261002912', help="J-Link device number")
parser.add_argument("-c", default='tags.csv', help="CSV-file name with EANs info")
args = parser.parse_args()
device_num = args.d
csv_file_name = args.c

HW_TYPE = 0
logging.basicConfig(filename='log.log',
                    level=logging.DEBUG,
                    filemode='a',
                    format='%(asctime)s ; %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
base_path = os.path.dirname(os.path.abspath(__file__))
DISPLAY_TYPES = {0: 'NONE',
                 1: 'HINK_E0154_BW_152_152',
                 2: 'HINK_E0154_BWR_152_152',
                 3: 'HINK_E0154_BWY_152_152',
                 4: 'HINK_E029_BW_296_128',
                 5: 'HINK_E029_BWR_296_128',
                 6: 'HINK_E029_BWY_296_128',
                 7: 'HINK_E0266_BW_296_152',
                 8: 'HINK_E0266_BWR_296_152',
                 9: 'HINK_E0266_BWY_296_152',
                 10: 'HINK_E042_BW_400_300',
                 11: 'HINK_E042_BWR_400_300',
                 12: 'HINK_E042_BWY_400_300',
                 13: 'HINK_E0584_BW_768_256',
                 14: 'HINK_E0584_BWR_768_256',
                 15: 'HINK_E0584_BWY_768_256',
                 16: 'HINK_E075_BW_640_384',
                 17: 'HINK_E075_BWR_640_384',
                 18: 'HINK_E075_BWY_640_384',
                 }


def upgrade_esl_firmware(num_device):
    num_device = check_device_num(num_device)
    file_extension = get_file_extension_by_os()
    commands = [f"nrfjprog{file_extension} -f NRF52 -s {num_device} -e",
                f"nrfjprog{file_extension} -f NRF52 -s {num_device} --program esl.hex",
                f"nrfjprog{file_extension} -f NRF52 -s {num_device} --program mbr.hex",
                f"nrfjprog{file_extension} -f NRF52 -s {num_device} --program bootloader_esl.hex",
                f"nrfjprog{file_extension} -f NRF52 -s {num_device} --program esl_settings.hex"
                ]
    print('ИНИЦИАЦИЯ ОБНОВЛЕНИЯ ПРОШИВКИ...')
    for stdin in commands:
        run_command(stdin)


def get_esl_mac_address():
    print('ИНИЦИАЦИЯ ПОЛУЧЕНИЯ MAC ЦЕННИКА...')
    file_extension = get_file_extension_by_os()
    command = f"nrfjprog{file_extension} --memrd 0x100000A4 --n 8"
    print(f"Выполнение команды: {command}")
    run_command_result = run_command(command)
    mac_address = get_mac_substring(run_command_result)
    return mac_address


def update_display_data(checksum='', hw_type=0, display_type=0, ean_1='', ean_2=''):
    file_extension = get_file_extension_by_os()
    commands = [f"nrfjprog{file_extension} --memwr 0x10001080 --val {checksum}",
                f"nrfjprog{file_extension} --memwr 0x10001084 --val {hw_type}",
                f"nrfjprog{file_extension} --memwr 0x10001088 --val {display_type}",
                f"nrfjprog{file_extension} --memwr 0x1000108C --val {ean_1}",
                f"nrfjprog{file_extension} --memwr 0x10001090 --val {ean_2}"]
    print('ИНИЦИАЦИЯ ОБНОВЛЕНИЯ ДАННЫХ НА ЦЕННИКЕ...')
    for stdin in commands:
        run_command(stdin)


def check_device_num(device_num):
    if not device_num:
        input(f"Не указан s/n J-Link устройства. Укажите корректный номер!. Нажмите Enter для продолжения...")
        sys.exit()
    else:
        return device_num


def get_file_extension_by_os():
    if os.name == 'nt':
        file_extension = '.exe'
    else:
        file_extension = ''
    return file_extension


def read_file(file_name):
    try:
        with open(file_name, 'r') as file:
            file_lines = file.readlines()
        return file_lines
    except FileNotFoundError:
        input(f"Указанный файл '{file_name}' не найден. "
              f"Укажите корректный csv-файл со списком EAN! "
              f"Нажмите Enter для продолжения...")
        sys.exit()


def get_mac_substring(result_str):
    string_with_mac = result_str.decode('ascii')
    _, first_mac_part, second_mac_part, *_ = string_with_mac.split(' ')
    n1 = first_mac_part[0:2]
    n2 = first_mac_part[2:4]
    n3 = first_mac_part[4:6]
    n4 = first_mac_part[6:8]
    mac = f'{n1}:{n2}:{n3}:{n4}'
    return mac


def find_substring_in_csv(mac, csv_file):
    csv_file_lines = read_file(csv_file)
    for line in csv_file_lines:
        if line.find(mac) != -1:
            return line
    input(f"Подстрока с mac-адресом '{mac}' не найдена в файле '{csv_file}'"
          f" Нажмите Enter для продолжения...")
    sys.exit()


def get_esl_display_params(substring):
    ean, size, color_type, screen_type, date_manufactured, type_, mac, version, firmware, width, height, screen_code, battery_type, color_index = substring.split(',')
    if width < height:
        width, height = height, width
    display_params = {'ean': ean,
                      'size': size,
                      'color_type': color_type,
                      'screen_type': screen_type,
                      'date_manufactured': date_manufactured,
                      'type': type_,
                      'mac': mac,
                      'version': version,
                      'firmware': firmware,
                      'width': width,
                      'height': height,
                      'screen_code': screen_code,
                      'battery_type': battery_type,
                      'color_index': color_index
                      }
    return display_params


def get_display_num(color_type, wight, height):
    for type_num in list(DISPLAY_TYPES.keys())[1:]:
        display_name, display_diagonal, display_color_type, display_wight, \
            display_height = DISPLAY_TYPES[type_num].split('_')
        if color_type.upper() == display_color_type.upper() \
                and display_wight == wight \
                and display_height == height:
            return int(type_num)
    error = f'Номер типа дисплея не найден в списке по cледующим параметрам: '\
        f"color_type->'{color_type}' wight->'{wight}' height->'{height}'! " \
        f"Нажмите Enter для продолжения..."
    input(error)
    sys.exit()


def get_ean_hex(num):
    full_hex_num = hex(int(num))
    hex_str = {'hex_full': full_hex_num,
               'hex_part1': '0x' + full_hex_num[-8:],
               'hex_part2': full_hex_num[:-8]}
    return hex_str


def check_command_success(command_stdout, command_err):
    if command_err:
        error = f"ERROR: Команда выполнена некорректно! " \
            f"Нажмите Enter для продолжения... " \
            f"STDERR: {str(command_err)}"
        input(error)
        sys.exit()
    else:
        print(f"Успешное выполнение команды. STDOUT: {str(command_stdout)}")
        return command_stdout


def run_command(command):
    print(f"Выполнение команды: {command}")
    proccess = subprocess.Popen(command, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    command_stdout, command_err = proccess.communicate()
    return check_command_success(command_stdout, command_err)


def hw_type_to_bytestr(num):
    hw_type_bytestr = struct.pack("<h", num)
    return hw_type_bytestr


def display_num_to_bytestr(display_num):
    display_num_bytestr = struct.pack("<h", display_num)
    return display_num_bytestr


def ean_hex_to_bytestr(ean_hex):
    res = b''
    for i in range(0, len(ean_hex), 2):
        res += int(ean_hex[i:i + 2], 16).to_bytes(1, byteorder='big')
    return res


def string_generate(ean_hex, hw_type, display_num):
    hw_type_bytestr = hw_type_to_bytestr(hw_type)
    display_num_bytestr = display_num_to_bytestr(display_num)
    ean_hex_bytestr = ean_hex_to_bytestr(ean_hex)
    return hw_type_bytestr + display_num_bytestr + ean_hex_bytestr


def generate_crc32(hex_string):
    crc32_out = hex(zlib.crc32(hex_string))
    return str(crc32_out)


def get_clean_hex_ean(hex_ean_str):
    ean_hex = hex_ean_str.replace('x', '')
    new_hex_ean = f'{ean_hex[10:12]}{ean_hex[8:10]}{ean_hex[6:8]}' \
        f'{ean_hex[4:6]}{ean_hex[2:4]}{ean_hex[0:2]}'
    return new_hex_ean


def main():
    upgrade_esl_firmware(device_num)
    esl_mac = get_esl_mac_address()
    esl_data = find_substring_in_csv(esl_mac, csv_file_name)
    esl_params = get_esl_display_params(esl_data)
    ean_hex = get_ean_hex(esl_params['ean'])
    clean_hex_ean = get_clean_hex_ean(ean_hex['hex_full'])
    display_num = get_display_num(esl_params['color_type'],
                                  esl_params['width'],
                                  esl_params['height'])
    hex_string = string_generate(clean_hex_ean,
                                 hw_type=HW_TYPE,
                                 display_num=display_num)
    check_sum = generate_crc32(hex_string)
    update_display_data(checksum=check_sum,
                        hw_type=HW_TYPE,
                        display_type=display_num,
                        ean_1=ean_hex['hex_part1'],
                        ean_2=ean_hex['hex_part2'])
    print(f"Подстрока для поиска Мак-адреса: {esl_mac} \n"
          f"EAN: {esl_params['ean']} \n"
          f"EAN HEX: {ean_hex['hex_full']} \n"
          f"color_type: {esl_params['color_type']} \n"
          f"screen_type: {esl_params['screen_type']} \n"
          f"width: {esl_params['width']} \n"
          f"height: {esl_params['height']} \n"
          f"mac: {esl_params['mac']} \n"
          f"Номер типа дисплея: {display_num} \n"
          f"new_hex_ean: {clean_hex_ean} \n"
          f"Найденая строка: {esl_data} \n"
          f"Checksum: {check_sum} \n"
          f"Hex_string: {hex_string} \n"
          )
    print('УСПЕШНАЯ ПЕРЕПРОШИВКА И ЗАПИСЬ EAN!')
    logging.info(f"{esl_params['ean']} ; "
                 f"{DISPLAY_TYPES[display_num]} ; "
                 f"{esl_params['mac']}")
    input("Press Enter to continue...")
    sys.exit()


if __name__ == '__main__':
    main()
