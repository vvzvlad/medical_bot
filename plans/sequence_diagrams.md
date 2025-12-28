# Диаграммы последовательности для ключевых сценариев

## Сценарий 1: Добавление медикамента через LLM

```mermaid
sequenceDiagram
    participant U as User
    participant TG as Telegram Bot
    participant MH as Message Handler
    participant LLM as LLM Integration
    participant GROQ as Groq API
    participant SM as Schedule Manager
    participant DM as Data Manager
    participant FS as File Storage

    U->>TG: "Добавь аспирин 100 мг утром и вечером"
    TG->>MH: process_message()
    MH->>DM: get_user_data(user_id)
    DM->>FS: read user JSON
    FS-->>DM: user_data
    DM-->>MH: current_schedule
    
    MH->>LLM: parse_schedule_command(user_message, current_schedule)
    LLM->>GROQ: POST /chat/completions
    Note over LLM,GROQ: Промпт с текущим расписанием<br/>и командой пользователя
    GROQ-->>LLM: JSON response
    LLM-->>MH: parsed_command
    
    alt Успешный парсинг
        MH->>SM: update_schedule_from_llm(parsed_command)
        SM->>SM: calculate_next_planned_time()
        SM->>DM: add_medication(medication_data)
        DM->>FS: atomic write JSON
        FS-->>DM: success
        DM-->>SM: medication_id
        SM-->>MH: success
        MH->>TG: send_message("✅ Добавлен Аспирин...")
        TG-->>U: Подтверждение
    else Ошибка парсинга
        LLM-->>MH: error_message
        MH->>TG: send_message("❌ Не удалось распознать...")
        TG-->>U: Запрос уточнения
    end
```

---

## Сценарий 2: Отправка напоминания и подтверждение приема

```mermaid
sequenceDiagram
    participant SCH as Scheduler Task
    participant SM as Schedule Manager
    participant DM as Data Manager
    participant NM as Notification Manager
    participant TG as Telegram Bot
    participant U as User
    participant CH as Callback Handler

    loop Каждую минуту
        SCH->>SCH: check_and_notify()
        SCH->>DM: get_all_users()
        DM-->>SCH: [user_ids]
        
        loop Для каждого пользователя
            SCH->>SM: is_in_dnd_period(user_id, current_time)
            SM-->>SCH: false
            
            SCH->>SM: get_pending_medications(user_id, current_time)
            SM->>DM: get_user_data(user_id)
            DM-->>SM: user_data
            SM->>SM: filter medications where<br/>next_planned_time <= current_time<br/>and not taken
            SM-->>SCH: [pending_medications]
            
            alt Есть непринятые медикаменты
                SCH->>NM: send_reminder(user_id, medications)
                NM->>NM: build_reminder_text()
                NM->>NM: build_inline_keyboard()
                NM->>TG: send_message(text, keyboard)
                TG-->>U: 💊 Время принять лекарства:<br/>• Аспирин 100 мг [Принял]
                TG-->>NM: message_id
                
                NM->>DM: update_medication(last_reminder_message_id)
                DM-->>NM: success
            end
        end
    end
    
    Note over U: Пользователь нажимает кнопку "Принял"
    
    U->>TG: callback: "take:med_123"
    TG->>CH: handle_take_medication(callback)
    CH->>DM: mark_taken(user_id, medication_id, timestamp)
    DM->>DM: update last_taken
    DM->>SM: calculate_next_planned_time()
    SM-->>DM: next_planned_time
    DM->>DM: atomic write JSON
    DM-->>CH: success
    
    CH->>DM: get_user_data(user_id)
    DM-->>CH: user_data
    CH->>CH: filter remaining medications<br/>from same reminder
    
    alt Остались непринятые медикаменты
        CH->>NM: update_reminder(message_id, remaining_meds)
        NM->>TG: edit_message_reply_markup()
        TG-->>U: Обновленная клавиатура
        CH->>TG: answer_callback("✅ Отмечено")
    else Все приняты
        CH->>TG: edit_message_text("✅ Все лекарства приняты!")
        TG-->>U: Подтверждение
        CH->>TG: answer_callback("✅ Все принято!")
    end
```

