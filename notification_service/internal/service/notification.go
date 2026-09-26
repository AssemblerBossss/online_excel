package service

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"notification_service/internal/domain"
	"notification_service/internal/repository"

	"github.com/google/uuid"
)

var (
	ErrInvalidUserID    = errors.New("user ID is required")
	ErrInvalidChannel   = errors.New("invalid notification channel")
	ErrInvalidRecipient = errors.New("recipient is required")
	ErrInvalidSubject   = errors.New("subject is required")
	ErrInvalidBody      = errors.New("body is required")
)

type CreateNotificationInput struct {
	UserID    int64
	Channel   domain.NotificationChannel
	Recipient string
	Subject   string
	Body      string
}

type UpdateNotificationStatusInput struct {
	Status domain.NotificationStatus
	Error  string
}
type NotificationService struct {
	repository repository.NotificationRepository
}

func NewNotificationService(repository repository.NotificationRepository) *NotificationService {
	return &NotificationService{
		repository: repository,
	}
}
func (s *NotificationService) Create(
	ctx context.Context,
	req CreateNotificationInput,
) (*domain.Notification, error) {

	if err := validateCreateInput(req); err != nil {
		return nil, err
	}

	now := time.Now()

	notification := &domain.Notification{
		ID:        uuid.NewString(),
		UserID:    req.UserID,
		Channel:   req.Channel,
		Recipient: req.Recipient,
		Subject:   req.Subject,
		Body:      req.Body,
		Status:    domain.StatusPending,
		CreatedAt: now,
		UpdatedAt: now,
	}

	if err := s.repository.Create(ctx, notification); err != nil {
		return nil, fmt.Errorf("create notification: %w", err)
	}

	return notification, nil
}

func (s *NotificationService) GetByID(
	ctx context.Context,
	id string,
) (*domain.Notification, error) {
	id = strings.TrimSpace(id)

	if id == "" {
		return nil, errors.New("notification ID is required")
	}

	notification, err := s.repository.GetByID(ctx, id)
	if err != nil {
		return nil, fmt.Errorf("get notification: %w", err)
	}
	return notification, nil
}

func (s *NotificationService) Update(
	ctx context.Context,
	id string,
	input UpdateNotificationStatusInput,
) (*domain.Notification, error) {
	id = strings.TrimSpace(id)
	if id == "" {
		return nil, errors.New("notification ID is required")
	}

	notification, err := s.repository.GetByID(ctx, id)
	if err != nil {
		return nil, fmt.Errorf("get notification for update: %w", err)
	}

	if !isValidNotificationStatus(notification.Status) {
		return nil, domain.ErrInvalidStatus
	}
	if !notification.Status.CanTransitionTo(input.Status) {
		return nil, domain.ErrInvalidTransition
	}
	now := time.Now().UTC()

	notification.Status = input.Status
	notification.UpdatedAt = now

	switch input.Status {
	case domain.StatusSent:
		notification.SentAt = &now
		notification.Error = nil

	case domain.StatusFailed:
		if strings.TrimSpace(input.Error) != "" {
			notification.Error = &input.Error
		}
	}

	if err := s.repository.Update(ctx, notification); err != nil {
		return nil, fmt.Errorf("update notification: %w", err)
	}
	return notification, nil
}

func (s *NotificationService) List(ctx context.Context) ([]*domain.Notification, error) {
	notifications, err := s.repository.List(ctx)
	if err != nil {
		return nil, fmt.Errorf("get notification: %w", err)
	}
	return notifications, nil
}

func validateCreateInput(input CreateNotificationInput) error {
	if input.UserID <= 0 {
		return ErrInvalidUserID
	}

	switch input.Channel {
	case domain.ChannelEmail, domain.ChannelPush:
	default:
		return ErrInvalidChannel
	}

	if strings.TrimSpace(input.Recipient) == "" {
		return ErrInvalidRecipient
	}
	if strings.TrimSpace(input.Subject) == "" {
		return ErrInvalidSubject
	}
	if strings.TrimSpace(input.Body) == "" {
		return ErrInvalidBody
	}

	return nil
}

func isValidNotificationStatus(status domain.NotificationStatus) bool {
	switch status {
	case domain.StatusPending,
		domain.StatusProcessing,
		domain.StatusSent,
		domain.StatusFailed:
		return true
	default:
		return false

	}
}
