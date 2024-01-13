"""скрипт для контроля работоспособности очередей
выполняет запросы в веб-панель управления очередями RabbitMQ
"""
import argparse
import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from logs import partial_clean_log_file
from queue_cheking import queue_check  # импортируем проверку очередей

# выбор типа планирвщика: работа в фоновом режиме внутри приложения
scheduler = BackgroundScheduler()


# определяем аргументы скрипта при использовании анализатора argparse:
parser = argparse.ArgumentParser(description="Script: system performance check")
parser.add_argument(
    "infranumber",
    type=int,
    help="The number of the data set (ip/login) from set_queue.ini",
)
parser.add_argument(
    "techreport",
    type=str,
    help="Send technical report in options: 'yes'"
)
parser.add_argument(
    "mode",
    type=str,
    help="Scheduler launch mode: 'test', 'local', 'live'",
)
args = parser.parse_args()


def get_infra_numbers(general_number: int) -> list[int]:
    """из аргумента формируем list с номерами наборов
    параметров доступа к проверяемым инфраструктурам
    SET_x из set_queue.ini
    """
    result_list: list[int] = []
    while general_number > 0:
        result_list.append(general_number % 10)  # остаток
        general_number //= 10  # целочисленное деление

    result_list.reverse()

    return result_list


def test_scheduler(infra_numbers: list[int], techreport: str):
    """быстрое тестирование - интервал проверки 10 секунд"""
    scheduler.add_job(
        queue_check,
        trigger="interval",
        seconds=10,
        kwargs={
            "infra_numbers": infra_numbers,
            "techreport": techreport,
        },
    )


def local_scheduler(infra_numbers: list[int], techreport: str):
    """тестирование на локальной машине - интервал проверки 15 минут"""
    scheduler.add_job(
        queue_check,
        "cron",
        minute="00, 15, 30, 45",
        kwargs={
            "infra_numbers": infra_numbers,
            "techreport": techreport,
        },
    )


def live_scheduler(infra_numbers: list[int], techreport: str):
    """'боевой' планировщик: будни, рабочее время с 9 до 18,
    интервал проверки - 1 час, jitter - "дребезг" 30 секунд"""
    scheduler.add_job(
        queue_check,
        "cron",
        day_of_week="0-4",
        hour="09-18/1",
        jitter=30,
        kwargs={
            "infra_numbers": infra_numbers,
            "techreport": techreport,
        },
    )


def default():
    """ошибка выбора режима"""
    logging.warning(" >>> mode switch ERROR!")


def run_scheduler():
    """планировщик заданий перенесён на 27 строку"""
    # scheduler = BackgroundScheduler()

    # из аргумента формируем list с номерами наборов
    # параметров доступа к проверяемым инфраструктурам
    # SET_x из set_queue.ini
    infra_numbers = get_infra_numbers(args.infranumber)

    # выбор соответствующего scheduler для последующего запуска:
    if args.mode == "test":
        test_scheduler(infra_numbers, args.techreport)
    elif args.mode == "local":
        local_scheduler(infra_numbers, args.techreport)
    elif args.mode == "live":
        live_scheduler(infra_numbers, args.techreport)
    else:
        default()

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
