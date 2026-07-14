import React, {useState} from 'react';
import Sidebar from './Sidebar';
import {useChat} from '../context/ChatContext';
import {colors, rounded} from '../styles/theme';


const SidebarWithToggle: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);
    const {unreadTotal, openPanel} = useChat();

    return (
        <>
            <Sidebar
                isOpen={isOpen}
                onClose={() => setIsOpen(false)}
                onOpenChat={() => {
                    openPanel();
                    setIsOpen(false);
                }}
                unreadChatsCount={unreadTotal}
            />

            {!isOpen && (
                <button
                    style={styles.openButton}
                    onClick={() => setIsOpen(true)}
                    aria-label="Открыть меню"
                    onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = colors.canvasSoft2;
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                >
                    <div style={{...styles.line, top: 12}}/>
                    <div style={{...styles.line, top: 19}}/>
                    <div style={{...styles.line, top: 26}}/>
                </button>
            )}
        </>
    );
};

export default SidebarWithToggle;

const styles: Record<string, React.CSSProperties> = {
    openButton: {
        position: 'fixed',
        top: 16,
        left: 16,
        width: 38,
        height: 38,
        background: 'transparent',
        border: `1px solid ${colors.hairline}`,
        borderRadius: rounded.sm,
        cursor: 'pointer',
        padding: 0,
        zIndex: 998,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'background-color 0.15s ease',
    },
    line: {
        position: 'absolute',
        width: 16,
        height: 1.5,
        backgroundColor: colors.ink,
        borderRadius: 2,
        left: '50%',
        marginLeft: -8,
    },
};