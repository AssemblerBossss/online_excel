package http

import (
	"time"
)

type CreateNotificationRequest struct {
	UserID    int64  `json:"user_id" validate:"required"`
	Channel   string `json:"channel" validate:"required,oneof=email push"`
	Recipient string `json:"recipient" validate:"required"`
	Subject   string `json:"subject" validate:"required" `
	Body      string `json:"body" validate:"required"`
}

type UpdateNotificationStatusRequest struct {
	Status string `json:"status"`
	Error  string `json:"error,omitempty"`
}

type NotificationResponse struct {
	ID        string     `json:"id"`
	UserID    int64      `json:"user_id"`
	Channel   string     `json:"channel"`
	Recipient string     `json:"recipient"`
	Subject   string     `json:"subject"`
	Body      string     `json:"body"`
	Status    string     `json:"status"`
	CreatedAt time.Time  `json:"created_at"`
	SentAt    *time.Time `json:"sent_at"`
	UpdatedAt time.Time  `json:"updated_at"`
	Error     *string    `json:"error"`
}

type ErrorResponse struct {
	Error string `json:"error"`
}

type ListNotificationsResponse struct {
	Items []*NotificationResponse `json:"items"`
}
