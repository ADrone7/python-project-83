from urllib.parse import urlparse

from validators.url import url as is_valid_url


def normalize_url(url):
    parse_result = urlparse(url)
    return f"{parse_result.scheme}://{parse_result.hostname}"


def validate_url(url):
    errors = {}

    if not is_valid_url(url):
        errors['url'] = 'Некорректный URL'
    if url == "":
        errors['url'] = 'URL не может быть пустым'
    if len(url) > 255:
        errors['url'] = 'Слишком длинный URL (должен быть короче 255 символов)'

    return errors
    
    