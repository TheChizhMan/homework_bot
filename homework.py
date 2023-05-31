import os
from time import time
import requests
import logging
from dotenv import load_dotenv
import telegram
import telegram.ext


load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler('main.log',
                                               maxBytes=1048576,
                                               backupCount=3)
handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(handler)
logger.addHandler(console_handler)

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


def check_tokens():
    """Провека наличия переменных окружения."""
    if not PRACTICUM_TOKEN:
        logger.critical('Отсутствует обязательная переменная YP_API.')
        return False
    elif not TELEGRAM_TOKEN:
        logger.critical('Отсутствует обязательная переменная TG_API.')
        return False
    elif not TELEGRAM_CHAT_ID:
        logger.critical('Отсутствует обязательная переменная chatid.')
        return False
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        response = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f"Сообщение отправлено. Ответ сервера: {response}")
    except Exception as error:
        logger.error(f"Сбой при отправке сообщения: {error}")


def get_api_answer(timestamp: int) -> dict:
    """Запрос к эндпоинту."""
    params = {'from_date': timestamp}
    try:
        # Получаем список со всей домашкой в dict.
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params)
        # Проверяем, был ли успешный запрос к API.
        if not 200 <= homework_statuses.status_code < 300:
            error_message = (f'Запрос к API завершился с ошибкой '
                             f'{homework_statuses.status_code}')
            logger.error(error_message)
            return {}

        # Проверяем, есть ли ключ 'homeworks' в ответе.
        if 'homeworks' not in homework_statuses.json():
            error_message = 'В ответе API отсутствует ключ "homeworks"'
            logger.error(error_message)
            return {}

        # Получаем список только с домашками.
        response = homework_statuses.json()['homeworks'][0]

        return response

    except requests.exceptions.RequestException as error:
        logger.error(f"Ошибка запроса к API: {error}")
        return {}

    except Exception as error:
        logger.error(f"Ошибка получения ответа: {error}")
        return {}


def check_response(response: dict):
    """Проверка ответа API на соответствие документации."""
    try:
        if not isinstance(response, dict):
            error_message = 'Некорректный тип данных в ответе API'
            logger.error(error_message)
            raise TypeError(error_message)

        if 'status' not in response:
            error_message = 'В ответе API отсутствует поле "status"'
            logger.error(error_message)
            raise KeyError(error_message)

        if 'homework_name' not in response:
            error_message = 'В ответе API отсутствует поле "homework_name"'
            logger.error(error_message)
            raise KeyError(error_message)

    except Exception as error:
        logger.error(f"Ошибка проверки ответа: {error}")


def parse_status(homework: dict) -> str:
    """Извлекаем статус домашней работы."""
    status = homework['status']

    if status not in HOMEWORK_VERDICTS:
        error_message = f'Неизвестный статус: {status}'
        logger.error(error_message)
        return error_message

    verdict = HOMEWORK_VERDICTS[status]
    homework_name = homework['homework_name']
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def main():
    """Основная логика работы бота."""
    print('Бот запущен!\nДля выключения бота нажмите CTRL + C')
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    # timestamp = 1549962000
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response:
                homework = response
                message = parse_status(homework)
                send_message(bot, message)
                timestamp = homework['date_updated']

            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)
            continue


if __name__ == '__main__':
    main()
