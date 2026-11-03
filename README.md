# LeadHunter AI

Pet-проект платформы автоматизированного поиска и квалификации B2B-лидов.

## Возможности MVP

- Поисковые задачи (Search Agent + mock/SerpAPI)
- Парсинг сайтов (HTTPX + BeautifulSoup)
- AI-анализ, скоринг и генерация черновиков предложений (OpenAI-compatible / Ollama)
- CRM-интерфейс: dashboard, лиды, карточка, статусы, экспорт CSV/XLSX
- Фоновая обработка через Celery + Redis
- PostgreSQL, Alembic, Docker Compose

## Просмотр без Docker (для коллег)

**GitHub Pages** публикует интерфейс с **демо-данными** (без backend):

1. В репозитории: **Settings → Pages → Source: GitHub Actions**.
2. После push в `main` откройте: **https://mckotello.github.io/leadhunter-ai/**

Локально тот же демо-режим: http://localhost:8080/?demo=1

Подробнее: [docs/hosting.md](docs/hosting.md)

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
```

Откройте [http://localhost:8080](http://localhost:8080).

**Презентация и проверка:** [presentation.html](http://localhost:8080/presentation.html) · [docs/verification-guide.md](docs/verification-guide.md)

API документация: [http://localhost:8080/docs](http://localhost:8080/docs)

## Конфигурация

| Переменная | Назначение |
|---|---|
| `SEARCH_PROVIDER` | `mock` (по умолчанию) или `serpapi` |
| `SERPAPI_API_KEY` | Ключ SerpAPI при реальном поиске |
| `LLM_BASE_URL` | URL OpenAI-compatible API (Ollama: `http://host.docker.internal:11434/v1`) |
| `LLM_MODEL` | Имя модели |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Учётные данные PostgreSQL (Docker Compose) |
| `CORS_ORIGINS` | Разрешённые origin через запятую (без `*` при credentials) |
| `HTTP_MAX_REDIRECTS` | Лимит redirect при безопасном парсинге |

При недоступности LLM включаются эвристические fallback-ответы. SerpAPI и LLM логируют сетевые/HTTP ошибки и не подменяют реальные провайдеры mock-данными.

## Локальная разработка backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

## Архитектура агентов

```
Orchestrator
 ├── SearchAgent
 ├── ParserAgent
 ├── AIAnalystAgent
 ├── ScoringAgent
 └── OfferAgent
```

## Демо-сценарий

1. Откройте «Поиск», задайте нишу/регион/limit 20.
2. Дождитесь статуса `completed`.
3. Перейдите в «Лиды», отсортируйте по score.
4. Откройте карточку, сгенерируйте предложение.
5. Экспортируйте CSV.

## Ограничения

- SSRF-фильтрация URL, проверка DNS и каждого redirect при парсинге.
- Автоотправка сообщений не реализована — только черновики.
- Playwright подключён в ТЗ как опция; MVP использует HTTPX (JS-страницы можно добавить отдельным провайдером).
