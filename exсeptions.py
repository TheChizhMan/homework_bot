class TheAnswerIsNot200Error(Exception):
    """Ответ сервера не 200."""

    pass


class EmptyDictionaryOrListError(Exception):
    """Пустой словарь или список."""

    pass


class UndocumentedStatusError(Exception):
    """Неизвестный статус."""

    pass


class RequestExceptionError(Exception):
    """Ошибка запроса."""

    pass


class NotTokenException(Exception):
    """Отсутствет или неверный токен."""

    pass
