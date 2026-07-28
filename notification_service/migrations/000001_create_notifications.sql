-- +goose Up

CREATE TABLE notifications (
    id          UUID PRIMARY KEY DEFAULT uuidv7(),
    user_id     BIGINT NOT NULL,
    type        TEXT NOT NULL,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPZ NOT NULL DEFAULT now(),
    read_at     TIMESTAMPZ
)

CREATE INDEX idx_notifications_user
    ON notifications(user_id);

CREATE INDEX idx_notifications_created
    ON notifications(created_at DESC);

-- +goose Down

DROP TABLE notifications;