# Setup and deployment

## Local setup

Use Python 3.12 or 3.13. Django 5.1 does not run on Python 3.14.

```
python -m venv venv
venv/Scripts/python -m pip install -r requirements.txt cryptography django-ckeditor-5
cp .env.example .env
venv/Scripts/python manage.py migrate
venv/Scripts/python manage.py runserver
```

`requirements.txt` does not yet list `cryptography` and `django-ckeditor-5`, and the app needs them to start.

## Tests

```
python manage.py test typingtest typingApp blog
node --test typingtest/engine.test.js
```

## Production deployment

1. Compare each file with the server first. The server has held changes the local copy lacked.
2. Back up the database with SQLite's backup API, and copy the files being replaced.
3. Upload only the changed files.
4. Run `manage.py migrate typingtest`. Name the app, because `games` has unrelated pending model changes.
5. Run `manage.py collectstatic --noinput`.
6. Run `touch tmp/restart.txt`.
7. Check the pages. Just after a restart, an old worker may briefly answer with old pages.

Do not commit `TapTapTyping/settings.py` while it holds a Google secret.

## Opening a language to search engines

Approve all of the language's word lists and paragraphs in the admin. Its pages then drop `noindex` and join the sitemap automatically.
