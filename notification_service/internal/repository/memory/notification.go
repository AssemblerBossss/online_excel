package memory

import (
	"context"
	"errors"
	"notification_service/internal/domain"
	"sync"
)

type NotificationRepository struct {
	mu   sync.RWMutex
	data map[string]*domain.Notification
}

func NewNotificationRepository() *NotificationRepository {
	return &NotificationRepository{
		data: make(map[string]*domain.Notification),
	}
}

func (r *NotificationRepository) Create(ctx context.Context, notification *domain.Notification) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.data[notification.ID] = notification
	return nil
}

func (r *NotificationRepository) GetByID(ctx context.Context, id string) (*domain.Notification, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	notification, ok := r.data[id]
	if !ok {
		return nil, errors.New("notification not found")
	}
	return notification, nil
}

func (r *NotificationRepository) List(ctx context.Context) ([]*domain.Notification, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	result := make([]*domain.Notification, 0, len(r.data))

	for _, notification := range r.data {
		result = append(result, notification)
	}
	return result, nil
}
