"""Функции общения с API RabbitMQ
запросы и обработка ответов на них"""
import json

import requests
from requests.auth import HTTPBasicAuth

from check_value import (
    byte_change_gib,
    byte_change_mebibyte,
    calculate_amount_messages,
    calculate_diskspace_free,
    calculate_memory_free,
    get_check_value,
    replace_symbol,
)

# импортируем количественные значения проверки работоспособности:
from Email_config.control_value import limit_value_messages, queue_control_values


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

    try:
        # время ожидания ответа от сервера timeout=15 секунд
        res = requests.get(url_requests, auth=auth, timeout=15)
        if res.status_code == 200:
            content = res.json()
            return content
        return {"name": "error", "status_code": str(res.status_code)}
    except requests.ConnectionError as error_text:
        return {
            "name": "connect_error",
            "status_code": "Ошибка подключения: " + str(error_text),
        }
    except requests.Timeout as error_text:
        return {
            "name": "connect_error",
            "status_code": "Ошибка тайм-аута: " + str(error_text),
        }
    except requests.RequestException as error_text:
        return {
            "name": "connect_error",
            "status_code": "Ошибка запроса: " + str(error_text),
        }


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


def check_mapping_nodes(responce: json) -> list:
    """проверяем узлы по количественным характеристикам
    из списка limit_value_messages
    на выходе текстовка для email в части 'УЗЛЫ'"""
    nodes_list: list = ["NODES:"]
    nodes_list.append("")  # разделитель
    num = 0

    while num < len(responce):  # 3, по кол-ву узлов
        # формируем отчётный list:
        nodes_list.append(replace_symbol(responce[num]["name"]))

        # проверка "Node not running"
        if responce[num]["running"] is False:
            nodes_list.append("Node not running >>> ERROR!")

        else:
            memory_percent, memory_result = calculate_memory_free(
                byte_change_gib(responce[num]["mem_used"]),
                byte_change_gib(responce[num]["mem_limit"]),
                queue_control_values[0],
            )

            nodes_list.append(
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

            nodes_list.append(
                "disk space "
                + byte_change_gib(responce[num]["disk_free"])
                + " GiB / check limit "
                + str(queue_control_values[1])
                + " GiB >>> Test: "
                + check_result
            )

            nodes_list.append("")  # разделитель

        num += 1
    return nodes_list


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


def check_mapping_queues(responce: json) -> list:
    """добавляем результат проверки очередей по текущему количеству сообщений
    на выходе текстовка email для 'технического' отчёта в части 'ОЧЕРЕДИ'"""
    tech_list: list = ["===============================", "QUEUES:", ""]
    num = 0

    while num < len(responce):  # 108, по кол-ву очередей
        # определяем пороговое значение:
        limit_value = get_check_value(limit_value_messages, responce[num]["name"])
        check_result = calculate_amount_messages(responce[num]["messages"], limit_value)

        # формируем отчётный list:
        tech_list.append(
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
    return tech_list


def alarm_mapping_queues(responce: json) -> list:
    """добавляем результат проверки очередей по текущему количеству сообщений
    на выходе текстовка email для 'тревожного' отчёта
    включаем в отчёт только очереди с ALARM"""
    alarm_list: list = ["===============================", "QUEUES:", ""]
    num = 0

    while num < len(responce):  # 108, по кол-ву очередей
        # определяем пороговое значение:
        limit_value = get_check_value(limit_value_messages, responce[num]["name"])
        check_result = calculate_amount_messages(responce[num]["messages"], limit_value)

        # в отчёт добавляем только 'тревожную' строку:
        if check_result == "ALARM!":
            # формируем отчётный list:
            alarm_list.append(
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
    return alarm_list


def queue_mapping(queue_settings):
    #           smtp_email_server, email_login,
    #           email_password_out_application,
    #           email_name_to,
    """основная функция проверки очереди"""
    # 1) отправляем запрос "cluster-name" в API Rabbit MQ:
    responce_cluster_name = requests_api_rabbit_mq(queue_settings, "/api/cluster-name")
    # получаем имя кластера для темы сообщения:
    email_topic = replace_symbol(responce_cluster_name["name"])

    # нет связи с RabbitMQ:
    if email_topic == "connect_error":
        email_text = ["status_code: " + responce_cluster_name["status_code"]]
        return "ERROR", email_text, email_text

    # есть связь с RabbitMQ, но ответ status_code != 200
    if email_topic == "error":
        email_text = ["status_code: " + responce_cluster_name["status_code"]]
        return "ERROR", email_text, email_text

    # почтовый сервер mail.ru ругается на непонятные темы сообщений,
    # поэтому укорачиваем тему (а на самом деле название узла)
    # до 12 последних символов:
    email_topic = email_topic[-12:]

    # 2) отправляем запрос "nodes" в API Rabbit MQ:
    responce_nodes: json = requests_api_rabbit_mq(queue_settings, "/api/nodes")
    # подготовили текстовку email сообщения:
    email_text_nodes = check_mapping_nodes(responce_nodes)

    # 3) отправляем запрос "queues" в API Rabbit MQ:
    responce_queues: json = requests_api_rabbit_mq(queue_settings, "/api/queues")
    # получили текстовку email для 'технического' отчёта в части 'ОЧЕРЕДИ'
    email_tech_queues = check_mapping_queues(responce_queues)
    # добавили ответ в текстовку 'технического' email сообщения:
    email_tech_text = email_text_nodes + email_tech_queues

    # получили текстовку email для 'тревожного' отчёта в части 'ОЧЕРЕДИ'
    email_alarm_queues = alarm_mapping_queues(responce_queues)

    # добавили ответ в текстовку 'технического' email сообщения:
    email_alarm_text = email_text_nodes + email_alarm_queues

    return email_topic, email_tech_text, email_alarm_text
