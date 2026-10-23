# Мануал: формулы, оформление и «бесконечный» лист как в Google Таблицах

Пошаговая инструкция по переводу проекта со строчной модели (`table_rows` + фиксированные колонки)
на **лист из ячеек**: формулы HyperFormula, выделение диапазонов, заливка и шрифт, копирование со сдвигом
ссылок, вставка/удаление строк и колонок, совместная работа через WebSocket.

> Ничего из этого в репозиторий **ещё не внесено**. Мануал собран из кода, который я написал и
> прогнал в отдельной копии проекта (что именно проверено — в разделе 2). Каждый кусок кода ниже
> скопирован из этой проверенной копии дословно.

## Содержание

1. Что получится и чего не будет
2. Что проверено, а что нет
3. Архитектура
4. Как применять мануал
5. Этап 0. Подготовка
6. Этап 1. База данных и модели
7. Этап 2. Схемы (pydantic) и исключение
8. Этап 3. Репозитории
9. Этап 4. Сервисы (лист, события, импорт и экспорт Excel)
10. Этап 5. API, зависимости, роутер
11. Этап 6. Проверка бэкенда
12. Этап 7. Фронтенд
13. Этап 8. Ручная проверка в браузере
14. Этап 9. Тесты и чистка
15. Что дальше (чего в этой версии нет)
16. Вопросы к вам
17. Приложения: проверочные скрипты

---

## 1. Что получится и чего не будет

**Получится:**

- Лист без жёсткой структуры: колонки `A, B, … ZZ, AAA…` (до 1 000) и строки (до 100 000), в базе хранятся
  только непустые ячейки. Сетка рисуется на canvas (Glide Data Grid), поэтому тормозов на сотнях тысяч
  «виртуальных» ячеек нет. Лист растёт, когда прокручиваешь к краю.
- Формулы HyperFormula (около 420 функций): `=SUM(A1:A10)`, `=IF(...)`, `=VLOOKUP(...)`, `=XLOOKUP(...)`,
  `=FILTER(...)`, `=SORT(...)`, `=UNIQUE(...)`, `=SEQUENCE(...)`, `=ARRAYFORMULA(...)`, `=TEXTJOIN(...)`.
  Ссылки между любыми ячейками, пересчёт зависимых ячеек, ошибки `#DIV/0!`, `#REF!`, `#NAME?`.
- Выделение ячейки/диапазона/целых строк и колонок, строка формул, адрес активной ячейки.
- Оформление: жирный, курсив, цвет текста и заливки, выравнивание, перенос текста, форматы чисел
  (число, процент, валюта, дата, дата и время), закрепление колонок, ширина колонок.
  Оформление целой колонки или строки хранится одной записью, а не миллионом ячеек.
- Копирование и вставка со сдвигом относительных ссылок (`=A1*2` → `=B1*2`) — как в Google Таблицах;
  вставка из внешнего буфера (Excel, Google) как текст/TSV.
- Вставка и удаление строк и колонок: ссылки в формулах пересчитываются (`SUM(A1:A2)` → `SUM(A1:A3)`),
  оформление едет вместе с ячейками.
- Совместная работа: правки видны другим пользователям сразу (WebSocket), события упорядочены,
  потеря соединения лечится перечитыванием листа.
- Импорт `.xlsx` с сохранением формул, значений и базового оформления; экспорт в `.xlsx` с формулами,
  заливкой, шрифтом, форматами чисел.
- Права доступа работают как раньше: читатель видит лист, но не может его менять.

**Не получится (в этой версии):**

- Функции Google без аналога в HyperFormula: `QUERY`, `IMPORTRANGE`, `GOOGLEFINANCE`, `REGEXMATCH`,
  `LET`, `LAMBDA`, `XMATCH`. Полный список функций — в документации HyperFormula.
- Русские имена функций (`=СУММ(...)`): я проверил — локаль `ruRU` в HyperFormula 3.5 регистрируется, но
  выражение `=СУММ(1;2)` она не разобрала (parse error). Используем английские имена и запятую.
- Несколько листов (вкладок) в одной таблице, undo/redo, вырезание (`Ctrl+X`: Glide его не поддерживает —
  используйте копирование и `Delete`), сортировка и фильтры диапазона, границы ячеек, объединение ячеек, условное форматирование, графики, комментарии, подчёркивание и зачёркивание, протягивание
  маркером заполнения. Что нужно, чтобы добавить каждое из них, — в разделе «Что дальше».
- Старые данные не переносятся: таблицы остаются, строки старой модели удаляются миграцией
  (по вашим словам, реальных пользователей нет). Если нужно сохранить — скажите, напишу перенос.

**Лицензии.** HyperFormula — GPL-3.0-only (в коде `licenseKey: 'gpl-v3'`): для учебного/открытого проекта
подходит. Glide Data Grid — MIT. Новых Python-зависимостей нет (`openpyxl` у вас уже есть).

---

## 2. Что проверено, а что нет

Я собрал все изменения в отдельной копии проекта и прогнал:

| Что | Как | Результат |
|---|---|---|
| Миграция БД | `alembic upgrade head` → `downgrade -1` → `upgrade head` → `alembic check` на PostgreSQL 16 | без ошибок, расхождений модели и схемы нет |
| Бэкенд-логика листа | `table_service/scripts/sheet_smoke.py` (приложение A) на настоящем PostgreSQL: запись, вставка/удаление строк и колонок, сдвиг стилей, 409 при устаревшей раскладке, 20 000 ячеек, дубли в пакете, события `batch`/`reload` | OK; сдвиг 20 000 ячеек ≈ 0,4 с |
| Импорт/экспорт xlsx | pytest (приложение C), 4 теста | OK |
| Линтер | `ruff check` и `ruff format` по `table_service/app` | мои файлы чистые (в `permission.py` есть старые замечания, я его не трогал) |
| Движок на HyperFormula | `frontend/scripts/engine-check.ts` (приложение B), Node: загрузка, diff, ошибки, даты, вставка/удаление строк и колонок, копирование со сдвигом ссылок, массивы (`SEQUENCE`), чужие события | OK |
| Очередь отправки и порядок событий | отдельный скрипт на Node: склейка правок, структурная операция в отдельном пакете, чанки по 5 000, дыра в ревизиях → перезагрузка | OK |
| Сборка фронта | `tsc --noEmit` (кроме старых ошибок про `import.meta.env`, они были и раньше), `vite build` | OK |
| Интерфейс | Playwright + Chromium на фронте с поддельным бэкендом: рендер сетки, ввод формулы, пересчёт зависимых, жирный, контекстное меню «вставить строку», строка формул, копирование/вставка со сдвигом ссылок, вставка TSV из буфера | OK, в запросах уходят ровно те diff'ы, что описаны ниже |

**Не проверено (проверьте при приёмке, сценарии в этапе 8):**

- Работа с реальным Redis и двумя браузерами одновременно (WebSocket-события, порядок, переподключение).
  Код рассылки — переименование существующего механизма, но end-to-end я его не запускал.
- Сборка Docker-образов и деплой в minikube.
- Старые тесты (`tests/`) — я их не обновлял, только составил список, что сломается (этап 9).
- Поведение на листах в десятки тысяч занятых ячеек в реальном браузере: движок на 50 000 ячеек грузится
  за ~0,5 с, правка пересчитывается за ~0,15 с (замер в Node), но интерфейс с таким листом я не открывал.
- Ввод «с клавиатуры без Enter»: в автотесте первый символ при наборе сразу после клика терялся (артефакт
  Playwright — редактор Glide открывается асинхронно), с живой клавиатурой должно работать, но проверьте.

---

## 3. Архитектура

### 3.1. Данные

```
data_tables                      sheet_cells                          (пустые ячейки не хранятся)
├─ id, name, ...                 ├─ table_id  ┐
├─ revision          (int)       ├─ row       ├─ PRIMARY KEY, координаты 0-based: A1 = (0, 0)
├─ layout_revision   (int)       ├─ col       ┘
└─ sheet_meta        (jsonb)     ├─ raw       text   то, что ввёл пользователь: "42", "привет", "=SUM(A1:A5)"
                                 ├─ value     jsonb  вычисленное: 42 | "text" | true | {"e": "#DIV/0!"}
                                 └─ style     jsonb  {"bg": "#ffeb3b", "bold": true, "numFmt": "percent", ...}
```

- **`raw` — единственный источник истины.** `value` — кэш: он нужен для экспорта в Excel, будущего поиска и
  быстрого показа. Если `value` разошёлся с `raw`, клиент при загрузке пересчитает и сам пришлёт поправку.
- Ячейка, «разлитая» формулой массива (`=SEQUENCE(3,1)` занимает три ячейки), хранится как `raw = NULL`,
  `value = …`. При загрузке такие ячейки в движок **не** кладутся — их пересоздаёт формула-источник.
- `sheet_meta`: `{"col_widths": {"0": 200}, "frozen_cols": 1, "col_styles": {"2": {"bg": "#eee"}},
  "row_styles": {"0": {"bold": true}}}`. Стиль ячейки сильнее стиля строки, стиль строки сильнее стиля колонки.
- `revision` растёт на каждый принятый пакет изменений (по ней упорядочены WebSocket-события).
  `layout_revision` растёт только при вставке/удалении строк и колонок.
- Лимиты (заданы и на сервере в `schemas/sheet.py`, и на клиенте в `sheet/address.ts`): 100 000 строк,
  1 000 колонок, 20 000 элементов в одном запросе, 50 000 символов в ячейке.

### 3.2. Потоки

```
Браузер                                                      table_service
┌──────────────────────────────────────┐                  ┌───────────────────────────────────────────┐
│ Glide Data Grid (canvas)             │                  │ GET  /data/{id}/sheet       снимок + ревизия │
│   getCellContent ◄── SheetEngine     │ ──── HTTP ─────► │ POST /data/{id}/sheet/batch пакет изменений  │
│                      (HyperFormula,  │                  │   1. права на запись                         │
│                       зеркало, стили,│                  │   2. SELECT ... FOR UPDATE по таблице        │
│                       meta)          │                  │   3. layout_revision совпал? иначе 409       │
│ SyncQueue: один запрос в полёте,     │                  │   4. структурная операция (сдвиг ячеек)      │
│   склейка правок, чанки по 5 000     │                  │   5. upsert ячеек и стилей, чистка пустых    │
│                                      │                  │   6. revision += 1, замена meta              │
│ EventSequencer: события строго по    │ ◄── WebSocket ── │   7. Redis PUBLISH events:sheet:{id}         │
│   revision, дыра > 2 с → перечитать  │                  │      (> 2 000 элементов — событие reload)    │
└──────────────────────────────────────┘                  └───────────────────────────────────────────┘
```

### 3.3. Правила, на которых всё держится

1. **Формулы считает только клиент** (HyperFormula). Сервер хранит и проверяет границы/формат, но не
   вычисляет. Плюс: ноль новых сервисов. Минус: сервер доверяет присланному `value` (для учебного проекта
   нормально; усиление — «Node-воркер пересчёта» в разделе «Что дальше»).
2. **Клиент шлёт не весь лист, а diff.** После каждой операции движок сравнивает ячейки с «зеркалом»
   (последнее состояние, известное серверу) и отправляет только изменившиеся `raw`/`value`. Поэтому правка `A1`
   доставляет на сервер и все зависимые ячейки (`=SUM(A1:A2)` получит новое `value`), а вставка строки —
   только формулы со сдвинутыми ссылками.
3. **Структурная операция — всегда отдельный пакет.** Сервер сдвигает ячейки и стили SQL-ом
   (`row = row + count`), клиент присылает только переписанные формулы уже в новых координатах.
   Сдвиг сделан в два шага через отрицательные индексы, потому что PRIMARY KEY в PostgreSQL проверяется
   построчно — прямой `UPDATE ... SET row = row + 1` упал бы на конфликте ключей.
4. **Пакеты упорядочены блокировкой строки таблицы.** Пока идёт один пакет, остальные ждут
   (`SELECT ... FOR UPDATE`); снимок читается под `FOR SHARE`, поэтому `revision` и ячейки в нём согласованы.
5. **Защита от записи «не туда».** Если пока вы редактировали, коллега вставил строку, ваши координаты
   устарели. Пакет несёт `base_layout_revision`; не совпало с серверным — ответ 409, клиент перечитывает
   лист и показывает сообщение.
6. **Порядок событий.** WebSocket-событие несёт `revision`. Клиент применяет события строго по порядку,
   «дыру» ждёт 2 секунды, потом перечитывает снимок. Собственные события приходят обратно, их не применяют
   повторно, но они продвигают счётчик. При переподключении WebSocket снимок перечитывается всегда.
7. **Самолечение.** После загрузки движок пересчитывает все формулы; если вычисленное `value` не совпало
   с сохранённым (импорт из Excel без кэша значений, старая версия функции) — клиент с правом записи
   отправляет поправку.

### 3.4. Что изменится в коде

| Было | Станет |
|---|---|
| `models/data.py` (`TableRow`), `columns_schema` | `models/cell.py` (`SheetCell`), `revision`, `layout_revision`, `sheet_meta` |
| `/data/{id}/rows…` (6 эндпоинтов) | `GET /data/{id}/sheet`, `POST /data/{id}/sheet/batch` |
| `DataService`, `DataValidationService`, кэш строк в Redis | `SheetService` (кэш убран: данные листа читаются одним снимком) |
| События `row.created/updated/deleted`, канал `events:rows:*` | События `batch`/`reload`, канал `events:sheet:*` |
| Импорт через pandas (только значения), экспорт значений | Импорт и экспорт через openpyxl (формулы, значения, оформление) |
| `TableViewPage` на 770 строк с таблицей на `<table>` | Страница ~200 строк + `useSheet` + `SheetEngine` + Glide Data Grid |
| `mathjs`, `new Function`, `evaluateFormula` | HyperFormula |

---

## 4. Как применять мануал

- Идите по этапам строго по порядку: этап 6 (проверка бэкенда) можно делать до фронтенда.
- **Нумерация строк в правках — по исходному файлу, до любых ваших изменений.** Внутри одного файла правки
  идут **снизу вверх**, поэтому, применяя их в указанном порядке, вы не сдвигаете номера строк, которые ещё
  не обработали. Над каждой правкой есть «Было» — по нему видно, что вы нашли ту самую строку.
- «Создать файл» — файл нужно создать с этим содержимым целиком. «Заменить файл целиком» — удалить всё
  старое содержимое и вставить новое.
- Рекомендую вести работу в отдельной ветке и коммитить после каждого этапа.

---

## 5. Этап 0. Подготовка

```bash
git checkout -b feature/sheet-formulas
docker compose stop table_service frontend   # или остановите их как у вас принято
```

Резервная копия БД не нужна, если старые таблицы вам не жалко (миграция удалит `table_rows`).
Если жалко — сделайте `pg_dump` до миграции.

---

## 6. Этап 1. База данных и модели

**Зачем.** Вместо строки `{колонка: значение}` — отдельная запись на каждую непустую ячейку. Оформление,
формулы и значения лежат рядом, координаты — числа, поэтому вставка строки — это один `UPDATE`.

#### Создать `table_service/app/models/cell.py`

Модель ячейки. Составной первичный ключ `(table_id, row, col)` даёт и уникальность, и быстрый поиск по диапазону строк. Индекс `(table_id, col)` нужен для сдвига колонок. `ondelete="CASCADE"` — при удалении таблицы ячейки удалятся сами (репозиторий удаляет таблицу обычным `DELETE`, ORM-каскад там не работает).

```python
from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from table_service.app.core.database import Base


class SheetCell(Base):
    """Одна непустая ячейка листа. Пустые ячейки в БД не хранятся (разреженная модель)."""

    __tablename__ = "sheet_cells"
    # Сдвиг колонок (вставка/удаление) ищет ячейки по (table_id, col)
    __table_args__ = (Index("ix_sheet_cells_table_col", "table_id", "col"),)

    table_id: Mapped[int] = mapped_column(
        ForeignKey("data_tables.id", ondelete="CASCADE"), primary_key=True
    )
    # 0-based координаты: row=0, col=0 -> A1
    row: Mapped[int] = mapped_column(Integer, primary_key=True)
    col: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Что ввёл пользователь: "42", "привет" или "=SUM(A1:A5)". NULL — ячейка без содержимого
    # (только оформление либо значение, «разлитое» формулой массива из другой ячейки).
    raw: Mapped[str | None] = mapped_column(Text)
    # Вычисленное значение: число, строка, bool или {"e": "#DIV/0!"} для ошибки.
    value: Mapped[Any] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # Оформление: {"bg": "#ffeb3b", "bold": true, ...}. NULL — без оформления.
    style: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))

    def __repr__(self):
        return f"<SheetCell(table={self.table_id}, r={self.row}, c={self.col})>"
```

#### Изменить `table_service/app/models/table.py`

В таблице больше нет `columns_schema` и связи `rows`; появились счётчики ревизий и `sheet_meta`. `JSONB` вместо `JSON` — чтобы Postgres мог индексировать/сравнивать, а `server_default` дал значения для уже существующих таблиц.


**Правка 1 из 7.** **Удалить строки 45–47**:

```python
    rows: Mapped[list[TableRow]] = relationship(
        "TableRow", back_populates="table", cascade="all, delete-orphan"
    )
```

**Правка 2 из 7.** **Заменить строку 31**.

Было:

```python
    columns_schema: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
```

Стало:

```python
    # Счётчик всех принятых пакетов изменений листа (порядок WS-событий)
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Счётчик структурных изменений (вставка/удаление строк и колонок)
    layout_revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Ширины колонок, оформление целых строк/колонок, закрепление и т.п.
    sheet_meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
```

**Правка 3 из 7.** **Удалить строки 18–20**:

```python
if TYPE_CHECKING:
    from table_service.app.models.data import TableRow

```

**Правка 4 из 7.** Вставить **после строки 14**:

```python
from sqlalchemy.dialects.postgresql import JSONB
```

**Правка 5 из 7.** Вставить **после строки 13**:

```python
    text,
```

**Правка 6 из 7.** **Удалить строку 6**:

```python
    JSON,
```

**Правка 7 из 7.** **Заменить строку 3**.

Было:

```python
from typing import TYPE_CHECKING, Any
```

Стало:

```python
from typing import Any
```

#### Заменить файл целиком: `table_service/app/models/__init__.py`

Экспортируем `SheetCell` вместо `TableRow`.

Было 12 строк. Новое содержимое:

```python
from .cell import SheetCell
from .table import DataTable, TablePermission
from .table_pin import TablePin
from .user_projection import UserProjection

__all__ = [
    "DataTable",
    "SheetCell",
    "TablePermission",
    "TablePin",
    "UserProjection",
]
```

#### Создать `table_service/alembic/versions/d3a1f0c5b7e2_sheet_cells.py`

Миграция. Идёт поверх текущей головы `2c0451adbe8c`. Создаёт `sheet_cells`, добавляет колонки в `data_tables`, удаляет `columns_schema` и `table_rows`. **Данные старых строк не переносятся.** `downgrade` возвращает структуру, но не данные.

```python
"""sheet_cells: разреженное хранение ячеек вместо table_rows

Revision ID: d3a1f0c5b7e2
Revises: 2c0451adbe8c
Create Date: 2026-10-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d3a1f0c5b7e2"
down_revision: str | Sequence[str] | None = "2c0451adbe8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema. Данные table_rows НЕ переносятся (проект учебный)."""
    op.create_table(
        "sheet_cells",
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("row", sa.Integer(), nullable=False),
        sa.Column("col", sa.Integer(), nullable=False),
        sa.Column("raw", sa.Text(), nullable=True),
        sa.Column("value", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("style", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.ForeignKeyConstraint(["table_id"], ["data_tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("table_id", "row", "col"),
    )
    # Сдвиг колонок (вставка/удаление) ищет ячейки по (table_id, col)
    op.create_index("ix_sheet_cells_table_col", "sheet_cells", ["table_id", "col"])

    op.add_column(
        "data_tables",
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "data_tables",
        sa.Column("layout_revision", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "data_tables",
        sa.Column(
            "sheet_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.drop_column("data_tables", "columns_schema")

    op.drop_table("table_rows")


def downgrade() -> None:
    """Downgrade schema. Ячейки не конвертируются обратно в строки."""
    op.create_table(
        "table_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("row_data", sa.JSON(), nullable=False),
        sa.Column("formulas", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["table_id"], ["data_tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_table_rows_id", "table_rows", ["id"])
    op.create_index(
        "ix_table_rows_table_id_created", "table_rows", ["table_id", "created_at"]
    )
    op.create_index(
        "ix_table_rows_table_id_updated", "table_rows", ["table_id", "updated_at"]
    )
    op.add_column(
        "data_tables",
        sa.Column(
            "columns_schema",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.drop_column("data_tables", "sheet_meta")
    op.drop_column("data_tables", "layout_revision")
    op.drop_column("data_tables", "revision")
    op.drop_index("ix_sheet_cells_table_col", table_name="sheet_cells")
    op.drop_table("sheet_cells")
```

**Применить и проверить миграцию** (локально, БД из вашего `docker-compose`):

```bash
alembic -c table_service/alembic.ini upgrade head
alembic -c table_service/alembic.ini check          # должно быть: No new upgrade operations detected.
# необязательно: убедиться, что откат тоже работает
alembic -c table_service/alembic.ini downgrade -1 && alembic -c table_service/alembic.ini upgrade head
```

Если `alembic` не видит настройки БД, задайте переменные из `docker-compose.yaml`:
`EXCEL_APP__DB_HOST`, `EXCEL_APP__DB_PORT`, `EXCEL_APP__DB_USER`, `EXCEL_APP__DB_PASSWORD`, `EXCEL_APP__DB_NAME`.
В docker-compose миграцию применит сервис `table_migrate` при следующем `up`.

---

## 7. Этап 2. Схемы (pydantic) и исключение

