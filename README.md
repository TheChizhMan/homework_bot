# Homework Telegram Bot

## Описание

Этот Telegram бот использует API Яндекс.Практикума и Telegram Bot API для получения результата проверки домашних работ в ваш аккаунт Telegram.

## Как использовать

1. Создайте виртуальное окружение

```
python3 -m venv env
```

2. Активируйте его

```
source env/bin/activate
```

3. Установите зависимости

```
pip install -r requirements.txt
```

4. Запустите исполняемый файл

```
python homework.py
```

5. Добавьте бота в свой аккаунт Telegram и отправьте ему /start

## Требования

- Python 3.9.6
- requests==2.26.0
- python-dotenv==0.19.0
- python-telegram-bot==13.7
- logging==0.5.1.2

## Автор

Игорь Чиж