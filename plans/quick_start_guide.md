# Краткое руководство по разработке Medication Bot

## Быстрый старт

### Порядок разработки модулей

Рекомендуемая последовательность реализации для минимально работающего прототипа:

```
1. Config & Logging (1-2 часа)
   └─> src/config.py
   └─> src/logging_config.py

2. Data Manager (2-3 часа)
   └─> src/data_manager.py
   └─> Тесты: tests/test_data_manager.py

3. Schedule Manager (3-4 часа)
   └─> src/schedule_manager.py
   └─> Тесты: tests/test_schedule_manager.py

4. Basic Bot Structure (1-2 часа)
   └─> src/bot.py
   └─> main.py

5. Message Handler (2-3 часа)
   └─> src/handlers/message_handler.py
   └─> Базовые команды: /start, /help, /list

6. Notification Manager (2-3 часа)
   └─> src/notification_manager.py

7. Callback Handler (1-2 часа)
   └─> src/handlers/callback_handler.py

8. Scheduler Task (2-3 часа)
   └─> src/scheduler.py

9. LLM Integration (3-4 часа)
   └─> src/llm_integration.py

10. Error Handlers (2-3 часа)
    └─> src/error_handlers.py

11. Monitoring (1-2 часа)
    └─> src/monitoring.py
```

**Общее время разработки MVP**: ~20-30 часов

---

## Минимальный MVP (Фаза 1)

### Цель
Базовый функционал без LLM - добавление медикаментов через команды, напоминания, подтверждение приема.

### Что включить

#### 1. Структура данных
```json
{
  "user_id": 123456789,
  "timezone": "Europe/Moscow",
  "dnd_settings": {
    "enabled": false,
    "start_time": "23:00",
    "end_time": "07:00",
    "postpone_to_end": true
  },
  "medications": []
}
```

#### 2. Команды бота
- `/start` - Приветствие и инструкции
- `/add <название> <дозировка> <время1> <время2>...` - Добавить медикамент
- `/list` - Показать все медикаменты
- `/delete <id>` - Удалить медикамент
- `/help` - Справка

#### 3. Базовый функционал
- ✅ Хранение данных в JSON
- ✅ Добавление медикаментов с фиксированным временем
- ✅ Отправка напоминаний
- ✅ Подтверждение приема через inline-кнопки
- ✅ Расчет следующего времени приема
- ❌ LLM интеграция (отложить на Фазу 2)
- ❌ DND режим (отложить на Фазу 2)
- ❌ Интервальные приемы (отложить на Фазу 2)

### Пример использования MVP

```
Пользователь: /start
Бот: Привет! Я помогу вам не забывать принимать лекарства.
     Используйте /add для добавления медикамента.

Пользователь: /add Аспирин 100мг 09:00 21:00
Бот: ✅ Добавлен Аспирин 100мг
     Напоминания: 09:00, 21:00

[В 09:00]
Бот: 💊 Время принять лекарства:
     • Аспирин 100мг
     [Кнопка: Принял]

Пользователь: [нажимает "Принял"]
Бот: ✅ Отмечено! Следующий прием в 21:00
```

---

## Расширенная версия (Фаза 2)

### Дополнительный функционал
- ✅ LLM интеграция для естественноязыковых команд
- ✅ DND режим
- ✅ Интервальные приемы
- ✅ Повторные напоминания
- ✅ Статистика приема
- ✅ Экспорт/импорт расписания

---

## Ключевые файлы для старта

### 1. [`src/config.py`](src/config.py)

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str
    
    # Groq LLM (опционально для MVP)
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_timeout: int = 30
    groq_max_retries: int = 3
    
    # Application
    log_level: str = "INFO"
    data_dir: str = "data/users"
    scheduler_interval_seconds: int = 60
    reminder_repeat_interval_hours: int = 1
    
    # Timezone
    default_timezone: str = "Europe/Moscow"
    
    # DND defaults
    default_dnd_enabled: bool = False
    default_dnd_start: str = "23:00"
    default_dnd_end: str = "07:00"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 2. [`src/data_manager.py`](src/data_manager.py) - Основные методы

```python
class DataManager:
    async def get_user_data(self, user_id: int) -> dict:
        """Получить данные пользователя."""
        
    async def save_user_data(self, user_id: int, data: dict) -> bool:
        """Сохранить данные пользователя."""
        
    async def add_medication(self, user_id: int, medication: dict) -> str:
        """Добавить медикамент. Возвращает medication_id."""
        
    async def mark_taken(self, user_id: int, medication_id: str, taken_at: datetime) -> bool:
        """Отметить прием медикамента."""
```

