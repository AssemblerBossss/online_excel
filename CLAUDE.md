
# online_excel — заметки для Claude

Клон Google Sheets: микросервисы + React-фронт. Файл ведётся вручную, чтобы не сканировать проект каждый раз.
Предпочтения пользователя: см. memory (сниппеты в чат, не править исходники без явной просьбы; чистый код; встроенные типы `dict/list`; бизнес-логика в сервисах, не в репо; сервис кидает кастомные исключения).

## Сервисы
- `auth_service` — FastAPI, пользователи/JWT, публикует события (RabbitMQ).
- `table_service` — FastAPI, таблицы/строки/права/экспорт/WS. Основной для формул.
- `chat_service`, `notification_service` (Go) — к формулам отношения не имеют.
- `frontend` — React 18 + Vite + TS, inline-стили (`styles/theme.ts`), без UI-библиотек. Зависит от `mathjs`.
- Gateway: Traefik + traefik-jwt-plugin (заголовки `X-User-*`), api_gateway удалён. Деплой: docker-compose и k8s (minikube).

## table_service (`table_service/app`) — ТЕКУЩЕЕ состояние (строчная модель, до миграции)
Слои: `api/endpoints` -> `services` -> `repository` (через `UnitOfWork`). Redis: кэш дефолтной страницы строк (`rows:table:{id}`, TTL 60с), Pub/Sub события строк (`events:rows:{id}`) -> `api/endpoints/ws.py` (одноразовый ticket в query).
- Модель `TableRow` (`models/data.py`): `id`, `table_id`, `row_data` JSON {имя_колонки: значение}, `formulas` JSON {имя_колонки: "=..."} | NULL, `created_at`, `updated_at`. **Нет поля порядка** — порядок = `id`/сортировка запроса.
- `DataTable.columns_schema`: list[{name, type, required, ...}]. **Колонки неизменяемы после создания** (PATCH таблицы меняет только name/description/is_public). Типы: string/number/boolean/date/datetime.
- Эндпоинты `/data/{table_id}/rows`: GET (skip/limit<=1000, sort_by, sort_order, `filter=field:op:value`), POST, PUT `/{row_id}`, DELETE, `bulk-delete`, `/{row_id}/duplicate`. Пакетного update **нет**.
- `DataService.update_table_row`: проверка write-доступа -> `DataValidationService.validate_row_data` по `row_data` (числовая колонка отвергает нечисловую строку, в т.ч. `#DIV/0!`) -> repo update (перезаписывает row_data+formulas целиком, last-write-wins, без версии) -> инвалидация кэша -> `RowEventPublisher` (событие содержит полную строку).
- Бэкенд формулы **не вычисляет**, только хранит. Серверные фильтры/сортировка (`repository/data.py`, cast в Numeric) и экспорт XLSX (`export_job.py`, стримит `row_data` чанками) работают по сохранённым значениям, не по формулам.
- `duplicate_table_row` и `copy_rows` копируют `formulas` дословно (при A1-адресах ссылки не сдвигаются).
- Импорт Excel (`excel_processor.py`, pandas) формул не читает, только значения.

## frontend — ТЕКУЩЕЕ состояние (до миграции)
- `src/api/tables.ts`: `evaluateFormula` (mathjs + `new Function` для строк), `isFormula`, `tablesAPI`. Семантика ссылок сейчас: `A5` = колонка A **этой же строки** (цифра игнорируется), буква = индекс в `columns_schema`.
- `src/pages/TableViewPage.tsx` (~770 строк, монолит): серверная пагинация PAGE_SIZE=50, сорт/фильтры серверные, `commitEdit` считает формулу и шлёт PUT одной строки, оптимистичный апдейт.
- `src/api/ws.ts`: `subscribeToTableEvents`; страница на любое событие делает debounce-перезагрузку страницы (событие с `row` не применяется точечно).
- Номер строки в UI = `page*PAGE_SIZE + index + 1` (не адрес).