---

## Сценарий 3: Обработка DND режима

```mermaid
sequenceDiagram
    participant SCH as Scheduler Task
    participant SM as Schedule Manager
    participant DM as Data Manager
    participant DND as DND Manager

    SCH->>DM: get_user_data(user_id)
    DM-->>SCH: user_data with dnd_settings
    
    SCH->>SM: is_in_dnd_period(user_id, current_time)
    SM->>DND: check_dnd(user_timezone, current_time, dnd_settings)
    
    Note over DND: Конвертировать current_time<br/>в локальное время пользователя
    DND->>DND: local_time = current_time.astimezone(user_tz)
    
    Note over DND: Проверить попадание в DND окно
    DND->>DND: is_between(local_time, start_time, end_time)
    
    alt Время в DND периоде
        DND-->>SM: true
        SM-->>SCH: true
        
        Note over SCH: Пропустить отправку напоминания
        
        alt postpone_to_end = true
            SCH->>SM: postpone_to_dnd_end(user_id, planned_time)
            SM->>DND: calculate_dnd_end(user_tz, dnd_settings)
            DND-->>SM: dnd_end_time
            SM->>DM: update_medication(next_planned_time = dnd_end_time)
            DM-->>SM: success
        else postpone_to_end = false
            Note over SCH: Просто пропустить,<br/>следующий прием по расписанию
        end
    else Время вне DND периода
        DND-->>SM: false
        SM-->>SCH: false
        Note over SCH: Продолжить обычную<br/>обработку напоминаний
    end
```

---

## Сценарий 4: Расчет следующего времени приема (fixed_times)

```mermaid
sequenceDiagram
    participant DM as Data Manager
    participant SM as Schedule Manager
    participant Med as Medication Data

    Note over DM: Пользователь принял медикамент
    DM->>SM: calculate_next_planned_time(medication, user_tz)
    
    SM->>Med: get schedule_type
    Med-->>SM: "fixed_times"
    
    SM->>Med: get schedule.times
    Med-->>SM: [{hour: 9, minute: 0}, {hour: 21, minute: 0}]
    
    SM->>Med: get last_planned_time
    Med-->>SM: "2024-12-27T06:00:00Z" (09:00 MSK)
    
    Note over SM: Конвертировать в локальное время
    SM->>SM: local_last = last_planned.astimezone(user_tz)
    SM->>SM: current_local = datetime.now(user_tz)
    
    Note over SM: Найти следующее время из списка
    loop Для каждого времени в schedule.times
        SM->>SM: create datetime with hour, minute
        
        alt time > local_last.time()
            SM->>SM: next_time = today at time
            
            alt next_time > current_local
                Note over SM: Нашли следующее время сегодня
                SM->>SM: break loop
            end
        end
    end
    
    alt Не нашли время сегодня
        SM->>SM: next_time = tomorrow at first time
    end
    
    Note over SM: Конвертировать обратно в UTC
    SM->>SM: next_utc = next_time.astimezone(UTC)
    
    SM-->>DM: next_utc
    DM->>Med: update next_planned_time
```

---

## Сценарий 5: Расчет следующего времени приема (interval)

