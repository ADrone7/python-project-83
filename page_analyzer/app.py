import os

from flask import (
    Flask,
    render_template,
)
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

# try:
    # пытаемся подключиться к базе данных
conn = psycopg2.connect(DATABASE_URL)
# except:
#     # в случае сбоя подключения будет выведено сообщение  в STDOUT
#     print('Can`t establish connection to database')

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/urls')
def urls_index():
    with conn.cursor() as curs:
        curs.execute('SELECT id, name FROM urls WHERE name=%s', ('John',))
        curs.fetchall()
    return render_template('urls/index.html')

@app.route('/urls/<int:id>')
def urls_show(id):
    # url = urls_repo.find(id)
    # if not url:
    #     return 'Url not found', 404
    return render_template(
        'urls/show.html',
        # url=url,
    )