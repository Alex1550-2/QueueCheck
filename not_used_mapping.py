""" устаревшие функции """

import json
from check_value import (byte_change_gib, replace_symbol,
                         byte_change_mebibyte)


def responce_mapping_nodes(responce: json) -> json:
    """преобразование ответа 'nodes'"""
    dict_responce: dict = {}
    num = 0

    while num < len(responce):  # 3, по кол-ву узлов
        # формируем отчётный json:
        dict_responce.update(
            {
                f"nodes_{str(num+1)}": {
                    "name": replace_symbol(responce[num]["name"]),
                    "file descriptors": responce[num]["fd_used"],
                    "file descriptors available": responce[num]["fd_total"],
                    "socket descriptors": responce[num]["sockets_used"],
                    "socket descriptors available": responce[num]["sockets_total"],
                    "erlang processes": responce[num]["proc_used"],
                    "erlang processes available": responce[num]["proc_total"],
                    "memory (GiB)": byte_change_gib(responce[num]["mem_used"]),
                    "memory high watermark (GiB)": byte_change_gib(
                        responce[num]["mem_limit"]
                    ),
                    "disk space (GiB)": byte_change_gib(responce[num]["disk_free"]),
                    "disk space low watermark (MiB)": byte_change_mebibyte(
                        responce[num]["disk_free_limit"]
                    ),
                }
            }
        )
        num += 1

    # встроенный pretty print, indent - отступ
    # для наглядного представления json
    # json.dumps(responce, indent=3)"""
    return json.dumps(dict_responce, indent=3)


def responce_mapping_queues(responce: json) -> json:
    """преобразование ответа 'queues'"""
    dict_responce: dict = {}
    num = 0

    while num < len(responce):  # 108, по кол-ву очередей
        # формируем отчётный json:
        dict_responce.update(
            {
                f"queue_{str(num + 1)}": {
                    "virtual host": responce[num]["vhost"],
                    "name": responce[num]["name"],
                    "messages_ready": responce[num]["messages_ready"],
                    "messages_unacknowledged": responce[num]["messages_unacknowledged"],
                    "messages": responce[num]["messages"],
                }
            }
        )
        num += 1

    # встроенный pretty print, indent - отступ
    # для наглядного представления json
    # json.dumps(responce, indent=3)"""
    return json.dumps(dict_responce, indent=3)
