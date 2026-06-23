import { api } from './axiosInstance';
import { evaluate, all, create, string } from 'mathjs';

const math = create(all);


export interface ColumnSchema {
    name: string;
    type: string;
    required?: boolean;
}

export interface DataTableResponse {
    id: number;
    name: string;
    description?: string;
    is_public?: boolean;
    columns_schema?: ColumnSchema[];
    created_by: number;
    created_at: string;
    updated_at?: string;
    is_deleted?: boolean; 
    deleted_at?: string;
}

export interface TableRow {
    id: number;
    table_id: number;
    row_data: Record<string, any>;
    /** Исходные формулы ячеек. Ключ — имя колонки, значение — строка формулы (например "=5+5"). */
    formulas?: Record<string, string>;
    created_at: string;
    updated_at?: string;
}

export interface CreateTableRequest {
    name: string;
    description?: string;
    is_public?: boolean;
    columns_schema?: ColumnSchema[];
}

export type FilterOp = 'eq' | 'ne' | 'contains' | 'gt' | 'gte' | 'lt' | 'lte';

export interface RowFilter {
    field: string;
    op: FilterOp;
    value: string;
}

export interface RowsQuery {
    skip?: number;
    limit?: number;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    filters?: RowFilter[];
}

export interface PaginatedRows {
    items: TableRow[];
    total: number;
    skip: number;
    limit: number;
}

interface ExportResult {
        blob: Blob;
        filename: string;
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

export function isFormula(value: string): boolean {
    return typeof value === 'string' && value.startsWith('=');
}


/**
 * Преобразует буквенное обозначение колонки в 0-based индекс.
 * A -> 0, B -> 1, ..., Z -> 25, AA -> 26, ...
 */
function columnLetterToIndex(letters: string): number {
    let result = 0;
    for (const ch of letters) {
        result = result * 26 + (ch.charCodeAt(0) - 'A'.charCodeAt(0) + 1);
    }
    return result - 1;
}

/**
 * Вычисляет формулу на стороне фронтенда.
 *
 * Поддерживает арифметику (+, -, *, /, **) и ссылки на ячейки (A1, B2...)
 * в пределах одной строки. Возвращает '#ОШИБКА!' при синтаксических ошибках.
 *
 * @param formula   Строка формулы, начинающаяся с '='
 * @param rowData   Текущие данные строки (для разрешения ссылок)
 * @param colNames  Упорядоченный список имён колонок таблицы
 */

export function evaluateFormula(
    formula: string,
    rowData: Record<string, any> = {},
    colNames: string[] = [],
): string | number {
    if (!isFormula(formula)) return formula;

    try {
        let expr = formula.slice(1).trim(); // убираем '='

        // Заменяем ссылки на ячейки значениями из rowData
        // Паттерн: одна или несколько букв + одна или несколько цифр (A1, BC12 и т.д.)
        expr = expr.replace(/\b([A-Za-z]+)(\d+)\b/g, (match, letters) => {
            const colIndex = columnLetterToIndex(letters.toUpperCase());
            if (colIndex >= colNames.length) {
                throw new Error(`Колонка '${letters}' не существует`);
            }
            const colName = colNames[colIndex];
            const value = rowData[colName];
            if (value === undefined || value === null || value === '') return '0';
            const num = Number(value);
            if (isNaN(num)) {
                throw new Error(`Значение '${value}' в колонке '${colName}' не является числом`);
            }
            return String(num);
        });

        // Если в выражении есть строки — используем обычную конкатенацию через Function
        // Если только числа — используем mathjs
        if (expr.includes('"')) {
            // eslint-disable-next-line no-new-func
            const result = new Function(`"use strict"; return (${expr.replace(/\+/g, '+')})`)();
            return String(result);
        }

        const result = math.evaluate(expr);

        if (typeof result === 'number') {
            if (!isFinite(result)) throw new Error('Деление на ноль или бесконечность');
            return Number.isInteger(result) ? result : parseFloat(result.toFixed(10));
        }

        return String(result);

    } catch (e) {
        console.warn(`Ошибка формулы "${formula}":`, e);
        return '#ОШИБКА!';

    }



};

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

    getTableRows: async (tableId: number, query: RowsQuery = {}): Promise<PaginatedRows> => {
        const params = new URLSearchParams();
        params.set('skip', String(query.skip ?? 0));
        params.set('limit', String(query.limit ?? 50));
        if (query.sortBy) params.set('sort_by', query.sortBy);
        if (query.sortOrder) params.set('sort_order', query.sortOrder);
        // повторяющийся параметр filter=field:op:value
        for (const f of query.filters ?? []) {
            params.append('filter', `${f.field}:${f.op}:${f.value}`);
        }
        const response = await api.get(`/data/${tableId}/rows?${params.toString()}`);

    permanentDelete: async (id: number): Promise<void> => {
        await api.delete(`/tables/trash/${id}/`);
    },

    restoreTable: async (id: number): Promise<void> => {
        const response = await api.post(`/tables/trash/${id}/restore/`);

    },

    exportTable: async (id: number): Promise<ExportResult> => {
        const response = await api.get(`/tables/${id}/export`, {
            responseType: 'blob',
        });

        const disposition = response.headers['content-disposition'] || '';
        const filename = parseFilename(disposition) || `table_${id}.xlsx`;

        return { blob: response.data, filename };
    },

    createRow: async (tableId: number, rowData: Record<string, any>, formulas?: Record<string, string>): Promise<TableRow> => {
        const response = await api.post(`/data/${tableId}/rows`, {
            row_data: rowData,
            formulas: formulas ?? null,
        });
        return response.data;
    },

    updateRow: async (
        tableId: number,
        rowId: number,
        rowData: Record<string, any>,
        formulas?: Record<string, string>,
    ): Promise<TableRow> => {
        const response = await api.put(`/data/${tableId}/rows/${rowId}`, {
            row_data: rowData,
            formulas: formulas ?? null,
        });
        return response.data;
    },

    deleteRow: async (tableId: number, rowId: number): Promise<void> => {
        await api.delete(`/data/${tableId}/rows/${rowId}`);
    },

    searchTables: async(query: string, limit: number = 10): Promise<DataTableResponse[]> => {
        const response = await api.get('/search', { params: { q: query, limit } });
        return response.data;
    },
};