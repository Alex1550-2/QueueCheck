"""Функция для логирования и
scheduler удаления 'лишних' файлов"""
import datetime
import json
import os

LOG_FILE_NAME = "Logs/log_file.txt"
LOG_FILE_MAX_STRING = 100  # макс кол-во строк в логе

REPORTS_FOLDER = "Report/"
REPORTS_AMOUNT = 25  # макс кол-во файлов в папке Report


def step_logging(new_logs_line: str):
    """Логирование шедулеров:
    записываем в лог новую строку вида
    дата/время >>> идентификатор шедулера"""
    now = datetime.datetime.now()  # команда now - текущее дата/время
    new_logs_line = now.strftime("%Y:%m:%d %H:%M:%S") + " >>> " + new_logs_line

    try:
        # Открытие файла в режиме дозаписи:
        log_txt = open(LOG_FILE_NAME, "a", encoding="utf-8")
    except FileNotFoundError:
        # Обработка ошибки, возникающей в том случае, если файл не найден
        log_txt = open(LOG_FILE_NAME, "w", encoding="utf-8")
    else:
        # После успешного открытия, записываем строку в лог
        log_txt.write(new_logs_line + "\n")
        log_txt.close()


def get_files(path):
    """Сбор файлов в папке
    обратно времени создания - reverse=True"""
    files = []

    directory = os.listdir(path)
    directory.sort(reverse=True)

    for file in directory:
        if file.endswith(".txt"):
            files.append(file)
    return files


def delete_old_files(path, files):
    """Оставляет последние n (REPORTS_AMOUNT) файлов, остальные удаляет"""
    max_files = REPORTS_AMOUNT
    if len(files) < max_files:
        return
    i = 0
    for log_string in files:
        i += 1
        if i > max_files:
            os.remove(os.path.join(path, log_string))


def partial_clean_log_file(log_file_name, string_amount: int):
    """чтобы лог не был слишком большой,
    оставляем последние string_amount строчек"""

    # считываем текущий лог и укорачиваем его:
    with open(log_file_name, "r", encoding="utf-8") as log_file:
        log_text = log_file.readlines()
        log_text = log_text[string_amount:]

    # перезаписываем лог-файл:
    with open(log_file_name, "w", encoding="utf-8") as log_file:
        log_file.writelines(log_text)


def remove_report_files():
    """основная функция удаления 'лишних' файлов,
    которую запускаем через scheduler"""

    # удаляем старые файлы:
    path = REPORTS_FOLDER
    files = get_files(path)
    delete_old_files(path, files)

    # укорачиваем лог-файл:
    partial_clean_log_file(LOG_FILE_NAME, LOG_FILE_MAX_STRING)

    # записываем в лог отчётную строку:
    step_logging("'лишние' отчётные файлы удалены")


def create_file_name(part_file_name: str) -> str:
    """Функция создаёт имя файла на основе текущих дата/время"""
    now = datetime.datetime.now()  # команда now - текущее дата/время
    new_file_name = (
        REPORTS_FOLDER + now.strftime("%Y_%m_%d_%H_%M_%S") + part_file_name + ".txt"
    )
    return new_file_name


def save_json_file(message_text: json, file_name: str):
    """сохраняем 'сырой' json в виде txt-файла"""
    json_obj = json.loads(message_text)

    with open(file_name, "a", encoding="utf-8") as file:
        json.dump(json_obj, file, indent=3)

        file.write("\n")