**Зачем.** Контракт API: пакет изменений, снимок, WebSocket-событие. Сервер строго проверяет вход: границы
координат, длину текста, формат цветов, набор полей стиля (`extra="forbid"` — произвольный JSON в БД не попадёт).

#### Создать `table_service/app/schemas/sheet.py`

Все схемы листа в одном файле. `MAX_*` — лимиты (дублируются на фронте). `SStyleWrite` при сериализации выбрасывает `null`-поля стиля, иначе на клиенте пустое свойство перекрыло бы стиль колонки.

```python
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_serializer, field_validator

# Лимиты листа. Те же числа продублированы на фронте (frontend/src/sheet/address.ts).
MAX_ROWS = 100_000
MAX_COLS = 1_000
MAX_BATCH_ITEMS = 20_000
MAX_RAW_LENGTH = 50_000
MAX_CELLS_IN_EVENT = 2_000

HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class SCellStyle(BaseModel):
    """Оформление ячейки. Неизвестные поля запрещены, чтобы в БД не попал мусор."""

    model_config = {"extra": "forbid"}

    bg: str | None = Field(default=None, pattern=HEX_COLOR)
    fg: str | None = Field(default=None, pattern=HEX_COLOR)
    bold: bool | None = None
    italic: bool | None = None
    halign: Literal["left", "center", "right"] | None = None
    wrap: bool | None = None
    numFmt: (
        Literal["general", "number", "percent", "currency", "date", "datetime"] | None
    ) = None
    decimals: int | None = Field(default=None, ge=0, le=10)

    def to_db(self) -> dict[str, Any] | None:
        data = self.model_dump(exclude_none=True)
        return data or None


class SCellWrite(BaseModel):
    row: int = Field(ge=0, lt=MAX_ROWS)
    col: int = Field(ge=0, lt=MAX_COLS)
    raw: str | None = Field(default=None, max_length=MAX_RAW_LENGTH)
    value: Any = None

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: Any) -> Any:
        if v is None or isinstance(v, str | int | float | bool):
            return v
        if isinstance(v, dict) and set(v) == {"e"} and isinstance(v["e"], str):
            return v
        raise ValueError("value: ожидается число, строка, bool, null или {'e': '#ERR'}")


class SStyleWrite(BaseModel):
    row: int = Field(ge=0, lt=MAX_ROWS)
    col: int = Field(ge=0, lt=MAX_COLS)
    style: SCellStyle | None = None

    @field_serializer("style")
    def serialize_style(self, style: SCellStyle | None) -> dict[str, Any] | None:
        """В JSON (события WS) уходят только заданные свойства, без null."""
        return style.to_db() if style else None


class SStructuralOp(BaseModel):
    kind: Literal["insert_rows", "delete_rows", "insert_cols", "delete_cols"]
    index: int = Field(ge=0)
    count: int = Field(ge=1, le=MAX_ROWS)

    @property
    def axis(self) -> Literal["row", "col"]:
        return "row" if self.kind.endswith("rows") else "col"

    @property
    def is_insert(self) -> bool:
        return self.kind.startswith("insert")


class SSheetBatch(BaseModel):
    """Пакет изменений листа: (опц.) структурная операция, затем ячейки, оформление, meta."""

    client_id: str = Field(min_length=1, max_length=64)
    base_layout_revision: int = Field(ge=0)
    structural: SStructuralOp | None = None
    cells: list[SCellWrite] = Field(default_factory=list, max_length=MAX_BATCH_ITEMS)
    styles: list[SStyleWrite] = Field(default_factory=list, max_length=MAX_BATCH_ITEMS)
    # Полная замена meta (ширины колонок, оформление целых строк/колонок, закрепление)
    meta: dict[str, Any] | None = None

    @field_validator("meta")
    @classmethod
    def validate_meta(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None and len(str(v)) > 200_000:
            raise ValueError("meta слишком большая")
        return v


class SSheetBatchResult(BaseModel):
    revision: int
    layout_revision: int


class SSheetSnapshot(BaseModel):
    table_id: int
    revision: int
    layout_revision: int
    can_write: bool
    meta: dict[str, Any]
    # Компактный формат: [row, col, raw, value, style]
    cells: list[list[Any]]


class SSheetEvent(BaseModel):
    """Событие, рассылаемое всем подписчикам листа через Redis Pub/Sub -> WebSocket."""

    kind: Literal["batch", "reload"]
    table_id: int
    revision: int
    layout_revision: int
    actor_id: int
    client_id: str
    structural: SStructuralOp | None = None
    cells: list[SCellWrite] = Field(default_factory=list)
    styles: list[SStyleWrite] = Field(default_factory=list)
    meta: dict[str, Any] | None = None
    occurred_at: datetime
```

#### Заменить файл целиком: `table_service/app/schemas/ws.py`

Событий строк больше нет — остался только тикет для WebSocket. События листа теперь в `schemas/sheet.py`.

Было 32 строк. Новое содержимое:

```python
from pydantic import BaseModel


class SWsTicketResponse(BaseModel):
    """Одноразовый тикет для WebSocket-подключения."""

    ticket: str
    expires_in: int
```

#### Заменить файл целиком: `table_service/app/schemas/__init__.py`

Убираем схемы строк (`TableRow*`, фильтры, пагинация), добавляем схемы листа.

Было 60 строк. Новое содержимое:

```python
from .export import (
    ExportJobStatus,
    SExportJob,
    SExportJobCreated,
    SExportJobStatusResponse,
)
from .permission import (
    TablePermissionCreate,
    TablePermissionResponse,
    TablePermissionUpdate,
)
from .sheet import (
    SCellStyle,
    SCellWrite,
    SSheetBatch,
    SSheetBatchResult,
    SSheetEvent,
    SSheetSnapshot,
    SStructuralOp,
    SStyleWrite,
)
from .table import (
    DataTableCreate,
    DataTableDuplicate,
    DataTableResponse,
    DataTableUpdate,
)
from .user import SCurrentUser, SUserFilter
from .ws import SWsTicketResponse

__all__ = [
    "DataTableCreate",
    "DataTableDuplicate",
    "DataTableResponse",
    "DataTableUpdate",
    "ExportJobStatus",
    "SCellStyle",
    "SCellWrite",
    "SCurrentUser",
    "SExportJob",
    "SExportJobCreated",
    "SExportJobStatusResponse",
    "SSheetBatch",
    "SSheetBatchResult",
    "SSheetEvent",
    "SSheetSnapshot",
    "SStructuralOp",
    "SStyleWrite",
    "SUserFilter",
    "SWsTicketResponse",
    "TablePermissionCreate",
    "TablePermissionResponse",
    "TablePermissionUpdate",
]
```

#### Изменить `table_service/app/schemas/table.py`

У таблицы больше нет схемы колонок. Лишний `Any` и импорт убираем. Клиент, который всё ещё пришлёт `columns_schema`, не сломается: pydantic по умолчанию игнорирует лишние поля.


**Правка 1 из 3.** **Удалить строку 34**:

```python
    columns_schema: list[dict[str, Any]] | None = None
```

**Правка 2 из 3.** **Удалить строку 24**:

```python
    columns_schema: list[dict[str, Any]] = Field(default_factory=list)
```

**Правка 3 из 3.** **Удалить строку 1**:

```python
from typing import Any
```

#### Изменить `table_service/app/exceptions.py`

Исключение для ответа 409: структура листа изменилась. Глобальный обработчик из `main.py` превратит его в `{"detail": ...}` со статусом 409.


**Правка 1 из 1.** Вставить **после строки 94**:

```python


class LayoutConflictException(AppException):
    status_code: int = 409
    detail: str = "Структура таблицы изменилась, обновите лист"
```

---

## 8. Этап 3. Репозитории

**Зачем.** Работа с БД без бизнес-логики (как у вас принято): репозиторий только выполняет SQL.

#### Создать `table_service/app/repository/cell.py`

`upsert_cells`/`upsert_styles` — `INSERT ... ON CONFLICT DO UPDATE` пачками по 5 000 (лимит asyncpg — 32 767 параметров на запрос). Отдельные upsert'ы для содержимого и оформления: правка текста не затирает заливку и наоборот. `shift` — двухшаговый сдвиг через отрицательные индексы (см. 3.3, пункт 3). `stream_all` — потоковое чтение для экспорта.

```python
from collections.abc import AsyncIterator, Sequence
from typing import Any, Literal

from sqlalchemy import Row, delete, insert, literal, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from table_service.app.models import SheetCell
from table_service.app.repository.base import Base

# asyncpg принимает не больше 32767 параметров на запрос: 5 колонок * 5000 строк = 25000
UPSERT_CHUNK = 5000


class CellRepository(Base):
    """Репозиторий ячеек листа (SheetCell). Бизнес-логики здесь нет."""

    @staticmethod
    def _axis_column(axis: Literal["row", "col"]):
        return SheetCell.row if axis == "row" else SheetCell.col

    async def get_all(self, table_id: int) -> Sequence[Row]:
        stmt = (
            select(
                SheetCell.row,
                SheetCell.col,
                SheetCell.raw,
                SheetCell.value,
                SheetCell.style,
            )
            .where(SheetCell.table_id == table_id)
            .order_by(SheetCell.row, SheetCell.col)
        )
        return (await self._session.execute(stmt)).all()

    async def stream_all(
        self, table_id: int, chunk_size: int = 5000
    ) -> AsyncIterator[Row]:
        """Потоково отдаёт ячейки в порядке строка -> колонка (для экспорта)."""
        stmt = (
            select(
                SheetCell.row,
                SheetCell.col,
                SheetCell.raw,
                SheetCell.value,
                SheetCell.style,
            )
            .where(SheetCell.table_id == table_id)
            .order_by(SheetCell.row, SheetCell.col)
            .execution_options(yield_per=chunk_size)
        )
        result = await self._session.stream(stmt)
        async for cell in result:
            yield cell

    async def upsert_cells(self, table_id: int, cells: list[dict[str, Any]]) -> None:
        """Записать raw+value. cells: [{row, col, raw, value}], без дублей (row, col)."""
        for start in range(0, len(cells), UPSERT_CHUNK):
            chunk = cells[start : start + UPSERT_CHUNK]
            stmt = pg_insert(SheetCell).values(
                [{"table_id": table_id, **cell} for cell in chunk]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[SheetCell.table_id, SheetCell.row, SheetCell.col],
                set_={"raw": stmt.excluded.raw, "value": stmt.excluded.value},
            )
            await self._session.execute(stmt)

    async def upsert_styles(self, table_id: int, styles: list[dict[str, Any]]) -> None:
        """Записать style. styles: [{row, col, style}], без дублей (row, col)."""
        for start in range(0, len(styles), UPSERT_CHUNK):
            chunk = styles[start : start + UPSERT_CHUNK]
            stmt = pg_insert(SheetCell).values(
                [{"table_id": table_id, **item} for item in chunk]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[SheetCell.table_id, SheetCell.row, SheetCell.col],
                set_={"style": stmt.excluded.style},
            )
            await self._session.execute(stmt)

    async def delete_empty(self, table_id: int, min_row: int, max_row: int) -> None:
        """Убрать «пустые» ячейки (нет ни raw, ни value, ни style) в диапазоне строк."""
        stmt = delete(SheetCell).where(
            SheetCell.table_id == table_id,
            SheetCell.row.between(min_row, max_row),
            SheetCell.raw.is_(None),
            SheetCell.value.is_(None),
            SheetCell.style.is_(None),
        )
        await self._session.execute(stmt)

    async def delete_range(
        self, table_id: int, axis: Literal["row", "col"], start: int, count: int
    ) -> None:
        """Удалить все ячейки в строках (или колонках) [start, start + count)."""
        column = self._axis_column(axis)
        stmt = delete(SheetCell).where(
            SheetCell.table_id == table_id, column >= start, column < start + count
        )
        await self._session.execute(stmt)

    async def shift(
        self, table_id: int, axis: Literal["row", "col"], from_index: int, delta: int
    ) -> None:
        """Сдвинуть все ячейки с индексом >= from_index на delta (может быть < 0).

        Делается в два шага через отрицательные индексы, чтобы не нарушать PRIMARY KEY
        посреди UPDATE: PK в PostgreSQL проверяется построчно, а не по завершении запроса.
        """
        column = self._axis_column(axis)
        name = axis
        await self._session.execute(
            update(SheetCell)
            .where(SheetCell.table_id == table_id, column >= from_index)
            .values({name: -(column + delta) - 1})
        )
        await self._session.execute(
            update(SheetCell)
            .where(SheetCell.table_id == table_id, column < 0)
            .values({name: -column - 1})
        )

    async def bulk_insert(self, table_id: int, cells: list[dict[str, Any]]) -> int:
        """Вставка новых ячеек (импорт из Excel). cells: [{row, col, raw, value, style}]."""
        for start in range(0, len(cells), UPSERT_CHUNK // 2):
            chunk = cells[start : start + UPSERT_CHUNK // 2]
            await self._session.execute(
                insert(SheetCell), [{"table_id": table_id, **cell} for cell in chunk]
            )
        return len(cells)

    async def copy_cells(self, source_table_id: int, target_table_id: int) -> int:
        """Скопировать все ячейки из одной таблицы в другую (дублирование таблицы)."""
        select_stmt = select(
            literal(target_table_id),
            SheetCell.row,
            SheetCell.col,
            SheetCell.raw,
            SheetCell.value,
            SheetCell.style,
        ).where(SheetCell.table_id == source_table_id)
        stmt = insert(SheetCell).from_select(
            ["table_id", "row", "col", "raw", "value", "style"], select_stmt
        )
        result = await self._session.execute(stmt)
        return result.rowcount
```

#### Изменить `table_service/app/repository/table.py`

Три новых метода: блокировка строки таблицы на запись (`get_table_for_update`) и на чтение (`get_table_for_share`), атомарное увеличение ревизий (`bump_revision`). Из `create_table` убираем `columns_schema`.

Важно: `populate_existing=True` в обоих методах блокировки обязателен. До блокировки сервис уже загрузил `DataTable` в сессию (проверка прав через `get_table_by_id`). Обычный `select().with_for_update()` в SQLAlchemy не перезаписывает атрибуты объекта, который уже есть в identity map, поэтому без этой опции `revision`/`layout_revision` останутся значениями «до блокировки». Тогда проверка `base_layout_revision` пропустит конфликт, а снимок получит устаревшую `revision`.


**Правка 1 из 3.** **Заменить строку 113**.

Было:

```python
        - Все строки таблицы (TableRow)
```

Стало:

```python
        - Все ячейки таблицы (SheetCell)
```

**Правка 2 из 3.** **Удалить строку 82**:

```python
                columns_schema=table_data.get("columns_schema"),
```

**Правка 3 из 3.** Вставить **после строки 44**:

```python
    async def get_table_for_update(self, table_id: int) -> DataTable | None:
        """Таблица с блокировкой строки (SELECT ... FOR UPDATE): сериализует записи в лист."""
        stmt = (
            select(DataTable)
            .where(DataTable.id == table_id, DataTable.is_deleted.is_(False))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_table_for_share(self, table_id: int) -> DataTable | None:
        """Таблица с разделяемой блокировкой: пока читаем снимок, пакеты изменений ждут."""
        stmt = (
            select(DataTable)
            .where(DataTable.id == table_id, DataTable.is_deleted.is_(False))
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def bump_revision(
        self,
        table_id: int,
        structural: bool,
        meta: dict | None,
    ) -> tuple[int, int]:
        """Увеличить revision (и layout_revision для структурных операций), опц. заменить meta."""
        values: dict = {"revision": DataTable.revision + 1}
        if structural:
            values["layout_revision"] = DataTable.layout_revision + 1
        if meta is not None:
            values["sheet_meta"] = meta
        stmt = (
            update(DataTable)
            .where(DataTable.id == table_id)
            .values(**values)
            .returning(DataTable.revision, DataTable.layout_revision)
        )
        revision, layout_revision = (await self._session.execute(stmt)).one()
        return revision, layout_revision

```

#### Заменить файл целиком: `table_service/app/repository/__init__.py`

Экспортируем `CellRepository` вместо `DataRepository`.

Было 13 строк. Новое содержимое:

```python
from .cell import CellRepository
from .permission import PermissionRepository
from .table import TableRepository
from .table_pin import TablePinRepository
from .user_projection import UserRepository

__all__ = [
    "CellRepository",
    "PermissionRepository",
    "TablePinRepository",
    "TableRepository",
    "UserRepository",
]
```

#### Изменить `table_service/app/core/unit_of_work.py`

В Unit of Work вместо `uow.data` теперь `uow.cells`.


**Правка 1 из 2.** **Заменить строки 46–47**.

Было:

```python
    def data(self) -> DataRepository:
        return DataRepository(self._session)
```

Стало:

```python
    def cells(self) -> CellRepository:
        return CellRepository(self._session)
```

**Правка 2 из 2.** **Заменить строку 6**.

Было:

```python
    DataRepository,
```

Стало:

```python
    CellRepository,
```

---

## 9. Этап 4. Сервисы

**Зачем.** Бизнес-логика листа (`SheetService`), публикация событий, импорт и экспорт Excel.

#### Создать `table_service/app/services/sheet_events.py`

Замена `row_events.py`: тот же механизм (Redis Pub/Sub), другой канал — `events:sheet:{id}` — и другой тип события.

```python
import logging

from redis.asyncio import Redis

from table_service.app.schemas import SSheetEvent

logger = logging.getLogger(__name__)


def sheet_channel(table_id: int) -> str:
    return f"events:sheet:{table_id}"


class SheetEventPublisher:
    """Публикует события листа в Redis Pub/Sub для WS-подписчиков."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def publish(self, event: SSheetEvent) -> None:
        try:
            await self.redis.publish(
                sheet_channel(event.table_id), event.model_dump_json()
            )
        except Exception:
            logger.exception("Не удалось опубликовать событие листа %s", event.table_id)
```

#### Создать `table_service/app/services/sheet.py`

Сердце бэкенда. `get_snapshot` читает лист под `FOR SHARE`. `apply_batch`: проверка прав → блокировка таблицы → проверка `layout_revision` (иначе 409) → структурная операция → upsert (дубли в одном пакете схлопываются, последний выигрывает) → чистка «пустых» записей → ревизия → событие. Если в пакете больше 2 000 элементов, вместо тела рассылается событие `reload`.

```python
import logging
from datetime import UTC, datetime

from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.exceptions import LayoutConflictException, NotFoundException
from table_service.app.schemas import (
    SSheetBatch,
    SSheetBatchResult,
    SSheetEvent,
    SSheetSnapshot,
)
from table_service.app.schemas.sheet import MAX_CELLS_IN_EVENT
from table_service.app.services.permission import PermissionService
from table_service.app.services.sheet_events import SheetEventPublisher

logger = logging.getLogger(__name__)


class SheetService:
    """Лист таблицы: снимок для клиента и применение пакетов изменений.

    Формулы сервер не вычисляет: клиент (HyperFormula) присылает raw и вычисленное value.
    """

    def __init__(
        self,
        permission_service: PermissionService,
        event_publisher: SheetEventPublisher | None = None,
    ):
        self.permission_service = permission_service
        self.event_publisher = event_publisher

    async def get_snapshot(
        self, uow_session: UnitOfWork, table_id: int, user_id: int, user_role: str
    ) -> SSheetSnapshot:
        """Все непустые ячейки + revision. Разделяемая блокировка строки таблицы
        гарантирует, что revision и ячейки относятся к одному и тому же моменту."""
        async with uow_session.start():
            table = await self.permission_service.get_table_with_read_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )
            can_write = await self.permission_service.check_write_access(
                uow_session=uow_session,
                table=table,
                user_id=user_id,
                user_role=user_role,
            )
            locked = await uow_session.tables.get_table_for_share(table_id)
            if locked is None:
                raise NotFoundException("Таблица не найдена")

            rows = await uow_session.cells.get_all(table_id)
            return SSheetSnapshot(
                table_id=table_id,
                revision=locked.revision,
                layout_revision=locked.layout_revision,
                can_write=can_write,
                meta=locked.sheet_meta or {},
                cells=[[r.row, r.col, r.raw, r.value, r.style] for r in rows],
            )

    async def apply_batch(
        self,
        uow_session: UnitOfWork,
        table_id: int,
        user_id: int,
        user_role: str,
        batch: SSheetBatch,
    ) -> SSheetBatchResult:
        async with uow_session.start():
            await self.permission_service.get_table_with_write_access(
                uow_session=uow_session,
                table_id=table_id,
                user_id=user_id,
                user_role=user_role,
            )
            # Дальше все записи в этот лист идут строго по очереди
            table = await uow_session.tables.get_table_for_update(table_id)
            if table is None:
                raise NotFoundException("Таблица не найдена")
            if batch.base_layout_revision != table.layout_revision:
                raise LayoutConflictException()

            op = batch.structural
            if op is not None:
                if op.is_insert:
                    await uow_session.cells.shift(table_id, op.axis, op.index, op.count)
                else:
                    await uow_session.cells.delete_range(
                        table_id, op.axis, op.index, op.count
                    )
                    await uow_session.cells.shift(
                        table_id, op.axis, op.index + op.count, -op.count
                    )

            # Дубли (row, col) в одном INSERT ... ON CONFLICT недопустимы: последний выигрывает
            cells = {
                (c.row, c.col): {
                    "row": c.row,
                    "col": c.col,
                    "raw": c.raw,
                    "value": c.value,
                }
                for c in batch.cells
            }
            styles = {
                (s.row, s.col): {
                    "row": s.row,
                    "col": s.col,
                    "style": s.style.to_db() if s.style else None,
                }
                for s in batch.styles
            }
            await uow_session.cells.upsert_cells(table_id, list(cells.values()))
            await uow_session.cells.upsert_styles(table_id, list(styles.values()))

            touched_rows = [r for r, _ in cells] + [r for r, _ in styles]
            if touched_rows:
                await uow_session.cells.delete_empty(
                    table_id, min(touched_rows), max(touched_rows)
                )

            revision, layout_revision = await uow_session.tables.bump_revision(
                table_id, structural=op is not None, meta=batch.meta
            )

        await self._publish(
            table_id,
            user_id,
            batch,
            revision,
            layout_revision,
            len(cells) + len(styles),
        )
        logger.info(
            "User %s applied batch to table %s: rev=%s, cells=%s, styles=%s, structural=%s",
            user_id,
            table_id,
            revision,
            len(cells),
            len(styles),
            op.kind if op else None,
        )
        return SSheetBatchResult(revision=revision, layout_revision=layout_revision)

    async def _publish(
        self,
        table_id: int,
        user_id: int,
        batch: SSheetBatch,
        revision: int,
        layout_revision: int,
        items: int,
    ) -> None:
        if self.event_publisher is None:
            return
        common = {
            "table_id": table_id,
            "revision": revision,
            "layout_revision": layout_revision,
            "actor_id": user_id,
            "client_id": batch.client_id,
            "occurred_at": datetime.now(UTC),
        }
        if items > MAX_CELLS_IN_EVENT:
            # Слишком много для WS-сообщения: клиентам проще перечитать снимок
            event = SSheetEvent(kind="reload", **common)
        else:
            event = SSheetEvent(
                kind="batch",
                structural=batch.structural,
                cells=batch.cells,
                styles=batch.styles,
                meta=batch.meta,
                **common,
            )
        await self.event_publisher.publish(event)
```

