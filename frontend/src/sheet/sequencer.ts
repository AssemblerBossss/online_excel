import type {SheetEvent} from './types';

const GAP_TIMEOUT_MS = 2_000;

/**
 * Выстраивает события WS строго по revision. Если очередное событие не пришло
 * за GAP_TIMEOUT_MS, вызывает onGap (клиент перечитывает снимок).
 */
export class EventSequencer {
    private expected: number | null = null;
    private buffer = new Map<number, SheetEvent>();
    private gapTimer: number | null = null;

    constructor(
        private readonly apply: (event: SheetEvent) => void,
        private readonly onGap: () => void,
    ) {}

    /** Снимок загружен на ревизии `revision`: ждём revision + 1. */
    reset(revision: number): void {
        this.expected = revision + 1;
        for (const key of Array.from(this.buffer.keys())) {
            if (key < this.expected) this.buffer.delete(key);
        }
        this.drain();
    }

    push(event: SheetEvent): void {
        if (this.expected !== null && event.revision < this.expected) return;
        this.buffer.set(event.revision, event);
        this.drain();
    }

    dispose(): void {
        if (this.gapTimer) window.clearTimeout(this.gapTimer);
        this.gapTimer = null;
        this.buffer.clear();
    }

    private drain(): void {
        if (this.expected === null) return;
        for (let next = this.buffer.get(this.expected); next; next = this.buffer.get(this.expected)) {
            this.buffer.delete(this.expected);
            this.expected += 1;
            this.apply(next);
        }
        if (this.buffer.size === 0) {
            if (this.gapTimer) window.clearTimeout(this.gapTimer);
            this.gapTimer = null;
        } else if (this.gapTimer === null) {
            this.gapTimer = window.setTimeout(() => {
                this.gapTimer = null;
                if (this.buffer.size > 0) this.onGap();
            }, GAP_TIMEOUT_MS);
        }
    }
}
