"""скрипт для контроля работоспособности очередей
выполняет запросы в веб-панель управления очередями RabbitMQ
"""
import asyncio
import configparser  # модуль для работы с .ini
import smtplib  # библиотека для отправки e-mail
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

# импортируем настройки email оправителя / получателя отчётов:
from Email_config.const_email import (
    EMAIL_LOGIN,
    EMAIL_NAME_ALARM_1,
    EMAIL_NAME_TO,
    EMAIL_PASSWORD_OUT_APPLICATIONS,
    INI_QUEUE_FILE_NAME,
    QUEUE_AMOUNT,
    QUEUE_EMAIL_ALARM,
    SMTP_EMAIL_SERVER,
)
from logs import create_file_name, remove_report_files, save_json_file, step_logging
from mapping import queue_mapping  # импортируем обработку запросов


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


def send_email(
    smtp_email_server,
    email_login,
    email_password_out_application,
    email_name_to,
    message_text,
    message_topic,
):  # pylint: disable=too-many-arguments
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
    queue_number: int = 1  # счётчик цикла: кол-во проверяемых инфраструктур

    while queue_number <= QUEUE_AMOUNT:
        # 1) получили настройки очереди из ini-файла:
        file_name_set_ini = get_file_name()
        queue_settings: tuple = read_ini(file_name_set_ini, queue_number)

        # 2) запустили проверку i-ой инфраструктуры:
        (
            email_topic,
            email_to_json_nodes,
            email_to_json_queues,
            email_alarm_list,
        ) = queue_mapping(queue_settings)

        # 3) заполняем тему письма
        message_topic: str = (
            datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ": " + email_topic
        )

        # 4) сохранить 'сырой' json в папке Report
        log_file_name = create_file_name("_nodes")
        save_json_file(email_to_json_nodes, log_file_name)

        log_file_name = create_file_name("_queues")
        save_json_file(email_to_json_queues, log_file_name)

        # записываем в лог отчётную строку:
        step_logging(message_topic + ": лог сохранён в папке Report")
        time.sleep(1)

        # 5) отправляем 'технический' email с результатами:
        general_big_string = ""
        for element in email_alarm_list:
            general_big_string += str(element) + "\r\n"

        send_email(
            SMTP_EMAIL_SERVER,
            EMAIL_LOGIN,
            EMAIL_PASSWORD_OUT_APPLICATIONS,
            EMAIL_NAME_TO,
            general_big_string,
            message_topic,
        )
        # записываем в лог отчётную строку:
        step_logging(message_topic + ": 'технический' email отправлен")

        # 6) если в тексте есть 'Alarm', то отправляем 'тревожные' email
        checklist = {"ALARM!"}

        common_words = set(general_big_string.split()) & checklist
        if len(common_words) > 0:
            alarm_number = 0  # счётчик цикла: кол-во отправляемых email

            while alarm_number < QUEUE_EMAIL_ALARM:
                send_email(
                    SMTP_EMAIL_SERVER,
                    EMAIL_LOGIN,
                    EMAIL_PASSWORD_OUT_APPLICATIONS,
                    EMAIL_NAME_ALARM_1,
                    general_big_string,
                    message_topic,
                )
                # записываем в лог отчётную строку:
                step_logging(message_topic + ": 'тревожный' email отправлен")

                # задержка, чтобы не забанил почтовый сервер:
                time.sleep(1)

                alarm_number += 1

        queue_number += 1

        # задержка, чтобы не забанил почтовый сервер:
        time.sleep(1)

    print("for test: cycle complete")


def run_scheduler():
    """планировщик заданий"""
    scheduler = BackgroundScheduler()

    # "боевой" планировщик: будни, рабочее время с 9 до 18, каждый час:
    # jitter - "дребезг" 30 секунд
    scheduler.add_job(queue_check, "cron", day_of_week="0-4", hour="09-18/1", jitter=30)

    # ежедневно в 23.30 часа удалить "лишние" файлы из папки Report:
    scheduler.add_job(remove_report_files, "cron", hour="23", minute="30", jitter=15)

    # только для тестирования:
    # scheduler.add_job(queue_check, trigger='interval', seconds=30)

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