#### Заменить файл целиком: `table_service/app/services/excel_processor.py`

Pandas больше не нужен: `openpyxl` читает формулы (`data_only=False`) и кэшированные значения (`data_only=True`) отдельными проходами, переносит заливку, жирный/курсив, цвет текста, выравнивание, перенос текста и формат «процент». Даты переводятся в текст `DD.MM.YYYY` (его понимает движок на фронте) и в серийное число Excel. Экспорт пишет формулы как формулы, пропуски между строками — пустыми строками, оформление — через `WriteOnlyCell`.

Было 184 строк. Новое содержимое:

```python
import logging
from collections.abc import Iterable
from datetime import date, datetime, time
from io import BytesIO
from typing import Any

from openpyxl import load_workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils.datetime import to_excel
from openpyxl.workbook import Workbook

from table_service.app.exceptions import EmptyFileException, ValidationException
from table_service.app.schemas.sheet import MAX_COLS, MAX_ROWS

logger = logging.getLogger(__name__)

# Форматы, которые понимает HyperFormula на фронте (dateFormats в engine.ts)
DATE_TEXT_FORMAT = "%d.%m.%Y"
DATETIME_TEXT_FORMAT = "%d.%m.%Y %H:%M:%S"

EXCEL_ERRORS = {"#DIV/0!", "#N/A", "#NAME?", "#NULL!", "#NUM!", "#REF!", "#VALUE!"}

EXCEL_NUMBER_FORMATS = {
    "number": "#,##0.00",
    "percent": "0.00%",
    "currency": '#,##0.00 "₽"',
    "date": "DD.MM.YYYY",
    "datetime": "DD.MM.YYYY HH:MM:SS",
}


class ExcelProcessorService:
    """Импорт .xlsx в ячейки листа и экспорт обратно. Без доступа к БД."""

    # ---------------------------------------------------------------- импорт

    def parse_workbook(self, file) -> list[dict[str, Any]]:
        """Прочитать первый лист: формулы сохраняются, значения берутся из кэша Excel.

        Возвращает ячейки в формате SheetCell: {row, col, raw, value, style}.
        """
        workbook = load_workbook(file, data_only=False)
        file.seek(0)
        cached_workbook = load_workbook(file, data_only=True)
        sheet = workbook.active
        cached_sheet = cached_workbook.active

        if sheet.max_row > MAX_ROWS or sheet.max_column > MAX_COLS:
            raise ValidationException(
                f"Лист слишком большой: максимум {MAX_ROWS} строк и {MAX_COLS} колонок"
            )

        cells: list[dict[str, Any]] = []
        for row in sheet.iter_rows():
            for cell in row:
                parsed = self._convert_cell(cell, cached_sheet[cell.coordinate].value)
                if parsed:
                    cells.append(parsed)
        if not cells:
            raise EmptyFileException("Файл не содержит данных для импорта")
        return cells

    def _convert_cell(self, cell, cached_value: Any) -> dict[str, Any] | None:
        content = getattr(
            cell.value, "text", cell.value
        )  # ArrayFormula -> текст формулы
        style = self._style_from_cell(cell)
        raw: str | None = None
        value: Any = None

        if content is None:
            pass
        elif isinstance(content, str) and content.startswith("="):
            raw, value = content, self._json_value(cached_value)
        elif isinstance(content, bool):
            raw, value = ("TRUE" if content else "FALSE"), content
        elif isinstance(content, datetime) and content.time() != time.min:
            raw, value = content.strftime(DATETIME_TEXT_FORMAT), to_excel(content)
            style["numFmt"] = "datetime"
        elif isinstance(content, date):  # datetime ровно в полночь тоже считаем датой
            raw, value = content.strftime(DATE_TEXT_FORMAT), to_excel(content)
            style["numFmt"] = "date"
        elif isinstance(content, int | float):
            raw, value = str(content), content
        else:
            raw, value = str(content), str(content)

        if raw is None and not style:
            return None
        return {
            "row": cell.row - 1,
            "col": cell.column - 1,
            "raw": raw,
            "value": value,
            "style": style or None,
        }

    @staticmethod
    def _json_value(value: Any) -> Any:
        if value is None or isinstance(value, bool | int | float):
            return value
        if isinstance(value, datetime | date):
            return to_excel(value)
        text = str(value)
        return {"e": text} if text in EXCEL_ERRORS else text

    @staticmethod
    def _rgb(color) -> str | None:
        rgb = getattr(color, "rgb", None)
        if isinstance(rgb, str) and len(rgb) == 8:  # AARRGGBB; тема/индексы пропускаем
            return f"#{rgb[2:].lower()}"
        return None

    def _style_from_cell(self, cell) -> dict[str, Any]:
        style: dict[str, Any] = {}
        if cell.fill and cell.fill.fill_type == "solid":
            bg = self._rgb(cell.fill.fgColor)
            if bg and bg != "#ffffff":
                style["bg"] = bg
        if cell.font:
            if cell.font.bold:
                style["bold"] = True
            if cell.font.italic:
                style["italic"] = True
            fg = self._rgb(cell.font.color)
            if fg and fg != "#000000":
                style["fg"] = fg
        if cell.alignment:
            if cell.alignment.horizontal in ("left", "center", "right"):
                style["halign"] = cell.alignment.horizontal
            if cell.alignment.wrap_text:
                style["wrap"] = True
        if cell.number_format and cell.number_format.endswith("%"):
            style["numFmt"] = "percent"
        return style

    # --------------------------------------------------------------- экспорт

    @staticmethod
    def create_streaming_workbook() -> tuple[Workbook, Any]:
        """Начать книгу в write-only режиме."""
        workbook = Workbook(write_only=True)
        return workbook, workbook.create_sheet()

    def append_rows_chunk(
        self, sheet, rows: Iterable[tuple[int, list]], next_row: int
    ) -> int:
        """Дописать строки [(row_index, [cell, ...])] в лист; пропуски заполняются пустыми.

        CPU-bound — звать из потока. Возвращает индекс следующей строки.
        """
        for row_index, cells in rows:
            for _ in range(row_index - next_row):
                sheet.append([])
            line: list[WriteOnlyCell | None] = []
            for cell in cells:
                line.extend([None] * (cell.col - len(line)))
                line.append(self._export_cell(sheet, cell))
            sheet.append(line)
            next_row = row_index + 1
        return next_row

    def _export_cell(self, sheet, cell) -> WriteOnlyCell:
        if cell.raw is not None and cell.raw.startswith("="):
            content = cell.raw
        elif isinstance(cell.value, dict):
            content = cell.value.get("e")
        elif cell.value is not None:
            content = cell.value
        else:
            content = cell.raw

        out = WriteOnlyCell(sheet, value=content)
        style = cell.style or {}
        if style.get("bg"):
            out.fill = PatternFill("solid", fgColor=style["bg"].lstrip("#"))
        if style.get("bold") or style.get("italic") or style.get("fg"):
            out.font = Font(
                bold=bool(style.get("bold")),
                italic=bool(style.get("italic")),
                color=style["fg"].lstrip("#") if style.get("fg") else None,
            )
        if style.get("halign") or style.get("wrap"):
            out.alignment = Alignment(
                horizontal=style.get("halign"), wrap_text=bool(style.get("wrap"))
            )
        if style.get("numFmt") in EXCEL_NUMBER_FORMATS:
            out.number_format = EXCEL_NUMBER_FORMATS[style["numFmt"]]
        return out

    @staticmethod
    def finalize_workbook(workbook: Workbook) -> BytesIO:
        """Сохранить книгу в буфер. CPU-bound — звать из потока."""
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer
```

#### Изменить `table_service/app/services/export_job.py`

Экспорт теперь стримит ячейки, группирует их по строкам и дописывает в книгу чанками по 4 000 строк.


**Правка 1 из 8.** **Заменить строку 159**.

Было:

```python
                total_rows += len(chunk)
```

Стало:

```python
            total_rows = next_row
```

**Правка 2 из 8.** **Заменить строки 156–157**.

Было:

```python
                await asyncio.to_thread(
                    self.excel_processor.append_rows_chunk, sheet, column_names, chunk
```

Стало:

```python
                next_row = await asyncio.to_thread(
                    self.excel_processor.append_rows_chunk, sheet, chunk, next_row
```

**Правка 3 из 8.** **Заменить строки 145–154**.

Было:

```python
                chunk.append(row.row_data)
                if len(chunk) >= CHUNK_SIZE:
                    await asyncio.to_thread(
                        self.excel_processor.append_rows_chunk,
                        sheet,
                        column_names,
                        chunk,
                    )
                    total_rows += len(chunk)
                    chunk = []
```

Стало:

```python
                if chunk and chunk[-1][0] == cell.row:
                    chunk[-1][1].append(cell)
                else:
                    if len(chunk) >= CHUNK_SIZE:
                        next_row = await asyncio.to_thread(
                            self.excel_processor.append_rows_chunk,
                            sheet,
                            chunk,
                            next_row,
                        )
                        chunk = []
                    chunk.append((cell.row, [cell]))
```

**Правка 4 из 8.** **Заменить строку 142**.

Было:

```python
            async for row in uow_session.data.stream_rows_by_table_id(
```

Стало:

```python
            async for cell in uow_session.cells.stream_all(
```

**Правка 5 из 8.** **Заменить строки 139–140**.

Было:

```python
            total_rows = 0
            chunk: list[dict] = []
```

Стало:

```python
            next_row = 0  # индекс следующей строки, которую нужно записать в лист
            chunk: list[tuple[int, list]] = []  # [(индекс строки, [ячейки])]
```

**Правка 6 из 8.** **Заменить строки 135–137**.

Было:

```python
            workbook, sheet, column_names = (
                self.excel_processor.create_streaming_workbook(table.columns_schema)
            )
```

Стало:

```python
            workbook, sheet = self.excel_processor.create_streaming_workbook()
```

**Правка 7 из 8.** **Заменить строку 129**.

Было:

```python
        """Собрать xlsx: строки из БД чанками, запись в write-only книгу в потоке."""
```

Стало:

```python
        """Собрать xlsx: ячейки из БД потоком, строка за строкой, запись в write-only книгу в потоке."""
```

**Правка 8 из 8.** **Заменить строку 27**.

Было:

```python
CHUNK_SIZE = 4000
```

Стало:

```python
CHUNK_SIZE = 4000  # строк листа в одном чанке записи в xlsx
```

#### Изменить `table_service/app/services/table.py`

Дублирование таблицы копирует ячейки и `sheet_meta`; импорт из Excel идёт через `parse_workbook` и принимает только `.xlsx` (openpyxl не читает `.xls`).


**Правка 1 из 20.** **Заменить строку 419**.

Было:

```python
        except (pd.errors.ParserError, ValueError, TypeError):
```

Стало:

```python
        except (InvalidFileException, BadZipFile, KeyError, ValueError, TypeError):
```

**Правка 2 из 20.** **Удалить строки 412–416**:

```python
        except pd.errors.EmptyDataError:
            logger.warning(
                "User %s uploaded empty Excel file '%s'", user_id, excel_file.filename
            )
            raise EmptyFileException("Excel файл пустой")
```

**Правка 3 из 20.** **Удалить строку 408**:

```python
                failed,
```

**Правка 4 из 20.** **Удалить строки 405–406**:

```python
                len(df.columns),
                len(df),
```

**Правка 5 из 20.** **Заменить строки 400–401**.

Было:

```python
                "User %s created table %s from Excel '%s' "
                "(%s columns, %s rows: %s imported, %s failed)",
```

Стало:

```python
                "User %s created table %s from Excel '%s' (%s cells imported)",
```

**Правка 6 из 20.** **Заменить строки 378–380**.

Было:

```python
                rows, failed = self.excel_processor.build_rows(df)
                created = await uow_session.data.bulk_create_table_row(
                    table_id=table.id, rows_data=rows
```

Стало:

```python
                created = await uow_session.cells.bulk_insert(
                    table_id=table.id, cells=cells
```

**Правка 7 из 20.** **Удалить строку 363**:

```python
                    columns_schema=columns_schema,
```

**Правка 8 из 20.** **Удалить строки 353–355**:

```python
            # Генерация схемы колонок на основе DataFrame
            columns_schema = self.excel_processor.build_columns_schema(df)

```

**Правка 9 из 20.** **Заменить строку 347**.

Было:

```python
            df = pd.read_excel(excel_file.file)
```

Стало:

```python
            cells = self.excel_processor.parse_workbook(excel_file.file)
```

**Правка 10 из 20.** **Заменить строки 331–333**.

Было:

```python
            raise InvalidFileFormatException(
                "Файл должен быть в формате Excel (.xlsx или .xls)"
            )
```

Стало:

```python
            raise InvalidFileFormatException("Файл должен быть в формате Excel (.xlsx)")
```

**Правка 11 из 20.** **Заменить строку 324**.

Было:

```python
        if not excel_file.filename.endswith((".xlsx", ".xls")):
```

Стало:

```python
        if not excel_file.filename.endswith(".xlsx"):
```

**Правка 12 из 20.** Вставить **после строки 278**:

```python
                await uow_session.tables.update_table(
                    new_table.id, {"sheet_meta": source_table.sheet_meta}
                )
```

**Правка 13 из 20.** **Заменить строку 276**.

Было:

```python
                copied = await uow_session.data.copy_rows(
```

Стало:

```python
                copied = await uow_session.cells.copy_cells(
```

**Правка 14 из 20.** **Удалить строку 265**:

```python
                "columns_schema": source_table.columns_schema,
```

**Правка 15 из 20.** **Заменить строку 247**.

Было:

```python
        Клонировать таблицу: копирует columns_schema, опционально строки.
```

Стало:

```python
        Клонировать таблицу: опционально копирует ячейки и meta (ширины колонок и т.п.).
```

**Правка 16 из 20.** **Удалить строку 59**:

```python
            columns_schema=table.columns_schema,
```

**Правка 17 из 20.** **Удалить строку 14**:

```python
    EmptyFileException,
```

**Правка 18 из 20.** Вставить **после строки 6**:

```python
from openpyxl.utils.exceptions import InvalidFileException
```

**Правка 19 из 20.** **Удалить строку 5**:

```python
import pandas as pd
```

**Правка 20 из 20.** Вставить **после строки 2**:

```python
from zipfile import BadZipFile
```

#### Заменить файл целиком: `table_service/app/services/__init__.py`

Убираем `DataService`, `DataValidationService`, `RowEventPublisher`; добавляем `SheetService`, `SheetEventPublisher`.

Было 25 строк. Новое содержимое:

```python
from .table import TableService
from .search import SearchService
from .sheet import SheetService
from .ws_ticket import WsTicketService
from .export_job import ExportJobService
from .permission import PermissionService
from .sheet_events import SheetEventPublisher
from .cache import AccessCache, AccessLevel
from .excel_processor import ExcelProcessorService


__all__ = [
    "ExcelProcessorService",
    "ExportJobService",
    "PermissionService",
    "SearchService",
    "SheetEventPublisher",
    "SheetService",
    "TableService",
    "WsTicketService",
    "AccessCache",
    "AccessLevel",
]
```

#### Изменить `table_service/app/core/ws_manager.py`

WebSocket-менеджер слушает новый паттерн каналов. Больше в нём ничего менять не надо: он рассылает строку как есть.


**Правка 1 из 1.** **Заменить строку 9**.

Было:

```python
EVENTS_PATTERN = "events:rows:*"
```

Стало:

```python
EVENTS_PATTERN = "events:sheet:*"
```

---

## 10. Этап 5. API, зависимости, роутер

**Зачем.** Два эндпоинта вместо шести. Префикс остаётся `/data`, поэтому маршруты в Traefik (`PathPrefix(`/data`)`)
и в nginx менять не нужно. WebSocket-маршрут `/ws/tables/{id}` тоже прежний.

#### Создать `table_service/app/api/endpoints/sheet.py`

`GET /data/{table_id}/sheet` и `POST /data/{table_id}/sheet/batch`.

```python
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from table_service.app.api.dependencies import (
    get_async_uow_session,
    get_current_active_user,
    get_sheet_service,
)
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.schemas import (
    SCurrentUser,
    SSheetBatch,
    SSheetBatchResult,
    SSheetSnapshot,
)
from table_service.app.services import SheetService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/{table_id}/sheet",
    response_model=SSheetSnapshot,
    status_code=status.HTTP_200_OK,
)
async def get_sheet(
    sheet_service: Annotated[SheetService, Depends(get_sheet_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
) -> SSheetSnapshot:
    """Все непустые ячейки листа и текущая ревизия."""
    return await sheet_service.get_snapshot(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
    )


@router.post(
    "/{table_id}/sheet/batch",
    response_model=SSheetBatchResult,
    status_code=status.HTTP_200_OK,
)
async def apply_sheet_batch(
    batch: SSheetBatch,
    sheet_service: Annotated[SheetService, Depends(get_sheet_service)],
    current_user: Annotated[SCurrentUser, Depends(get_current_active_user)],
    uow_session: Annotated[UnitOfWork, Depends(get_async_uow_session)],
    table_id: int = Path(..., description="ID таблицы", ge=1),
) -> SSheetBatchResult:
    """Применить пакет изменений: структурная операция, ячейки, оформление, meta."""
    return await sheet_service.apply_batch(
        uow_session=uow_session,
        table_id=table_id,
        user_id=current_user.user_id,
        user_role=current_user.role,
        batch=batch,
    )
```

#### Заменить файл целиком: `table_service/app/api/endpoints/__init__.py`

Роутер `data_router` заменяется на `sheet_router`.

Было 17 строк. Новое содержимое:

```python
from .health import router as health_router
from .permissions import router as permissions_router
from .search import router as search_router
from .sheet import router as sheet_router
from .tables import router as tables_router
from .trash import router as trash_router
from .ws import router as ws_router

__all__ = [
    "health_router",
    "permissions_router",
    "search_router",
    "sheet_router",
    "tables_router",
    "trash_router",
    "ws_router",
]
```

#### Изменить `table_service/app/api/endpoints/ws.py`

Только текст docstring.


**Правка 1 из 1.** **Заменить строку 39**.

Было:

```python
    """Подписка на события строк таблицы. Аутентификация — одноразовым тикетом в query."""
```

Стало:

```python
    """Подписка на события листа таблицы. Аутентификация — одноразовым тикетом в query."""
```

#### Изменить `table_service/app/api/dependencies.py`

Фабрики зависимостей: `get_sheet_event_publisher` и `get_sheet_service` вместо `get_row_event_publisher`, `get_validation_service`, `get_data_service`.


**Правка 1 из 9.** **Удалить строку 110**:

```python
        validation_service=validation_service,
```

**Правка 2 из 9.** **Заменить строки 101–107**.

Было:

```python
    validation_service: Annotated[
        DataValidationService, Depends(get_validation_service)
    ],
) -> DataService:
    """Получить экземпляр сервиса данных."""
    return DataService(
        redis=redis,
```

Стало:

```python
) -> SheetService:
    """Получить экземпляр сервиса листа."""
    return SheetService(
```

**Правка 3 из 9.** **Заменить строки 97–99**.

Было:

```python
def get_data_service(
    redis: Annotated[Redis, Depends(get_redis_client)],
    event_publisher: Annotated[RowEventPublisher, Depends(get_row_event_publisher)],
```

Стало:

```python
def get_sheet_service(
    event_publisher: Annotated[SheetEventPublisher, Depends(get_sheet_event_publisher)],
```

**Правка 4 из 9.** **Удалить строки 65–69**:

```python
async def get_validation_service() -> DataValidationService:
    """Получить экземпляр сервиса валидации данных."""
    return DataValidationService()


```

**Правка 5 из 9.** **Заменить строки 46–48**.

Было:

```python
) -> RowEventPublisher:
    """Получить издателя событий строк (Redis Pub/Sub)."""
    return RowEventPublisher(redis=redis)
```

Стало:

```python
) -> SheetEventPublisher:
    """Получить издателя событий листа (Redis Pub/Sub)."""
    return SheetEventPublisher(redis=redis)
```

**Правка 6 из 9.** **Заменить строку 44**.

Было:

```python
def get_row_event_publisher(
```

Стало:

```python
def get_sheet_event_publisher(
```

**Правка 7 из 9.** Вставить **после строки 24**:

```python
    SheetEventPublisher,
    SheetService,
```

**Правка 8 из 9.** **Удалить строку 23**:

```python
    RowEventPublisher,
```

**Правка 9 из 9.** **Удалить строки 18–19**:

```python
    DataService,
    DataValidationService,
```

#### Изменить `table_service/app/main.py`

