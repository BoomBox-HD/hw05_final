from datetime import datetime


def year(request) -> int:
    """Добавляет переменную с текущим годом."""
    return{
        'year': datetime.now().year
    }
