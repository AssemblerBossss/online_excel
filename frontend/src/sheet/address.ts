// Лимиты листа. Те же числа заданы на бэкенде в table_service/app/schemas/sheet.py
export const MAX_ROWS  = 100_000;
export const MAX_COLS = 1_000;
export const MAX_BATCH_ITEMS = 20_000;

export const DEFAULT_ROWS = 1_000;
export const DEFAULT_COLS = 26;


// Числовой ключ ячейки для Map
const COL_STRIDE = 1024;

export const cellKey = (row: number, col: number): number => row * COL_STRIDE + col;
export const keyRow = (key: number): number => Math.floor(key/ COL_STRIDE);
export const keyCol  = (key: number): number => key % COL_STRIDE;


/** Преобразует индекс колонки в буквы Excel: 0 → "A", 25 → "Z", 26 → "AA". */
export function colToLetters(col: number): string {
    let n = col + 1;
    let result = '';
    while (n > 0) {
        const rem  = (n - 1) % 26;
        result = String.fromCharCode(65 + rem) + result;
        n = Math.floor((n - 1) / 26); 
    }
    return result;
}

/** Возвращает адрес ячейки в стиле Excel: (0, 0) → "A1", (99, 26) → "AA100". */
export const addressLabel = (row: number, col: number): string => `${colToLetters(col)}${row + 1}`;
