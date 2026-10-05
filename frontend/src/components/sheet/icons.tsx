import React from "react";

const Svg: React.FC<{ children: React.ReactNode }> = ({children}) => (
    <svg width={16} height={16} viewBox="0 0 16 16" fill="none"
         stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
        {children}
    </svg>
);

export const IconUndo = () => <Svg>
    <path d="M4 6h6a3 3 0 0 1 0 6H7"/>
    <path d="M6 4 4 6l2 2"/>
</Svg>;

export const IconRedo = () => <Svg>
    <path d="M12 6H6a3 3 0 0 0 0 6h3"/>
    <path d="m10 4 2 2-2 2"/>
</Svg>;

export const IconPlus = () => <Svg>
    <path d="M8 3v10M3 8h10"/>
</Svg>;

export const IconCopy = () => <Svg>
    <rect x="5" y="5" width="8" height="8" rx="1.5"/>
    <path d="M3 11V4a1 1 0 0 1 1-1h7"/>
</Svg>;

export const IconTrash = () => <Svg>
    <path d="M3 4h10M6 4V3h4v1M4.5 4l.5 9h6l.5-9"/>
</Svg>;

export const IconSortAsc = () => <Svg>
    <path d="M4 3v10M2 11l2 2 2-2M9 4h5M9 8h3M9 12h1"/>
</Svg>;

export const IconSortDesc = () => <Svg>
    <path d="M4 3v10M2 11l2 2 2-2M9 4h1M9 8h3M9 12h5"/>
</Svg>;

export const IconFilter = () => <Svg>
    <path d="M2 3h12l-4.5 5.5V13l-3-1.5v-3z"/>
</Svg>;

export const IconDownload = () => <Svg>
    <path d="M8 2v8M5 7l3 3 3-3M3 13h10"/>
</Svg>;

export const IconStar = ({filled}: { filled?: boolean }) =>
    <Svg>
        <path d="m8 2 1.8 3.8 4.2.5-3.1 2.9.8 4.1L8 11.3l-3.7 2 .8-4.1L2 6.3l4.2-.5z"
              fill={filled ? "currentColor" : "none"}/>
    </Svg>;

export const IconSheet = () => <Svg>
    <rect x="2.5" y="1.5" width="11" height="13" rx="1.5"/>
    <path d="M5 6h6M5 9h6M5 12h6M8 6v6"/>
</Svg>;

export const IconCaret = () => <Svg>
    <path d="m5 6.5 3 3 3-3"/>
</Svg>;