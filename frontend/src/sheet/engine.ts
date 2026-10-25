import {
    CellType,
    DetailedCellError,
    HyperFormula,
    type ExportedChange,
    type SimpleCellAddress,
} from 'hyperformula';

import { cellKey, keyCol, keyRow, MAX_COLS, MAX_ROWS } from './address';
import { formatValue } from './format';
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
    StyleWrite
} from './types';
import { LinkedCamera } from '@mui/icons-material';

const SHEET_NAME = 'Sheet1';
const MAX_STYLE_CELLS = 20_000;

/** Снимок ячейки: сырое содержимое и вычисленное значение. */
interface CellSnap {
    raw: string | null;
    value: CellValue;
}

/** Что подставить в выделение при применении оформления. */
export type StyleTarget = {kind: 'range'; rect: Rect} | {kind: 'cols'; cols: number[]} | {kind: 'rows'; rows: number[]};

/** Представление ячейки для отрисовки в UI. */
export interface CellView {
    /** Что показать в ячейке */
    text: string;
    /** Что показать при редактировании (формула или введённый текст) */
    raw: string;
    isError: boolean;
    isNumber: boolean;
    style: CellStyle | undefined;
}

/** Пустой результат движка. */
const EMPTY_RESULT = (): EngineResult => ({cells: [], styles: []});

/** Приводит произвольное содержимое к строке для HyperFormula. */
function serialize(content: unknown): string | null {
    if (content === null || content === undefined) return null;
    if (typeof content === 'boolean') return content ? 'TRUE' : 'FALSE';
    return String(content);
}

/** Преобразует значение HyperFormula в формат для передачи в UI. */
function toWire(value: unknown): CellValue {
    if (value instanceof DetailedCellError) return {e:value.value};
    if (value === null || value === undefined) return null;
    if (typeof value === 'number' && !Number.isFinite(value)) return {e: '#NUM'};
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value;
    return String(value);
}

/** Сравнивает два значения ячеек на равенство. */
function sameValue(a: CellValue, b: CellValue): boolean {
    if (a === b) return true;
    if (typeof a === 'object' && a !== null && typeof b === 'object' && b !== null) return a.e === b.e;
    return false;
}

/** Накладывает патч стиля на базовый стиль; возвращает null, если стиль пуст. */
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

/** Является ли операция операцией над строками. */
const isRowOp = (kind: StructuralKind): boolean => kind.endsWith('rows');

/** Сдвигает индексы в словаре meta (ширины колонок, оформление строк/колонок). */
function remapRecord<T>(record: Record<string, T> | undefined, op: StructuralOp): Record<string, T> | undefined {
    if (!record) return record;
    const out: Record<string, T> = {};
    for (const [key, value] of Object.entries(record)) {
        const next = mapIndex(Number(key), op);
        if (next !== null) out[String(next)] = value;
    }
}

/** Пересчитывает метаданные листа после структурной операции. */
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

export class SheetEngine {
    private readonly hf: HyperFormula;
    private readonly sheet: number;

    /** Последнее известное серверу состояние непустых ячеек: ключ -> {raw, value}. */
    private mirror = new Map<number, CellSnap>();
    /** Оформление отдельных ячеек (по ключу ячейки). */
    styles = new Map<number, CellStyle>();
    /** Метаданные листа: ширины колонок, оформление строк/колонок, закрепление. */
    meta: SheetMeta = {};

    /** Прямоугольник, скопированный через hf.copy, и его оформление (для вставки со сдвигом ссылок). */
    private clip: {rect: Rect; styles: (CellStyle | undefined)[][]} | null = null;

    /**
     * Создаёт движок HyperFormula с одним листом `Sheet1`.
     */
    constructor() {
        this.hf = HyperFormula.buildEmpty({
            licenseKey: 'gpl-v3',
            maxRows: MAX_ROWS,
            maxColumns: MAX_COLS,
            dateFormats: ['DD.MM.YYYY', 'YYYY-MM-DD', 'DD/MM/YYYY'],
        });
        this.hf.addSheet(SHEET_NAME);
        this.sheet = this.hf.getSheetId(SHEET_NAME)!;
    }

    /** Уничтожает экземпляр HyperFormula и освобождает память. */
    destroy(): void {
        this.hf.destroy();
    }

    /** Собирает адрес ячейки для HyperFormula из строки и колонки текущего листа. */
    private addr(row: number, col: number): SimpleCellAddress {
        return {sheet: this.sheet, row, col};
    }

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