### 3. [`src/schedule_manager.py`](src/schedule_manager.py) - Основные методы

```python
class ScheduleManager:
    async def calculate_next_planned_time(
        self, 
        medication: dict, 
        user_timezone: str
    ) -> datetime:
        """Рассчитать следующее плановое время приема."""
        
    async def get_pending_medications(
        self, 
        user_id: int, 
        current_time: datetime
    ) -> list[dict]:
        """Получить медикаменты, требующие напоминания."""
```

### 4. [`src/bot.py`](src/bot.py) - Главный класс

```python
class MedicationBot:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.bot = Bot(token=settings.telegram_bot_token)
        self.dp = Dispatcher()
        
        # Инициализация компонентов
        self.data_manager = DataManager(settings.data_dir)
        self.schedule_manager = ScheduleManager(self.data_manager)
        self.notification_manager = NotificationManager(
            self.bot, 
            self.schedule_manager
        )
        self.scheduler = MedicationScheduler(
            self.data_manager,
            self.schedule_manager,
            self.notification_manager
        )
        
        # Регистрация handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрация обработчиков."""
        from src.handlers import message_handler, callback_handler
        self.dp.include_router(message_handler.router)
        self.dp.include_router(callback_handler.router)
    
    async def start(self):
        """Запустить бота."""
        # Запустить планировщик
        await self.scheduler.start()
        
        # Запустить polling
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """Остановить бота."""
        await self.scheduler.stop()
        await self.bot.session.close()
```

### 5. [`main.py`](main.py)

```python
import asyncio
from src.config import get_settings
from src.logging_config import setup_logging
from src.bot import MedicationBot

async def main():
    settings = get_settings()
    setup_logging(settings.log_level)
    
    bot = MedicationBot(settings)
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Тестирование

### Структура тестов

```
tests/
├── __init__.py
├── conftest.py                    # Fixtures
├── test_data_manager.py           # Тесты DataManager
├── test_schedule_manager.py       # Тесты ScheduleManager
├── test_notification_manager.py   # Тесты NotificationManager
├── test_llm_integration.py        # Тесты LLM
└── test_scheduler.py              # Тесты Scheduler
```

### Пример теста

```python
# tests/test_data_manager.py
import pytest
from datetime import datetime, timezone
from src.data_manager import DataManager

@pytest.fixture
async def data_manager(tmp_path):
    """Создать DataManager с временной директорией."""
    return DataManager(str(tmp_path))

@pytest.mark.asyncio
async def test_add_medication(data_manager):
    """Тест добавления медикамента."""
    user_id = 123456789
    
    medication = {
        "name": "Аспирин",
        "dosage": "100 мг",
        "schedule_type": "fixed_times",
        "schedule": {
            "times": [{"hour": 9, "minute": 0}]
        }
    }
    
    med_id = await data_manager.add_medication(user_id, medication)
    
    assert med_id.startswith("med_")
    
    user_data = await data_manager.get_user_data(user_id)
    assert len(user_data["medications"]) == 1
    assert user_data["medications"][0]["name"] == "Аспирин"

@pytest.mark.asyncio
async def test_mark_taken(data_manager):
    """Тест отметки приема."""
    user_id = 123456789
    
    medication = {
        "name": "Аспирин",
        "dosage": "100 мг",
        "schedule_type": "fixed_times",
        "schedule": {
            "times": [{"hour": 9, "minute": 0}]
        }
    }
    
    med_id = await data_manager.add_medication(user_id, medication)
    taken_at = datetime.now(timezone.utc)
    
    success = await data_manager.mark_taken(user_id, med_id, taken_at)
    
    assert success
    
    user_data = await data_manager.get_user_data(user_id)
    med = user_data["medications"][0]
    assert med["last_taken"] is not None
```

### Запуск тестов

```bash
# Установить pytest
pip install pytest pytest-asyncio

# Запустить все тесты
pytest

# Запустить с покрытием
pytest --cov=src --cov-report=html

