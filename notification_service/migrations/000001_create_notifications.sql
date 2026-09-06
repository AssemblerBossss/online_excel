-- +goose Up

CREATE TABLE notifications (
    id         UUID        PRIMARY KEY DEFAULT uuidv7(),
    user_id    BIGINT      NOT NULL,
    channel    TEXT        NOT NULL,
    status     TEXT        NOT NULL,
    recipient  TEXT        NOT NULL,
    subject    TEXT        NOT NULL,
    body       TEXT        NOT NULL,
    body       TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    sent_at    TIMESTAMPTZ,
    error      TEXT
)

CREATE INDEX idx_notifications_user
    ON notifications(user_id);

CREATE INDEX idx_notifications_created
    ON notifications(created_at DESC);