Подключаем новый роутер на тот же префикс `/data`.


**Правка 1 из 3.** **Заменить строку 143**.

Было:

```python
        (data_router, "/data", "Data"),
```

Стало:

```python
        (sheet_router, "/data", "Sheet"),
```

**Правка 2 из 3.** Вставить **после строки 18**:

```python
    sheet_router,
```

**Правка 3 из 3.** **Удалить строку 15**:

```python
    data_router,
```

#### Удалить файлы

Эти файлы больше не используются. Удалите их **после** предыдущих правок (иначе на промежуточном шаге
будут ошибки импорта):


- `table_service/app/models/data.py` — модель `TableRow`

- `table_service/app/repository/data.py` — репозиторий строк, сортировка и фильтры по JSON

- `table_service/app/schemas/data.py` — схемы строк, фильтров, пагинации

- `table_service/app/services/data.py` — `DataService` и кэш строк

- `table_service/app/services/data_validation.py` — валидация строки по `columns_schema`

- `table_service/app/services/row_events.py` — заменён `sheet_events.py`

- `table_service/app/api/endpoints/data.py` — эндпоинты строк


```bash
git rm table_service/app/models/data.py table_service/app/repository/data.py \
       table_service/app/schemas/data.py table_service/app/services/data.py \
       table_service/app/services/data_validation.py table_service/app/services/row_events.py \
       table_service/app/api/endpoints/data.py
```

> `pandas` в `table_service/requirements.txt` больше нигде в сервисе не используется. Удалять необязательно
> (`pandas==2.3.3`, строка 44), но тесты и фикстуры ещё его импортируют — см. этап 9.

---

## 11. Этап 6. Проверка бэкенда

Всё это можно сделать до фронтенда.

**1. Импорты и роуты:**

```bash
python -c "import table_service.app.main as m; print([r.path for r in m.app.routes if r.path.startswith('/data')])"
# ['/data/{table_id}/sheet', '/data/{table_id}/sheet/batch']
```

**2. Линтер:**

```bash
ruff check table_service/app && ruff format --check table_service/app
```

(в `services/permission.py` ruff ругается на дублирующиеся импорты `Awaitable`/`Callable` — это старое
замечание, не из этой работы.)

**3. Смоук-скрипт на настоящем PostgreSQL** — приложение A. Он проверяет запись, вставку/удаление строк и колонок,
сдвиг стилей, 409, дубли, большие пакеты и события:

```bash
docker run -d --rm --name sheet_pg -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=t -p 54329:5432 postgres:16-alpine
export EXCEL_APP__DB_HOST=localhost EXCEL_APP__DB_PORT=54329 EXCEL_APP__DB_USER=postgres \
       EXCEL_APP__DB_PASSWORD=pw EXCEL_APP__DB_NAME=t
alembic -c table_service/alembic.ini upgrade head
python -m table_service.scripts.sheet_smoke      # в конце: SMOKE OK [...]
docker stop sheet_pg
```

**4. Руками через Swagger** (`/api/docs` у table_service): создайте таблицу `POST /tables/create`, затем

```http
POST /data/{id}/sheet/batch
{"client_id": "me", "base_layout_revision": 0,
 "cells": [{"row": 0, "col": 0, "raw": "5", "value": 5},
           {"row": 1, "col": 0, "raw": "=A1*2", "value": 10}],
 "styles": [{"row": 0, "col": 0, "style": {"bg": "#ffeb3b", "bold": true}}]}
```

→ `{"revision": 1, "layout_revision": 0}`; `GET /data/{id}/sheet` вернёт эти ячейки в формате
`[row, col, raw, value, style]`. Проверка защиты от устаревшей раскладки: отправьте пакет со
`"structural": {"kind": "insert_rows", "index": 0, "count": 1}` — `layout_revision` вырастет до 1; повторите
любой пакет с `"base_layout_revision": 0` — получите 409.

---

## 12. Этап 7. Фронтенд

### 7.0. Как устроен фронтенд (прочитайте один раз)

```
pages/TableViewPage.tsx          страница: шапка, панель инструментов, строка формул, сетка, контекстное меню
 ├─ hooks/useSheet.ts            всё состояние листа: движок, очередь отправки, WebSocket, операции для UI
 │    ├─ sheet/engine.ts         SheetEngine = HyperFormula + зеркало + стили + meta + diff
 │    ├─ sheet/syncQueue.ts      очередь исходящих пакетов
 │    ├─ sheet/sequencer.ts      упорядочивание входящих событий
 │    └─ api/sheet.ts, api/ws.ts HTTP и WebSocket
 └─ components/sheet/            SheetGrid (Glide), Toolbar, FormulaBar, SheetContextMenu
sheet/address.ts, types.ts, format.ts   адреса и лимиты, типы данных, форматирование значений
```

Главная идея `SheetEngine`: любая операция (ввод, вставка, удаление, оформление, вставка из буфера) возвращает
`EngineResult` — «что нужно отправить на сервер» (`cells`, `styles`, `meta`, `structural`). Хук кладёт это в
`SyncQueue`, а сетка перерисовывается по счётчику `version`. Движок — изменяемый объект вне React-состояния:
HyperFormula нельзя копировать на каждую правку.

Основные методы `SheetEngine`:

| Метод | Что делает |
|---|---|
| `load(snapshot)` | кладёт ячейки в HyperFormula; возвращает «починку» (ячейки, где `value` на сервере не совпал с вычисленным) |
| `view(row, col)` | текст для показа, `raw` для редактора, признаки «ошибка»/«число», эффективный стиль |
| `setRaw` / `setMatrix` | ввод и вставка текста; зависимые ячейки попадают в diff; даты получают формат «дата» |
| `clearRange` | очистка содержимого (стиль остаётся) |
| `applyStructural(op)` | вставка/удаление строк и колонок; сдвиг зеркала, стилей, `meta` |
| `copy(rect)` / `paste(row, col)` | копирование и вставка со сдвигом относительных ссылок (`hf.copy/paste`) |
| `applyStyle(target, patch)` | оформление диапазона, целых колонок или строк (последние — в `meta`) |
| `applyRemote(event)` | применить чужое событие; на сервер ничего не уходит |

### 7.1. Зависимости

В каталоге `frontend/`:

```bash
npm install hyperformula@3.5.0 @glideapps/glide-data-grid@6.0.3 lodash@4 marked@4 react-responsive-carousel
npm install -D @types/lodash
npm uninstall mathjs
```

`lodash`, `marked` и `react-responsive-carousel` — обязательные peer-зависимости Glide Data Grid (в сетке они
почти не используются, но без них падает сборка). Команды сами обновят `package.json` и `package-lock.json`;
Dockerfile фронта делает `npm install`, дополнительных шагов не нужно.

В `package.json` должно оказаться (версии могут чуть отличаться по патчам):

```json
"@glideapps/glide-data-grid": "^6.0.3",
"hyperformula": "^3.5.0",
"lodash": "^4.17.21",
"marked": "^4.3.0",
"react-responsive-carousel": "^3.2.23"
```

и **не должно** быть `mathjs`.

#### Изменить `frontend/index.html`

Glide Data Grid рисует редактор ячейки (поле ввода поверх сетки) в элементе `#portal` — без него редактирование не откроется.


**Правка 1 из 1.** Вставить **после строки 13**:

```html
    <!-- Glide Data Grid рисует редактор ячейки в этом контейнере -->
    <div id="portal" style="position: fixed; left: 0; top: 0; z-index: 9999"></div>
```

### 7.2. Базовые модули (`frontend/src/sheet/`)

Создайте каталог `frontend/src/sheet/` и положите в него шесть файлов, **в таком порядке**.

#### Создать `frontend/src/sheet/address.ts`

Лимиты (те же, что на сервере), числовой ключ ячейки для `Map` (быстрее строкового), перевод номера колонки в буквы.

```ts
// Лимиты листа. Те же числа заданы на бэкенде в table_service/app/schemas/sheet.py
export const MAX_ROWS = 100_000;
export const MAX_COLS = 1_000;
export const MAX_BATCH_ITEMS = 20_000;

export const DEFAULT_ROWS = 1_000;
export const DEFAULT_COLS = 26;

// Числовой ключ ячейки для Map: быстрее, чем строка "row:col". MAX_COLS < COL_STRIDE.
const COL_STRIDE = 1024;

export const cellKey = (row: number, col: number): number => row * COL_STRIDE + col;
export const keyRow = (key: number): number => Math.floor(key / COL_STRIDE);
export const keyCol = (key: number): number => key % COL_STRIDE;

/** 0 -> A, 25 -> Z, 26 -> AA */
export function colToLetters(col: number): string {
    let n = col + 1;
    let result = '';
    while (n > 0) {
        const rem = (n - 1) % 26;
        result = String.fromCharCode(65 + rem) + result;
        n = Math.floor((n - 1) / 26);
    }
    return result;
}

export const addressLabel = (row: number, col: number): string => `${colToLetters(col)}${row + 1}`;
```

#### Создать `frontend/src/sheet/types.ts`

Типы: стиль ячейки, `meta`, снимок, пакет изменений, WebSocket-событие, результат операции движка.

```ts
export type NumFmt = 'general' | 'number' | 'percent' | 'currency' | 'date' | 'datetime';

export interface CellStyle {
    bg?: string;
    fg?: string;
    bold?: boolean;
    italic?: boolean;
    halign?: 'left' | 'center' | 'right';
    wrap?: boolean;
    numFmt?: NumFmt;
    decimals?: number;
}

/** Патч оформления: null — убрать свойство. */
export type StylePatch = { [K in keyof CellStyle]?: CellStyle[K] | null };

/** Вычисленное значение ячейки; ошибки приходят как {e: "#DIV/0!"}. */
export type CellValue = string | number | boolean | null | { e: string };

export interface SheetMeta {
    /** Ширины колонок: индекс колонки -> px */
    col_widths?: Record<string, number>;
    /** Сколько левых колонок закреплено */
    frozen_cols?: number;
    /** Оформление целых колонок / строк (индекс -> стиль) */
    col_styles?: Record<string, CellStyle>;
    row_styles?: Record<string, CellStyle>;
}

// [row, col, raw, value, style]
export type WireCell = [number, number, string | null, CellValue, CellStyle | null];

export interface SheetSnapshot {
    table_id: number;
    revision: number;
    layout_revision: number;
    can_write: boolean;
    meta: SheetMeta;
    cells: WireCell[];
}

export type StructuralKind = 'insert_rows' | 'delete_rows' | 'insert_cols' | 'delete_cols';

export interface StructuralOp {
    kind: StructuralKind;
    index: number;
    count: number;
}

export interface CellWrite {
    row: number;
    col: number;
    raw: string | null;
    value: CellValue;
}

export interface StyleWrite {
    row: number;
    col: number;
    style: CellStyle | null;
}

export interface SheetBatch {
    client_id: string;
    base_layout_revision: number;
    structural: StructuralOp | null;
    cells: CellWrite[];
    styles: StyleWrite[];
    meta: SheetMeta | null;
}

export interface SheetBatchResult {
    revision: number;
    layout_revision: number;
}

export interface SheetEvent {
    kind: 'batch' | 'reload';
    table_id: number;
    revision: number;
    layout_revision: number;
    actor_id: number;
    client_id: string;
    structural: StructuralOp | null;
    cells: CellWrite[];
    styles: StyleWrite[];
    meta: SheetMeta | null;
    occurred_at: string;
}

/** Результат любой локальной операции: что нужно отправить на сервер. */
export interface EngineResult {
    cells: CellWrite[];
    styles: StyleWrite[];
    meta?: SheetMeta;
    structural?: StructuralOp;
}

export interface Rect {
    x: number;
    y: number;
    width: number;
    height: number;
}
```

#### Создать `frontend/src/sheet/format.ts`

Как значение HyperFormula превратить в текст ячейки: ошибки, булевы, числа с форматами (число, процент, валюта), даты и дата-время (через `hf.numberToDate`). Числа «general» чистятся от двоичных хвостов (`0.1+0.2` → `0.3`).

```ts
import type {HyperFormula} from 'hyperformula';
import {DetailedCellError} from 'hyperformula';
import type {CellStyle, NumFmt} from './types';

export interface FormattedValue {
    text: string;
    isError: boolean;
    isNumber: boolean;
}

interface DateTimeParts {
    year: number;
    month: number;
    day: number;
    hours: number;
    minutes: number;
    seconds: number;
}

const pad = (n: number, len = 2): string => String(n).padStart(len, '0');

const AUTO_FORMATS: Record<string, NumFmt> = {
    NUMBER_DATE: 'date',
    NUMBER_DATETIME: 'datetime',
    NUMBER_PERCENT: 'percent',
    NUMBER_CURRENCY: 'currency',
};

const intl = (options: Intl.NumberFormatOptions) => new Intl.NumberFormat('en-US', options);

function formatNumber(n: number, fmt: NumFmt, decimals: number | undefined): string {
    switch (fmt) {
        case 'number':
            return intl({minimumFractionDigits: decimals ?? 2, maximumFractionDigits: decimals ?? 2}).format(n);
        case 'percent':
            return intl({style: 'percent', minimumFractionDigits: decimals ?? 0, maximumFractionDigits: decimals ?? 2}).format(n);
        case 'currency':
            return intl({
                style: 'currency', currency: 'RUB', currencyDisplay: 'narrowSymbol',
                minimumFractionDigits: decimals ?? 2, maximumFractionDigits: decimals ?? 2,
            }).format(n);
        default:
            // general: убираем «хвосты» двоичной арифметики (0.1 + 0.2)
            return Number.isInteger(n) ? String(n) : String(parseFloat(n.toPrecision(12)));
    }
}

/**
 * Значение HyperFormula -> строка для показа в ячейке.
 * detailedType — результат hf.getCellValueDetailedType (NUMBER_DATE и т.п.).
 */
export function formatValue(
    hf: HyperFormula,
    value: unknown,
    detailedType: string,
    style: CellStyle | undefined,
): FormattedValue {
    if (value === null || value === undefined) return {text: '', isError: false, isNumber: false};
    if (value instanceof DetailedCellError) return {text: value.value, isError: true, isNumber: false};
    if (typeof value === 'boolean') return {text: value ? 'TRUE' : 'FALSE', isError: false, isNumber: false};
    if (typeof value === 'string') return {text: value, isError: false, isNumber: false};
    if (typeof value !== 'number') return {text: String(value), isError: false, isNumber: false};

    const fmt = style?.numFmt ?? AUTO_FORMATS[detailedType] ?? 'general';
    if (fmt === 'date') {
        const d = hf.numberToDate(value) as DateTimeParts | undefined;
        if (d) return {text: `${pad(d.day)}.${pad(d.month)}.${d.year}`, isError: false, isNumber: true};
    }
    if (fmt === 'datetime') {
        const d = hf.numberToDateTime(value) as DateTimeParts | undefined;
        if (d) {
            const time = `${pad(d.hours)}:${pad(d.minutes)}:${pad(Math.floor(d.seconds))}`;
            return {text: `${pad(d.day)}.${pad(d.month)}.${d.year} ${time}`, isError: false, isNumber: true};
        }
    }
    return {text: formatNumber(value, fmt, style?.decimals), isError: false, isNumber: true};
}
```

#### Создать `frontend/src/sheet/engine.ts`

Главный модуль. Обратите внимание на три места: (1) `diffKeys` — сравнение с зеркалом; (2) `applyStructural` — сначала HyperFormula переписывает формулы, потом сдвигаются зеркало и стили, потом считается diff; (3) `applyRemote` — внутри `hf.batch()` читать из движка нельзя (бросает `EvaluationSuspendedError`), поэтому решения принимаются до `batch`.

