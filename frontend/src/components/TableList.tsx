import {useEffect, useState} from "react";
import {getTables} from "../api/tables";

export default function TableList() {
    const [tables, setTables] = useState<any[]>([]);

    useEffect(() => {
        getTables().then(setTables).catch(console.error);
    }, []);

    return (
        <div>
            <h2>Мои таблицы</h2>
            <ul>
                {tables.map((t) => (
                    <li key={t.id}>{t.name}</li>
                ))}
            </ul>
        </div>
    );
}
