import React from 'react';
import type {SheetEngine, StyleTarget} from '../../sheet/engine';
import type {NumFmt, StylePatch} from '../../sheet/types';
import {colors, rounded, spacing, typography} from '../../styles/theme';
import apply from 'lodash/fp/apply';


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

const Toolbar: React.FC<Props> = ({engine, version, canWrite, active, target, onStyle, onFreeze}) => {
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
    
}