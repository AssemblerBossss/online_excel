import { cellKey, CellKey } from './address';
import type { CellWrite, EngineResult, SheetMeta, StructuralOp, StyleWrite} from './types';


const CHUNK = 5_000;

export interface OutgoingBatch {
    structural: StructuralOp | null;
    cells: CellWrite[];
    styles: StyleWrite[];
    meta: SheetMeta |  null;
}

interface PendingItem {
    structural : StructuralOp | null;
    cells:  Map<number, CellWrite>;
    styles: Map<number, StyleWrite>;
    meta: SheetMeta | null;
}

export interface SyncQueueHandlers {
    send: (batch: OutgoingBatch) => Promise<void>;
    onConflict: () => void;
    onError: (error: unknown) => void;
    onBusyChange: (busy: boolean) => void;
}

const newItem = (structural: StructuralOp | null): PendingItem => ({
    structural,
    cells: new Map(),
    styles: new Map(),
    meta: null,
});

export class SyncQueue {
    private items: PendingItem[] = [];
    private busy = false;

    constructor(private readonly handlers:  SyncQueueHandlers) {}

    push(change: EngineResult): void {
        let tail = this.items[this.items.length -1];
        if (change.structural || !tail) {
            tail = newItem(change.structural ?? null);
            this.items.push(tail);
        }

        for (const cell of change.cells) tail.cells.set(cellKey(cell.row, cell.col), cell);
        for (const style of change.styles) tail.styles.set(cellKey(style.row, style.col), style);
        if (change.meta) tail.meta =  change.meta;
        void this.pump();
    }

    clear(): void { 
        this.items = [];
    }

    private async pump(): Promise<void> {
        if (this.busy) return;
        this.busy = true;
        this.handlers.onBusyChange(true);
        try {
            while (this.items.length) {
                await this.sendItem(this.items.shift()!)
            }
        } catch (error) {
            if ((error as {response?: {status?: number}})?.response?.status === 409) {
                this.handlers.onError(error);
            }
        } finally {
            this.busy = false;
            this.handlers.onBusyChange(false);
        }
    }

    private async sendItem(item: PendingItem): Promise<void> {
        
    }
}