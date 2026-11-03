# LeadHunter AI — проверка системы и демо

Дата последней автоматической проверки: **2026-03-25**

## Результаты проверки (локально)

| Проверка | Статус | Примечание |
|----------|--------|------------|
| `pytest` (backend) | **OK** | 26 passed |
| `docker compose config` | **OK** | синтаксис compose валиден |
| `docker compose up` / E2E | **Не выполнено** | Docker Desktop не запущен на машине проверки |

Для полного прогона: запустите Docker Desktop, затем `docker compose up --build` и пройдите [демо-сценарий](#демо-сценарий-mvp).

---

## Четыре уровня проверки

| Уровень | Что проверяем | Время | Действие |
|---------|---------------|-------|----------|
| 1. Unit / API | SSRF, скоринг, агенты, CORS, Celery, health | ~5 мин | `pytest` |
| 2. Инфра | Postgres, Redis, API, worker, nginx | ~10 мин | `docker compose up` |
| 3. E2E UI | Поиск → лиды → карточка → КП → CSV | ~15 мин | http://localhost:8080 |
| 4. Интеграции | SerpAPI, Ollama/OpenAI, реальные сайты | по необходимости | `.env` |

---

## Автотесты

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

**Модули:**

- `tests/test_ssrf.py` — IP, redirect, DNS rebinding
- `tests/test_scoring.py`, `test_agents.py`, `test_core.py` — бизнес-логика
- `tests/test_api.py`, `test_cors.py`, `test_celery.py` — API и инфра

---

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Проверки:

- http://localhost:8080 — UI
- http://localhost:8080/presentation.html — презентация (этот гайд в слайдах)
- http://localhost:8080/docs — Swagger
- http://localhost:8080/health — health API
- `docker compose ps` — сервисы **healthy**
- логи `worker` — задачи `search.run_pipeline`

---

## Демо-сценарий (MVP)

1. **Поиск:** ниша «оптовая торговля», регион «Москва», limit **20**.
2. Дождаться статуса **completed** на странице поиска.
3. **Лиды:** таблица, ориентир — score.
4. **Карточка:** AI-анализ, расшифровка score, смена статуса.
5. **КП:** сгенерировать черновик (автоотправки нет).
6. **Экспорт:** `/api/export?format=csv`.

`SEARCH_PROVIDER=mock` — без внешнего API. Для боевого прогона: `serpapi` + ключ, LLM через `LLM_BASE_URL`.

---

## API (без UI)

```http
POST /api/search
Content-Type: application/json

{"niche":"опт","region":"Москва","keywords":"","need_type":"other","limit":5}
```

Далее: `GET /api/search/{id}`, `GET /api/leads`, `GET /api/leads/{id}`, `PATCH /api/leads/{id}`, `POST .../analyze`, `POST .../offer`, `GET /api/dashboard`, `GET /api/export?format=csv`.

---

## Безопасность и качество (после аудита)

- Parser: валидация **каждого** redirect; блок private IP / localhost.
- DNS rebinding: повторная DNS-проверка перед каждым HTTP-hop.
- CORS: `CORS_ORIGINS` — явный список, не `*` с credentials.
- Скоринг: актуальность = полнота данных, не «есть сайт».
- LLM / SerpAPI: ошибки логируются; mock не подменяет SerpAPI.

---

## Чеклист перед показом

- [ ] `pytest` — все зелёные
- [ ] `docker compose up` — сервисы healthy
- [ ] Демо-поиск (mock) — лиды в таблице
- [ ] LLM доступна или осознанно fallback
- [ ] CSV открывается в Excel
- [ ] `CORS_ORIGINS` совпадает с URL фронта

---

## Презентация

Интерактивные слайды в репозитории: [frontend/presentation.html](../frontend/presentation.html)  
После запуска Docker: http://localhost:8080/presentation.html
