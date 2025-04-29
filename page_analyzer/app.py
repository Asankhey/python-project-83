from flask import Flask, render_template, request, redirect, url_for, flash
from urllib.parse import urlparse
import os
import psycopg2
from psycopg2.errors import UniqueViolation
from dotenv import load_dotenv
from datetime import datetime
import validators

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
        flash('Invalid URL', 'danger')
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
                flash('Page successfully added', 'success')
                return redirect(url_for('show_url', id=url_id))
    except UniqueViolation:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM urls WHERE name = %s", (normalized_url,))
                url_id = cur.fetchone()[0]
                flash('Page already exists', 'info')
                return redirect(url_for('show_url', id=url_id))


@app.route('/urls/<int:id>')
def show_url(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM urls WHERE id = %s", (id,))
            row = cur.fetchone()
            url = dict(id=row[0], name=row[1], created_at=row[2])
    return render_template('url.html', url=url)
