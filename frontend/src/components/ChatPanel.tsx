import React from "react";
import {useChat} from "../context/ChatContext";
import ChatDialogList from "./ChatDialogList";
import ChatConversationView from "./ChatConversationView";
import {colors, shadowLevel5} from "../styles/theme";

const ChatPanel: React.FC = () => {
    const {
        isPanelOpen,
        activeEmail,
        closePanel,
        backToList,
        openConversation,
        dialogs,
        currentUserEmail,
        lastEvent,
        refreshDialogs,
    } = useChat();

    return (
        <>
            {isPanelOpen && <div style={styles.overlay} onClick={closePanel}/>}
            <div style={{...styles.panel, transform: isPanelOpen ? "translateX(0)" : "translateX(100%)"}}>
                {activeEmail ? (
                    <ChatConversationView
                        interlocutorEmail={activeEmail}
                        currentUserEmail={currentUserEmail}
                        onBack={backToList}
                        onClosePanel={closePanel}
                        incomingEvent={lastEvent}
                        onRead={refreshDialogs}
                    />
                ) : (
                    <ChatDialogList dialogs={dialogs} onSelect={openConversation} onClose={closePanel}/>
                )}
            </div>
        </>
    );
};

export default ChatPanel;

const styles: Record<string, React.CSSProperties> = {
    overlay: {
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(23, 23, 23, 0.5)",
        zIndex: 1099,
        animation: "fadeIn 0.2s ease",
    },
    panel: {
        position: "fixed",
        top: 0,
        right: 0,
        width: 380,
        maxWidth: "100vw",
        height: "100%",
        backgroundColor: colors.canvasSoft,
        boxShadow: shadowLevel5,
        zIndex: 1100,
        transition: "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        display: "flex",
        flexDirection: "column",
    },
};