"""Функци для логирования"""
import logging

LOG_FILE_NAME = "Logs/log.log"
LOG_FILE_MAX_STRING = 110  # макс кол-во строк в логе

# уровень штатного логирования поднял до WARNING, чтобы INFO не засоряло лог-файл,
# поэтому пришлось поднимать уровень своих информационных сообщений до WARNING
# пример: logging.warning(f"очистка лог-файла {LOG_FILE_NAME} выполнена")
logging.basicConfig(
    level=logging.WARNING,
    filename=LOG_FILE_NAME,
    filemode="a",
    format="%(asctime)s %(levelname)s %(message)s",
)


def get_log(log_file_name: str) -> list:
    """получаем list с содержимым лог-файла"""
    with open(log_file_name, "r", encoding="utf-8") as log_file:
        log_text = log_file.readlines()

    return log_text


def write_log(log_file_name: str, log_text: list):
    """укорачиваем и записываем лог обратно в файл"""
    log_text = log_text[-LOG_FILE_MAX_STRING:]

    with open(log_file_name, "w", encoding="utf-8") as log_file:
        log_file.writelines(log_text)


def partial_clean_log_file():
    """чтобы лог не был слишком большой,
    оставляем последние string_amount строчек"""
    log_text = get_log(LOG_FILE_NAME)
    write_log(LOG_FILE_NAME, log_text)
    logging.warning(f"очистка лог-файла {LOG_FILE_NAME} выполнена")
