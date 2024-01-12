"""скрипт для контроля работоспособности очередей
выполняет запросы в веб-панель управления очередями RabbitMQ
"""
import asyncio
import argparse
import configparser  # модуль для работы с .ini
import logging
import smtplib  # библиотека для отправки e-mail
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

# импортируем настройки email оправителя / получателя отчётов:
from Email_config.const_email import (EMAIL_LOGIN, EMAIL_NAME_TO,
                                      EMAIL_PASSWORD_OUT_APPLICATIONS,
                                      INI_QUEUE_FILE_NAME, QUEUE_AMOUNT,
                                      SMTP_EMAIL_SERVER, email_name_alarm_list)
from logs import partial_clean_log_file
from mapping import queue_mapping  # импортируем обработку запросов

# выбор типа планирвщика: работа в фоновом режиме внутри приложения
scheduler = BackgroundScheduler()


# определяем аргументы скрипта при использовании анализатора argparse:
parser = argparse.ArgumentParser(
    description="Script: system performance check"
)
parser.add_argument(
    "infranumber", type=str, help="The number of the data set (ip/login) from set_queue.ini"
)
parser.add_argument(
    "techreport", type=str, help="Send technical report in options: 'yes'"
)
parser.add_argument(
    "mode", type=str, help="Scheduler launch mode: 'test', 'local', 'live'",
)
args = parser.parse_args()


def get_infra_numbers(general_number: int) -> list[int]:
    """из аргумента формируем list с номерами наборов
    параметров доступа к проверяемым инфраструктурам
    SET_x из set_queue.ini
    """
    return list(str(general_number))


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
        logging.warning(
            f"SET_{queue_number} >>> NoSectionError: No section "
        )
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


def queue_check():
    #           smtp_email_server, email_login,
    #           email_password_out_application,
    #           email_name_to,
    """основная функция проверки очереди"""

    # получаем из аргумента args.infranumber номера инфраструктур SET_x
    # из set_queue.ini, которые должны проверить:
    infra_numbers: list[int] = get_infra_numbers(args.infranumber)

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
        # получен соответствующий аргумент techreport=yes:
        if args.techreport == "yes":
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
                f"{EMAIL_NAME_TO} >>> {message_topic} >>> 'технический' email отправлен"
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
                    f"{email_name_alarm} >>> "
                    f"{message_topic} >>> 'тревожный' email отправлен"
                )

                # задержка, чтобы не забанил почтовый сервер:
                time.sleep(3)

        # задержка, чтобы не забанил почтовый сервер:
        time.sleep(3)

    # логируем завершение цикла:
    logging.warning(
        " >>> cycle complete"
    )


def test_scheduler():
    """быстрое тестирование - интервал проверки 10 секунд"""
    scheduler.add_job(queue_check, trigger="interval", seconds=10)


def local_scheduler():
    """тестирование на локальной машине - интервал проверки 15 минут"""
    scheduler.add_job(queue_check, "cron", minute="00, 15, 30, 45")


def live_scheduler():
    """'боевой' планировщик: будни, рабочее время с 9 до 18,
    интервал проверки - 1 час, jitter - "дребезг" 30 секунд"""
    scheduler.add_job(queue_check, "cron", day_of_week="0-4", hour="09-18/1", jitter=30)


def default():
    """ошибка выбора режима"""
    logging.warning(
        " >>> mode switch ERROR!"
    )


mode_switch = {
    "test": test_scheduler,
    "local": local_scheduler,
    "live": live_scheduler,
}


def run_scheduler():
    """планировщик заданий перенесён на 27 строку"""
    # scheduler = BackgroundScheduler()

    # получаем из аргумента режим проверки mode
    # и запускаем соответствующую функцию (шедулер)
    # из словаря mode_switch
    mode_switch.get(args.mode, default)()

    # этот шедулер выполняем при любом аргументе mode
    # ежедневно в 23.30 часа удалить "лишние" строки из лога:
    scheduler.add_job(partial_clean_log_file, "cron", hour="23", minute="30", jitter=15)

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