## План: лист как в Google Sheets (HyperFormula + Glide Data Grid) — код НЕ внесён
Полный пошаговый мануал с номерами строк и всем кодом: **`SHEETS_MIGRATION.md`** (корень репо). Код в нём собран и проверен в отдельной копии (scratchpad, не в репо).
Ключевые решения:
- Хранение: `sheet_cells(table_id,row,col PK; raw text; value jsonb; style jsonb)`, только непустые ячейки, координаты 0-based. `data_tables`: `revision`, `layout_revision`, `sheet_meta jsonb` (ширины колонок, `col_styles`/`row_styles`, `frozen_cols`). `columns_schema` и `table_rows` удаляются (данные не переносятся).
- Формулы считает **клиент** (HyperFormula 3.5.0, GPL-3.0, `licenseKey:'gpl-v3'`); сервер хранит `raw` и присланное `value`, не вычисляет. Клиент шлёт только diff против «зеркала» состояния сервера.
- API: `GET /data/{id}/sheet` (снимок `[row,col,raw,value,style]`), `POST /data/{id}/sheet/batch` ({structural?, cells, styles, meta, base_layout_revision}). Префикс `/data` — Traefik/nginx не менять. WS-канал `events:sheet:{id}`, события `batch`/`reload` (>2000 элементов), порядок по `revision`.
- Конкурентность: `SELECT ... FOR UPDATE` по таблице в пакете, `FOR SHARE` при снимке; устаревший `layout_revision` -> 409.
- Сдвиг строк/колонок в SQL делается в два шага через отрицательные индексы (PK в PostgreSQL проверяется построчно).
- UI: Glide Data Grid 6.0.3 (canvas, MIT; нужны peer-deps lodash, marked, react-responsive-carousel и `<div id="portal">` в index.html), `SheetEngine` (`frontend/src/sheet/engine.ts`), хук `useSheet`.
Факты о HyperFormula 3.5.0, проверенные руками (не угадывать заново):
- Функций ~423 (enGB). Есть XLOOKUP, FILTER, SORT, UNIQUE, SEQUENCE, ARRAYFORMULA, TEXTJOIN, IFS, SWITCH, SPLIT, MAXIFS. Нет QUERY, IMPORTRANGE, REGEXMATCH, XMATCH, LET, LAMBDA, CONCAT.
- Локаль ruRU регистрируется (`hyperformula/i18n/languages`), но `=СУММ(1;2)` даёт parse error — берём английские имена и `,`.
- `"2024-01-05"` по умолчанию строка; даты парсятся только по `dateFormats` (у нас `DD.MM.YYYY`, `YYYY-MM-DD`, `DD/MM/YYYY`). `"007"` -> число 7 (как в Sheets).
- `addRows/removeRows/addColumns/removeColumns` возвращают список изменённых **значений**, а переписанные формулы (текст) в нём нет — поэтому diff считается сравнением с зеркалом.
- «Разлитые» ячейки массива: `getCellType` = `ARRAY`, у них нет своего raw; в БД хранятся как raw=NULL,value=...; в движок при загрузке не кладутся.
- Внутри `hf.batch()` чтение (`getCellSerialized`, `getCellType`) запрещено (EvaluationSuspendedError); `batch()` возвращает список изменений, а `setCellContents` внутри возвращает [].
- `hf.copy/paste` сдвигают относительные ссылки; `getCellValue` возвращает `DetailedCellError` (`.value` = '#DIV/0!').
- 50 000 ячеек грузятся ~0,5 с, правка ~0,15 с (Node).
Факты о Glide: `onPaste` вернуть `false` и вставлять самому; Ctrl+X нет; в Playwright первый символ после клика теряется — сначала `Enter`, пауза, потом ввод.
Проверено: alembic upgrade/downgrade/check на PG16, смоук-скрипт сервиса на PG, ruff, pytest импорта/экспорта, движок и очередь в Node, vite build, Playwright с поддельным бэкендом. НЕ проверено: WS на живом Redis с двумя браузерами, Docker/k8s сборка, старые тесты (список поломок в мануале, этап 9).
