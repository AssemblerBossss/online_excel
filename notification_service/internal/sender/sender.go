package sender

import (
	"context"
	"notification_service/internal/domain"
)

type Sender interface {
	Send(ctx context.Context, notification *domain.Notification) error
}
