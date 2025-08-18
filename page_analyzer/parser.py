from bs4 import BeautifulSoup


def get_data(response):
    soup = BeautifulSoup(response.text, 'html.parser')
    desc = soup.find('meta', {'name': 'description'})

    result = {
        'status_code': response.status_code,
        'h1': soup.h1.text if soup.h1 else '',
        'title': soup.title.text if soup.title else '',
        'description': desc.get('content') if desc else '',
    }
    return result