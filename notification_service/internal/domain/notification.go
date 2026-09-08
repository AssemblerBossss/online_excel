package domain

import (
	"errors"
	"time"
)

var (
	ErrNotificationNotFound = errors.New("notification not found")
	ErrInvalidStatus        = errors.New("invalid notification status")
	ErrInvalidTransition    = errors.New("invalid notification transition")
)

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
	Error     *string
}

// CanTransitionTo returns true if the current status can transition to the given status.
func (s NotificationStatus) CanTransitionTo(next NotificationStatus) bool {
	switch s {
	case StatusPending:
		return next == StatusProcessing
	case StatusProcessing:
		return next == StatusSent || next == StatusFailed
	case StatusSent, StatusFailed:
		return false
	default:
		return false
	}
}
