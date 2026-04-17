import {api} from './axiosInstance';

export interface ColumnSchema {
    name: string;
    type: string;
    required?: boolean;
}

export interface DataTableResponse {
    id: number;
    name: string;
    description?: string;
    is_public?: boolean;
    columns_schema?: ColumnSchema[];
    created_by: number;
    created_at: string;
    updated_at?: string;
}

export interface TableRow {
    id: number;
    table_id: number;
    row_data: Record<string, any>;
    created_at: string;
    updated_at?: string;
}

export interface CreateTableRequest {
    name: string;
    description?: string;
    is_public?: boolean;
    columns_schema?: ColumnSchema[];
}

export const tablesAPI = {
    getAllTables: async (): Promise<DataTableResponse[]> => {
        const response = await api.get('/tables');
        return response.data;
    },

    createTable: async (data: CreateTableRequest): Promise<DataTableResponse> => {
        const response = await api.post('/tables/create', data);
        return response.data;
    },

    getTableById: async (id: number): Promise<DataTableResponse> => {
        const response = await api.get(`/tables/${id}`);
        return response.data;
    },

    deleteTable: async (id: number): Promise<void> => {
        await api.delete(`/tables/delete/${id}`);
    },

    getTableRows: async (tableId: number): Promise<TableRow[]> => {
        const response = await api.get(`/data/${tableId}/rows`);
        return response.data;
    },

    createRow: async (tableId: number, rowData: Record<string, any>): Promise<TableRow> => {
        const response = await api.post(`/data/${tableId}/rows`, {row_data: rowData});
        return response.data;
    },

    updateRow: async (tableId: number, rowId: number, rowData: Record<string, any>): Promise<TableRow> => {
        const response = await api.put(`/data/${tableId}/rows/${rowId}`, {row_data: rowData});
        return response.data;
    },

    deleteRow: async (tableId: number, rowId: number): Promise<void> => {
        await api.delete(`/data/${tableId}/rows/${rowId}`);
    },

    searchTables: async(query: string, limit: number = 10): Promise<DataTableResponse[]> => {
        const response = await api.get('/search/', { params: { q: query, limit } });
        return response.data;
    },
};