# Запустить конкретный тест
pytest tests/test_data_manager.py::test_add_medication
```

---

## Чек-лист разработки

### Фаза 1: MVP (Базовый функционал)

- [ ] Настроить окружение и зависимости
- [ ] Создать структуру проекта
- [ ] Реализовать [`src/config.py`](src/config.py)
- [ ] Реализовать [`src/logging_config.py`](src/logging_config.py)
- [ ] Реализовать [`src/data_manager.py`](src/data_manager.py)
  - [ ] `get_user_data()`
  - [ ] `save_user_data()`
  - [ ] `add_medication()`
  - [ ] `update_medication()`
  - [ ] `delete_medication()`
  - [ ] `mark_taken()`
- [ ] Написать тесты для DataManager
- [ ] Реализовать [`src/schedule_manager.py`](src/schedule_manager.py)
  - [ ] `calculate_next_planned_time()` для fixed_times
  - [ ] `get_pending_medications()`
- [ ] Написать тесты для ScheduleManager
- [ ] Реализовать [`src/bot.py`](src/bot.py)
- [ ] Реализовать [`src/handlers/message_handler.py`](src/handlers/message_handler.py)
  - [ ] `/start` команда
  - [ ] `/help` команда
  - [ ] `/add` команда
  - [ ] `/list` команда
  - [ ] `/delete` команда
- [ ] Реализовать [`src/notification_manager.py`](src/notification_manager.py)
  - [ ] `send_reminder()`
  - [ ] `build_reminder_text()`
  - [ ] `build_inline_keyboard()`
- [ ] Реализовать [`src/handlers/callback_handler.py`](src/handlers/callback_handler.py)
  - [ ] Обработка `take:{medication_id}`
- [ ] Реализовать [`src/scheduler.py`](src/scheduler.py)
  - [ ] Фоновая задача проверки
  - [ ] `check_and_notify()`
- [ ] Создать [`main.py`](main.py)
- [ ] Протестировать MVP вручную
- [ ] Создать Docker образ
- [ ] Развернуть и протестировать в продакшене

### Фаза 2: Расширенный функционал

- [ ] Реализовать [`src/llm_integration.py`](src/llm_integration.py)
  - [ ] `parse_schedule_command()`
  - [ ] Retry-логика
  - [ ] Обработка ошибок
- [ ] Добавить естественноязыковые команды в message_handler
- [ ] Реализовать DND режим в ScheduleManager
  - [ ] `is_in_dnd_period()`
  - [ ] `postpone_to_dnd_end()`
- [ ] Добавить команды управления DND
  - [ ] `/dnd_on`
  - [ ] `/dnd_off`
  - [ ] `/dnd_settings`
- [ ] Реализовать интервальные приемы
  - [ ] `calculate_next_planned_time()` для interval
  - [ ] Поддержка `strict_schedule`
  - [ ] Поддержка `preferred_time_windows`
- [ ] Реализовать повторные напоминания
- [ ] Реализовать [`src/error_handlers.py`](src/error_handlers.py)
  - [ ] `TelegramErrorHandler`
  - [ ] `LLMErrorHandler`
  - [ ] `FileSystemErrorHandler`
- [ ] Реализовать [`src/monitoring.py`](src/monitoring.py)
  - [ ] `HealthMonitor`
  - [ ] `/health` команда
- [ ] Добавить статистику
  - [ ] `/stats` команда
- [ ] Добавить экспорт/импорт
  - [ ] `/export` команда
  - [ ] `/import` команда
- [ ] Написать интеграционные тесты
- [ ] Обновить документацию
- [ ] Развернуть обновленную версию

### Фаза 3: Дополнительные возможности

- [ ] Интеграция с календарем (iCal)
- [ ] Уведомления о заканчивающихся медикаментах
- [ ] Поддержка курсов лечения (начало/конец)
- [ ] Графики соблюдения режима
- [ ] Напоминания близким (опекунам)
- [ ] Мультиязычность
- [ ] Web-интерфейс для управления

---

## Частые проблемы и решения

### Проблема 1: Временные зоны

**Симптом**: Напоминания приходят не в то время

**Решение**:
- Всегда хранить времена в UTC
- Конвертировать в локальное время только для отображения и расчетов
- Использовать `pytz` для работы с временными зонами

```python
import pytz
from datetime import datetime, timezone

# Правильно
utc_time = datetime.now(timezone.utc)
user_tz = pytz.timezone("Europe/Moscow")
local_time = utc_time.astimezone(user_tz)

# Неправильно
local_time = datetime.now()  # Без timezone!
```

### Проблема 2: Атомарность записи

**Симптом**: Данные повреждаются при одновременной записи

**Решение**:
- Использовать временный файл + `os.replace()`
- Блокировки через `asyncio.Lock`

```python
import asyncio
from pathlib import Path

locks = {}

async def atomic_write(filepath: Path, data: dict):
    user_id = filepath.stem
    
    if user_id not in locks:
        locks[user_id] = asyncio.Lock()
    
    async with locks[user_id]:
        temp_path = filepath.with_suffix('.tmp')
        
        # Записать во временный файл
        async with aiofiles.open(temp_path, 'w') as f:
            await f.write(json.dumps(data, indent=2))
        
        # Атомарная замена
        temp_path.replace(filepath)
