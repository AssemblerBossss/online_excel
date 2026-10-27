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
}