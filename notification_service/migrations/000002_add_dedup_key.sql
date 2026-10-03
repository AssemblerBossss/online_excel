-- +goose Up


ALTER TABLE notifications ADD COLUMN dedup_key TEXT;

CREATE UNIQUE INDEX uq_notifications_dedup_key ON
    notifications (dedup_key);



-- +goose Down


DROP INDEX IF EXISTS uq_notifications_dedup_key;
ALTER TABLE notifications DROP COLUMN IF EXISTS dedup_key;