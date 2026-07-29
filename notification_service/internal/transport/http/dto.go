package http

import "notification_service/internal/domain"

type CreateNotificationRequest struct {
	UserID    string
	Channel   domain.NotificationChannel
	Recipient string
	Subject   string
	Body      string
}
