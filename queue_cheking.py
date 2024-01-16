"""здесь основная функция проверки очередей queue_check
и её вспомогательные функции
"""
import configparser  # модуль для работы с .ini
import logging
import smtplib  # библиотека для отправки e-mail
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# импортируем настройки email оправителя / получателя отчётов:
from Email_config.const_email import (
    EMAIL_LOGIN,
    EMAIL_NAME_TO,
    EMAIL_PASSWORD_OUT_APPLICATIONS,
    INI_QUEUE_FILE_NAME,
    SMTP_EMAIL_SERVER,
    email_name_alarm_list,
)
from mapping import queue_mapping  # импортируем обработку запросов


def get_file_name() -> str:
    """Определяем абсолютные пути текстовых файлов проекта"""
    # {WindowsPath} C:\Users\user\PycharmProjects\Lesson_01
    project_directory = Path(__file__).resolve(strict=True).parent

    # str "C:\\Users\\user\\PycharmProjects\\Lesson_01\\Email_config\\set_queue.ini"
    file_name_queue_set_ini = str(project_directory / INI_QUEUE_FILE_NAME)

    return file_name_queue_set_ini


def read_ini(file_name: str, queue_number: int) -> tuple:
    """чтение параметров конфигурации из файла set_queue.ini"""
    section_name: str = f"SET_{queue_number}"

    conf = configparser.RawConfigParser()
    conf.read(file_name)

    try:
        result = (
            conf.get(section_name, "SERVER_IP"),
            conf.get(section_name, "SERVER_PORT"),
            conf.get(section_name, "USER_NAME"),
            conf.get(section_name, "USER_PASSWORD"),
        )
    except configparser.NoSectionError:
        logging.warning("SET_%s >>> NoSectionError: No section", queue_number)
        result = (0, 0, 0, 0)

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


def queue_check(infra_numbers: list[int], techreport: str):
    #           smtp_email_server, email_login,
    #           email_password_out_application,
    #           email_name_to,
    """основная функция проверки очереди

    infra_numbers: list[int] - список с номерами инфраструктур SET_x
    из set_queue.ini, которые должны проверить:
    """

    for queue_number in infra_numbers:
        # 1) получили настройки очереди из ini-файла:
        file_name_set_ini = get_file_name()
        queue_settings: tuple = read_ini(file_name_set_ini, queue_number)

        # если настройки не найдены, то пропускаем итерацию
        if queue_settings == (0, 0, 0, 0):
            continue

        # 2) запустили проверку i-ой инфраструктуры:
        email_topic, email_tech_text, email_alarm_text = queue_mapping(queue_settings)

        # 3) заполняем тему письма
        current_data_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        message_topic: str = f"{current_data_time}: {email_topic}"

        # 4) отправляем 'технический' email с результатами:
        # преобразование исходного list в str с разделителями методом join:
        tech_text_big_string = "\r\n".join(email_tech_text)

        # технический отчёт отправляем только если
        # получен соответствующий аргумент args.techreport=yes:
        if techreport == "yes":
            send_email(
                SMTP_EMAIL_SERVER,
                EMAIL_LOGIN,
                EMAIL_PASSWORD_OUT_APPLICATIONS,
                EMAIL_NAME_TO,
                tech_text_big_string,
                message_topic,
            )

            # записываем в лог отчётную строку:
            logging.warning(
                "%s >>> %s >>> 'технический' email отправлен", EMAIL_NAME_TO, message_topic
            )

        # 5) отправляем 'тревожные' email
        # проверяем текстовку на наличие слова "ALARM!":
        checklist = {"ALARM!"}
        common_words = set(tech_text_big_string.split()) & checklist

        # и тему email на наличие слова "ERROR":
        if len(common_words) > 0 or message_topic.find("ERROR") != -1:
            # создаём укороченный 'тревожный' email:
            # преобразование исходного list в str с разделителями методом join:
            alarm_text_big_string = "\r\n".join(email_alarm_text)

            for email_name_alarm in email_name_alarm_list:
                send_email(
                    SMTP_EMAIL_SERVER,
                    EMAIL_LOGIN,
                    EMAIL_PASSWORD_OUT_APPLICATIONS,
                    email_name_alarm,
                    alarm_text_big_string,
                    message_topic,
                )
                # записываем в лог отчётную строку:
                logging.warning(
                    "%s >>> %s >>> 'тревожный' email отправлен", email_name_alarm, message_topic
                )

                # задержка, чтобы не забанил почтовый сервер:
                time.sleep(3)

        # задержка, чтобы не забанил почтовый сервер:
        time.sleep(3)

    # логируем завершение цикла:
    logging.warning(" >>> cycle complete")
