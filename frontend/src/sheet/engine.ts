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
