package service

import (
	"context"
	"errors"
)

var (
	ErrUnsupportedEventType = errors.New("unsupported event type")
)

type EventHandler struct {
	notifications *NotificationService
	sender        sender.Sender
}

func (h *EventHandler) Handle(ctx context.Context, eventType string, body []byte) error {
	switch eventType {
	case "user.registered":
		return h.handlerUserRegistered(ctx, body)
	default:
		return ErrUnsupportedEventType
	}
}