```mermaid
sequenceDiagram
    participant DM as Data Manager
    participant SM as Schedule Manager
    participant Med as Medication Data

    Note over DM: Пользователь принял медикамент
    DM->>SM: calculate_next_planned_time(medication, user_tz)
    
    SM->>Med: get schedule_type
    Med-->>SM: "interval"
    
    SM->>Med: get schedule.interval_hours
    Med-->>SM: 8
    
    SM->>Med: get strict_schedule
    Med-->>SM: false
    
    alt strict_schedule = true
        SM->>Med: get last_planned_time
        Med-->>SM: planned_time
        SM->>SM: base_time = planned_time
    else strict_schedule = false
        SM->>Med: get last_taken
        Med-->>SM: taken_time
        
        alt last_taken exists
            SM->>SM: base_time = taken_time
        else last_taken is null
            SM->>Med: get last_planned_time
            Med-->>SM: planned_time
            SM->>SM: base_time = planned_time
        end
    end
    
    Note over SM: Добавить интервал
    SM->>SM: next_time = base_time + interval_hours
    
    alt Есть preferred_time_windows
        SM->>Med: get preferred_time_windows
        Med-->>SM: [{start: "07:00", end: "23:00"}]
        
        SM->>SM: local_next = next_time.astimezone(user_tz)
        
        alt next_time вне окна
            SM->>SM: Найти ближайшее начало окна
            SM->>SM: next_time = window_start
        end
    end
    
    Note over SM: Проверить DND
    SM->>SM: is_in_dnd = check_dnd(next_time)
    
    alt is_in_dnd and postpone_to_end
        SM->>SM: next_time = dnd_end_time
    end
    
    SM-->>DM: next_time (UTC)
    DM->>Med: update next_planned_time
```

---

## Сценарий 6: Обработка ошибки LLM API

```mermaid
sequenceDiagram
    participant U as User
    participant MH as Message Handler
    participant LLM as LLM Integration
    participant GROQ as Groq API
    participant EH as Error Handler

    U->>MH: "Добавь витамины"
    MH->>LLM: parse_schedule_command()
    
    loop Retry до 3 раз
        LLM->>GROQ: POST /chat/completions
        
        alt Timeout
            GROQ--xLLM: TimeoutException
            LLM->>EH: handle_llm_error(TimeoutException)
            EH->>EH: wait = 2^attempt seconds
            EH->>EH: sleep(wait)
            Note over LLM: Retry запрос
        else Rate Limit (429)
            GROQ-->>LLM: 429 Too Many Requests<br/>Retry-After: 60
            LLM->>EH: handle_llm_error(RateLimitError)
            EH->>EH: wait = Retry-After header
            EH->>EH: sleep(wait)
            Note over LLM: Retry запрос
        else Server Error (5xx)
            GROQ-->>LLM: 500 Internal Server Error
            LLM->>EH: handle_llm_error(ServerError)
            EH->>EH: wait = 2^attempt seconds
            EH->>EH: sleep(wait)
            Note over LLM: Retry запрос
        else Success
            GROQ-->>LLM: 200 OK + JSON
            LLM->>LLM: parse JSON response
            
            alt Валидный JSON
                LLM-->>MH: parsed_command
                MH->>U: "✅ Добавлен..."
            else Невалидный JSON
                LLM->>EH: handle_llm_error(JSONDecodeError)
                EH-->>LLM: error_response
                LLM-->>MH: error_response
                MH->>U: "❌ Не удалось распознать команду"
            end
        end
    end
    
    alt Все retry исчерпаны
        LLM->>EH: get_fallback_response()
        EH-->>LLM: fallback_response
        LLM-->>MH: fallback_response
        MH->>U: "❌ Сервис временно недоступен"
    end
```

---

## Сценарий 7: Повторные напоминания

```mermaid
sequenceDiagram
    participant SCH as Scheduler Task
    participant SM as Schedule Manager
    participant DM as Data Manager
    participant NM as Notification Manager
    participant TG as Telegram Bot
    participant U as User

    Note over SCH: Прошел 1 час с последнего напоминания
    
    SCH->>SM: get_pending_medications(user_id, current_time)
    SM->>DM: get_user_data(user_id)
    DM-->>SM: user_data
    
    loop Для каждого медикамента
        SM->>SM: check if next_planned_time <= current_time
        SM->>SM: check if last_taken < next_planned_time
        
        alt Медикамент не принят
            SM->>SM: check last_notification_time
            
            alt Прошло >= 60 минут
                SM->>SM: add to pending_list
                SM->>SM: increment missed_count
            end
        end
    end
    
    SM-->>SCH: [pending_medications]
    
    alt Есть непринятые медикаменты
        SCH->>NM: send_reminder(user_id, medications)
        
        Note over NM: Формирование текста с опозданием
        NM->>NM: calculate delay for each medication
        NM->>NM: build_reminder_text() with delays
        
        alt Есть активное напоминание
            NM->>TG: edit_message_text(message_id, new_text)
            Note over NM: Обновить существующее сообщение
        else Нет активного напоминания
            NM->>TG: send_message(text, keyboard)
            Note over NM: Отправить новое напоминание
        end
        
        TG-->>U: 💊 Напоминание:<br/>• Аспирин ⏰ опоздание 1 ч 15 мин
        
        NM->>DM: update last_notification_time
        DM-->>NM: success
    end
```

