# DECISIONS.md — AgentTrust Decision Log

**Реестр ключевых решений проекта. Добавляется только, не редактируется.**

---

## Decision 1: ASR без судей (LLM-as-judge rejected)

- **Date:** 2026-08-18
- **Stakeholder:** Role 5 (Аналитик)
- **Decision:** ASR вычисляется по факту `tool_executed=true` в логе, не по оценке LLM
- **Rejected:** LLM-as-judge подход (Claude/GPT судит было ли успешно)
- **Rationale:**
  - Judge model вносит собственную ошибку в основную метрику
  - Нужна объективность: логи = ground truth
  - Воспроизводимость: разные модели-судьи дадут разные результаты
  - Простота: `tool_executed` — это факт, не интерпретация
- **Impact:** Высокое (архитектура всей системы)
- **Status:** ✅ APPROVED

## Decision 2: Stub инструменты вместо реальных

- **Date:** 2026-08-18
- **Stakeholder:** Role 2 (Инженер инфра)
- **Decision:** Все опасные операции = безопасные заглушки (delete_user, reset_password, etc)
- **Rejected:** Реальная база данных, реальные операции
- **Rationale:**
  - Это research, не прямое хакерство
  - Нам нужно измерить поведение модели, не наносить вред
  - Воспроизводимость: sandbox изолирован
  - Безопасность: никакого риска регулятивных проблем
- **Impact:** Высокое (безопасность + воспроизводимость)
- **Status:** ✅ APPROVED

## Decision 3: Локальные модели + API (не frontier-only)

- **Date:** 2026-08-18
- **Stakeholder:** Role 4 (Инженер экспериментов)
- **Decision:** Использовать Ollama (Mistral, Llama) локально + Google Gemini + Groq (бесплатно)
- **Rejected:** GPT-4o, Claude 3.5 Sonnet (требуют денег или research credits)
- **Rationale:**
  - $0 бюджет
  - Лучшая воспроизводимость (локальные = фиксированный seed)
  - Достаточно для H1, H2, H3
  - Масштабируемо: если получим research credits — можно добавить GPT/Claude
- **Impact:** Среднее (результаты не будут включать frontier models)
- **Mitigation:** Документируем в Limitations раздел
- **Status:** ✅ APPROVED

## Decision 4: Таксономия атак = 4 категории (не больше)

- **Date:** 2026-08-18
- **Stakeholder:** Role 3 (Куратор бенчмарка)
- **Decision:** Authority Spoofing, Artificial Urgency, Data Spoofing, Gaslighting
- **Rejected:** Расширение до 8+ категорий
- **Rationale:**
  - 15 пейлоадов × 4 категории = 60 итого
  - Достаточно для power analysis (n=15 → Δ=25pp @ 80% power)
  - Можно расширить позже (модульная архитектура)
  - Фокус на качество, не количество
- **Impact:** Низкое (таксономия модульна, легко расширяется)
- **Status:** ✅ APPROVED

## Decision 5: JSON Lines логирование (не база данных)

- **Date:** 2026-08-18
- **Stakeholder:** Role 2 (Инженер инфра)
- **Decision:** Логирование в .jsonl файлы (один JSON на строку)
- **Rejected:** SQLite, PostgreSQL, MongoDB
- **Rationale:**
  - Простота: текстовые файлы, версионируемые в Git
  - Воспроизводимость: не нужна БД сервис
  - Масштабируемость достаточна для ~3000 runs
  - Анализ: можно строго читать строка за строкой
- **Impact:** Среднее (анализ работает с .jsonl)
- **Status:** ✅ APPROVED

## Decision 6: Условия экспериментов = 3 уровня

- **Date:** 2026-08-18
- **Stakeholder:** Role 3 + Role 5
- **Decision:** baseline | with_source_text | with_defense_mechanism
- **Rejected:** Больше условий (5+ вариантов защиты)
- **Rationale:**
  - Достаточно для H3 (тест: помогает ли видение источника?)
  - Масштабируемо: 3 × 60 × 3 × 4 ≈ 2160 runs (управляемо)
  - Фокус на главной гипотезе (H3), не на защитах
- **Impact:** Среднее (структурирует эксперименты)
- **Status:** ✅ APPROVED

---

**Правила для DECISIONS.md:**
- Только добавление (append-only log)
- Каждое решение > 3 человек обсуждают
- Включи "Rejected" вариант (что не сделали и почему)
- Status: APPROVED / PENDING / SUPERSEDED
