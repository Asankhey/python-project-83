from flask import Flask, render_template, request, redirect, url_for, flash
from urllib.parse import urlparse
import os
from psycopg2.errors import UniqueViolation
from dotenv import load_dotenv
import validators
import requests
from bs4 import BeautifulSoup

from page_analyzer import db

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


@app.route('/')
def index():
    return render_template('index.html')


@app.post('/urls')
def add_url():
    url = request.form.get('url')

    if not url or not validators.url(url) or len(url) > 255:
        flash('Некорректный URL', 'danger')
        return render_template('index.html'), 422  # <- Критично для тестов

    parsed_url = urlparse(url)
    normalized_url = f'{parsed_url.scheme}://{parsed_url.netloc}'

    try:
        with db.get_connection(DATABASE_URL) as conn:
            url_id = db.insert_url(conn, normalized_url)
            flash('Страница успешно добавлена', 'success')
    except UniqueViolation:
        with db.get_connection(DATABASE_URL) as conn:
            row = db.find_url_by_name(conn, normalized_url)
            url_id = row['id']
            flash('Страница уже существует', 'info')

    return redirect(url_for('show_url', id=url_id))


@app.route('/urls/<int:id>')
def show_url(id):
    with db.get_connection(DATABASE_URL) as conn:
        url = db.get_url_by_id(conn, id)
        checks = db.get_url_checks(conn, id)

    return render_template('url.html', url=url, checks=checks)


@app.route('/urls/<int:id>/checks', methods=['POST'])
def run_check(id):
    with db.get_connection(DATABASE_URL) as conn:
        url = db.get_url_by_id(conn, id)
        if url is None:
            flash('URL не найден', 'danger')
            return redirect(url_for('index'))

    try:
        response = requests.get(url['name'])
        response.raise_for_status()
        status_code = response.status_code

        soup = BeautifulSoup(response.text, 'html.parser')
        h1_tag = soup.h1.string.strip() if soup.h1 and soup.h1.string else ''
        title_tag = soup.title.string.strip() if soup.title and soup.title.string else ''
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        description = meta_tag['content'].strip() if meta_tag and meta_tag.get('content') else ''
    except Exception:
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('show_url', id=id))

    with db.get_connection(DATABASE_URL) as conn:
        db.insert_check(conn, id, status_code, h1_tag, title_tag, description)

    flash('Страница успешно проверена', 'success')
    return redirect(url_for('show_url', id=id))


@app.route('/urls')
def urls_list():
    with db.get_connection(DATABASE_URL) as conn:
        urls = db.get_all_urls(conn)

    return render_template('urls.html', urls=urls)
