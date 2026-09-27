package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"notification_service/internal/domain"
	"notification_service/internal/events"
	"notification_service/internal/sender"
)

var (
	ErrUnsupportedEventType = errors.New("unsupported event type")
	ErrMalformedEvent       = errors.New("malformed event payload")
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

func (h *EventHandler) handlerUserRegistered(ctx context.Context, body []byte) error {
	var event events.UserRegistered
	if err := json.Unmarshal(body, &event); err != nil {
		return fmt.Errorf("%w: %v", ErrMalformedEvent, err)
	}
	n, err := h.notifications.Create(ctx, CreateNotificationInput{
		UserID:    event.UserID,
		Channel:   domain.ChannelEmail,
		Recipient: event.Email,
		Subject:   "Добро пожаловать в Online Excel",
		Body:      welcomeBody(event.FirstName),
		DedupKey:  "user.registered" + event.EventID,
	})
	if errors.Is(err, domain.ErrDuplicateNotification) {
		return nil
	}
	if err != nil {
		return err
	}
	return h.notifications.Dispatch(ctx, n.ID, h.sender)

}
