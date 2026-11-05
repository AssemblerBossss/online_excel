import {api} from './axiosInstance';


export interface DataTableResponse {
    id: number;
    name: string;
    description?: string;
    is_public?: boolean;
    created_by: number;
    created_at: string;
    updated_at?: string;
    is_deleted?: boolean;
    deleted_at?: string;
    is_pinned?: boolean;
}

export interface CreateTableRequest {
    name: string;
    description?: string;
    is_public?: boolean;
}

export interface UpdateTableRequest {
    name?: string;
    description?: string;
    is_public?: boolean;
}

export type ExportJobStatus = 'pending' | 'running' | 'completed' | 'error';

export interface ExportJobCreated {
    job_id: string;
    status: ExportJobStatus;
}

interface ExportResult {
    blob: Blob;
    filename: string;
}

export type ExportJobState = {
    job_id: string;
    status: ExportJobStatus;
    filename: string;
    download_url: string | null;
    error: string | null;
}


// Достаёт имя файла из заголовка Content-Disposition (поддержка filename*=UTF-8'')
function parseFilename(disposition: string): string | null {
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match) {
        return decodeURIComponent(utf8Match[1]);
    }
    const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
    return plainMatch ? plainMatch[1] : null;
}


export const tablesAPI = {
    getAllTables: async (): Promise<DataTableResponse[]> => {
        const response = await api.get('/tables');
        return response.data;
    },

    getTrash: async (): Promise<DataTableResponse[]> => {
        const response = await api.get(`/tables/trash/`);
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

    updateTable: async (id: number, data: UpdateTableRequest): Promise<DataTableResponse> => {
        const response = await api.patch(`/tables/${id}/`, data);
        return response.data;
    },

    duplicateTable: async (id: number, options: {
        name?: string;
        withRows?: boolean
    } = {}): Promise<DataTableResponse> => {
        const response = await api.post(`/tables/${id}/duplicate`, {
            name: options.name || null,
            with_rows: options.withRows ?? null,
        });
        return response.data;
    },

    permanentDelete: async (id: number): Promise<void> => {
        await api.delete(`/tables/trash/${id}/`);
    },

    restoreTable: async (id: number): Promise<void> => {
        const response = await api.post(`/tables/trash/${id}/restore/`);

    },

    searchTables: async (query: string, limit: number = 10): Promise<DataTableResponse[]> => {
        const response = await api.get('/search', {params: {q: query, limit}});
        return response.data;
    },

    startExport: async (tableId: number): Promise<ExportJobCreated> => {
        const response = await api.post(`/tables/${tableId}/export-jobs`, {})
        return response.data;
    },

    getExportStatus: async (jobId: string): Promise<ExportJobState> => {
        const {data} = await api.get<ExportJobState>(`/tables/export-jobs/${jobId}`);
        return data;
    },

    waitForExport: async (jobId: string, secondsBetween = 2, timeoutMs = 10 * 60_000): Promise<ExportJobState> => {
        const deadline = Date.now() + timeoutMs;
        while (Date.now() < deadline) {
            const state = await tablesAPI.getExportStatus(jobId);
            if (state.status === 'completed' || state.status === 'error') return state;
            await new Promise(r => setTimeout(r, secondsBetween * 1000));
        }
        throw new Error('Экспорт не завершился за отведённое время');
    },

    pinTable: async (id: number): Promise<void> => {
        await api.post(`/tables/${id}/pin`);
    },

    unpinTable: async (id: number): Promise<void> => {
        await api.delete(`/tables/${id}/pin`);
    },
};