---

## Сценарий 8: Обработка блокировки бота пользователем

```mermaid
sequenceDiagram
    participant SCH as Scheduler Task
    participant NM as Notification Manager
    participant TG as Telegram Bot
    participant TAPI as Telegram API
    participant EH as Error Handler
    participant DM as Data Manager

    SCH->>NM: send_reminder(user_id, medications)
    NM->>TG: send_message(user_id, text, keyboard)
    TG->>TAPI: POST /sendMessage
    
    alt Пользователь заблокировал бота
        TAPI-->>TG: 403 Forbidden<br/>"bot was blocked by the user"
        TG->>EH: handle_send_message_error(error, user_id)
        
        EH->>EH: check error type
        Note over EH: Обнаружена блокировка
        
        EH->>DM: get_user_data(user_id)
        DM-->>EH: user_data
        
        loop Для каждого медикамента
            EH->>DM: update_medication(medication_id, {active: false})
            Note over EH: Мягкое удаление всех медикаментов
        end
        
        EH->>EH: log warning
        Note over EH: "User {user_id} blocked bot,<br/>deactivated all medications"
        
        EH-->>NM: false (не retry)
        NM-->>SCH: failed
        
    else Временная сетевая ошибка
        TAPI--xTG: NetworkError
        TG->>EH: handle_send_message_error(error, user_id, retry=0)
        
        EH->>EH: wait = 2^retry seconds
        EH->>EH: sleep(wait)
        EH-->>NM: true (можно retry)
        
        NM->>TG: send_message(user_id, text, keyboard)
        Note over NM: Повторная попытка
        
    else Rate Limit
        TAPI-->>TG: 429 Too Many Requests<br/>Retry-After: 30
        TG->>EH: handle_send_message_error(error, user_id)
        
        EH->>EH: wait = Retry-After seconds
        EH->>EH: sleep(wait)
        EH-->>NM: true (можно retry)
        
        NM->>TG: send_message(user_id, text, keyboard)
        Note over NM: Повторная попытка после ожидания
    end
```

---

## Легенда

### Участники
- **U (User)**: Пользователь Telegram
- **TG (Telegram Bot)**: Telegram Bot клиент (aiogram)
- **MH (Message Handler)**: Обработчик текстовых сообщений
- **CH (Callback Handler)**: Обработчик callback-запросов
- **LLM (LLM Integration)**: Модуль интеграции с LLM
- **GROQ (Groq API)**: Внешний API Groq
- **SM (Schedule Manager)**: Менеджер расписаний
- **DM (Data Manager)**: Менеджер данных
- **FS (File Storage)**: Файловое хранилище JSON
- **NM (Notification Manager)**: Менеджер уведомлений
- **SCH (Scheduler Task)**: Фоновый планировщик
- **DND (DND Manager)**: Менеджер режима "Не беспокоить"
- **EH (Error Handler)**: Обработчик ошибок
- **TAPI (Telegram API)**: Внешний API Telegram

### Обозначения
- `-->>`: Синхронный ответ
- `->>`: Синхронный вызов
- `--x`: Ошибка
- `Note over`: Комментарий
- `alt/else/end`: Условное ветвление
- `loop/end`: Цикл
