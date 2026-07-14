// Design tokens extracted from DESIGN.md (Vercel-inspired system).
import type {CSSProperties} from "react";

export const colors = {
    primary: "#171717",
    onPrimary: "#ffffff",
    ink: "#171717",
    body: "#4d4d4d",
    mute: "#888888",
    hairline: "#ebebeb",
    hairlineStrong: "#a1a1a1",
    canvas: "#ffffff",
    canvasSoft: "#fafafa",
    canvasSoft2: "#f5f5f5",
    link: "#0070f3",
    linkDeep: "#0761d1",
    linkBgSoft: "#d3e5ff",
    success: "#0070f3",
    error: "#ee0000",
    errorSoft: "#f7d4d6",
    errorDeep: "#c50000",
    warning: "#f5a623",
    warningSoft: "#ffefcf",
    warningDeep: "#ab570a",
} as const;

const fontSans = "'Geist', Inter, system-ui, -apple-system, sans-serif";
const fontMono = "'Geist Mono', 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, monospace";

export const typography = {
    displayMd: { fontFamily: fontSans, fontSize: 24, fontWeight: 600, lineHeight: "32px", letterSpacing: "-0.96px" } as CSSProperties,
    displaySm: { fontFamily: fontSans, fontSize: 20, fontWeight: 600, lineHeight: "28px", letterSpacing: "-0.6px" } as CSSProperties,
    bodyMd: { fontFamily: fontSans, fontSize: 16, fontWeight: 400, lineHeight: "24px" } as CSSProperties,
    bodyMdStrong: { fontFamily: fontSans, fontSize: 16, fontWeight: 500, lineHeight: "24px" } as CSSProperties,
    bodySm: { fontFamily: fontSans, fontSize: 14, fontWeight: 400, lineHeight: "20px", letterSpacing: "-0.28px" } as CSSProperties,
    bodySmStrong: { fontFamily: fontSans, fontSize: 14, fontWeight: 500, lineHeight: "20px", letterSpacing: "-0.28px" } as CSSProperties,
    caption: { fontFamily: fontSans, fontSize: 12, fontWeight: 400, lineHeight: "16px" } as CSSProperties,
    buttonMd: { fontFamily: fontSans, fontSize: 14, fontWeight: 500, lineHeight: "20px" } as CSSProperties,
    buttonLg: { fontFamily: fontSans, fontSize: 16, fontWeight: 500, lineHeight: "24px" } as CSSProperties,
    code: { fontFamily: fontMono, fontSize: 13, fontWeight: 400, lineHeight: "20px" } as CSSProperties,
};

export const rounded = {
    xs: 4,
    sm: 6,
    md: 8,
    lg: 12,
    xl: 16,
    pill: 100,
    full: 9999,
} as const;

export const spacing = {
    xxs: 4,
    xs: 8,
    sm: 12,
    md: 16,
    lg: 24,
    xl: 32,
    "2xl": 40,
    "3xl": 48,
    "4xl": 64,
} as const;

// Elevation Level 2 — Subtle Drop (card-marketing chrome)
export const shadowLevel2 = "0px 1px 1px #00000005, 0px 2px 2px #0000000a, inset 0 0 0 1px #00000014";
// Elevation Level 3 — Soft Stack (feature-grid cards)
export const shadowLevel3 = "0px 2px 2px #0000000a, 0px 8px 8px -8px #0000000a, inset 0 0 0 1px #00000014";
// Elevation Level 4 — Float Stack (pricing/callout cards)
export const shadowLevel4 = "0px 2px 2px #0000000a, 0px 8px 16px -4px #0000000a, inset 0 0 0 1px #00000014";
// Elevation Level 5 — Modal / dropdown
export const shadowLevel5 = "0px 1px 1px #00000005, 0px 8px 16px -4px #0000000a, 0px 24px 32px -8px #0000000f, inset 0 0 0 1px #00000014";