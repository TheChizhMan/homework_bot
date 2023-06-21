import datetime
import json
import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv
from http import HTTPStatus

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_API')
TELEGRAM_TOKEN = os.getenv('TG_API')
TELEGRAM_CHAT_ID = os.getenv('chatid')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='main.log',
    level=logging.DEBUG,
    filemode='w')
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)


def check_tokens():
    """Проверка наличия токенов."""
    logger.info('Проверка наличия токенов.')
    return all((PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN))


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    logger.info(
        'Отправляем сообщения в телеграм. '
        'Отправка сообщения может завершиться с ошибкой: '
        'сбой сети или ресурса, '
        'изменится интерфейс (Telegram API). Вернется ошибка.'
    )
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Отправлено сообщение в Telegram: {message}')
    except telegram.TelegramError as telegram_error:
        logger.error(f'Сообщение в Telegram не отправлено: {telegram_error}')


def get_api_answer(current_timestamp):
    """Получение данных от API Практикума."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            code_api_msg = (
                f'Эндпоинт {ENDPOINT} недоступен.'
                f' Код ответа API: {response.status_code}')
            raise exceptions.TheAnswerIsNot200Error(code_api_msg)
        return response.json()
    except json.JSONDecodeError as error:
        raise error


def status_homework(status):
    """Проверка статуса работы."""
    if not HOMEWORK_VERDICTS.get(status):
        code_api_msg = f'Ошибка, неизвестный статус: {status}'
        logger.error(code_api_msg)
        raise exceptions.UndocumentedStatusError(code_api_msg)


def check_response(response):
    """Проверяем данные в response."""
    logger.info(
        'Начинается проверка данных в response.'
        'Проверяется в каком формате перадаются данные запроса к API и ключи '
        'от полученного запроса. Так же проверяется статус проверки работы.'
    )

    if isinstance(response, list):
        logger.info('API передал список')

    if not isinstance(response, dict):
        code_api_msg = 'API передал не словарь'
        logger.error(code_api_msg)
        raise TypeError(code_api_msg)

    missed_keys = {'current_date', 'homeworks'} - response.keys()
    if missed_keys:
        code_api_msg = (f'В ответе API нет ожидаемых ключей: {missed_keys}')
        logger.error(code_api_msg)
        raise KeyError(code_api_msg)

    if not isinstance(response.get('homeworks'), list):
        code_api_msg = 'Содержимое не список'
        logger.error(code_api_msg)
        raise TypeError(code_api_msg)

    if len(response['homeworks']) == 0:
        return {}
    status_homework(response['homeworks'][0].get('status'))
    return response['homeworks'][0]


def parse_status(homework):
    """Анализируем статус если изменился."""
    logger.info(
        'Начинается анализ статуса проверки работы. '
        'Когда статус обновится, придет сообщение в телеграм'
    )

    missed_keys = {'homework_name', 'status'} - homework.keys()
    if missed_keys:
        code_api_msg = (f'В ответе API нет ожидаемых ключей: {missed_keys}')
        logger.error(code_api_msg)
        raise KeyError(code_api_msg)
    status_homework(homework.get('status'))
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS[homework.get('status')]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logger.info('Старт работы бота')
    if not check_tokens():
        logger.critical(
            'Проверьте наличие PRACTICUM_TOKEN, TELEGRAM_TOKEN, '
            'TELEGRAM_CHAT_ID'
        )
        sys.exit("Отсутствует обязательная переменная окружения")

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    now = datetime.datetime.now()
    send_message(
        bot,
        f'Я начал свою работу: {now.strftime("%d-%m-%Y %H:%M")}')
    tmp_status = 'reviewing'

    while True:
        try:
            current_timestamp = int(time.time())
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework and tmp_status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                tmp_status = homework['status']
            logger.info('Изменений нет, ждем 10 минут и проверяем API')
        except exceptions.TheAnswerIsNot200Error as error:
            code_api_msg = f'Код ответа API: {error}'
            logger.error(code_api_msg)
            send_message(bot, f'Ошибка ответа API: {error}')
        except (requests.exceptions.RequestException,
                json.JSONDecodeError) as error:
            logger.error(f'Ошибка запроса к API: {error}')
            send_message(bot, f'Ошибка запроса к API: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
