import type {HyperFormula} from 'hyperformula';
import {DetailedCellError} from 'hyperformula';
import type {CellStyle, NumFmt} from './types';


/** Результат форматирования значения ячейки для показа. */
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
}

const intl = (options: Intl.NumberFormatOptions) => new Intl.NumberFormat('en-US', options);

/**
 * Форматирует число по заданному формату.
 * @param n — число для форматирования
 * @param fmt — формат: number / percent / currency / general
 * @param decimals — сколько знаков после запятой (если не задано — по умолчанию)
 */
function formatNumber(n: number, fmt: NumFmt, decimals: number | undefined): string {
    switch (fmt) {
        case 'number':
            // Обычное число с разделителями тысяч.
            // По умолчанию — 2 знака после запятой, если decimals не задан.
            return intl({minimumFractionDigits: decimals ?? 2, maximumFractionDigits: decimals ?? 2}).format(n);
        case 'percent':
            // Процент: Intl умножает число на 100 и добавляет «%».
            // По умолчанию — 0 знаков минимум, 2 максимум (0.5 → "50%").
            return intl({style: 'percent', minimumFractionDigits: decimals ?? 0, maximumFractionDigits: decimals ?? 2}).format(n);
        case 'currency':
            // Деньги: рубли, короткий символ «₽» (narrowSymbol).
            // По умолчанию — 2 знака после запятой.
            return intl({
                style: 'currency', currency: 'RUB', currencyDisplay: 'narrowSymbol',
                minimumFractionDigits: decimals ?? 2, maximumFractionDigits: decimals ?? 2,
            }).format(n);
        default:
            // general: убираем «хвосты» двоичной арифметики (0.1 + 0.2)
            // Целые числа — как есть (без ".0"); дробные — обрезаем до 12 значащих цифр.
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
