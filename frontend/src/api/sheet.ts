import { api } from './axiosInstance';
import type {SheetBatch, SheetBatchResult, SheetSnapshot} from '../sheet/types'

export const sheetAPI = {
    getSheet: async (tableId: number): Promise<SheetSnapshot> => {
        const response = await api.get(`/data/${tableId}/sheet`);
        return response.data;
    },

    applyBatch: async (tableId: number, batch: SheetBatch): Promise<SheetBatchResult> => {
        const response = await api.post(`/data/${tableId}/sheet/batch`, batch);
        return response.data;
    }
    
}