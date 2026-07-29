package service

import (
	"context"
	"notification_service/internal/domain"
	"notification_service/internal/repository"
	"time"

	"github.com/google/uuid"
)

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
	req CreateNotificationRequest,
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
	return notification, nill
}
