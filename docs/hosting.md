# Просмотр и деплой без Docker

Git **хранит код**, но не запускает приложение. Чтобы другой человек открыл проект в браузере **без Docker**, есть два уровня.

## 1. Демо интерфейса (GitHub Pages) — рекомендуется для «просто посмотреть»

После включения Pages в репозитории workflow `.github/workflows/github-pages.yml` публикует папку `frontend/`.

**URL (пример для публичного репозитория):**  
https://mckotello.github.io/leadhunter-ai/

На GitHub Pages включён **демо-режим**:

- dashboard, поиск, лиды и карточка работают на **примерных данных**;
- backend (PostgreSQL, Celery, AI) **не нужен**;
- локально тот же режим: http://localhost:8080/?demo=1

### Как включить (один раз, владелец репозитория)

1. GitHub → репозиторий **leadhunter-ai** → **Settings** → **Pages**.
2. **Build and deployment** → Source: **GitHub Actions**.
3. Дождаться успешного workflow **Deploy GitHub Pages** после push в `main`.
4. Отправить ссылку `https://<user>.github.io/leadhunter-ai/` коллеге.

## 2. Полная система (backend + БД) — без Docker у зрителя

Зрителю по-прежнему **не нужен Docker** — нужен только браузер. Развернуть backend один раз можно из того же GitHub-репозитория:

| Платформа | Что даёт | Сложность |
|-----------|----------|-----------|
| [Render](https://render.com) | Web + PostgreSQL + Redis (платные/ free tier меняется) | средняя |
| [Railway](https://railway.app) | Compose-подобный деплой из Git | средняя |
| VPS + `docker compose up` | полный контроль | выше |

Минимальный набор сервисов: **API**, **Celery worker**, **PostgreSQL**, **Redis**, прокси/static (nginx или CDN для `frontend/`).

Переменные — из `.env.example`. После деплоя укажите URL API в `CORS_ORIGINS`.

## 3. Локально без Docker (для разработчика)

Требуются установленные **Python 3.12**, **PostgreSQL**, **Redis**:

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
# отдельный терминал:
celery -A app.tasks.celery_app worker
```

Frontend: открыть файлы из `frontend/` или раздать через nginx. Без backend API не работает (кроме `?demo=1`).

## Что выбрать

| Цель | Решение |
|------|---------|
| Показать UI заказчику | GitHub Pages |
| Потестировать поиск и AI | Docker локально или облачный деплой |
| Только код | Клонировать репозиторий с GitHub |
