"""Функции общения с API RabbitMQ
запросы и обработка ответов на них
а также отправки email"""
import json

import requests
from requests.auth import HTTPBasicAuth

queue_control_values = (
    0.2,  # [0] memory free, ratio
    50,  # [1] free disk space, GB
)

# мониторинг корректности работы системы по числу сообщений в очереди
# https://cf-dcto.grfc.ru/pages/viewpage.action?pageId=158630351
limit_value_messages = {
    "analyse_new_materials": 100000,
    "analyse_result": 100000,
    "bulk_add_to_sample": 1000,
    "reanalyse_sample": 1000,
    "worker_re_in_other": 5000,
    "worker_re_in_smi": 300000,
    "worker_re_in_sn": 300000,
    "worker_re_out": 250000,
    "REST": 300000,
}


def get_check_value(dict_name, dict_kay: str) -> int:
    """получаем количественный показатель для оценки
    корректности работы очереди
    limit_value - количество сообщений (queue message total)"""
    limit_value: int = 300000  # значение по умолчанию

    if dict_kay in dict_name:
        limit_value = int(dict_name[dict_kay])

    return limit_value


def requests_api_rabbit_mq(queue_settings: tuple, command: str) -> json:
    """запрашиваем и получаем отчёт из API Rabbit MQ
    примеры команд (переменная command):
    - "/api/overview"
    - "/api/cluster-name" - Name identifying this RabbitMQ cluster,
    - "/api/nodes" - A list of nodes in the RabbitMQ cluster.
    - "/api/queues" - A list of all queues.
    """
    server_ip: str = queue_settings[0]
    server_port: str = queue_settings[1]
    user_name: str = queue_settings[2]
    user_password: str = queue_settings[3]

    auth = HTTPBasicAuth(user_name, user_password)
    url_requests = "http://" + server_ip + ":" + server_port + command
    res = requests.get(url_requests, auth=auth)

    if res.status_code == 200:
        content = res.json()
        return content

    return {"response": "error"}


def byte_change_gib(byte: str) -> str:
    """функция преобразования Байт в Гибибайт (GiB)"""
    gib: int = round(int(byte) / (1024**3), 2)
    return str(gib)


def byte_change_mebibyte(byte: str) -> str:
    """функция преобразования Байт в Мебибайт (MiB)"""
    mib: int = round(int(byte) / (1024**2), 2)
    return str(mib)


def calculate_memory_free(used_memory: str, total_memory: str, limit_ratio: float):
    """функция рассчитывает % свободной памяти и
    сравнивает его с пороговым значением ratio"""
    current_ratio = int(
        (float(total_memory) - float(used_memory)) / float(total_memory) * 100
    )

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


def calculate_amount_messages(message_amount: int, limit_message_amount: int) -> str:
    """функция сравнивает текущее количество message
    в очереди и пороговое значение limit"""
    if message_amount < limit_message_amount:
        return "OK"
    return "ALARM!"


def responce_mapping_nodes(responce: json) -> json:
    """преобразование ответа 'nodes'"""
    dict_responce: dict = {}
    num = 0

    while num < len(responce):  # 3, по кол-ву узлов
        # формируем отчётный json:
        dict_responce.update(
            {
                "nodes_"
                + str(num + 1): {
                    "name": responce[num]["name"],
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


def alarm_mapping_nodes(responce: json) -> list:
    """проверяем узлы по количественным характеристикам
    из списка limit_value_messages"""
    check_list: list = ["NODES:"]
    check_list.append("")  # разделитель
    num = 0

    while num < len(responce):  # 3, по кол-ву узлов
        # формируем отчётный list:
        check_list.append(responce[num]["name"])

        memory_percent, memory_result = calculate_memory_free(
            byte_change_gib(responce[num]["mem_used"]),
            byte_change_gib(responce[num]["mem_limit"]),
            queue_control_values[0],
        )

        check_list.append(
            "used "
            + byte_change_gib(responce[num]["mem_used"])
            + " GiB / total "
            + byte_change_gib(responce[num]["mem_limit"])
            + " GiB >>> "
            + str(memory_percent)
            + "% free >>> Test: "
            + memory_result
        )

        check_result = calculate_diskspace_free(
            byte_change_gib(responce[num]["disk_free"]), queue_control_values[1]
        )

        check_list.append(
            "disk space "
            + byte_change_gib(responce[num]["disk_free"])
            + " GiB / check limit "
            + str(queue_control_values[1])
            + " GiB >>> Test: "
            + check_result
        )

        check_list.append("")  # разделитель

        num += 1
    return check_list


def responce_mapping_queues(responce: json) -> json:
    """преобразование ответа 'queues'"""
    dict_responce: dict = {}
    num = 0

    while num < len(responce):  # 108, по кол-ву очередей
        # формируем отчётный json:
        dict_responce.update(
            {
                "queue_"
                + str(num + 1): {
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


def alarm_mapping_queues_add(check_list: list, responce: json) -> list:
    """добавляем проверку очередей по текущему количеству сообщений"""
    check_list.append("===============================")
    check_list.append("QUEUES:")
    check_list.append("")  # разделитель

    num = 0

    while num < len(responce):  # 3, по кол-ву узлов
        # определяем пороговое значение:
        limit_value = get_check_value(limit_value_messages, responce[num]["name"])
        check_result = calculate_amount_messages(responce[num]["messages"], limit_value)

        # формируем отчётный list:
        check_list.append(
            responce[num]["vhost"]
            + ": "
            + responce[num]["name"]
            + " >>> messages: ready "
            + str(responce[num]["messages_ready"])
            + " / unacked "
            + str(responce[num]["messages_unacknowledged"])
            + " / total "
            + str(responce[num]["messages"])
            + " >>> check limit "
            + str(limit_value)
            + " >>> Test: "
            + check_result
        )
        num += 1
    return check_list


def queue_mapping(queue_settings):
    #           smtp_email_server, email_login,
    #           email_password_out_application,
    #           email_name_to,
    """основная функция проверки очереди"""

    # 1) отправляем запрос "cluster-name" в API Rabbit MQ:
    responce_cluster_name = requests_api_rabbit_mq(queue_settings, "/api/cluster-name")
    # получаем имя кластера для темы сообщения:
    email_topic = responce_cluster_name["name"]

    # 2) отправляем запрос "nodes" в API Rabbit MQ:
    responce_nodes: json = requests_api_rabbit_mq(queue_settings, "/api/nodes")
    # подготовили текстовку технического и тревожного сообщений:
    email_to_json_nodes = responce_mapping_nodes(responce_nodes)
    email_alarm_list = alarm_mapping_nodes(responce_nodes)

    # 3) отправляем запрос "queues" в API Rabbit MQ:
    responce_queues: json = requests_api_rabbit_mq(queue_settings, "/api/queues")
    # подготовили текстовку технического сообщениz:
    email_to_json_queues = responce_mapping_queues(responce_queues)

    # 4) добавить текстовку тревожного сообщения:
    email_alarm_list = alarm_mapping_queues_add(email_alarm_list, responce_queues)

    return email_topic, email_to_json_nodes, email_to_json_queues, email_alarm_list