```ts
import {
    CellType,
    DetailedCellError,
    HyperFormula,
    type ExportedChange,
    type SimpleCellAddress,
} from 'hyperformula';
import {cellKey, keyCol, keyRow, MAX_COLS, MAX_ROWS} from './address';
import {formatValue} from './format';
import type {
    CellStyle,
    CellValue,
    CellWrite,
    EngineResult,
    Rect,
    SheetEvent,
    SheetMeta,
    SheetSnapshot,
    StructuralKind,
    StructuralOp,
    StylePatch,
    StyleWrite,
} from './types';

const SHEET_NAME = 'Sheet1';
const MAX_STYLE_CELLS = 20_000;

interface CellSnap {
    raw: string | null;
    value: CellValue;
}

/** Что подставить в выделение при применении оформления. */
export type StyleTarget =
    | {kind: 'range'; rect: Rect}
    | {kind: 'cols'; cols: number[]}
    | {kind: 'rows'; rows: number[]};

export interface CellView {
    /** Что показать в ячейке */
    text: string;
    /** Что показать при редактировании (формула или введённый текст) */
    raw: string;
    isError: boolean;
    isNumber: boolean;
    style: CellStyle | undefined;
}

const EMPTY_RESULT = (): EngineResult => ({cells: [], styles: []});

function serialize(content: unknown): string | null {
    if (content === null || content === undefined) return null;
    if (typeof content === 'boolean') return content ? 'TRUE' : 'FALSE';
    return String(content);
}

function toWire(value: unknown): CellValue {
    if (value instanceof DetailedCellError) return {e: value.value};
    if (value === null || value === undefined) return null;
    if (typeof value === 'number' && !Number.isFinite(value)) return {e: '#NUM!'};
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value;
    return String(value);
}

function sameValue(a: CellValue, b: CellValue): boolean {
    if (a === b) return true;
    if (typeof a === 'object' && a !== null && typeof b === 'object' && b !== null) return a.e === b.e;
    return false;
}

function mergeStyle(base: CellStyle | undefined, patch: StylePatch): CellStyle | null {
    const out: Record<string, unknown> = {...(base ?? {})};
    for (const [key, value] of Object.entries(patch)) {
        if (value === null || value === undefined) delete out[key];
        else out[key] = value;
    }
    return Object.keys(out).length ? (out as CellStyle) : null;
}

/** Новый индекс после структурной операции; null — строка/колонка удалена. */
function mapIndex(i: number, op: StructuralOp): number | null {
    if (op.kind.startsWith('insert')) return i >= op.index ? i + op.count : i;
    if (i < op.index) return i;
    if (i < op.index + op.count) return null;
    return i - op.count;
}

const isRowOp = (kind: StructuralKind): boolean => kind.endsWith('rows');

/** Сдвиг индексов в словаре meta (ширины колонок, оформление строк/колонок). */
function remapRecord<T>(record: Record<string, T> | undefined, op: StructuralOp): Record<string, T> | undefined {
    if (!record) return record;
    const out: Record<string, T> = {};
    for (const [key, value] of Object.entries(record)) {
        const next = mapIndex(Number(key), op);
        if (next !== null) out[String(next)] = value;
    }
    return out;
}

export function remapMeta(meta: SheetMeta, op: StructuralOp): SheetMeta {
    const next: SheetMeta = {...meta};
    if (isRowOp(op.kind)) {
        next.row_styles = remapRecord(meta.row_styles, op);
    } else {
        next.col_widths = remapRecord(meta.col_widths, op);
        next.col_styles = remapRecord(meta.col_styles, op);
    }
    return next;
}

/**
 * Обёртка над HyperFormula: один лист, «зеркало» того, что уже сохранено на сервере,
 * и вычисление diff'а для отправки пакетов.
 */
export class SheetEngine {
    private readonly hf: HyperFormula;
    private readonly sheet: number;

    /** Последнее известное серверу состояние непустых ячеек: ключ -> {raw, value}. */
    private mirror = new Map<number, CellSnap>();
    /** Оформление отдельных ячеек. */
    styles = new Map<number, CellStyle>();
    meta: SheetMeta = {};

    /** Прямоугольник, скопированный через hf.copy, и его оформление (для вставки со сдвигом ссылок). */
    private clip: {rect: Rect; styles: (CellStyle | undefined)[][]} | null = null;

    constructor() {
        this.hf = HyperFormula.buildEmpty({
            licenseKey: 'gpl-v3', // GPLv3: подходит для открытого/учебного проекта
            maxRows: MAX_ROWS,
            maxColumns: MAX_COLS,
            // Как вводит пользователь; "2024-01-05" по умолчанию считается строкой
            dateFormats: ['DD.MM.YYYY', 'YYYY-MM-DD', 'DD/MM/YYYY'],
        });
        this.hf.addSheet(SHEET_NAME);
        this.sheet = this.hf.getSheetId(SHEET_NAME)!;
    }

    destroy(): void {
        this.hf.destroy();
    }

    private addr(row: number, col: number): SimpleCellAddress {
        return {sheet: this.sheet, row, col};
    }

    // ───────────────────────────── загрузка ─────────────────────────────

    /**
     * Заменить содержимое снимком с сервера.
     * Возвращает «починку»: ячейки, у которых сохранённое value не совпало с вычисленным
     * (например, импорт из Excel без кэша значений) — её нужно отправить на сервер.
     */
    load(snapshot: SheetSnapshot): CellWrite[] {
        this.hf.clearSheet(this.sheet);
        this.mirror.clear();
        this.styles.clear();
        this.clip = null;
        this.meta = snapshot.meta ?? {};

        this.hf.suspendEvaluation();
        for (const [row, col, raw, value, style] of snapshot.cells) {
            const key = cellKey(row, col);
            if (style) this.styles.set(key, style);
            // raw == null: значение «разлито» формулой массива из другой ячейки — его пересчитает HF
            if (raw !== null) this.hf.setCellContents(this.addr(row, col), raw);
            if (raw !== null || value !== null) this.mirror.set(key, {raw, value});
        }
        this.hf.resumeEvaluation();

        return this.diffKeys(Array.from(this.mirror.keys()));
    }

    /** Размеры занятой области (для начального числа строк/колонок в сетке). */
    extent(): {rows: number; cols: number} {
        let rows = 0;
        let cols = 0;
        const grow = (key: number) => {
            rows = Math.max(rows, keyRow(key) + 1);
            cols = Math.max(cols, keyCol(key) + 1);
        };
        for (const key of this.mirror.keys()) grow(key);
        for (const key of this.styles.keys()) grow(key);
        return {rows, cols};
    }

    // ───────────────────────────── чтение ─────────────────────────────

    effectiveStyle(row: number, col: number): CellStyle | undefined {
        const colStyle = this.meta.col_styles?.[col];
        const rowStyle = this.meta.row_styles?.[row];
        const cellStyle = this.styles.get(cellKey(row, col));
        if (!colStyle && !rowStyle && !cellStyle) return undefined;
        return {...colStyle, ...rowStyle, ...cellStyle};
    }

    view(row: number, col: number): CellView {
        const style = this.effectiveStyle(row, col);
        const addr = this.addr(row, col);
        const type = this.hf.getCellType(addr);
        if (type === CellType.EMPTY) return {text: '', raw: '', isError: false, isNumber: false, style};

        const value = this.hf.getCellValue(addr);
        const shown = formatValue(this.hf, value, this.hf.getCellValueDetailedType(addr), style);
        // У «разлитых» ячеек нет собственного содержимого — при редактировании показываем значение
        const raw = type === CellType.ARRAY ? shown.text : (serialize(this.hf.getCellSerialized(addr)) ?? '');
        return {...shown, raw, style};
    }

    // ───────────────────────────── diff ─────────────────────────────

    private snap(row: number, col: number): CellSnap {
        const addr = this.addr(row, col);
        const type = this.hf.getCellType(addr);
        if (type === CellType.EMPTY) return {raw: null, value: null};
        const value = toWire(this.hf.getCellValue(addr));
        if (type === CellType.ARRAY) return {raw: null, value};
        return {raw: serialize(this.hf.getCellSerialized(addr)), value};
    }

    /** Сравнить текущее состояние движка с зеркалом для указанных ячеек, обновить зеркало. */
    private diffKeys(keys: Iterable<number>): CellWrite[] {
        const out: CellWrite[] = [];
        for (const key of new Set(keys)) {
            const row = keyRow(key);
            const col = keyCol(key);
            const now = this.snap(row, col);
            const old = this.mirror.get(key);
            if (old && old.raw === now.raw && sameValue(old.value, now.value)) continue;
            if (!old && now.raw === null && now.value === null) continue;
            if (now.raw === null && now.value === null) this.mirror.delete(key);
            else this.mirror.set(key, now);
            out.push({row, col, raw: now.raw, value: now.value});
        }
        return out;
    }

    private keysOf(changes: ExportedChange[], extra: Iterable<number> = []): number[] {
        const keys = new Set<number>(extra);
        for (const change of changes) {
            if ('address' in change && change.address.sheet === this.sheet) {
                keys.add(cellKey(change.address.row, change.address.col));
            }
        }
        return Array.from(keys);
    }

    private rectKeys(rect: Rect): number[] {
        const keys: number[] = [];
        for (let r = rect.y; r < rect.y + rect.height; r++) {
            for (let c = rect.x; c < rect.x + rect.width; c++) keys.push(cellKey(r, c));
        }
        return keys;
    }

    /** Даты, введённые руками, получают формат «дата» автоматически (как в Google Таблицах). */
    private autoDateStyles(keys: number[]): StyleWrite[] {
        const out: StyleWrite[] = [];
        for (const key of keys) {
            const row = keyRow(key);
            const col = keyCol(key);
            const addr = this.addr(row, col);
            if (this.hf.getCellType(addr) !== CellType.VALUE) continue;
            const detailed = this.hf.getCellValueDetailedType(addr);
            const fmt = detailed === 'NUMBER_DATE' ? 'date' : detailed === 'NUMBER_DATETIME' ? 'datetime' : null;
            if (!fmt || this.styles.get(key)?.numFmt) continue;
            const style = {...this.styles.get(key), numFmt: fmt} as CellStyle;
            this.styles.set(key, style);
            out.push({row, col, style});
        }
        return out;
    }

    // ───────────────────────────── редактирование ─────────────────────────────

    setRaw(row: number, col: number, raw: string): EngineResult {
        return this.setMatrix(row, col, [[raw]]);
    }

    /** Записать прямоугольник «как ввёл пользователь» (ввод, вставка из буфера). */
    setMatrix(row: number, col: number, matrix: string[][]): EngineResult {
        const height = Math.min(matrix.length, MAX_ROWS - row);
        const width = Math.min(Math.max(...matrix.map((r) => r.length)), MAX_COLS - col);
        if (height <= 0 || width <= 0) return EMPTY_RESULT();

        const content = matrix.slice(0, height).map((line) =>
            Array.from({length: width}, (_, i) => (line[i] === undefined || line[i] === '' ? null : line[i])),
        );
        const changes = this.hf.setCellContents(this.addr(row, col), content);
        const touched = this.rectKeys({x: col, y: row, width, height});
        const cells = this.diffKeys(this.keysOf(changes, touched));
        return {cells, styles: this.autoDateStyles(touched)};
    }

    /** Очистить содержимое (оформление остаётся). */
    clearRange(rect: Rect): EngineResult {
        const targets: number[] = [];
        for (const key of this.mirror.keys()) {
            const r = keyRow(key);
            const c = keyCol(key);
            if (r >= rect.y && r < rect.y + rect.height && c >= rect.x && c < rect.x + rect.width) targets.push(key);
        }
        // batch() сам собирает изменения всех внутренних операций и возвращает их списком
        const changes = this.hf.batch(() => {
            for (const key of targets) {
                const addr = this.addr(keyRow(key), keyCol(key));
                // Ячейки, «разлитые» из формулы массива, очищаются вместе с формулой-источником
                if (this.hf.getCellType(addr) === CellType.ARRAY) continue;
                this.hf.setCellContents(addr, null);
            }
        });
        return {cells: this.diffKeys(this.keysOf(changes, targets)), styles: []};
    }

    // ───────────────────────────── структура ─────────────────────────────

    canApply(op: StructuralOp): boolean {
        const range: [number, number] = [op.index, op.count];
        switch (op.kind) {
            case 'insert_rows':
                return this.hf.isItPossibleToAddRows(this.sheet, range);
            case 'delete_rows':
                return this.hf.isItPossibleToRemoveRows(this.sheet, range);
            case 'insert_cols':
                return this.hf.isItPossibleToAddColumns(this.sheet, range);
            case 'delete_cols':
                return this.hf.isItPossibleToRemoveColumns(this.sheet, range);
        }
    }

    private runStructural(op: StructuralOp): ExportedChange[] {
        const range: [number, number] = [op.index, op.count];
        switch (op.kind) {
            case 'insert_rows':
                return this.hf.addRows(this.sheet, range);
            case 'delete_rows':
                return this.hf.removeRows(this.sheet, range);
            case 'insert_cols':
                return this.hf.addColumns(this.sheet, range);
            case 'delete_cols':
                return this.hf.removeColumns(this.sheet, range);
        }
    }

    /** Переставить зеркало и оформление ячеек после структурной операции. */
    private remapState(op: StructuralOp): void {
        const remapKey = (key: number): number | null => {
            const row = keyRow(key);
            const col = keyCol(key);
            if (isRowOp(op.kind)) {
                const next = mapIndex(row, op);
                return next === null ? null : cellKey(next, col);
            }
            const next = mapIndex(col, op);
            return next === null ? null : cellKey(row, next);
        };
        const mirror = new Map<number, CellSnap>();
        for (const [key, snap] of this.mirror) {
            const next = remapKey(key);
            if (next !== null) mirror.set(next, snap);
        }
        const styles = new Map<number, CellStyle>();
        for (const [key, style] of this.styles) {
            const next = remapKey(key);
            if (next !== null) styles.set(next, style);
        }
        this.mirror = mirror;
        this.styles = styles;
        this.clip = null;
    }

    /**
     * Вставка/удаление строк и колонок. Сервер сам сдвинет ячейки и оформление; клиент присылает
     * только ячейки, чей raw (формула со сдвинутыми ссылками) или value изменились.
     */
    applyStructural(op: StructuralOp): EngineResult {
        const changes = this.runStructural(op);
        this.remapState(op);
        this.meta = remapMeta(this.meta, op);
        const cells = this.diffKeys(this.keysOf(changes, this.mirror.keys()));
        return {cells, styles: [], meta: this.meta, structural: op};
    }

    // ───────────────────────────── копирование ─────────────────────────────

    copy(rect: Rect): void {
        this.hf.copy({
            start: this.addr(rect.y, rect.x),
            end: this.addr(rect.y + rect.height - 1, rect.x + rect.width - 1),
        });
        const styles: (CellStyle | undefined)[][] = [];
        for (let r = 0; r < rect.height; r++) {
            const line: (CellStyle | undefined)[] = [];
            for (let c = 0; c < rect.width; c++) line.push(this.styles.get(cellKey(rect.y + r, rect.x + c)));
            styles.push(line);
        }
        this.clip = {rect, styles};
    }

    hasClip(): boolean {
        return this.clip !== null && !this.hf.isClipboardEmpty();
    }

    /** Вставка скопированного: относительные ссылки в формулах сдвигаются, как в Google Таблицах. */
    paste(row: number, col: number): EngineResult {
        const clip = this.clip;
        if (!clip) return EMPTY_RESULT();
        const changes = this.hf.paste(this.addr(row, col));
        const rect = {x: col, y: row, width: clip.rect.width, height: clip.rect.height};

        const styles: StyleWrite[] = [];
        clip.styles.forEach((line, dr) =>
            line.forEach((style, dc) => {
                const key = cellKey(row + dr, col + dc);
                if (!style && !this.styles.has(key)) return;
                if (style) this.styles.set(key, style);
                else this.styles.delete(key);
                styles.push({row: row + dr, col: col + dc, style: style ?? null});
            }),
        );
        return {cells: this.diffKeys(this.keysOf(changes, this.rectKeys(rect))), styles};
    }

    // ───────────────────────────── оформление ─────────────────────────────

    /** Применить патч оформления к диапазону / целым колонкам / целым строкам. */
    applyStyle(target: StyleTarget, patch: StylePatch): EngineResult {
        const styles: StyleWrite[] = [];
        const setCell = (row: number, col: number, next: CellStyle | null) => {
            const key = cellKey(row, col);
            if (next) this.styles.set(key, next);
            else if (!this.styles.delete(key)) return;
            styles.push({row, col, style: next});
        };

        if (target.kind === 'range') {
            const {rect} = target;
            if (rect.width * rect.height > MAX_STYLE_CELLS) {
                throw new Error(`Оформление можно применять не больше чем к ${MAX_STYLE_CELLS} ячейкам за раз`);
            }
            for (let r = rect.y; r < rect.y + rect.height; r++) {
                for (let c = rect.x; c < rect.x + rect.width; c++) {
                    setCell(r, c, mergeStyle(this.styles.get(cellKey(r, c)), patch));
                }
            }
            return {cells: [], styles};
        }

        // Целые колонки/строки: стиль живёт в meta, а у отдельных ячеек затираем те же свойства
        const meta: SheetMeta = {...this.meta};
        const isCols = target.kind === 'cols';
        const indexes = isCols ? target.cols : target.rows;
        const holder = {...((isCols ? meta.col_styles : meta.row_styles) ?? {})};
        for (const index of indexes) {
            const next = mergeStyle(holder[index], patch);
            if (next) holder[index] = next;
            else delete holder[index];
        }
        if (isCols) meta.col_styles = holder;
        else meta.row_styles = holder;
        this.meta = meta;

        const overridePatch = Object.fromEntries(Object.keys(patch).map((k) => [k, null])) as StylePatch;
        for (const [key, style] of Array.from(this.styles)) {
            const index = isCols ? keyCol(key) : keyRow(key);
            if (indexes.includes(index)) setCell(keyRow(key), keyCol(key), mergeStyle(style, overridePatch));
        }
        return {cells: [], styles, meta};
    }

    setColumnWidth(col: number, width: number): SheetMeta {
        this.meta = {...this.meta, col_widths: {...this.meta.col_widths, [col]: Math.round(width)}};
        return this.meta;
    }

    setFrozenCols(count: number): SheetMeta {
        this.meta = {...this.meta, frozen_cols: count};
        return this.meta;
    }

    // ───────────────────────────── чужие изменения ─────────────────────────────

    /** Применить событие другого клиента (WS). Обратно на сервер ничего не отправляется. */
    applyRemote(event: SheetEvent): void {
        if (event.structural) {
            this.runStructural(event.structural);
            this.remapState(event.structural);
        }
        if (event.meta) this.meta = event.meta;

        // Внутри batch() чтение из движка запрещено, поэтому сначала решаем, что записывать
        const writes: {addr: SimpleCellAddress; content: string | null}[] = [];
        for (const cell of event.cells) {
            const key = cellKey(cell.row, cell.col);
            const addr = this.addr(cell.row, cell.col);
            const type = this.hf.getCellType(addr);
            if (cell.raw !== null) {
                if (serialize(this.hf.getCellSerialized(addr)) !== cell.raw) writes.push({addr, content: cell.raw});
            } else if (type !== CellType.ARRAY && type !== CellType.EMPTY) {
                writes.push({addr, content: null});
            }
            if (cell.raw === null && cell.value === null) this.mirror.delete(key);
            else this.mirror.set(key, {raw: cell.raw, value: cell.value});
        }
        this.hf.batch(() => {
            for (const {addr, content} of writes) this.hf.setCellContents(addr, content);
        });
        for (const s of event.styles) {
            const key = cellKey(s.row, s.col);
            if (s.style) this.styles.set(key, s.style);
            else this.styles.delete(key);
        }
    }
}
```

#### Создать `frontend/src/sheet/syncQueue.ts`

Очередь отправки: один запрос в полёте, правки склеиваются в хвостовой пакет, структурная операция всегда открывает новый пакет, пакеты больше 5 000 ячеек режутся на несколько запросов (структурная операция и `meta` — только в первом). 409 → `onConflict`, остальные ошибки → `onError`.

```ts
import {cellKey} from './address';
import type {CellWrite, EngineResult, SheetMeta, StructuralOp, StyleWrite} from './types';

// Запросов на сервер не больше, чем MAX_BATCH_ITEMS (20 000) элементов; берём с запасом
const CHUNK = 5_000;

export interface OutgoingBatch {
    structural: StructuralOp | null;
    cells: CellWrite[];
    styles: StyleWrite[];
    meta: SheetMeta | null;
}

interface PendingItem {
    structural: StructuralOp | null;
    cells: Map<number, CellWrite>;
    styles: Map<number, StyleWrite>;
    meta: SheetMeta | null;
}

export interface SyncQueueHandlers {
    send: (batch: OutgoingBatch) => Promise<void>;
    /** Сервер отклонил пакет, потому что структура листа изменилась (409) */
    onConflict: () => void;
    onError: (error: unknown) => void;
    onBusyChange: (busy: boolean) => void;
}

const newItem = (structural: StructuralOp | null): PendingItem => ({
    structural,
    cells: new Map(),
    styles: new Map(),
    meta: null,
});

/**
 * Очередь исходящих изменений: один запрос в полёте, подряд идущие правки склеиваются.
 * Структурная операция всегда начинает новый пакет: координаты последующих ячеек
 * относятся к листу уже ПОСЛЕ неё.
 */
export class SyncQueue {
    private items: PendingItem[] = [];
    private busy = false;

    constructor(private readonly handlers: SyncQueueHandlers) {}

    push(change: EngineResult): void {
        let tail = this.items[this.items.length - 1];
        if (change.structural || !tail) {
            tail = newItem(change.structural ?? null);
            this.items.push(tail);
        }
        for (const cell of change.cells) tail.cells.set(cellKey(cell.row, cell.col), cell);
        for (const style of change.styles) tail.styles.set(cellKey(style.row, style.col), style);
        if (change.meta) tail.meta = change.meta;
        void this.pump();
    }

    /** Выбросить всё неотправленное (после перезагрузки снимка). */
    clear(): void {
        this.items = [];
    }

    private async pump(): Promise<void> {
        if (this.busy) return;
        this.busy = true;
        this.handlers.onBusyChange(true);
        try {
            while (this.items.length) {
                await this.sendItem(this.items.shift()!);
            }
        } catch (error) {
            this.items = [];
            if ((error as {response?: {status?: number}})?.response?.status === 409) this.handlers.onConflict();
            else this.handlers.onError(error);
        } finally {
            this.busy = false;
            this.handlers.onBusyChange(false);
        }
    }

    private async sendItem(item: PendingItem): Promise<void> {
        const cells = Array.from(item.cells.values());
        const styles = Array.from(item.styles.values());
        let first = true;
        for (let ci = 0, si = 0; first || ci < cells.length || si < styles.length; ci += CHUNK, si += CHUNK) {
            await this.handlers.send({
                structural: first ? item.structural : null,
                meta: first ? item.meta : null,
                cells: cells.slice(ci, ci + CHUNK),
                styles: styles.slice(si, si + CHUNK),
            });
            first = false;
        }
    }
}
```

#### Создать `frontend/src/sheet/sequencer.ts`

Упорядочивание WebSocket-событий по `revision`. События до загрузки снимка копятся и после `reset(revision)` проигрываются.

```ts
import type {SheetEvent} from './types';

const GAP_TIMEOUT_MS = 2_000;

/**
 * Выстраивает события WS строго по revision. Если очередное событие не пришло
 * за GAP_TIMEOUT_MS, вызывает onGap (клиент перечитывает снимок).
 */
export class EventSequencer {
    private expected: number | null = null;
    private buffer = new Map<number, SheetEvent>();
    private gapTimer: number | null = null;

    constructor(
        private readonly apply: (event: SheetEvent) => void,
        private readonly onGap: () => void,
    ) {}

    /** Снимок загружен на ревизии `revision`: ждём revision + 1. */
    reset(revision: number): void {
        this.expected = revision + 1;
        for (const key of Array.from(this.buffer.keys())) {
            if (key < this.expected) this.buffer.delete(key);
        }
        this.drain();
    }

    push(event: SheetEvent): void {
        if (this.expected !== null && event.revision < this.expected) return;
        this.buffer.set(event.revision, event);
        this.drain();
    }

    dispose(): void {
        if (this.gapTimer) window.clearTimeout(this.gapTimer);
        this.gapTimer = null;
        this.buffer.clear();
    }

    private drain(): void {
        if (this.expected === null) return;
        for (let next = this.buffer.get(this.expected); next; next = this.buffer.get(this.expected)) {
            this.buffer.delete(this.expected);
            this.expected += 1;
            this.apply(next);
        }
        if (this.buffer.size === 0) {
            if (this.gapTimer) window.clearTimeout(this.gapTimer);
            this.gapTimer = null;
        } else if (this.gapTimer === null) {
            this.gapTimer = window.setTimeout(() => {
                this.gapTimer = null;
                if (this.buffer.size > 0) this.onGap();
            }, GAP_TIMEOUT_MS);
        }
    }
}
```

### 7.3. API-слой

#### Создать `frontend/src/api/sheet.ts`

Два вызова: снимок и пакет изменений.

```ts
import {api} from './axiosInstance';
import type {SheetBatch, SheetBatchResult, SheetSnapshot} from '../sheet/types';

export const sheetAPI = {
    getSheet: async (tableId: number): Promise<SheetSnapshot> => {
        const response = await api.get(`/data/${tableId}/sheet`);
        return response.data;
    },

    applyBatch: async (tableId: number, batch: SheetBatch): Promise<SheetBatchResult> => {
        const response = await api.post(`/data/${tableId}/sheet/batch`, batch);
        return response.data;
    },
};
```

#### Изменить `frontend/src/api/ws.ts`

Событие теперь `SheetEvent`; добавлен колбэк `onReconnect` — при каждом повторном подключении клиент обязан перечитать лист, потому что за время обрыва события могли потеряться.


**Правка 1 из 6.** **Заменить строку 59**.

Было:

```ts
        ws.onmessage = (msg) => onEvent(JSON.parse(msg.data) as RowEvent);
```

Стало:

```ts
        ws.onmessage = (msg) => onEvent(JSON.parse(msg.data) as SheetEvent);
```

**Правка 2 из 6.** Вставить **после строки 57**:

```ts
            if (wasConnected) onReconnect?.();
            wasConnected = true;
```

**Правка 3 из 6.** Вставить **после строки 40**:

```ts
    let wasConnected = false;
```

**Правка 4 из 6.** **Заменить строку 36**.

Было:

```ts
    onEvent: (event: RowEvent) => void,
```

Стало:

```ts
    onEvent: (event: SheetEvent) => void,
    onReconnect?: () => void,
```

**Правка 5 из 6.** **Заменить строку 31**.

Было:

```ts
 * Подписка на события строк таблицы с автопереподключением (экспоненциальный backoff).
```

Стало:

```ts
 * Подписка на события листа с автопереподключением (экспоненциальный backoff).
 * onReconnect вызывается при каждом ПОВТОРНОМ подключении: за время обрыва
 * могли пропасть события, поэтому клиент перечитывает снимок листа.
```

**Правка 6 из 6.** **Заменить строки 2–13**.

Было:

```ts
import {TableRow} from './tables';

export type RowEventType = 'row.created' | 'row.updated' | 'row.deleted';

export interface RowEvent {
    event: RowEventType;
    table_id: number;
    row_id: number;
    actor_id: number;
    row: TableRow | null;
    occurred_at: string;
}
```

Стало:

```ts
import type {SheetEvent} from '../sheet/types';
```

#### Заменить файл целиком: `frontend/src/api/tables.ts`

Из файла уходят `mathjs`, `evaluateFormula`, `isFormula`, типы строк и колонок и все методы строк (`getTableRows`, `createRow`, `updateRow`, `deleteRow`, `bulkDeleteRows`, `duplicateRow`). Остальное — без изменений. Если у вас в этом файле появились свои правки после моего чтения, перенесите только удаление перечисленного.

Было 316 строк. Новое содержимое:

