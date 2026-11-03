# Полная версия в облаке (Render)

Один публичный URL: **UI + API + PostgreSQL + Redis + Celery worker**.  
Docker на компьютере зрителю **не нужен**.

## Вариант A — Render (рекомендуется)

### 1. Создать Blueprint

1. Зайдите на [render.com](https://render.com) → **New** → **Blueprint**.
2. Подключите репозиторий `mckotello/leadhunter-ai`.
3. Render прочитает [`render.yaml`](../render.yaml) и создаст:
   - PostgreSQL `leadhunter-db`
   - Redis `leadhunter-redis`
   - Web `leadhunter` (FastAPI + статический frontend)
   - Worker `leadhunter-worker` (Celery)

4. Дождитесь статуса **Live** у сервиса **leadhunter** (первый деплой 5–15 мин).

5. Откройте URL вида `https://leadhunter-xxxx.onrender.com` — **полное приложение**.

### 2. Обновить CORS

В Render → сервис **leadhunter** → **Environment**:

```
CORS_ORIGINS=https://mckotello.github.io,https://ВАШ-СЕРВИС.onrender.com
```

Подставьте реальный URL Render. Сохраните → redeploy.

### 3. (Опционально) GitHub Pages → тот же backend

Чтобы на `github.io` работал **не демо**, а живой API:

1. GitHub → repo → **Settings** → **Secrets and variables** → **Actions**.
2. Secret **`LEADHUNTER_API_URL`** = `https://ВАШ-СЕРВИС.onrender.com` (без `/api`).
3. Перезапустите workflow **Deploy GitHub Pages**.

После этого https://mckotello.github.io/leadhunter-ai/ ходит в облачный backend.

### 4. LLM и поиск (по желанию)

В Environment web + worker:

| Переменная | Пример |
|------------|--------|
| `LLM_BASE_URL` | URL OpenAI-compatible API |
| `LLM_API_KEY` | ключ |
| `SEARCH_PROVIDER` | `serpapi` |
| `SERPAPI_API_KEY` | ключ |

Без LLM работают эвристические fallback-ответы.

---

## Вариант B — только Docker локально / на VPS

```bash
docker compose up --build
```

На VPS с публичным IP: откройте порт 8080 или поставьте reverse-proxy + TLS.

---

## Стоимость

Render: PostgreSQL и сервисы на плане **Starter/Basic** — платные (есть trial).  
Для бесплатного эксперимента оставьте **GitHub Pages + demo** или локальный Docker.

---

## Проверка после деплоя

- `GET https://ВАШ-СЕРВIS.onrender.com/health` → `{"status":"ok"}`
- UI: главная, поиск (mock), лиды после задачи
- Worker logs: `search.run_pipeline`
