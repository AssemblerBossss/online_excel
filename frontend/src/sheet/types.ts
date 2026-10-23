import { NumberCell } from "@glideapps/glide-data-grid"; // ← не используется, удалить

/** Формат отображения числа в ячейке. */
export type NumFmt = 'general' | 'number' | 'percent' | 'currency' | 'date' | 'datetime';

/** Оформление ячейки. */
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

/** Патч стиля: значение свойства или null (убрать свойство). */
export type StylePatch = { [K in keyof CellStyle]?: CellStyle[K] | null };

/** Вычисленное значение ячейки; ошибки — как {e: "#DIV/0!"}. */
export type CellValue = string | number | boolean | null | {e: string};

/** Настройки листа: ширины, закрепления, стили целых строк/колонок. */
export interface SheetMeta {
    /** Ширины колонок: индекс колонки -> px */
    col_widths?: Record<string, number>;
    /** Сколько левых колонок закреплено */
    frozen_cols?: number;
    /** Оформление целых колонок / строк (индекс -> стиль) */
    col_styles?: Record<string, CellStyle>;
    row_styles?: Record<string, CellStyle>;
}

/** Ячейка в компактном формате для сети: [row, col, raw, value, style]. */
export type WireCell = [number, number, string | null, CellValue, CellStyle | null];

/** Полное состояние листа при загрузке. */
export interface SheetSnapshot {
    table_id: number;
    revision: number;
    layout_revision: number;
    can_write: boolean;
    meta: SheetMeta;
    cells: WireCell[];
}

/** Вид структурной операции над листом. */
export type StructuralKind = 'insert_rows' | 'delete_rows' | 'insert_cols' | 'delete_cols';

/** Структурная операция: что, с какой позиции, сколько. */
export interface StructuralOP {
    kind: StructuralKind;
    index: number;
    count: number;
}

/** Изменение содержимого одной ячейки. */
export interface CellWrite {
    row: number;
    col: number;
    raw: string | null;
    value: CellValue;
}

/** Изменение стиля одной ячейки; null — сбросить стиль. */
export interface StyleWrite {
    row: number;
    col: number;
    style: CellStyle | null;
}

/** Пакет изменений от клиента на сервер. */
export interface SheetBatch {
    client_id: string;
    base_layout_revision: number;
    structural: StructuralOP | null;
    cells: CellWrite[];
    styles: StyleWrite[];
    meta: SheetMeta | null;
}

/** Ответ сервера на батч: новые версии данных и структуры. */
export interface SheetBatchResult {
    revision: number;
    layout_revision: number;
}

/** Событие синхронизации для других клиентов (batch — применить патч, reload — перезагрузить). */
export interface SheetEvent {
    kind: 'batch' | 'reload';
    table_id: number;
    revision: number;
    layout_revision: number;
    actor_id: number;
    client_id: string;
    structural: StructuralOP | null;
    cells: CellWrite[];
    styles: StyleWrite[];
    meta: SheetMeta | null;
    occurred_at: string;
}

/** Результат локальной операции: что нужно отправить на сервер. */
export interface EngineResult {
    cells: CellWrite[];
    styles: StyleWrite[];
    meta?: SheetMeta;
    structural?: StructuralOP;
}

/** Прямоугольная область (для выделения, оверлеев, видимой зоны). */
export interface Rect {
    x: number;
    y: number;
    width: number;
    height: number;
}