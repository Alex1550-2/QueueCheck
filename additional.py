""" Вспомогательный модуль
"""
import os  # модуль для работы с операционной системой


def delete_files(dir_name: str):
    """Функция удаляет все файлы из папки
    dir_name = "Report/"
    """
    all_files = os.listdir(dir_name)
    for file in all_files:
        file = dir_name + file
        print("Файл " + file + " удалён")
        os.remove(file)


if __name__ == "__main__":
    delete_files("Report/")
