#####
# в папке Text должны находиться два файла:
#####
# 1) const_email.py - файл с константами 
#####
# 1.1) настройки email оправителя отчётов:
SMTP_EMAIL_SERVER
EMAIL_LOGIN
EMAIL_PASSWORD_OUT_APPLICATIONS
# 1.2) email получателя отчётов:
EMAIL_NAME_TO
# 1.3) указатель на файл с настройками
INI_QUEUE_FILE_NAME
# 1.4) количество проверяемых инфраструктур / очередей:
QUEUE_AMOUNT
#####
# 2) set_queue.ini - файл с параметрами доступа к Rabbit MQ:
# 2.1) заголовок комплекта данных:
[SET_x]
# 2.2) содержимое комплекта:
SERVER_IP
SERVER_PORT
USER_NAME
USER_PASSWORD
