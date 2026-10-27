import type { SheetEvent } from './types';

const GAP_TIMEOUT_MS = 2_000;

export class EventSequencer {
    private expected:  number | null = null;
    private buffer = new Map<number, SheetEvent>();
    private gapTimer: number | null = null;

    constructor(
        private readonly apply: (event: SheetEvent) => void,
        private readonly onGap: () => void
    ) {}

    reset(revision: number): void {
        this.expected  = revision + 1;
        for (const key of Array.from(this.buffer.keys())) {
            if (key < this.expected) this.buffer.delete(key);
        }
        this.drain();
    }

    private drain(): void {
        if (this.expected === null) return;
        for (let next = this.buffer.get(this.expected); next;
         next = this.buffer.get(this.expected)) {
            this.buffer.delete(this.expected);
            this.expected +=1;
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