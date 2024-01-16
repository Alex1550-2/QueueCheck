""" устаревшие функции """

import json

from check_value import byte_change_gib, byte_change_mebibyte, replace_symbol


def response_mapping_nodes(response: json) -> json:
    """преобразование ответа 'nodes'"""
    dict_response: dict = {}
    num = 0

    while num < len(response):  # 3, по кол-ву узлов
        # формируем отчётный json:
        dict_response.update(
            {
                f"nodes_{str(num+1)}": {
                    "name": replace_symbol(response[num]["name"]),
                    "file descriptors": response[num]["fd_used"],
                    "file descriptors available": response[num]["fd_total"],
                    "socket descriptors": response[num]["sockets_used"],
                    "socket descriptors available": response[num]["sockets_total"],
                    "erlang processes": response[num]["proc_used"],
                    "erlang processes available": response[num]["proc_total"],
                    "memory (GiB)": byte_change_gib(response[num]["mem_used"]),
                    "memory high watermark (GiB)": byte_change_gib(
                        response[num]["mem_limit"]
                    ),
                    "disk space (GiB)": byte_change_gib(response[num]["disk_free"]),
                    "disk space low watermark (MiB)": byte_change_mebibyte(
                        response[num]["disk_free_limit"]
                    ),
                }
            }
        )
        num += 1

    # встроенный pretty print, indent - отступ
    # для наглядного представления json
    # json.dumps(response, indent=3)"""
    return json.dumps(dict_response, indent=3)


def response_mapping_queues(response: json) -> json:
    """преобразование ответа 'queues'"""
    dict_response: dict = {}
    num = 0

    while num < len(response):  # 108, по кол-ву очередей
        # формируем отчётный json:
        dict_response.update(
            {
                f"queue_{str(num + 1)}": {
                    "virtual host": response[num]["vhost"],
                    "name": response[num]["name"],
                    "messages_ready": response[num]["messages_ready"],
                    "messages_unacknowledged": response[num]["messages_unacknowledged"],
                    "messages": response[num]["messages"],
                }
            }
        )
        num += 1

    # встроенный pretty print, indent - отступ
    # для наглядного представления json
    # json.dumps(response, indent=3)"""
    return json.dumps(dict_response, indent=3)
