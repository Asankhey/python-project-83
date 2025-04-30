from flask import Flask, render_template, request, redirect, url_for, flash
from urllib.parse import urlparse
import os
import psycopg2
from psycopg2.errors import UniqueViolation
from dotenv import load_dotenv
from datetime import datetime
import validators
import requests

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


def get_connection():
    return psycopg2.connect(DATABASE_URL)


@app.route('/')
def index():
    return render_template('index.html')


@app.post('/urls')
def add_url():
    url = request.form.get('url')

    if not url or not validators.url(url) or len(url) > 255:
        flash('Некорректный URL', 'danger')
        return render_template('index.html'), 422

    parsed_url = urlparse(url)
    normalized_url = f'{parsed_url.scheme}://{parsed_url.netloc}'

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id",
                    (normalized_url, datetime.now())
                )
                url_id = cur.fetchone()[0]
                flash('Страница успешно добавлена', 'success')
                return redirect(url_for('show_url', id=url_id))
    except UniqueViolation:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM urls WHERE name = %s", (normalized_url,))
                url_id = cur.fetchone()[0]
                flash('Страница уже существует', 'info')
                return redirect(url_for('show_url', id=url_id))


@app.route('/urls/<int:id>')
def show_url(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM urls WHERE id = %s", (id,))
            row = cur.fetchone()
            url = dict(id=row[0], name=row[1], created_at=row[2])

            cur.execute(
                "SELECT id, status_code, created_at FROM url_checks WHERE url_id = %s ORDER BY id DESC",
                (id,)
            )
            rows = cur.fetchall()
            checks = [{'id': r[0], 'status_code': r[1], 'created_at': r[2]} for r in rows]

    return render_template('url.html', url=url, checks=checks)


@app.route('/urls/<int:id>/checks', methods=['POST'])
def run_check(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM urls WHERE id = %s", (id,))
            row = cur.fetchone()
            if row is None:
                flash('Страница не найдена', 'danger')
                return redirect(url_for('index'))
            url = row[0]

    try:
        response = requests.get(url)
        response.raise_for_status()
        status_code = response.status_code
    except Exception:
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('show_url', id=id))

    created_at = datetime.now()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO url_checks (url_id, status_code, created_at) VALUES (%s, %s, %s)",
                (id, status_code, created_at)
            )

    flash('Страница успешно проверена', 'success')
    return redirect(url_for('show_url', id=id))


@app.route('/urls')
def urls_list():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.name, u.created_at, MAX(c.created_at), MAX(c.status_code)
                FROM urls u
                LEFT JOIN url_checks c ON u.id = c.url_id
                GROUP BY u.id
                ORDER BY u.id DESC
            """)
            rows = cur.fetchall()
            urls = [{
                'id': r[0],
                'name': r[1],
                'created_at': r[2],
                'last_check': r[3],
                'status_code': r[4]
            } for r in rows]
    return render_template('urls.html', urls=urls)