```ts
import {api} from './axiosInstance';

export interface DataTableResponse {
    id: number;
    name: string;
    description?: string;
    is_public?: boolean;
    created_by: number;
    created_at: string;
    updated_at?: string;
    is_deleted?: boolean;
    deleted_at?: string;
    is_pinned?: boolean;
}

export interface CreateTableRequest {
    name: string;
    description?: string;
    is_public?: boolean;
}

export interface UpdateTableRequest {
    name?: string;
    description?: string;
    is_public?: boolean;
}


interface ExportResult {
    blob: Blob;
    filename: string;
}

export type ExportJobStatus = 'pending' | 'running' | 'completed' | 'error';

export interface ExportJobCreated {
    job_id: string;
    status: ExportJobStatus;
}

export type ExportJobState = {
    job_id: string;
    status: ExportJobStatus;
    filename: string;
    download_url: string | null;
    error: string | null;
}


// Достаёт имя файла из заголовка Content-Disposition (поддержка filename*=UTF-8'')
function parseFilename(disposition: string): string | null {
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match) {
        return decodeURIComponent(utf8Match[1]);
    }
    const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
    return plainMatch ? plainMatch[1] : null;
}

export const tablesAPI = {
    getAllTables: async (): Promise<DataTableResponse[]> => {
        const response = await api.get('/tables');
        return response.data;
    },

    getTrash: async (): Promise<DataTableResponse[]> => {
        const response = await api.get(`/tables/trash/`);
        return response.data;
    },

    createTable: async (data: CreateTableRequest): Promise<DataTableResponse> => {
        const response = await api.post('/tables/create', data);
        return response.data;
    },

    getTableById: async (id: number): Promise<DataTableResponse> => {
        const response = await api.get(`/tables/${id}`);
        return response.data;
    },

    deleteTable: async (id: number): Promise<void> => {
        await api.delete(`/tables/delete/${id}`);
    },

    updateTable: async (id: number, data: UpdateTableRequest): Promise<DataTableResponse> => {
        const response = await api.patch(`/tables/${id}/`, data);
        return response.data;
    },

    duplicateTable: async (id: number, options: {
        name?: string;
        withRows?: boolean
    } = {}): Promise<DataTableResponse> => {
        const response = await api.post(`/tables/${id}/duplicate`, {
            name: options.name || null,
            with_rows: options.withRows ?? null,
        });
        return response.data;
    },

    permanentDelete: async (id: number): Promise<void> => {
        await api.delete(`/tables/trash/${id}/`);
    },

    restoreTable: async (id: number): Promise<void> => {
        const response = await api.post(`/tables/trash/${id}/restore/`);

    },

    searchTables: async (query: string, limit: number = 10): Promise<DataTableResponse[]> => {
        const response = await api.get('/search', {params: {q: query, limit}});
        return response.data;
    },

    startExport: async (tableId: number): Promise<ExportJobCreated> => {
        const response = await api.post(`/tables/${tableId}/export-jobs`, {})
        return response.data;
    },

    getExportStatus: async (jobId: string): Promise<ExportJobState> => {
        const {data} = await api.get<ExportJobState>(`/tables/export-jobs/${jobId}`);
        return data;
    },

    waitForExport: async (jobId: string, secondsBetween = 2, timeoutMs = 10 * 60_000): Promise<ExportJobState> => {
        const deadline = Date.now() + timeoutMs;
        while (Date.now() < deadline) {
            const state = await tablesAPI.getExportStatus(jobId);
            if (state.status === 'completed' || state.status === 'error') return state;
            await new Promise(r => setTimeout(r, secondsBetween * 1000));
        }
        throw new Error('Экспорт не завершился за отведённое время');
    },
    pinTable: async (id: number): Promise<void> => {
        await api.post(`/tables/${id}/pin`);
    },

    unpinTable: async (id: number): Promise<void> => {
        await api.delete(`/tables/${id}/pin`);
    },
};
```

### 7.4. Хук и компоненты

#### Создать `frontend/src/hooks/useSheet.ts`

Склеивает движок, очередь и WebSocket. Порядок в эффекте важен: сначала подписка на события, потом загрузка снимка — события, пришедшие во время загрузки, секвенсор придержит. `engine.destroy()` намеренно не вызывается: `React.StrictMode` (он у вас включён в `main.tsx`) в dev-режиме монтирует эффект дважды на одном и том же объекте.

```ts
import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {sheetAPI} from '../api/sheet';
import {subscribeToTableEvents} from '../api/ws';
import {MAX_COLS, MAX_ROWS} from '../sheet/address';
import {SheetEngine, type StyleTarget} from '../sheet/engine';
import {EventSequencer} from '../sheet/sequencer';
import {SyncQueue} from '../sheet/syncQueue';
import type {EngineResult, Rect, SheetEvent, StructuralOp, StylePatch} from '../sheet/types';

export interface AccessError {
    status: number | null;
    message: string;
}

const makeClientId = (): string => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;

/**
 * Состояние листа: движок формул, синхронизация с сервером и WS.
 * Движок изменяемый, поэтому React узнаёт об изменениях через счётчик `version`.
 */
export function useSheet(tableId: number) {
    const engine = useMemo(() => new SheetEngine(), [tableId]);
    const clientId = useMemo(makeClientId, [tableId]);
    const layoutRevision = useRef(0);

    const [version, setVersion] = useState(0);
    const [loading, setLoading] = useState(true);
    const [canWrite, setCanWrite] = useState(false);
    const [saving, setSaving] = useState(false);
    const [notice, setNotice] = useState('');
    const [accessError, setAccessError] = useState<AccessError | null>(null);

    const redraw = useCallback(() => setVersion((v) => v + 1), []);

    // Очередь и секвенсор живут столько же, сколько таблица; ссылки на загрузчик — через ref,
    // потому что loadSnapshot создаётся после них.
    const loadRef = useRef<() => Promise<void>>(async () => {});

    const queue = useMemo(
        () =>
            new SyncQueue({
                send: async (batch) => {
                    const result = await sheetAPI.applyBatch(tableId, {
                        client_id: clientId,
                        base_layout_revision: layoutRevision.current,
                        ...batch,
                    });
                    layoutRevision.current = Math.max(layoutRevision.current, result.layout_revision);
                },
                onConflict: () => {
                    setNotice('Структуру листа изменил другой пользователь — данные обновлены, повторите действие');
                    void loadRef.current();
                },
                onError: (error) => {
                    console.error('sheet save error', error);
                    setNotice('Не удалось сохранить изменения — данные обновлены с сервера');
                    void loadRef.current();
                },
                onBusyChange: setSaving,
            }),
        [tableId, clientId],
    );

    const sequencer = useMemo(
        () =>
            new EventSequencer(
                (event: SheetEvent) => {
                    if (event.kind === 'reload') {
                        // Большой пакет: тело в событие не вошло. Свой же пакет перечитывать не нужно
                        if (event.client_id !== clientId) void loadRef.current();
                        return;
                    }
                    layoutRevision.current = Math.max(layoutRevision.current, event.layout_revision);
                    // Своё событие уже применено локально
                    if (event.client_id !== clientId) {
                        engine.applyRemote(event);
                        redraw();
                    }
                },
                () => void loadRef.current(),
            ),
        [engine, clientId, redraw],
    );

    const loadSnapshot = useCallback(async () => {
        try {
            const snapshot = await sheetAPI.getSheet(tableId);
            queue.clear();
            const repair = engine.load(snapshot);
            layoutRevision.current = snapshot.layout_revision;
            sequencer.reset(snapshot.revision);
            setCanWrite(snapshot.can_write);
            setAccessError(null);
            // Значения, которых не было на сервере (импорт из Excel и т.п.), досчитаны движком — сохраняем
            if (snapshot.can_write && repair.length) queue.push({cells: repair, styles: []});
            redraw();
        } catch (err: any) {
            const status = err.response?.status ?? null;
            setAccessError({
                status,
                message:
                    err.response?.data?.detail ||
                    (status === 403 ? 'Нет доступа к этой таблице' : status === 404 ? 'Таблица не найдена' : 'Не удалось загрузить таблицу'),
            });
        } finally {
            setLoading(false);
        }
    }, [tableId, engine, queue, sequencer, redraw]);
    loadRef.current = loadSnapshot;

    useEffect(() => {
        setLoading(true);
        // Сначала подписка, потом снимок: события, пришедшие во время загрузки, секвенсор придержит
        const unsubscribe = subscribeToTableEvents(tableId, (event) => sequencer.push(event), () => void loadSnapshot());
        void loadSnapshot();
        return () => {
            unsubscribe();
            sequencer.dispose();
            // engine.destroy() не зовём: в StrictMode эффект отрабатывает дважды на одном и том же движке
        };
    }, [tableId, engine, sequencer, loadSnapshot]);

    // ── операции ──

    const commit = useCallback(
        (result: EngineResult) => {
            if (!result.cells.length && !result.styles.length && !result.meta && !result.structural) return;
            queue.push(result);
            redraw();
        },
        [queue, redraw],
    );

    const guard = useCallback(
        <T,>(action: () => T): T | undefined => {
            if (!canWrite) {
                setNotice('У вас нет прав на редактирование этой таблицы');
                return undefined;
            }
            try {
                return action();
            } catch (err: any) {
                setNotice(err?.message || 'Операция не выполнена');
                return undefined;
            }
        },
        [canWrite],
    );

    const setCell = useCallback((row: number, col: number, raw: string) => guard(() => commit(engine.setRaw(row, col, raw))), [guard, commit, engine]);

    const setMatrix = useCallback(
        (row: number, col: number, matrix: string[][]) => guard(() => commit(engine.setMatrix(row, col, matrix))),
        [guard, commit, engine],
    );

    const clearRange = useCallback((rect: Rect) => guard(() => commit(engine.clearRange(rect))), [guard, commit, engine]);

    const structural = useCallback(
        (op: StructuralOp) =>
            guard(() => {
                const isRows = op.kind.endsWith('rows');
                const extent = engine.extent();
                if (op.kind.startsWith('insert') && (isRows ? extent.rows + op.count > MAX_ROWS : extent.cols + op.count > MAX_COLS)) {
                    throw new Error('Достигнут предел размера листа');
                }
                if (!engine.canApply(op)) throw new Error('Эту операцию выполнить нельзя');
                commit(engine.applyStructural(op));
            }),
        [guard, commit, engine],
    );

    const applyStyle = useCallback((target: StyleTarget, patch: StylePatch) => guard(() => commit(engine.applyStyle(target, patch))), [guard, commit, engine]);

    const setColumnWidth = useCallback(
        (col: number, width: number) => guard(() => commit({cells: [], styles: [], meta: engine.setColumnWidth(col, width)})),
        [guard, commit, engine],
    );

    const setFrozenCols = useCallback((count: number) => guard(() => commit({cells: [], styles: [], meta: engine.setFrozenCols(count)})), [guard, commit, engine]);

    const copyRange = useCallback((rect: Rect) => engine.copy(rect), [engine]);

    const paste = useCallback((row: number, col: number) => guard(() => commit(engine.paste(row, col))), [guard, commit, engine]);

    return {
        engine,
        version,
        loading,
        canWrite,
        saving,
        accessError,
        notice,
        clearNotice: () => setNotice(''),
        setCell,
        setMatrix,
        clearRange,
        structural,
        applyStyle,
        setColumnWidth,
        setFrozenCols,
        copyRange,
        paste,
    };
}
```

#### Создать `frontend/src/components/sheet/SheetGrid.tsx`

Обёртка над Glide Data Grid: колонки `A, B, C…`, номера строк, ширина колонок, стили ячеек через `themeOverride`, редактирование (`data` = формула, `displayData` = результат), вставка из буфера (`onPaste` возвращает `false`, вставку делаем сами), Ctrl+C запоминает диапазон в движке для вставки со сдвигом ссылок, `Delete` очищает выделение, контекстное меню. Сетка растёт сама при прокрутке к краю.

```tsx
import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {
    CompactSelection,
    DataEditor,
    GridCellKind,
    type DataEditorRef,
    type EditableGridCell,
    type GridCell,
    type GridColumn,
    type GridSelection,
    type Item,
    type Rectangle,
    type Theme,
} from '@glideapps/glide-data-grid';
import '@glideapps/glide-data-grid/dist/index.css';
import {colToLetters, DEFAULT_COLS, DEFAULT_ROWS, MAX_COLS, MAX_ROWS} from '../../sheet/address';
import type {SheetEngine} from '../../sheet/engine';
import type {CellStyle, Rect} from '../../sheet/types';
import {colors} from '../../styles/theme';

const ROW_HEIGHT = 24;
const GROW_ROWS = 500;
const GROW_COLS = 10;
const DEFAULT_COL_WIDTH = 100;

const baseTheme: Partial<Theme> = {
    accentColor: colors.link,
    accentLight: colors.linkBgSoft,
    textDark: colors.ink,
    bgCell: colors.canvas,
    bgHeader: colors.canvasSoft,
    borderColor: colors.hairline,
    fontFamily: "'Geist', Inter, system-ui, sans-serif",
    baseFontStyle: '13px',
    headerFontStyle: '600 12px',
};

function cellTheme(style: CellStyle | undefined, isError: boolean): Partial<Theme> | undefined {
    if (!style && !isError) return undefined;
    const theme: Partial<Theme> = {};
    if (style?.bg) theme.bgCell = style.bg;
    if (style?.fg) theme.textDark = style.fg;
    if (isError) theme.textDark = colors.errorDeep;
    if (style?.bold || style?.italic) {
        theme.baseFontStyle = `${style.italic ? 'italic ' : ''}${style.bold ? 'bold ' : ''}13px`;
    }
    return theme;
}

export interface ContextMenuState {
    x: number;
    y: number;
    row: number;
    col: number;
}

interface Props {
    engine: SheetEngine;
    /** Меняется при каждом изменении движка: заставляет сетку перерисоваться */
    version: number;
    canWrite: boolean;
    selection: GridSelection;
    onSelectionChange: (selection: GridSelection) => void;
    onEdit: (row: number, col: number, raw: string) => void;
    onPasteText: (row: number, col: number, matrix: string[][]) => void;
    onPasteInternal: (row: number, col: number) => void;
    onCopy: (rect: Rect) => void;
    onClear: (selection: GridSelection) => void;
    onColumnResize: (col: number, width: number) => void;
    onContextMenu: (menu: ContextMenuState) => void;
}

const tsv = (matrix: readonly (readonly string[])[]): string => matrix.map((line) => line.join('\t')).join('\n');

const SheetGrid: React.FC<Props> = ({
    engine, version, canWrite, selection, onSelectionChange, onEdit, onPasteText, onPasteInternal,
    onCopy, onClear, onColumnResize, onContextMenu,
}) => {
    const gridRef = useRef<DataEditorRef>(null);
    const lastCopyText = useRef<string | null>(null);

    // Сколько строк/колонок показываем: занятая область + запас; растёт при прокрутке к краю
    const [size, setSize] = useState({rows: DEFAULT_ROWS, cols: DEFAULT_COLS});
    useEffect(() => {
        const extent = engine.extent();
        setSize((prev) => ({
            rows: Math.min(MAX_ROWS, Math.max(prev.rows, extent.rows + 100)),
            cols: Math.min(MAX_COLS, Math.max(prev.cols, extent.cols + 5)),
        }));
    }, [engine, version]);

    // Ширину колонок меняем «вживую» локально и отправляем на сервер один раз — по окончании перетаскивания
    const [liveWidths, setLiveWidths] = useState<Record<number, number>>({});

    const columns = useMemo<GridColumn[]>(
        () =>
            Array.from({length: size.cols}, (_, col) => ({
                id: String(col),
                title: colToLetters(col),
                width: liveWidths[col] ?? engine.meta.col_widths?.[col] ?? DEFAULT_COL_WIDTH,
            })),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [size.cols, liveWidths, engine, version],
    );

    const getCellContent = useCallback(
        ([col, row]: Item): GridCell => {
            const view = engine.view(row, col);
            const align = view.style?.halign ?? (view.isNumber ? 'right' : 'left');
            return {
                kind: GridCellKind.Text,
                allowOverlay: canWrite,
                readonly: !canWrite,
                // data — то, что попадёт в редактор (формула), displayData — то, что видно в ячейке
                data: view.raw,
                displayData: view.text,
                copyData: view.text,
                contentAlign: align,
                allowWrapping: view.style?.wrap,
                themeOverride: cellTheme(view.style, view.isError),
            };
        },
        // version нужен, чтобы сетка перечитала ячейки после изменения движка
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [engine, canWrite, version],
    );

    const onCellEdited = useCallback(
        ([col, row]: Item, value: EditableGridCell) => {
            if (value.kind === GridCellKind.Text) onEdit(row, col, value.data);
        },
        [onEdit],
    );

    const onVisibleRegionChanged = useCallback((range: Rectangle) => {
        setSize((prev) => {
            const needRows = range.y + range.height > prev.rows - 30;
            const needCols = range.x + range.width > prev.cols - 3;
            if (!needRows && !needCols) return prev;
            return {
                rows: needRows ? Math.min(MAX_ROWS, prev.rows + GROW_ROWS) : prev.rows,
                cols: needCols ? Math.min(MAX_COLS, prev.cols + GROW_COLS) : prev.cols,
            };
        });
    }, []);

    const selectedRect = (): Rect | null => {
        const range = selection.current?.range;
        return range ? {x: range.x, y: range.y, width: range.width, height: range.height} : null;
    };

    return (
        <DataEditor
            ref={gridRef}
            columns={columns}
            rows={size.rows}
            getCellContent={getCellContent}
            onCellEdited={onCellEdited}
            gridSelection={selection}
            onGridSelectionChange={onSelectionChange}
            onVisibleRegionChanged={onVisibleRegionChanged}
            theme={baseTheme}
            rowHeight={ROW_HEIGHT}
            headerHeight={26}
            rowMarkers="number"
            freezeColumns={engine.meta.frozen_cols ?? 0}
            smoothScrollX
            smoothScrollY
            width="100%"
            height="100%"
            getCellsForSelection={true}
            // Ctrl+C: запоминаем диапазон в движке (hf.copy) и текст, который уйдёт в системный буфер
            onKeyDown={(event) => {
                if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'c') {
                    const rect = selectedRect();
                    if (!rect) return;
                    onCopy(rect);
                    const lines: string[][] = [];
                    for (let r = rect.y; r < rect.y + rect.height; r++) {
                        const line: string[] = [];
                        for (let c = rect.x; c < rect.x + rect.width; c++) line.push(engine.view(r, c).text);
                        lines.push(line);
                    }
                    lastCopyText.current = tsv(lines);
                }
            }}
            // Вставка: если в буфере то, что мы сами скопировали, вставляем через движок (сдвиг ссылок)
            onPaste={(target, values) => {
                const [col, row] = target;
                if (lastCopyText.current !== null && tsv(values) === lastCopyText.current && engine.hasClip()) {
                    onPasteInternal(row, col);
                } else {
                    onPasteText(row, col, values.map((line) => [...line]));
                }
                return false;
            }}
            onDelete={(sel) => {
                onClear(sel);
                return false;
            }}
            onColumnResize={(_column, newSize, index) => setLiveWidths((prev) => ({...prev, [index]: newSize}))}
            onColumnResizeEnd={(_column, newSize, index) => {
                setLiveWidths((prev) => {
                    const {[index]: _dropped, ...rest} = prev;
                    return rest;
                });
                onColumnResize(index, newSize);
            }}
            onCellContextMenu={([col, row], event) => {
                event.preventDefault();
                onContextMenu({x: event.bounds.x + event.localEventX, y: event.bounds.y + event.localEventY, row, col});
            }}
            onHeaderContextMenu={(col, event) => {
                event.preventDefault();
                onContextMenu({x: event.bounds.x + event.localEventX, y: event.bounds.y + event.localEventY, row: -1, col});
            }}
        />
    );
};

export const emptySelection = (): GridSelection => ({
    columns: CompactSelection.empty(),
    rows: CompactSelection.empty(),
});

export default SheetGrid;
```

#### Создать `frontend/src/components/sheet/FormulaBar.tsx`

Строка формул: адрес активной ячейки и её содержимое. `Enter` — сохранить, `Esc` — отменить.

```tsx
import React, {useEffect, useState} from 'react';
import type {GridSelection} from '@glideapps/glide-data-grid';
import {addressLabel} from '../../sheet/address';
import type {SheetEngine} from '../../sheet/engine';
import {colors, rounded, spacing, typography} from '../../styles/theme';

interface Props {
    engine: SheetEngine;
    version: number;
    selection: GridSelection;
    canWrite: boolean;
    onCommit: (row: number, col: number, raw: string) => void;
}

/** Строка формул: адрес активной ячейки и её содержимое (формула или значение). */
const FormulaBar: React.FC<Props> = ({engine, version, selection, canWrite, onCommit}) => {
    const active = selection.current?.cell;
    const [draft, setDraft] = useState('');
    const [focused, setFocused] = useState(false);

    const col = active?.[0];
    const row = active?.[1];

    useEffect(() => {
        if (focused) return;
        setDraft(row === undefined || col === undefined ? '' : engine.view(row, col).raw);
    }, [engine, version, row, col, focused]);

    const commit = () => {
        if (row === undefined || col === undefined) return;
        if (draft !== engine.view(row, col).raw) onCommit(row, col, draft);
    };

    return (
        <div style={styles.bar}>
            <div style={styles.address}>{row === undefined || col === undefined ? '' : addressLabel(row, col)}</div>
            <span style={styles.fx}>ƒx</span>
            <input
                style={styles.input}
                value={draft}
                disabled={!canWrite || row === undefined}
                placeholder="Введите значение или формулу, например =SUM(A1:A10)"
                onChange={(e) => setDraft(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        commit();
                        (e.target as HTMLInputElement).blur();
                    }
                    if (e.key === 'Escape') {
                        setDraft(row === undefined || col === undefined ? '' : engine.view(row, col).raw);
                        (e.target as HTMLInputElement).blur();
                    }
                }}
            />
        </div>
    );
};

const styles: Record<string, React.CSSProperties> = {
    bar: {
        display: 'flex', alignItems: 'center', gap: spacing.xs, padding: `${spacing.xxs}px ${spacing.xs}px`,
        background: colors.canvas, border: `1px solid ${colors.hairline}`, borderBottom: 'none',
    },
    address: {
        ...typography.code, width: 64, textAlign: 'center', color: colors.body,
        borderRight: `1px solid ${colors.hairline}`,
    },
    fx: {...typography.caption, color: colors.mute, fontStyle: 'italic'},
    input: {
        ...typography.code, flex: 1, border: `1px solid ${colors.hairline}`, borderRadius: rounded.xs,
        padding: `${spacing.xxs}px ${spacing.xs}px`, outline: 'none', color: colors.ink,
    },
};

export default FormulaBar;
```