    /**
     * Возвращает размеры занятой области (максимальные строка и колонка среди
     * ячеек с содержимым и ячеек с оформлением).
     * Используется для начального числа строк/колонок в сетке.
     */
    extent(): {rows: number, cols: number} {
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

    /**
     * Возвращает итоговый стиль ячейки: слияние стиля колонки, строки и самой ячейки
     * (в порядке возрастания приоритета). `undefined`, если стилей нет вовсе.
     */
    effectiveStyle(row: number, col: number): CellStyle | undefined {
        const colStyle = this.meta.col_styles?.[col];
        const rowStyle = this.meta.row_styles?.[row];
        const cellStyle = this.styles.get(cellKey(row, col));
        if (!colStyle && !rowStyle && !cellStyle) return undefined;
        return {...colStyle, ...rowStyle, ...cellStyle};
    }

    /**
     * Возвращает представление ячейки для UI: отображаемый текст, исходное содержимое
     * для редактирования, признаки ошибки/числа и эффективный стиль.
     */
    view(row: number, col: number): CellView {
        const style = this.effectiveStyle(row, col);
        const addr = this.addr(row, col);
        const cellType = this.hf.getCellType(addr);
        if (cellType === CellType.EMPTY) return {text: '', raw: '', isError: false, isNumber: false, style};
        
        const value = this.hf.getCellValue(addr);
        const shown = formatValue(this.hf, value, this.hf.getCellValueDetailedType(addr), style);
        const raw = cellType === CellType.ARRAY ? shown.text : (serialize(this.hf.getCellSerialized(addr)) ?? '');
        return {...shown, raw, style};

    }

    /**
     * Снимает текущее состояние ячейки из движка: `raw` (что ввели) и `value` (что вычислилось).
     * Для пустой ячейки оба поля `null`; для «разлитой» (ARRAY) — `raw: null`, только значение.
     */
    private snap(row: number, col: number): CellSnap {
        const addr = this.addr(row, col);
        const cellType = this.hf.getCellType(addr);
        if (cellType === CellType.EMPTY) return {raw: null, value: null};
        const value = toWire(this.hf.getCellValue(addr));
        if (cellType === CellType.ARRAY) return {raw: null, value};
        return {raw: serialize(this.hf.getCellSerialized(addr)), value: value};
    }

    /**
     * Сравнивает текущее состояние указанных ячеек с зеркалом `mirror`.
     * Обновляет зеркало и возвращает список изменений для отправки на сервер.
     * Ячейки, которые не изменились, в результат не попадают.
     */
    private diffKeys(keys: Iterable<number>): CellWrite[] {
        const out: CellWrite[] = [];
        for (const key of new Set(keys)) {
            const row = keyRow(key);
            const col = keyCol(key);
            const now =  this.snap(row, col);
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
            for (let c = rect.x; c < rect.x + rect.width; c++) {
                keys.push(cellKey(r,c));
            }
        }
        return keys;
    }

    private autoDateStyles(keys: number[]): StyleWrite[] {
        const out: StyleWrite[] = [];
        for (const key of keys) {
            const row = keyRow(key);
            const col = keyCol(key);
            const addr = this.addr(row, col);
            if (this.hf.getCellType(addr) != CellType.VALUE) continue;
            const detailed = this.hf.getCellValueDetailedType(addr);
            const fmt = detailed === 'NUMBER_DATE' ? 'date' : detailed === 'NUMBER_DATETIME' ? 'datetime': null;
            if (!fmt || this.styles.get(key)?.numFmt) continue;
            const style = {...this.styles.get(key), numFmt: fmt} as CellStyle;
            this.styles.set(key, style);
            out.push({row, col, style});
        }
        return out;
    }



        /**
     * Собирает уникальные ключи ячеек, затронутых изменениями HyperFormula,
     * и добавляет к ним ключи из `extra`.
     *
     * HyperFormula не всегда возвращает в `changes` все затронутые ячейки
     * (например, при записи пустой строки в уже пустую ячейку или при
     * структурных сдвигах). Параметр `extra` позволяет проверить
     * дополнительные ячейки, которые вы подозреваете могли измениться.
     *
     * @param changes - массив изменений, возвращённый методами HyperFormula
     * @param extra - дополнительные ключи ячеек для проверки
     * @returns массив уникальных ключей ячеек текущего листа
     */
    private keysOf(changes: ExportedChange[], extra: Iterable<number> = []): number[] {
        const keys = new Set<number>(extra);
        for (const change of changes) {
            if ('address' in change && change.address.sheet === this.sheet) {
                keys.add(cellKey(change.address.row, change.address.col));
            }
        }
        return Array.from(keys);
    }

    /**
     * Возвращает ключи всех ячеек внутри прямоугольника `rect`.
     * Используется, когда нужно проверить или обновить целую область
     * (вставка, очистка, применение оформления).
     *
     * @param rect - прямоугольная область (координаты + размеры)
     * @returns массив ключей ячеек внутри прямоугольника
     */
    private rectKeys(rect: Rect): number[] {
        const keys: number[] = [];
        for (let r = rect.y; r < rect.y + rect.height; r++) {
            for (let c = rect.x; c < rect.x + rect.width; c++) {
                keys.push(cellKey(r,c));
            }
        }
        return keys;
    }

    /**
     * Автоматически назначает формат даты/даты-времени ячейкам,
     * в которые пользователь ввёл дату вручную (как в Google Таблицах).
     *
     * Проверяет только ячейки с типом `VALUE`. Если HyperFormula распознал
     * значение как `NUMBER_DATE` или `NUMBER_DATETIME` и у ячейки ещё нет
     * собственного `numFmt`, добавляет соответствующий формат в стиль
     * и возвращает список изменений для отправки в UI.
     *
     * @param keys - ключи ячеек для проверки (обычно прямоугольник ввода)
     * @returns список записей стилей для изменённых ячеек
     */
    private autoDateStyles(keys: number[]): StyleWrite[] {
        const out: StyleWrite[] = [];
        for (const key of keys) {
            const row = keyRow(key);
            const col = keyCol(key);
            const addr = this.addr(row, col);
            if (this.hf.getCellType(addr) != CellType.VALUE) continue;
            const detailed = this.hf.getCellValueDetailedType(addr);
            const fmt = detailed === 'NUMBER_DATE' ? 'date' : detailed === 'NUMBER_DATETIME' ? 'datetime': null;
            if (!fmt || this.styles.get(key)?.numFmt) continue;
            const style = {...this.styles.get(key), numFmt: fmt} as CellStyle;
            this.styles.set(key, style);
            out.push({row, col, style});
        }
        return out;
    }





}
