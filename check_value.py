"""содержит вспомогательные функции проверки работоспособности"""


def replace_symbol(string: str) -> str:
    """Функция возвращает строку без запрещённых /
    нежелательных символов в имени файла"""
    string = string.replace("@", "*")
    string = string.replace(".", "_")
    return string


def get_check_value(dict_name, dict_kay: str) -> int:
    """получаем количественный показатель для оценки
    корректности работы очереди
    limit_value - количество сообщений (queue message total)"""
    if dict_kay in dict_name:
        return int(dict_name[dict_kay])

    return int(dict_name["REST"])


def byte_change_gib(byte: str) -> str:
    """функция преобразования Байт в Гибибайт (GiB)"""
    gib: float = round(int(byte) / (1024**3), 2)
    return str(gib)


def byte_change_mebibyte(byte: str) -> str:
    """функция преобразования Байт в Мебибайт (MiB)"""
    mib: float = round(int(byte) / (1024**2), 2)
    return str(mib)


def calculate_memory_free(used_memory: str, total_memory: str, limit_ratio: float):
    """функция рассчитывает % свободной памяти и
    сравнивает его с пороговым значением ratio"""
    current_ratio = float(
        (float(total_memory) - float(used_memory)) / float(total_memory) * 100
    )
    current_ratio = round(current_ratio, 1)  # округляем до десятой

    if current_ratio > limit_ratio:
        check_result = "OK"
    else:
        check_result = "ALARM!"

    return current_ratio, check_result


def calculate_diskspace_free(free_diskspace: str, limit_diskspace: int) -> str:
    """функция сравнивает свободный объём диска и
    пороговое значение limit"""
    if float(free_diskspace) > float(limit_diskspace):
        return "OK"
    return "ALARM!"


def calculate_amount_queues(queue_amount: int, limit_queue_amount: int) -> str:
    """функция сравнивает текущее количество
    очередей и пороговое значение limit

    ДУБЛИРУЕТ функцию calculate_amount_messages,
    специально сделал отдельно под будущее усложнение"""
    if queue_amount < limit_queue_amount:
        return "OK"
    return "ALARM!"


def calculate_amount_messages(message_amount: int, limit_message_amount: int) -> str:
    """функция сравнивает текущее количество message
    в очереди и пороговое значение limit"""
    if message_amount < limit_message_amount:
        return "OK"
    return "ALARM!"