#### Создать `frontend/src/components/sheet/Toolbar.tsx`

Панель оформления: жирный, курсив, выравнивание, перенос, цвет заливки и текста, формат чисел, знаки после запятой, сброс, закрепление колонок. Применяется к диапазону, к целым колонкам или к целым строкам — в зависимости от выделения.

```tsx
import React from 'react';
import type {SheetEngine, StyleTarget} from '../../sheet/engine';
import type {NumFmt, StylePatch} from '../../sheet/types';
import {colors, rounded, spacing, typography} from '../../styles/theme';

interface Props {
    engine: SheetEngine;
    version: number;
    canWrite: boolean;
    /** Активная ячейка (для показа текущего состояния кнопок) */
    active: {row: number; col: number} | null;
    target: StyleTarget | null;
    onStyle: (target: StyleTarget, patch: StylePatch) => void;
    onFreeze: (count: number) => void;
}

const NUM_FORMATS: {value: NumFmt; label: string}[] = [
    {value: 'general', label: 'Авто'},
    {value: 'number', label: '1,234.00'},
    {value: 'percent', label: 'Процент'},
    {value: 'currency', label: 'Валюта'},
    {value: 'date', label: 'Дата'},
    {value: 'datetime', label: 'Дата и время'},
];

const ALL_STYLE_KEYS: StylePatch = {
    bg: null, fg: null, bold: null, italic: null, halign: null, wrap: null, numFmt: null, decimals: null,
};

const Toolbar: React.FC<Props> = ({engine, version, canWrite, active, target, onStyle, onFreeze}) => {
    // version в зависимостях не нужен: компонент перерисовывается вместе со страницей
    void version;
    const current = active ? engine.effectiveStyle(active.row, active.col) : undefined;
    const disabled = !canWrite || !target;
    const apply = (patch: StylePatch) => target && onStyle(target, patch);

    const button = (label: string, title: string, on: boolean, patch: StylePatch, extra?: React.CSSProperties) => (
        <button
            key={title}
            title={title}
            disabled={disabled}
            style={{...styles.btn, ...(on ? styles.btnOn : {}), ...extra}}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => apply(patch)}
        >
            {label}
        </button>
    );

    return (
        <div style={styles.bar}>
            {button('B', 'Жирный', !!current?.bold, {bold: !current?.bold}, {fontWeight: 700})}
            {button('I', 'Курсив', !!current?.italic, {italic: !current?.italic}, {fontStyle: 'italic'})}
            <span style={styles.sep} />
            {button('⟸', 'По левому краю', current?.halign === 'left', {halign: 'left'})}
            {button('⇔', 'По центру', current?.halign === 'center', {halign: 'center'})}
            {button('⟹', 'По правому краю', current?.halign === 'right', {halign: 'right'})}
            {button('↵', 'Перенос текста', !!current?.wrap, {wrap: !current?.wrap})}
            <span style={styles.sep} />
            <label style={styles.color} title="Цвет заливки">
                Заливка
                <input type="color" disabled={disabled} value={current?.bg ?? '#ffffff'} onChange={(e) => apply({bg: e.target.value})} />
            </label>
            <label style={styles.color} title="Цвет текста">
                Текст
                <input type="color" disabled={disabled} value={current?.fg ?? '#171717'} onChange={(e) => apply({fg: e.target.value})} />
            </label>
            <span style={styles.sep} />
            <select
                style={styles.select}
                disabled={disabled}
                value={current?.numFmt ?? 'general'}
                onChange={(e) => apply({numFmt: e.target.value === 'general' ? null : (e.target.value as NumFmt)})}
            >
                {NUM_FORMATS.map((f) => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                ))}
            </select>
            {button('.0←', 'Меньше знаков после запятой', false, {decimals: Math.max(0, (current?.decimals ?? 2) - 1)})}
            {button('.00→', 'Больше знаков после запятой', false, {decimals: Math.min(10, (current?.decimals ?? 2) + 1)})}
            <span style={styles.sep} />
            {button('Сброс', 'Очистить оформление', false, ALL_STYLE_KEYS)}
            <select
                style={styles.select}
                disabled={!canWrite}
                value={engine.meta.frozen_cols ?? 0}
                onChange={(e) => onFreeze(Number(e.target.value))}
                title="Закрепить колонки"
            >
                {[0, 1, 2, 3].map((n) => (
                    <option key={n} value={n}>{n === 0 ? 'Не закреплять' : `Закрепить колонок: ${n}`}</option>
                ))}
            </select>
        </div>
    );
};

const styles: Record<string, React.CSSProperties> = {
    bar: {
        display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: spacing.xxs,
        padding: `${spacing.xxs}px ${spacing.xs}px`, background: colors.canvasSoft,
        border: `1px solid ${colors.hairline}`, borderBottom: 'none',
    },
    btn: {
        ...typography.bodySmStrong, minWidth: 28, height: 28, padding: `0 ${spacing.xs}px`, cursor: 'pointer',
        background: colors.canvas, color: colors.ink, border: `1px solid ${colors.hairline}`, borderRadius: rounded.xs,
    },
    btnOn: {background: colors.linkBgSoft, borderColor: colors.link},
    sep: {width: 1, height: 20, background: colors.hairline, margin: `0 ${spacing.xxs}px`},
    color: {...typography.caption, display: 'flex', alignItems: 'center', gap: 4, color: colors.body},
    select: {...typography.caption, height: 28, borderRadius: rounded.xs, border: `1px solid ${colors.hairline}`, background: colors.canvas},
};

export default Toolbar;
```

#### Создать `frontend/src/components/sheet/SheetContextMenu.tsx`

Контекстное меню: вставить/удалить строки и колонки (по числу выделенных), очистить. Меню строк доступно только по клику на ячейку; по заголовку колонки — только операции с колонками.

```tsx
import React, {useEffect} from 'react';
import type {StructuralOp} from '../../sheet/types';
import {colors, rounded, shadowLevel5, spacing, typography} from '../../styles/theme';
import type {ContextMenuState} from './SheetGrid';

interface Props {
    menu: ContextMenuState;
    /** Сколько строк / колонок выделено вокруг ячейки, по которой кликнули */
    rowSpan: {index: number; count: number};
    colSpan: {index: number; count: number};
    onStructural: (op: StructuralOp) => void;
    onClear: () => void;
    onClose: () => void;
}

const SheetContextMenu: React.FC<Props> = ({menu, rowSpan, colSpan, onStructural, onClear, onClose}) => {
    useEffect(() => {
        const close = () => onClose();
        window.addEventListener('click', close);
        window.addEventListener('scroll', close, true);
        return () => {
            window.removeEventListener('click', close);
            window.removeEventListener('scroll', close, true);
        };
    }, [onClose]);

    const onRow = menu.row >= 0;
    const rows = rowSpan.count;
    const cols = colSpan.count;
    const items: {label: string; action: () => void}[] = [
        ...(onRow
            ? [
                  {label: `Вставить ${rows} стр. выше`, action: () => onStructural({kind: 'insert_rows', index: rowSpan.index, count: rows})},
                  {label: `Вставить ${rows} стр. ниже`, action: () => onStructural({kind: 'insert_rows', index: rowSpan.index + rows, count: rows})},
                  {label: `Удалить строки (${rows})`, action: () => onStructural({kind: 'delete_rows', index: rowSpan.index, count: rows})},
              ]
            : []),
        {label: `Вставить ${cols} кол. слева`, action: () => onStructural({kind: 'insert_cols', index: colSpan.index, count: cols})},
        {label: `Вставить ${cols} кол. справа`, action: () => onStructural({kind: 'insert_cols', index: colSpan.index + cols, count: cols})},
        {label: `Удалить колонки (${cols})`, action: () => onStructural({kind: 'delete_cols', index: colSpan.index, count: cols})},
        {label: 'Очистить содержимое', action: onClear},
    ];

    return (
        <div style={{...styles.menu, left: menu.x, top: menu.y}} onContextMenu={(e) => e.preventDefault()}>
            {items.map((item) => (
                <button key={item.label} style={styles.item} onClick={item.action}>{item.label}</button>
            ))}
        </div>
    );
};

const styles: Record<string, React.CSSProperties> = {
    menu: {
        position: 'fixed', zIndex: 1000, minWidth: 220, display: 'flex', flexDirection: 'column',
        background: colors.canvas, borderRadius: rounded.sm, boxShadow: shadowLevel5, padding: spacing.xxs,
    },
    item: {
        ...typography.bodySm, textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer',
        padding: `${spacing.xxs}px ${spacing.xs}px`, borderRadius: rounded.xs, color: colors.ink,
    },
};

export default SheetContextMenu;
```

### 7.5. Страница и остальные правки

#### Заменить файл целиком: `frontend/src/pages/TableViewPage.tsx`

Старая страница (770 строк: пагинация, фильтры, `<table>`, `commitEdit`, `evaluateFormula`) заменяется компактной. Из прежней страницы сохранены: боковая панель, `TablePermissionsPanel`, экспорт в Excel, оформление шапки. Исчезли: пагинация, серверные сортировка и фильтры, массовое удаление строк, кнопки «Добавить строку» и «Копировать строку» — их заменяет вставка/удаление строк в контекстном меню.

Было 771 строк. Новое содержимое:

```tsx
// frontend/src/pages/TableViewPage.tsx
import React, {useState} from "react";
import {useParams, useNavigate} from "react-router-dom";
import type {CompactSelection, GridSelection} from "@glideapps/glide-data-grid";
import TablePermissionsPanel from '../components/TablePermissionsPanel';
import SidebarWithToggle from '../components/SidebarWithToggle';
import SheetGrid, {emptySelection, type ContextMenuState} from '../components/sheet/SheetGrid';
import FormulaBar from '../components/sheet/FormulaBar';
import Toolbar from '../components/sheet/Toolbar';
import SheetContextMenu from '../components/sheet/SheetContextMenu';
import {tablesAPI} from "../api/tables";
import {useSheet} from '../hooks/useSheet';
import {MAX_COLS, MAX_ROWS} from '../sheet/address';
import type {StyleTarget} from '../sheet/engine';
import type {Rect} from '../sheet/types';
import {colors, rounded, shadowLevel3, spacing, typography} from '../styles/theme';

/** Выделение, в которое попал кликнутый индекс -> {index, count}; иначе одна строка/колонка. */
function spanOf(clicked: number, picked: CompactSelection, start?: number, length?: number) {
    if (picked.hasIndex(clicked)) {
        const all = picked.toArray();
        return {index: Math.min(...all), count: all.length};
    }
    if (start !== undefined && length !== undefined && clicked >= start && clicked < start + length) {
        return {index: start, count: length};
    }
    return {index: clicked, count: 1};
}

const TableViewPage: React.FC = () => {
    const {id} = useParams();
    const navigate = useNavigate();
    const tableId = Number(id);

    const sheet = useSheet(tableId);
    const {engine, version, canWrite} = sheet;

    const [selection, setSelection] = useState<GridSelection>(emptySelection());
    const [menu, setMenu] = useState<ContextMenuState | null>(null);
    const [exporting, setExporting] = useState(false);
    const [error, setError] = useState("");

    const range = selection.current?.range;
    const active = selection.current ? {row: selection.current.cell[1], col: selection.current.cell[0]} : null;

    // К чему применять оформление: целые колонки / целые строки / прямоугольник
    const styleTarget = (): StyleTarget | null => {
        if (selection.columns.length > 0) return {kind: 'cols', cols: selection.columns.toArray()};
        if (selection.rows.length > 0) return {kind: 'rows', rows: selection.rows.toArray()};
        if (range) return {kind: 'range', rect: {x: range.x, y: range.y, width: range.width, height: range.height}};
        return null;
    };

    const clearSelection = (sel: GridSelection) => {
        const rects: Rect[] = [];
        if (sel.current) {
            const r = sel.current.range;
            rects.push({x: r.x, y: r.y, width: r.width, height: r.height});
        }
        sel.columns.toArray().forEach((col) => rects.push({x: col, y: 0, width: 1, height: MAX_ROWS}));
        sel.rows.toArray().forEach((row) => rects.push({x: 0, y: row, width: MAX_COLS, height: 1}));
        rects.forEach((rect) => sheet.clearRange(rect));
    };

    const handleExport = async () => {
        try {
            setExporting(true);
            const {job_id} = await tablesAPI.startExport(tableId);
            const result = await tablesAPI.waitForExport(job_id);

            if (result.status === 'error' || !result.download_url) {
                setError(result.error || 'Не удалось экспортировать таблицу');
                return;
            }

            // presigned-ссылка уже содержит content-disposition с именем файла
            const link = document.createElement('a');
            link.href = result.download_url;
            link.click();
        } catch (err: any) {
            console.error('export error:', err);
            setError(err.response?.data?.detail || 'Не удалось экспортировать таблицу')
        } finally {
            setExporting(false);
        }
    };

    if (sheet.loading) {
        return (
            <div style={styles.loadingContainer}>
                <div style={styles.spinner}></div>
                <p>Загрузка данных...</p>
            </div>
        );
    }

    if (sheet.accessError) {
        return (
            <div style={styles.container}>
                <SidebarWithToggle/>
                <main style={styles.main}>
                    <div style={styles.error}>{sheet.accessError.message}</div>
                    <button style={styles.backButton} onClick={() => navigate("/tables")}>← Назад</button>
                </main>
            </div>
        );
    }

    return (
        <div style={styles.container}>
            <SidebarWithToggle/>

            <header style={styles.header}>
                <div style={styles.headerContent}>
                    <h1 style={styles.title}>Таблица №{id}</h1>
                    <div style={styles.headerActions}>
                        <span style={styles.status}>
                            {!canWrite ? 'Только чтение' : sheet.saving ? 'Сохранение…' : 'Все изменения сохранены'}
                        </span>
                        <button style={styles.exportButton} onClick={handleExport} disabled={exporting}>
                            {exporting ? "Экспорт…" : "⬇ Экспорт в Excel"}
                        </button>
                        <button style={styles.backButton} onClick={() => navigate("/tables")}>
                            ← Назад
                        </button>
                    </div>
                </div>
            </header>

            <main style={styles.main}>
                <div style={styles.contentLayout}>
                    <div style={styles.tableColumn}>
                        {(error || sheet.notice) && (
                            <div style={styles.error}>
                                {error || sheet.notice}
                                <button style={styles.closeError} onClick={() => { setError(""); sheet.clearNotice(); }}>×</button>
                            </div>
                        )}

                        <Toolbar
                            engine={engine}
                            version={version}
                            canWrite={canWrite}
                            active={active}
                            target={styleTarget()}
                            onStyle={sheet.applyStyle}
                            onFreeze={sheet.setFrozenCols}
                        />
                        <FormulaBar
                            engine={engine}
                            version={version}
                            selection={selection}
                            canWrite={canWrite}
                            onCommit={sheet.setCell}
                        />
                        <div style={styles.gridWrapper}>
                            <SheetGrid
                                engine={engine}
                                version={version}
                                canWrite={canWrite}
                                selection={selection}
                                onSelectionChange={setSelection}
                                onEdit={sheet.setCell}
                                onPasteText={sheet.setMatrix}
                                onPasteInternal={sheet.paste}
                                onCopy={sheet.copyRange}
                                onClear={clearSelection}
                                onColumnResize={sheet.setColumnWidth}
                                onContextMenu={setMenu}
                            />
                        </div>
                    </div>
                    <aside style={styles.sidePanel}>
                        <TablePermissionsPanel tableId={tableId}/>
                    </aside>
                </div>
            </main>

            {menu && canWrite && (
                <SheetContextMenu
                    menu={menu}
                    rowSpan={spanOf(menu.row, selection.rows, range?.y, range?.height)}
                    colSpan={spanOf(menu.col, selection.columns, range?.x, range?.width)}
                    onStructural={sheet.structural}
                    onClear={() => {
                        const r = spanOf(menu.row, selection.rows, range?.y, range?.height);
                        const c = spanOf(menu.col, selection.columns, range?.x, range?.width);
                        sheet.clearRange(menu.row >= 0
                            ? {x: c.index, y: r.index, width: c.count, height: r.count}
                            : {x: c.index, y: 0, width: c.count, height: MAX_ROWS});
                    }}
                    onClose={() => setMenu(null)}
                />
            )}
        </div>
    );
};

export default TableViewPage;

// ── Стили ──

const styles: Record<string, React.CSSProperties> = {
    container: {minHeight: "100vh", background: colors.canvasSoft},
    header: {
        background: colors.canvas,
        borderBottom: `1px solid ${colors.hairline}`,
        padding: `${spacing.md}px 0`,
    },
    headerContent: {
        maxWidth: "1600px",
        margin: "0 auto",
        padding: `0 ${spacing.lg}px`,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
    },
    headerActions: {display: "flex", gap: spacing.sm, alignItems: "center"},
    title: {...typography.displayMd, color: colors.ink, margin: 0},
    status: {...typography.caption, color: colors.mute},
    backButton: {
        ...typography.bodySmStrong,
        background: "transparent",
        color: colors.body,
        border: "none",
        padding: `0 ${spacing.xs}px`,
        height: 32,
        cursor: "pointer",
    },
    exportButton: {
        ...typography.buttonMd,
        background: colors.canvas,
        color: colors.ink,
        border: `1px solid ${colors.hairline}`,
        padding: `0 ${spacing.md}px`,
        height: 32,
        borderRadius: rounded.sm,
        cursor: "pointer",
    },
    main: {maxWidth: "1600px", margin: "0 auto", padding: `${spacing.lg}px ${spacing.lg}px`},
    contentLayout: {display: "flex", gap: spacing.lg, alignItems: "flex-start"},
    tableColumn: {flex: 1, minWidth: 0},
    sidePanel: {width: 320, flexShrink: 0},
    // У Glide Data Grid должен быть задан размер контейнера
    gridWrapper: {
        height: "calc(100vh - 260px)", minHeight: 400,
        background: colors.canvas, border: `1px solid ${colors.hairline}`, boxShadow: shadowLevel3,
    },
    loadingContainer: {
        minHeight: "50vh", display: "flex", flexDirection: "column",
        gap: spacing.md, justifyContent: "center", alignItems: "center", color: colors.body,
    },
    spinner: {
        width: 40, height: 40,
        border: `4px solid ${colors.hairline}`, borderTop: `4px solid ${colors.primary}`,
        borderRadius: rounded.full, animation: "spin 1s linear infinite",
    },
    error: {
        ...typography.bodySm,
        background: colors.errorSoft, color: colors.errorDeep, border: `1px solid ${colors.errorSoft}`,
        padding: spacing.md, borderRadius: rounded.sm, marginBottom: spacing.md,
        display: "flex", justifyContent: "space-between", alignItems: "center",
    },
    closeError: {background: "none", border: "none", cursor: "pointer", fontSize: 18, color: colors.errorDeep},
};
```

#### Изменить `frontend/src/pages/TrashPage.tsx`

Колонок у таблицы больше нет — убираем счётчик «Столбцов».


**Правка 1 из 1.** **Удалить строки 100–103**:

```tsx
                                    <div style={styles.metaItem}>
                                        <span style={styles.metaLabel}>Столбцов:</span>
                                        <span>{table.columns_schema?.length || 0}</span>
                                    </div>
```

#### Изменить `frontend/src/pages/TablePage.tsx`

(1) При создании таблицы больше не передаём `columns_schema`. (2) Убираем счётчик «Столбцов». (3) Импорт — только `.xlsx`: бэкенд на openpyxl не читает `.xls`, а `.csv` не принимал и раньше.


**Правка 1 из 6.** **Заменить строку 576**.

Было:

```tsx
                                                    <span style={styles.fileHint}>Поддерживаемые форматы: .xlsx, .xls, .csv</span>
```

Стало:

```tsx
                                                    <span style={styles.fileHint}>Поддерживаемый формат: .xlsx</span>
```

**Правка 2 из 6.** **Заменить строку 560**.

Было:

```tsx
                                            accept=".xlsx,.xls,.csv"
```

Стало:

```tsx
                                            accept=".xlsx"
```

**Правка 3 из 6.** **Удалить строки 473–476**:

```tsx
                                    <div style={styles.metaItem}>
                                        <span style={styles.metaLabel}>Столбцов:</span>
                                        <span>{table.columns_schema?.length || 0}</span>
                                    </div>
```

**Правка 4 из 6.** **Заменить строку 172**.

Было:

```tsx
                setError('Пожалуйста, выберите файл Excel (.xlsx, .xls) или CSV');
```

Стало:

```tsx
                setError('Пожалуйста, выберите файл Excel (.xlsx)');
```

**Правка 5 из 6.** **Заменить строку 168**.

Было:

```tsx
            const validExtensions = ['.xlsx', '.xls', '.csv'];
```

Стало:

```tsx
            const validExtensions = ['.xlsx'];
```

**Правка 6 из 6.** **Удалить строки 110–114**:

```tsx
                columns_schema: [
                    {name: 'A', type: 'string'},
                    {name: 'B', type: 'number'},
                    {name: 'C', type: 'string'}
                ]
```

### 7.6. Проверка фронтенда

