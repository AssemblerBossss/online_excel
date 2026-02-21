import { api } from './axiosInstance';

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

export interface CreateTableRequest {
  name: string;
  description?: string;
  is_public?: boolean;
  columns_schema?: ColumnSchema[];
}

export const tablesAPI = {
  // Получить все таблицы
  getAllTables: async (): Promise<DataTableResponse[]> => {
    const response = await api.get('/tables');
    return response.data;
  },

  // Создать новую таблицу - используем правильный эндпоинт
  createTable: async (data: CreateTableRequest): Promise<DataTableResponse> => {
    const response = await api.post('/tables/create', data);
    return response.data;
  },

  // Получить таблицу по ID
  getTableById: async (id: number): Promise<DataTableResponse> => {
    const response = await api.get(`/data/${id}/rows`);
    return response.data;
  },

  // Удалить таблицу - нужно добавить этот эндпоинт на бэкенде
  deleteTable: async (id: number): Promise<void> => {
    await api.delete(`/tables/delete/${id}`);
  },

  // Обновить таблицу - нужно добавить этот эндпоинт на бэкенде
  updateTable: async (id: number, data: Partial<CreateTableRequest>): Promise<DataTableResponse> => {
    const response = await api.put(`/tables/${id}`, data);
    return response.data;
  }
};