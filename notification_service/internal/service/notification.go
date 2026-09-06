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
	UserID    string
	Channel   domain.NotificationChannel
	Recipient string
	Subject   string
	Body      string
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

func (s *NotificationService) List(ctx context.Context) ([]*domain.Notification, error) {
	notifications, err := s.repository.List(ctx)
	if err != nil {
		return nil, fmt.Errorf("get notification: %w", err)
	}
	return notifications, nil
}

func validateCreateInput(input CreateNotificationInput) error {
	if strings.TrimSpace(input.UserID) == "" {
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
