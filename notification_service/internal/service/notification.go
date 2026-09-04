package service

import (
	"context"
	"fmt"
	"notification_service/internal/domain"
	"notification_service/internal/repository"
	"time"

	"github.com/google/uuid"
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
		return nil, err
	}
	return notification, nil
}

func (s *NotificationService) GetByID(
	ctx context.Context,
	id string,
) (*domain.Notification, error) {
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