```

### Проблема 3: Пропущенные напоминания

**Симптом**: Бот не отправляет напоминания

**Возможные причины**:
1. Планировщик не запущен
2. Ошибка в расчете `next_planned_time`
3. Пользователь в DND режиме
4. Бот заблокирован пользователем

**Отладка**:
```python
# Добавить логирование в scheduler
logger.debug(f"Checking user {user_id}")
logger.debug(f"Pending medications: {len(pending_meds)}")
logger.debug(f"In DND: {is_in_dnd}")
```

### Проблема 4: LLM возвращает невалидный JSON

**Симптом**: Ошибка парсинга ответа LLM

**Решение**:
- Использовать `response_format: {"type": "json_object"}` в запросе
- Добавить fallback парсинг с удалением markdown блоков
- Retry с измененным промптом

```python
try:
    result = json.loads(content)
except json.JSONDecodeError:
    # Попробовать удалить markdown блоки
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        result = json.loads(content)
```

---

## Полезные команды

### Разработка

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить бота локально
python main.py

# Запустить тесты
pytest

# Проверить типы
mypy src/

# Форматирование кода
black src/
isort src/

# Линтер
flake8 src/
pylint src/
```

### Docker

```bash
# Собрать образ
docker build -t medication-bot .

# Запустить контейнер
docker run -d --name medication-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  medication-bot

# Просмотр логов
docker logs -f medication-bot

# Остановить и удалить
docker stop medication-bot
docker rm medication-bot

# Docker Compose
docker-compose up -d
docker-compose logs -f
docker-compose down
```

### Мониторинг

```bash
# Просмотр логов в реальном времени
tail -f logs/bot_$(date +%Y-%m-%d).log

# Поиск ошибок
grep ERROR logs/bot_*.log

# Статистика по пользователям
jq '.user_id' data/users/*.json | sort | uniq | wc -l

# Количество активных медикаментов
jq '[.medications[] | select(.active == true)] | length' data/users/*.json
```

---

## Ресурсы

### Документация
- [aiogram 3.x](https://docs.aiogram.dev/en/latest/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Groq API](https://console.groq.com/docs)
- [pytz](https://pythonhosted.org/pytz/)
- [loguru](https://loguru.readthedocs.io/)

### Примеры кода
- [`examples/llm_groq.py`](../examples/llm_groq.py) - Пример интеграции с Groq
- [`examples/main.py`](../examples/main.py) - Пример структуры бота

### Инструменты
- [JSON Schema Validator](https://www.jsonschemavalidator.net/)
- [Cron Expression Generator](https://crontab.guru/)
- [Timezone Converter](https://www.timeanddate.com/worldclock/converter.html)

---

## Контрольные точки

### Milestone 1: Базовая инфраструктура
- ✅ Структура проекта создана
- ✅ Конфигурация работает
- ✅ Логирование настроено
- ✅ DataManager реализован и протестирован

### Milestone 2: Базовый функционал
- ✅ Бот запускается и отвечает на команды
- ✅ Можно добавить медикамент
- ✅ Можно просмотреть список медикаментов
- ✅ Можно удалить медикамент

### Milestone 3: Напоминания
- ✅ Планировщик работает
- ✅ Напоминания отправляются вовремя
- ✅ Можно подтвердить прием через кнопку
- ✅ Следующее время приема рассчитывается правильно

### Milestone 4: LLM интеграция
- ✅ LLM парсит естественноязыковые команды
- ✅ Можно добавить медикамент через текст
- ✅ Можно изменить расписание через текст
- ✅ Обработка ошибок работает

### Milestone 5: Продакшен
- ✅ Docker образ собирается
- ✅ Бот работает в контейнере
- ✅ Логи пишутся корректно
- ✅ Данные персистентны
- ✅ Мониторинг работает

---

## Следующие шаги

После завершения разработки:

1. **Тестирование**
   - Провести нагрузочное тестирование
   - Протестировать edge cases
   - Провести security audit

2. **Документация**
   - Написать пользовательскую документацию
   - Создать FAQ
   - Записать видео-инструкцию

3. **Развертывание**
   - Настроить CI/CD
   - Настроить мониторинг и алерты
   - Настроить резервное копирование

4. **Маркетинг**
   - Создать landing page
   - Опубликовать в каталогах ботов
   - Собрать обратную связь от пользователей

5. **Итерация**
   - Анализировать метрики использования
   - Добавлять запрошенные функции
   - Оптимизировать производительность