```bash
cd frontend
npx tsc --noEmit        # ошибки "Property 'env' does not exist on type 'ImportMeta'" были и до изменений
npm run build
```

Проверочный скрипт движка (приложение B) без браузера:

```bash
npx esbuild scripts/engine-check.ts --bundle --platform=node --format=esm --outfile=/tmp/engine-check.mjs
node /tmp/engine-check.mjs         # в конце: ALL OK
```

---

## 13. Этап 8. Ручная проверка в браузере

Поднимите стек (`docker compose up --build`) или запустите `table_service` и `npm run dev` локально.
Откройте таблицу (маршрут прежний: `/data/{id}/rows`).

| № | Что сделать | Что должно быть |
|---|---|---|
| 1 | Нажать на ячейку `A1`, ввести `10`, `Enter`; в `A2` — `20`; в `A3` — `=SUM(A1:A2)` | В `A3` — `30`, число справа; в строке формул при выборе `A3` — формула |
| 2 | Изменить `A1` на `100` | `A3` сразу `120`; в БД: `select row, col, raw, value from sheet_cells where table_id = N order by row, col` — у `A3` новое `value` |
| 3 | В `B1` ввести `=A1/0` | Красная `#DIV/0!`; в БД `value = {"e": "#DIV/0!"}` |
| 4 | Выделить `A1`, нажать **B**, выбрать заливку; обновить страницу | Оформление сохранилось |
| 5 | Выделить колонку `A` кликом по заголовку, задать заливку | Закрашена вся колонка, в БД новых строк почти нет (стиль — в `sheet_meta.col_styles`) |
| 6 | ПКМ по ячейке `A2` → «Вставить 1 стр. выше» | Данные съехали вниз, `=SUM(A1:A2)` стала `=SUM(A1:A3)` |
| 7 | Скопировать (`Ctrl+C`) ячейку с `=A1*2`, вставить (`Ctrl+V`) вправо | В новой ячейке `=B1*2` |
| 8 | Скопировать блок ячеек в Excel/Google Таблицах и вставить в лист (`Ctrl+V`) | Встали значения (во внешний буфер программы кладут значения, а не формулы) и не переносится оформление; формулы вида `=A1+C1` в вставляемом тексте остаются формулами |
| 9 | Ввести `05.01.2024` | Ячейка получила формат «дата»; `=A1+1` даёт `06.01.2024` |
| 10 | Ввести `=SEQUENCE(3,1)` | Три ячейки вниз; очистить источник — очистятся все три |
| 11 | Два браузера на одной таблице: править в первом | Во втором изменения появляются сразу; вставка строки в первом сдвигает данные и ссылки во втором |
| 12 | Во втором браузере править, пока в первом вставлена строка (быстро, до обновления) | Сообщение «Структуру листа изменил другой пользователь…», лист обновился |
| 13 | Отключить сеть на минуту и включить | После восстановления WebSocket лист перечитан |
| 14 | «Экспорт в Excel», открыть в Excel/LibreOffice | Формулы живые, заливка и жирный на месте |
| 15 | Импорт `.xlsx` с формулами (создание таблицы из файла) | Формулы сохранились, значения посчитаны; в `sheet_cells` у формул заполнено `value` (самолечение при первой загрузке) |
| 16 | Зайти пользователем с правом «Чтение» | Надпись «Только чтение», ячейки не редактируются, панель инструментов выключена |
| 17 | Вставить блок на 20 000+ ячеек | Сохраняется несколькими запросами по 5 000, интерфейс не зависает |

---

## 14. Этап 9. Тесты и чистка

### 9.1. Что сломается в существующих тестах

Я их не менял — только нашёл, что зависит от удалённого кода:

| Файл | Что делать |
|---|---|
| `tests/unit/table_service/test_services/test_data.py` (93 упоминания) | удалить: тестирует `DataService` |
| `tests/integration/table_service/test_api/test_data_endpoints.py` (29) | удалить; вместо него писать тесты на `/data/{id}/sheet` и `/sheet/batch` |
| `tests/unit/table_service/conftest.py`, строки 103–109 | убрать `columns_schema=[...]` из `DataTable(...)` в фикстуре `real_data_table`: у модели нет такого поля, конструктор бросит `TypeError` |
| `tests/unit/table_service/test_services/test_table.py` (14) | убрать `columns_schema=[]` из `DataTableCreate(...)` (строки 116, 139, 153 — лишнее поле игнорируется, но тест `test_generates_correct_columns_schema` (строка ~198) и тесты про DataFrame (строки ~260–290, 464–510) надо переписать или удалить: нет `build_columns_schema`/`build_rows` |
| `tests/fixtures/excel_factories.py` | остаётся рабочим (pandas ещё нужен тестам), но фабрики можно переписать на `openpyxl.Workbook` |
| `tests/unit/table_service/test_services/test_excel_processor.py` | сейчас пустой — положить сюда тесты из приложения C |
| `tests/integration/table_service/test_api/test_tables_endpoints.py`, строка 29 | поле `columns_schema` в payload можно убрать (сервер его игнорирует) |
| `online_api_collection/Create Table.yml` (стр. 16), `Get table.yml` (стр. 8) | коллекция Bruno: убрать `columns_schema`, заменить запрос строк на `GET /data/1/sheet` |

Запуск: `pytest tests/unit/table_service -q`.

### 9.2. Чистка

- `table_service/requirements.txt`: `pandas==2.3.3` можно удалить после правки тестов и фикстур.
- Положите проверочные скрипты из приложений A и B в `table_service/scripts/` и `frontend/scripts/` (или не
  кладите — они нужны только для проверки).
- Обновите `README.md`/`CLAUDE.md`: формулы теперь считает клиент (HyperFormula), строк больше нет, есть ячейки.

---

## 15. Что дальше (чего в этой версии нет)

Каждый пункт можно добавить отдельно; точки расширения уже заложены.

| Возможность | Как добавить |
|---|---|
| **Undo / Redo** | У HyperFormula есть `hf.undo()` / `hf.redo()`. После вызова пройти `diffKeys` по всем ключам зеркала и отправить результат. Оформление HyperFormula не откатывает — нужен отдельный стек стилей. |
| **Маркер заполнения** (протянуть ячейку вниз) | Включить `fillHandle` и обработать `onFillPattern` в Glide; содержимое со сдвигом ссылок даёт `hf.getFillRangeData(source, target)`. |
| **Несколько листов** | Таблица `sheets (id, table_id, name, position)`, `sheet_id` в первичный ключ `sheet_cells`, `sheet_id` в пакеты; в движке — `hf.addSheet`. Ссылки `Лист2!A1` заработают сами. |
| **Сортировка диапазона** | Клиент сортирует диапазон в памяти и отправляет обычный пакет ячеек. HyperFormula сортировку не умеет, но `=SORT()` есть. |
| **Фильтры** | Скрытие строк на клиенте: список скрытых строк в `sheet_meta`, `rowHeight` = 0 для скрытых. |
| **Границы, объединение ячеек, подчёркивание, зачёркивание, условное форматирование** | Свойства в `SCellStyle` / `sheet_meta.merges`, отрисовка — через `drawCell` в Glide. Условное форматирование — правила в `sheet_meta`, вычисляются на клиенте. |
| **Курсоры и выделения коллег** | Клиент → сервер по WebSocket (сейчас канал односторонний: сервер молча читает и игнорирует). |
| **Доверие значениям клиента** | Вынести пересчёт на сервер: маленький Node-сервис с той же HyperFormula (`buildFromSheets` из `sheet_cells`, пересчёт пакета, сверка `value`). Нужен и для изменений не из браузера (например, REST-клиентов). |
| **Очень большие листы** | Движок в Web Worker; снимок потоком/чанками; серверная пагинация по диапазонам строк. Сейчас практический потолок — десятки тысяч занятых ячеек. |
| **Русские имена функций** | `HyperFormula.registerLanguage('ruRU', ruRU)` + `language: 'ruRU'`, `functionArgSeparator: ';'`. Я проверил: в 3.5.0 парсер не разобрал `=СУММ(1;2)` — нужно разбираться отдельно или обратиться к автору библиотеки. |
| **Именованные диапазоны** | В HyperFormula есть named expressions; хранить в `sheet_meta`. |

---

## 16. Вопросы к вам

Я принял решения по умолчанию, чтобы не блокировать работу. Если какой-то ответ другой — скажите, перепишу
соответствующие этапы.

1. **Несколько листов (вкладок) в одной таблице** нужны? Сейчас: один лист на таблицу.
2. **Undo/Redo** нужен в первой версии? Сейчас: нет (есть путь добавления).
3. **Старые данные** (строки в `table_rows`) переносить в ячейки? Сейчас: нет, удаляются миграцией.
4. **Кому доверять значения формул**: клиенту (как сейчас, проще) или считать на сервере Node-воркером (надёжнее, ещё один сервис)?
5. **Русская локаль**: нужны ли русские имена функций и десятичная запятая? Сейчас: английские имена, точка.

---

## 17. Приложения: проверочные скрипты

Это те же скрипты, которыми я проверял код; их удобно прогонять после каждого этапа.

### Приложение A. Смоук-проверка бэкенда на PostgreSQL

Файл `table_service/scripts/sheet_smoke.py`. Запуск — в этапе 6.


```python
"""Смоук-проверка листа на настоящем PostgreSQL (без HTTP, Redis и прочего стека).

Запуск (из корня репозитория), БД — одноразовый контейнер:

    docker run -d --rm --name sheet_pg -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=t -p 54329:5432 postgres:16-alpine
    export EXCEL_APP__DB_HOST=localhost EXCEL_APP__DB_PORT=54329 EXCEL_APP__DB_USER=postgres \
           EXCEL_APP__DB_PASSWORD=pw EXCEL_APP__DB_NAME=t
    alembic -c table_service/alembic.ini upgrade head
    python -m table_service.scripts.sheet_smoke
    docker stop sheet_pg
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from table_service.app.core import AsyncSessionFactory
from table_service.app.core.unit_of_work import UnitOfWork
from table_service.app.exceptions import LayoutConflictException
from table_service.app.schemas import (
    SCellStyle,
    SCellWrite,
    SSheetBatch,
    SStructuralOp,
    SStyleWrite,
)
from table_service.app.services import PermissionService, SheetService


def cells_of(snapshot) -> dict[tuple[int, int], tuple]:
    return {(r, c): (raw, value, style) for r, c, raw, value, style in snapshot.cells}


async def main() -> None:
    uow = UnitOfWork(AsyncSessionFactory)
    publisher = MagicMock()
    publisher.publish = AsyncMock()
    service = SheetService(PermissionService(redis=MagicMock()), publisher)

    async with uow.start():
        table = await uow.tables.create_table(
            {"name": "smoke", "description": None, "is_public": False}, user_id=1
        )
    table_id = table.id

    async def batch(layout: int, **kwargs):
        payload = SSheetBatch(client_id="smoke", base_layout_revision=layout, **kwargs)
        return await service.apply_batch(uow, table_id, 1, "USER", payload)

    async def snapshot():
        return await service.get_snapshot(uow, table_id, 1, "USER")

    # 1. запись ячеек и оформления
    await batch(
        0,
        cells=[
            SCellWrite(row=0, col=0, raw="5", value=5),
            SCellWrite(row=1, col=0, raw="7", value=7),
            SCellWrite(row=2, col=0, raw="=SUM(A1:A2)", value=12),
        ],
        styles=[
            SStyleWrite(row=0, col=0, style=SCellStyle(bg="#ffeb3b", bold=True)),
            SStyleWrite(row=5, col=5, style=SCellStyle(fg="#ff0000")),
        ],
    )
    cells = cells_of(await snapshot())
    assert cells[(0, 0)] == ("5", 5, {"bg": "#ffeb3b", "bold": True})
    assert cells[(5, 5)] == (None, None, {"fg": "#ff0000"})

    # 2. вставка двух строк: ячейки и стили сдвигаются, присланная формула записана
    await batch(
        0,
        structural=SStructuralOp(kind="insert_rows", index=1, count=2),
        cells=[SCellWrite(row=4, col=0, raw="=SUM(A1:A4)", value=12)],
    )
    cells = cells_of(await snapshot())
    assert cells[(3, 0)][0] == "7" and cells[(4, 0)][0] == "=SUM(A1:A4)"
    assert (7, 5) in cells and (5, 5) not in cells

    # 3. устаревший layout_revision -> 409
    try:
        await batch(0, cells=[SCellWrite(row=0, col=0, raw="1", value=1)])
        raise AssertionError("ожидали LayoutConflictException")
    except LayoutConflictException:
        pass

    # 4. удаление строк и вставка/удаление колонок
    await batch(1, structural=SStructuralOp(kind="delete_rows", index=1, count=2))
    assert (1, 0) in cells_of(await snapshot())
    await batch(2, structural=SStructuralOp(kind="insert_cols", index=0, count=1))
    assert (1, 1) in cells_of(await snapshot())
    await batch(3, structural=SStructuralOp(kind="delete_cols", index=1, count=1))
    cells = cells_of(await snapshot())
    assert (5, 5) in cells and (0, 0) not in cells

    # 5. пустая ячейка без оформления удаляется из БД, с оформлением — остаётся
    await batch(4, cells=[SCellWrite(row=5, col=5)])
    assert (5, 5) in cells_of(await snapshot())

    # 6. большой пакет + meta, сдвиг 20 000 ячеек, дубли в одном пакете
    big = [
        SCellWrite(row=i, col=j, raw=str(i * j), value=i * j)
        for i in range(1000)
        for j in range(20)
    ]
    await batch(4, cells=big, meta={"col_widths": {"0": 200}})
    snap = await snapshot()
    assert len(snap.cells) == 20_000 and snap.meta == {"col_widths": {"0": 200}}
    await batch(4, structural=SStructuralOp(kind="insert_rows", index=10, count=5))
    await batch(
        5,
        cells=[
            SCellWrite(row=0, col=0, raw="a", value="a"),
            SCellWrite(row=0, col=0, raw="b", value="b"),
        ],
    )
    assert cells_of(await snapshot())[(0, 0)][0] == "b"

    # 7. события: маленькие пакеты уходят как batch, большой — как reload
    kinds = [call.args[0].kind for call in publisher.publish.call_args_list]
    assert kinds[0] == "batch" and "reload" in kinds
    print("SMOKE OK", kinds)


asyncio.run(main())
```

### Приложение B. Проверка движка без браузера

Файл `frontend/scripts/engine-check.ts`. Запуск — в разделе 7.6.


```ts
import {SheetEngine} from '../src/sheet/engine';
import assert from 'node:assert/strict';

const e = new SheetEngine();
const snap = (cells: any[], meta = {}) => ({table_id:1,revision:0,layout_revision:0,can_write:true,meta,cells});
// 1. load + reconcile (value=null у формулы -> починка)
let fix = e.load(snap([[0,0,'5',5,null],[1,0,'7',7,null],[2,0,'=SUM(A1:A2)',null,{bg:'#ffffff'}],[0,2,null,null,{bold:true}]]));
console.log('reconcile', JSON.stringify(fix)); assert.equal(fix.length,1); assert.equal(fix[0].value,12);
assert.deepEqual(e.extent(), {rows:3, cols:3});
// 2. setRaw: зависимые ячейки попадают в diff
let r = e.setRaw(0,0,'10'); console.log('setRaw', JSON.stringify(r)); assert.equal(r.cells.length,2);
// 3. ошибка
r = e.setRaw(0,1,'=A1/0'); console.log(JSON.stringify(r.cells)); assert.deepEqual(r.cells[0].value,{e:'#DIV/0!'});
// 4. дата -> автоформат
r = e.setRaw(5,0,'05.01.2024'); console.log('date', JSON.stringify(r)); assert.equal(r.styles[0].style?.numFmt,'date');
assert.equal(e.view(5,0).text,'05.01.2024');
// 5. структурная: вставка 2 строк перед строкой 1 -> SUM(A1:A4) + сдвиг зеркала
r = e.applyStructural({kind:'insert_rows', index:1, count:2}); console.log('insert', JSON.stringify(r.cells), JSON.stringify(r.meta));
assert.equal(r.cells.length,1); assert.equal(r.cells[0].row,4); assert.equal(r.cells[0].raw,'=SUM(A1:A4)');
assert.equal(e.view(4,0).raw,'=SUM(A1:A4)'); assert.equal(e.view(3,0).raw,'7');
// стиль ячейки (0,2) остался, (2,0)->(4,0)
assert.ok(e.styles.has(0*1024+2)); assert.ok(e.styles.has(4*1024+0));
// 6. удаление строки с данными -> #REF! в формуле, diff только изменённые
r = e.applyStructural({kind:'delete_rows', index:3, count:1}); console.log('delete', JSON.stringify(r.cells));
// 7. удаление колонки
r = e.applyStructural({kind:'delete_cols', index:1, count:1}); console.log('delcol', JSON.stringify(r.cells));
// 8. copy/paste со сдвигом ссылок
e.setRaw(10,0,'1'); e.setRaw(10,1,'=A11*2');
e.copy({x:0,y:10,width:2,height:1});
r = e.paste(12,3); console.log('paste', JSON.stringify(r.cells)); assert.equal(r.cells.find(c=>c.col===4)!.raw,'=D13*2');
// 9. spill: массив
r = e.setRaw(20,0,'=SEQUENCE(3,1)'); console.log('spill', JSON.stringify(r.cells));
assert.equal(r.cells.length,3); assert.equal(r.cells[1].raw,null);
// очистка источника убирает «разлитые»
r = e.clearRange({x:0,y:20,width:1,height:1}); console.log('clear spill', JSON.stringify(r.cells)); assert.equal(r.cells.length,3);
// 10. стили: целая колонка
r = e.applyStyle({kind:'cols', cols:[0]}, {bg:'#ff0000'}); console.log('colstyle', JSON.stringify(r)); assert.equal(e.effectiveStyle(50,0)?.bg,'#ff0000');
r = e.applyStyle({kind:'range', rect:{x:0,y:0,width:2,height:2}}, {bold:true}); assert.equal(e.effectiveStyle(0,0)?.bold,true);
// 11. remote
const e2 = new SheetEngine(); e2.load(snap([]));
e2.applyRemote({kind:'batch',table_id:1,revision:1,layout_revision:0,actor_id:2,client_id:'x',structural:null,
  cells:[{row:0,col:0,raw:'3',value:3},{row:0,col:1,raw:'=A1*2',value:6}],styles:[{row:0,col:0,style:{bold:true}}],meta:{frozen_cols:1},occurred_at:''});
assert.equal(e2.view(0,1).text,'6'); assert.equal(e2.meta.frozen_cols,1);
e2.applyRemote({kind:'batch',table_id:1,revision:2,layout_revision:1,actor_id:2,client_id:'x',structural:{kind:'insert_cols',index:0,count:1},
  cells:[],styles:[],meta:null,occurred_at:''});
assert.equal(e2.view(0,2).raw,'=B1*2'); assert.equal(e2.view(0,2).text,'6'); assert.ok(e2.styles.has(1));
console.log('ALL OK');
```

### Приложение C. Тесты импорта/экспорта Excel

Файл `tests/unit/table_service/test_services/test_excel_processor.py` (сейчас он пустой). Запуск:
`pytest tests/unit/table_service/test_services/test_excel_processor.py -q`.


```python
import io
from datetime import date

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from table_service.app.exceptions import EmptyFileException
from table_service.app.services import ExcelProcessorService


@pytest.fixture
def processor() -> ExcelProcessorService:
    return ExcelProcessorService()


def make_xlsx(fill) -> io.BytesIO:
    workbook = Workbook()
    fill(workbook.active)
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def by_position(cells: list[dict]) -> dict[tuple[int, int], dict]:
    return {(c["row"], c["col"]): c for c in cells}


def test_parse_keeps_formulas_and_types(processor):
    def fill(sheet):
        sheet["A1"] = "Имя"
        sheet["B1"] = 10
        sheet["B2"] = 20
        sheet["B3"] = "=SUM(B1:B2)"
        sheet["C1"] = date(2024, 1, 5)
        sheet["D1"] = True

    cells = by_position(processor.parse_workbook(make_xlsx(fill)))

    assert cells[(0, 0)]["raw"] == "Имя"
    assert cells[(0, 1)] == {"row": 0, "col": 1, "raw": "10", "value": 10, "style": None}
    assert cells[(2, 1)]["raw"] == "=SUM(B1:B2)"
    assert cells[(0, 2)]["raw"] == "05.01.2024"
    assert cells[(0, 2)]["style"] == {"numFmt": "date"}
    assert cells[(0, 3)]["value"] is True


def test_parse_reads_basic_style(processor):
    def fill(sheet):
        sheet["A1"] = "x"
        sheet["A1"].font = Font(bold=True)
        sheet["A1"].fill = PatternFill("solid", fgColor="FFFF00")

    cells = by_position(processor.parse_workbook(make_xlsx(fill)))

    assert cells[(0, 0)]["style"] == {"bg": "#ffff00", "bold": True}


def test_parse_empty_file_raises(processor):
    with pytest.raises(EmptyFileException):
        processor.parse_workbook(make_xlsx(lambda sheet: None))


class FakeCell:
    def __init__(self, row, col, raw, value, style=None):
        self.row, self.col, self.raw, self.value, self.style = row, col, raw, value, style


def test_export_writes_formulas_gaps_and_styles(processor):
    workbook, sheet = processor.create_streaming_workbook()
    rows = [
        (0, [FakeCell(0, 0, "=SUM(B1:B2)", 30, {"bg": "#ffeb3b", "bold": True})]),
        (3, [FakeCell(3, 2, "x", "x")]),
    ]

    next_row = processor.append_rows_chunk(sheet, rows, 0)
    result = load_workbook(processor.finalize_workbook(workbook)).active

    assert next_row == 4
    assert result["A1"].value == "=SUM(B1:B2)"
    assert result["A1"].font.bold is True
    assert result["C4"].value == "x"
    assert result["A2"].value is None
```
