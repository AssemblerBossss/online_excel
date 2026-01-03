import React, { useState } from 'react';
import Sidebar from './Sidebar';

const SidebarWithToggle: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            <Sidebar isOpen={isOpen} onClose={() => setIsOpen(false)} />

            {/* Кнопка открытия - всегда видна в левом верхнем углу */}
            {!isOpen && (
                <button
                    style={styles.openButton}
                    onClick={() => setIsOpen(true)}
                    aria-label="Открыть меню"
                >
                    <div style={{ ...styles.line, top: 6 }} />
                    <div style={{ ...styles.line, top: 13 }} />
                    <div style={{ ...styles.line, top: 20 }} />
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
        width: 30,
        height: 30,
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        padding: 0,
        zIndex: 998,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    },
    line: {
        position: 'absolute',
        width: 24,
        height: 2,
        backgroundColor: '#333',
        borderRadius: 2,
        left: '50%',
        marginLeft: -12,
    },
};