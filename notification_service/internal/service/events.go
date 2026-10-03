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

func NewEventHandler(notifications *NotificationService, sender sender.Sender) *EventHandler {
	return &EventHandler{notifications: notifications, sender: sender}
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

	if event.EventID == "" {
		return fmt.Errorf("%w: event_id is required", ErrMalformedEvent)
	}

	dedupKey := "user.registered:" + event.EventID

	n, err := h.notifications.Create(ctx, CreateNotificationInput{
		UserID:    event.UserID,
		Channel:   domain.ChannelEmail,
		Recipient: event.Email,
		Subject:   "Добро пожаловать в Online Excel",
		Body:      welcomeBody(event.FirstName),
		DedupKey:  dedupKey,
	})

	if errors.Is(err, domain.ErrDuplicateNotification) {
		return h.redispatch(ctx, dedupKey)
	}
	if err != nil {
		return err
	}
	return h.notifications.Dispatch(ctx, n.ID, h.sender)
}

// redispatch обрабатывает повторную доставку события: уведомление уже создано
// прошлой попыткой. Досылаем, если письмо ещё не ушло.
func (h *EventHandler) redispatch(ctx context.Context, dedupKey string) error {
	existing, err := h.notifications.GetByDedupKey(ctx, dedupKey)
	if err != nil {
		return err
	}

	switch existing.Status {
	case domain.StatusSent:
		return nil
	case domain.StatusProcessing:
		// Прошлая попытка умерла посреди Send: ушло письмо или нет, неизвестно.
		// Выбираем «не задублировать», а не «точно доставить».
		return nil
	default: // pending, failed
		return h.notifications.Dispatch(ctx, existing.ID, h.sender)
	}
}

func welcomeBody(firstName string) string {
	if firstName == "" {
		return "Здравствуйте!\n\nВы успешно зарегистрировались в Online Excel."
	}
	return fmt.Sprintf("Здравствуйте, %s!\n\nВы успешно зарегистрировались в Online Excel.", firstName)
}
