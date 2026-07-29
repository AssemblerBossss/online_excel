package domain

import "time"

type NotificationStatus string

const StatusPending NotificationStatus = "PENDING"
const StatusProcessing NotificationStatus = "PROCESSING"
const StatusSent NotificationStatus = "SENT"
const StatusFailed NotificationStatus = "FAILED"

type NotificationChannel string

const ChannelEmail NotificationChannel = "EMAIL"
const ChannelPush NotificationChannel = "PUSH"

type Notification struct {
	ID      string
	UserID  string
	Channel NotificationChannel
	Status  NotificationStatus
	Body    string

	CreatedAt time.Time
	UpdatedAt time.Time
	SentAt    *time.Time
	Error     *error
}
