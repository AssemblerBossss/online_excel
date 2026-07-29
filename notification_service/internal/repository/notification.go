package repository

import (
	"context"

	"notification_service/internal/domain"
)

type NotificationRepository interface {
	Create(ctx context.Context, notification *domain.Notification) error
	GetByID(ctx context.Context, id string) (*domain.Notification, error)
	List(ctx context.Context) ([]*domain.Notification, error)
}
