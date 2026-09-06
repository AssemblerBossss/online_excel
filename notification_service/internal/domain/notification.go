package domain

import (
	"errors"
	"time"
)

var ErrNotificationNotFound = errors.New("notification not found")

type NotificationStatus string

const (
	StatusPending    NotificationStatus = "pending"
	StatusProcessing NotificationStatus = "processing"
	StatusSent       NotificationStatus = "sent"
	StatusFailed     NotificationStatus = "failed"
)

type NotificationChannel string

const (
	ChannelEmail NotificationChannel = "email"
	ChannelPush  NotificationChannel = "push"
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
