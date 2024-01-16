""" пристальный контроль за некоторыми очередями
с сохранением текущих значений Messages
в текстовом файле """
import logging
import os
from datetime import datetime
from pathlib import Path

from check_value import replace_symbol

# список очередей, текущие значения Mesages которых
# сохраняем в соответствующем текстовом файле
save_some_queues_list = {
    "materials_masm-t1.urasmk.org",
    "materials_an-materials-receiver-test",
    "dz.task.create",
    "lj.task.create",
    "lk.task.create",
    "my.task.create",
    "ok.task.create",
    "vk.task.create",
    "yp.task.create",
    "yt.task.create",
    "image_analysis",
}


def check_queue_inside_list(queue_name: str) -> bool:
    """проверяем список очередей"""
    if queue_name in save_some_queues_list:
        return True
    return False


def add_new_value(new_value: str, queue_name: str):
    """Функция добавляет значение Massages
    в соответствующий тектовый файл очереди Queue
    """
    # {WindowsPath} C:\Users\user\PycharmProjects\Lesson_01
    project_directory = Path(__file__).resolve(strict=True).parent

    file_name: str = f"{project_directory}/Logs/{replace_symbol(queue_name)}.txt"

    current_data_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    added_data = f"{current_data_time} : {new_value}"

    try:
        with open(file_name, "a", encoding="utf-8") as file:
            try:
                file.writelines(f"{added_data}\n")
            except OSError:
                logging.warning("%s : Ошибка записи в файл!", added_data)
    except OSError:  # OSError - файл не найден или диск полон
        logging.warning("%s : Файл не найден!", added_data)


def delete_files(dir_name: str):
    """Функция удаляет все файлы .txt из вспомогательных папок проекта:"""
    # dir_name = "Logs/"
    for file in os.listdir(dir_name):
        if file.endswith(".txt"):  # фильтр по расширению
            try:
                os.remove(dir_name + file)
            except FileNotFoundError:
                logging.warning("%s : Файл не найден!", file)


if __name__ == "__main__":
    delete_files("Logs/")
