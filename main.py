"""скрипт для контроля работоспособности очередей
выполняет запросы в веб-панель управления очередями RabbitMQ
"""
import asyncio
import configparser  # модуль для работы с .ini
import json
import smtplib  # библиотека для отправки e-mail
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from requests.auth import HTTPBasicAuth

# импортируем настройки email оправителя / получателя отчётов:
from Email_config.const_email import (
    EMAIL_LOGIN,
    EMAIL_NAME_TO,
    EMAIL_PASSWORD_OUT_APPLICATIONS,
    INI_QUEUE_FILE_NAME,
    QUEUE_AMOUNT,
    SMTP_EMAIL_SERVER,
)


def byte_change_gib(byte: str) -> str:
    """функция преобразования Байт в Гибибайт (GiB)"""
    gib: int = round(int(byte) / (1024**3), 2)
    return str(gib)


def byte_change_mebibyte(byte: str) -> str:
    """функция преобразования Байт в Мебибайт (MiB)"""
    mib: int = round(int(byte) / (1024**2), 2)
    return str(mib)


def get_file_name() -> str:
    """Определяем абсолютные пути текстовых файлов проекта"""
    # {WindowsPath} C:\Users\user\PycharmProjects\Lesson_01
    project_directory = Path(__file__).resolve(strict=True).parent

    # str "C:\\Users\\user\\PycharmProjects\\Lesson_01\\Email_config\\set_queue.ini"
    file_name_queue_set_ini = str(project_directory / INI_QUEUE_FILE_NAME)

    return file_name_queue_set_ini


def read_ini(file_name: str, queue_number: int) -> tuple:
    """чтение конфигурационного параметра из файла set_queue.ini"""
    section_name: str = "SET_" + str(queue_number)

    conf = configparser.RawConfigParser()
    conf.read(file_name)

    result = (
        conf.get(section_name, "SERVER_IP"),
        conf.get(section_name, "SERVER_PORT"),
        conf.get(section_name, "USER_NAME"),
        conf.get(section_name, "USER_PASSWORD"),
    )
    return result  # нумерация с нуля!


def requests_api_nodes(queue_settings: tuple, command: str) -> json:
    """запрашиваем и получаем отчёт из API Rabbit MQ
    примеры команд (переменная command):
    - "/api/overview"
    - "/api/cluster-name" - Name identifying this RabbitMQ cluster,
    - "/api/nodes" - A list of nodes in the RabbitMQ cluster.
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


def responce_mapping(responce: json) -> json:
    """преобразование ответа 'nodes'"""
    dict_responce: dict = {}
    num = 0

    nodes_amount = len(responce)  # 3

    while num < nodes_amount:
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


def send_email(
    smtp_email_server,
    email_login,
    email_password_out_application,
    email_name_to,
    message_text,
    message_topic,
):
    # pylint: disable=too-many-arguments
    """функция отправки email, библиотека smtplib"""

    # настройка url:port SMTP сервера
    smtp_server = smtplib.SMTP_SSL(smtp_email_server)

    # настройка параметров входа в email рассылки (from)
    smtp_server.login(email_login, email_password_out_application)

    message = MIMEMultipart()  # create a message

    # настраиваем параметры сообщения:
    message["From"] = email_login
    message["To"] = email_name_to
    message["Subject"] = message_topic

    # добавляем текст сообщения:
    message.attach(MIMEText(message_text, "plain"))

    # отправляем сообщение
    smtp_server.send_message(message)
    del message

    # удаляем SMTP сессию и закрываем соединение
    smtp_server.quit()


def queue_check():
    #           smtp_email_server, email_login,
    #           email_password_out_application,
    #           email_name_to,
    """основная функция проверки очереди"""

    queue_number: int = 1  # количество проверяемых инфраструктур

    while queue_number <= QUEUE_AMOUNT:
        # 1) получили настройки очереди из ini-файла:
        file_name_set_ini = get_file_name()
        queue_settings: tuple = read_ini(file_name_set_ini, queue_number)

        # 2) отправили запрос "nodes" в API Rabbit MQ
        responce_nodes: json = requests_api_nodes(queue_settings, "/api/nodes")

        # 3) преобразование ответа "nodes"
        message_text = responce_mapping(responce_nodes)

        # 4) заполняем тему письма
        responce_cluster_name = requests_api_nodes(queue_settings, "/api/cluster-name")
        message_topic: str = responce_cluster_name["name"]

        message_topic += ": " + datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

        # 5) отправили email с результатами
        send_email(
            SMTP_EMAIL_SERVER,
            EMAIL_LOGIN,
            EMAIL_PASSWORD_OUT_APPLICATIONS,
            EMAIL_NAME_TO,
            message_text,
            message_topic,
        )

        queue_number += 1

        # задержка, чтобы не забанил почтовый сервер:
        time.sleep(1)


def run_scheduler():
    """планировщик заданий
    1) проверочные 2 письма (утро-вечер) / рабочий день
    2) тревожное сообщение в случае mem_limit < допустимого"""
    scheduler = BackgroundScheduler()
    # "боевой" планировщик: будни, рабочее время с 9 до 18, каждый час:
    # jitter - "дребезг" 30 секунд
    # scheduler.add_job(queue_check, 'cron', day_of_week='0-4', hour='09-18/1', jitter=30)

    # "интервальное" задание для отладки:
    # scheduler.add_job(queue_check, args=[SMTP_EMAIL_SERVER, EMAIL_LOGIN,
    #             EMAIL_PASSWORD_OUT_APPLICATIONS,
    #             EMAIL_NAME_TO,
    #             queue_number], trigger='interval', seconds=30)

    # контрольная отправка в будни утром и вечером:
    scheduler.add_job(
        queue_check, "cron", day_of_week="0-4", hour="09, 18", minute="02", jitter=30
    )

    # только для тестирования:
    # scheduler.add_job(queue_check, trigger='interval', seconds=5)

    scheduler.start()

    try:
        # создаём новый цикл события, устнавливаем его как текущий
        # run_forever() запускает цикл, пока не будет вызван stop().
        asyncio.get_event_loop().run_forever()
    except SystemExit:
        # ??? asyncio.get_event_loop().stop() ???
        # ??? scheduler.remove_all_jobs() ???
        scheduler.shutdown()


if __name__ == "__main__":

    run_scheduler()

    # queue_check()

    # queue_check(SMTP_EMAIL_SERVER, EMAIL_LOGIN,
    #                 EMAIL_PASSWORD_OUT_APPLICATIONS,
    #                 EMAIL_NAME_TO)
