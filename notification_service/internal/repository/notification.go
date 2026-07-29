package repository

import "context"

type NotificationRepository interface {
	Create(ctx context.Context, notification *NotificationStub) error
	GetByID(ctx context.Context, id string) (*NotificationStub, error)
	List(ctx context.Context) []*NotificationStub
}
