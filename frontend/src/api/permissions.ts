import {api} from './axiosInstance';

export interface TablePermission {
    id: number;
    user_id: number;
    table_id: number;
    user_email: string | null;
    can_read: boolean;
    can_write: boolean;
    can_manage: boolean;
    created_at: string;
}

export interface GrantPermissionPayload {
    email: string;
    can_read?: boolean;
    can_write?: boolean;
    can_manage?: boolean;
}

export interface UpdatePermissionPayload {
    can_read?: boolean;
    can_write?: boolean;
    can_manage?: boolean;
}

export const permissionsAPI = {
    list: async (tableId: number): Promise<TablePermission[]> => {
        const response = await api.get(`/tables/${tableId}/permissions/`);
        return response.data;
    },

    grant: async (tableId: number, payload: GrantPermissionPayload): Promise<TablePermission> => {
        const response = await api.post(`/tables/${tableId}/permissions/`, payload);
        return response.data;
    },

    update: async (
        tableId: number,
        targetUserId: number,
        payload: UpdatePermissionPayload,
    ): Promise<TablePermission> => {
        const response = await api.patch(`/tables/${tableId}/permissions/${targetUserId}`, payload);
        return response.data;
    },

    revoke: async (tableId: number, targetUserId: number): Promise<void> => {
        await api.delete(`/tables/${tableId}/permissions/${targetUserId}`);
    },
};