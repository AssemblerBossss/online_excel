package http

import (
	"notification_service/internal/domain"
	"time"
)

type CreateNotificationRequest struct {
	UserID    string                     `json:"user_id" validate:"required"`
	Channel   domain.NotificationChannel `json:"channel" validate:"required,oneof=email push"`
	Recipient string                     `json:"recipient" validate:"required"`
	Subject   string                     `json:"subject" validate:"required" `
	Body      string                     `json:"body" validate:"required"`
}
type NotificationResponse struct {
	ID        string                     `json:"id"`
	UserID    string                     `json:"user_id"`
	Channel   domain.NotificationChannel `json:"channel"`
	Recipient string                     `json:"recipient"`
	Subject   string                     `json:"subject"`
	Body      string                     `json:"body"`
	Status    string                     `json:"status"`
	CreatedAt time.Time                  `json:"created_at"`
	SentAt    *time.Time                 `json:"sent_at"`
}

type ErrorResponse struct {
	Error string `json:"error"`
}

type ListNotificationsResponse struct {
	Items []*NotificationResponse `json:"items"`
}
