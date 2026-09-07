package postgres

import (
	"context"
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"notification_service/internal/domain"
	"notification_service/internal/repository"
)

var _ repository.NotificationRepository = (*NotificationRepository)(nil)

type NotificationRepository struct {
	db *pgxpool.Pool
}

func NewNotificationRepository(db *pgxpool.Pool) *NotificationRepository {
	return &NotificationRepository{
		db: db,
	}
}

func (r *NotificationRepository) Create(ctx context.Context, notification *domain.Notification) error {
	const query = `
		INSERT INTO notifications (
			id,
			user_id,
			channel,
			status,
			recipient,
			subject,
			body,
			created_at,
			updated_at,
			sent_at,
			error
		)
		VALUES (
			$1,
			$2,
			$3,
			$4,
			$5,
			$6,
			$7,
			$8,
			$9,
			$10,
			$11
		)
		`
	var errorMessage *string

	if notification.Error != nil {
		errorMessage = new((*notification.Error).Error())
	}

	_, err := r.db.Exec(ctx,
		query,
		notification.ID,
		notification.UserID,
		notification.Channel,
		notification.Status,
		notification.Recipient,
		notification.Subject,
		notification.Body,
		notification.CreatedAt,
		notification.UpdatedAt,
		notification.SentAt,
		errorMessage,
	)

	if err != nil {
		return fmt.Errorf("insert notification: %w", err)
	}
	return nil
}

func (r *NotificationRepository) GetByID(ctx context.Context, id string) (*domain.Notification, error) {
	const query = `
		SELECT 
		    id,
		    user_id,
    channel,    
    status,   
    recipient,  
    subject ,  
    body,            
    created_at,
    updated_at, 
    sent_at,
    error   
FROM notifications
		WHERE id = $1
		`

	var notification domain.Notification
	var errorMessage *string

	err := r.db.QueryRow(ctx, query, id).Scan(
		&notification.ID,
		&notification.UserID,
		&notification.Channel,
		&notification.Status,
		&notification.Recipient,
		&notification.Subject,
		&notification.Body,
		&notification.CreatedAt,
		&notification.UpdatedAt,
		&notification.SentAt,
		&errorMessage)

	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrNotificationNotFound
		}
		return nil, fmt.Errorf("get notification: %w", err)
	}

	if errorMessage != nil {
		err := errors.New(*errorMessage)
		notification.Error = &err
	}

	return &notification, nil
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
