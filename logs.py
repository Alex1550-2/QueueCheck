"""Функци для логирования"""
import datetime

LOG_FILE_NAME = "Logs/log_file.txt"
LOG_FILE_MAX_STRING = 100  # макс кол-во строк в логе


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


def clean_log_file():
    """основная функция удаления 'лишних' файлов,
    которую запускаем через scheduler"""

    # укорачиваем лог-файл:
    partial_clean_log_file(LOG_FILE_NAME, LOG_FILE_MAX_STRING)

    # записываем в лог отчётную строку:
    step_logging("'лишние' отчётные файлы удалены")
