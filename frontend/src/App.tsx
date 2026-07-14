import {BrowserRouter, Routes, Route, Navigate} from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import TablesPage from './pages/TablePage';
import TableViewPage from './pages/TableViewPage';
import ProfilePage from './pages/ProfilePage';
import AboutPage from './pages/AboutPage';
import TrashPage from "./pages/TrashPage";
import {ChatProvider} from "./context/ChatContext";
import ChatPanel from "./components/ChatPanel";

console.log("App loaded");

function App() {
    return (
        <BrowserRouter>
            <ChatProvider>
                <Routes>
                    <Route path="/login" element={<LoginPage/>}/>
                    <Route path="/register" element={<RegisterPage/>}/>
                    <Route path="/tables" element={<TablesPage/>}/>
                    <Route path="/data/:id/rows" element={<TableViewPage/>}/>
                    <Route path="/profile" element={<ProfilePage/>}/>
                    <Route path="/about" element={<AboutPage/>}/>
                    <Route path="*" element={<Navigate to="/login"/>}/>
                    <Route path="/trash" element={<TrashPage/>}/>
                </Routes>
                <ChatPanel/>
            </ChatProvider>
        </BrowserRouter>
    );
}

export default App;