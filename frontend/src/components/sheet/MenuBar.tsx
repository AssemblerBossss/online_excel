import React, {useEffect, useRef, useState} from "react";
import {colors, rounded, shadowLevel5, spacing, typography} from "../../styles/theme";

export interface MenuItem {
    label: string;
    hotkey?: string;
    onClick?: () => void;      // нет onClick => пункт disabled
    divider?: boolean;         // разделитель ПЕРЕД пунктом
    checked?: boolean;         // галочка для toggle-пунктов (Вид)
}

export interface Menu {
    title: string;
    items: MenuItem[];
}

const MenuBar: React.FC<{ menus: Menu[] }> = ({menus}) => {
    const [openIndex, setOpenIndex] = useState<number | null>(null);
    const rootRef = useRef<HTMLDivElement>(null);

    // клик вне меню / Escape — закрыть
    useEffect(() => {
        if (openIndex === null) return;
        const onDown = (e: MouseEvent) => {
            if (!rootRef.current?.contains(e.target as Node)) setOpenIndex(null);
        };
        const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpenIndex(null);
        document.addEventListener("mousedown", onDown);
        document.addEventListener("keydown", onKey);
        return () => {
            document.removeEventListener("mousedown", onDown);
            document.removeEventListener("keydown", onKey);
        };
    }, [openIndex]);

    return (
        <div ref={rootRef} style={styles.bar}>
            {menus.map((menu, i) => (
                <div key={menu.title} style={{position: "relative"}}>
                    <button
                        className="sheet-hover"
                        style={{...styles.trigger, ...(openIndex === i ? styles.triggerActive : {})}}
                        onClick={() => setOpenIndex(openIndex === i ? null : i)}
                        // как в Google: если одно меню открыто, наведение переключает на соседнее
                        onMouseEnter={() => openIndex !== null && setOpenIndex(i)}
                    >
                        {menu.title}
                    </button>
                    {openIndex === i && (
                        <div style={styles.dropdown} role="menu">
                            {menu.items.map(item => (
                                <React.Fragment key={item.label}>
                                    {item.divider && <div style={styles.divider}/>}
                                    <button
                                        className="sheet-hover"
                                        role="menuitem"
                                        disabled={!item.onClick}
                                        style={{...styles.item, ...(!item.onClick ? styles.itemDisabled : {})}}
                                        onClick={() => {
                                            setOpenIndex(null);
                                            item.onClick?.();
                                        }}
                                    >
                                        <span style={styles.check}>{item.checked ? "✓" : ""}</span>
                                        <span style={{flex: 1}}>{item.label}</span>
                                        {item.hotkey && <span style={styles.hotkey}>{item.hotkey}</span>}
                                    </button>
                                </React.Fragment>
                            ))}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};

export default MenuBar;

const styles: Record<string, React.CSSProperties> = {
    bar: {display: "flex", gap: 2, marginLeft: -spacing.xs},
    trigger: {
        ...typography.bodySm, color: colors.ink, background: "transparent", border: "none",
        padding: `2px ${spacing.xs}px`, borderRadius: rounded.xs, cursor: "pointer",
    },
    triggerActive: {background: colors.canvasSoft2},
    dropdown: {
        position: "absolute", top: "calc(100% + 4px)", left: 0, zIndex: 1000,
        minWidth: 260, padding: `${spacing.xxs}px 0`,
        background: colors.canvas, borderRadius: rounded.sm, boxShadow: shadowLevel5,
    },
    item: {
        ...typography.bodySm, color: colors.ink, width: "100%",
        display: "flex", alignItems: "center", gap: spacing.xs,
        padding: `6px ${spacing.md}px 6px ${spacing.xs}px`,
        background: "transparent", border: "none", textAlign: "left", cursor: "pointer",
    },
    itemDisabled: {color: colors.mute, cursor: "default"},
    check: {width: 16, textAlign: "center", color: colors.ink},
    hotkey: {...typography.captionMono, color: colors.mute},
    divider: {height: 1, background: colors.hairline, margin: `${spacing.xxs}px 0`},
};
