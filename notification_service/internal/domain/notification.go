package domain

import "time"

type NotificationStatus string

const (
	StatusPending    NotificationStatus = "PENDING"
	StatusProcessing NotificationStatus = "PROCESSING"
	StatusSent       NotificationStatus = "SENT"
	StatusFailed     NotificationStatus = "FAILED"
)

type NotificationChannel string

const (
	ChannelEmail NotificationChannel = "EMAIL"
	ChannelPush  NotificationChannel = "PUSH"
)

type Notification struct {
	ID        string
	UserID    string
	Channel   NotificationChannel
	Status    NotificationStatus
	Recipient string
	Subject   string
	Body      string

	CreatedAt time.Time
	UpdatedAt time.Time
	SentAt    *time.Time
	Error     *error
}
