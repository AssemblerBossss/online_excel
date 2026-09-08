package service

import (
	"context"
	"notification_service/internal/domain"
	"notification_service/internal/repository/memory"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestNotificationService_Create(t *testing.T) {
	repository := memory.NewNotificationRepository()
	service := NewNotificationService(repository)

	input := CreateNotificationInput{
		UserID:    "42",
		Channel:   domain.ChannelEmail,
		Recipient: "user@example.com",
		Subject:   "Welcome",
		Body:      "Your account has been created",
	}

	notification, err := service.Create(context.Background(), input)

	require.NoError(t, err)
	require.NotNil(t, notification)

	require.NotEmpty(t, notification.ID)

	require.Equal(t, "42", notification.UserID)
	require.Equal(t, domain.ChannelEmail, notification.Channel)
	require.Equal(t, domain.StatusPending, notification.Status)
	require.Equal(t, "user@example.com", notification.Recipient)
	require.Equal(t, "Welcome", notification.Subject)
	require.Equal(t, "Your account has been created", notification.Body)

	require.False(t, notification.CreatedAt.IsZero())
	require.False(t, notification.UpdatedAt.IsZero())
}

func TestNotificationService_Create_InvalidInput(t *testing.T) {
	tests := []struct {
		name  string
		input CreateNotificationInput
		err   error
	}{
		{
			name: "empty user id",
			input: CreateNotificationInput{
				UserID:    "",
				Channel:   domain.ChannelEmail,
				Recipient: "user@example.com",
				Subject:   "Welcome",
				Body:      "Hello",
			},
			err: ErrInvalidUserID,
		},
		{
			name: "invalid channel",
			input: CreateNotificationInput{
				UserID:    "42",
				Channel:   "sms",
				Recipient: "user@example.com",
				Subject:   "Welcome",
				Body:      "Hello",
			},
			err: ErrInvalidChannel,
		},
		{
			name: "empty recipient",
			input: CreateNotificationInput{
				UserID:    "42",
				Channel:   domain.ChannelEmail,
				Recipient: "",
				Subject:   "Welcome",
				Body:      "Hello",
			},
			err: ErrInvalidRecipient,
		},
		{
			name: "empty subject",
			input: CreateNotificationInput{
				UserID:    "42",
				Channel:   domain.ChannelEmail,
				Recipient: "user@example.com",
				Subject:   "",
				Body:      "Hello",
			},
			err: ErrInvalidSubject,
		},
		{
			name: "empty body",
			input: CreateNotificationInput{
				UserID:    "42",
				Channel:   domain.ChannelEmail,
				Recipient: "user@example.com",
				Subject:   "Welcome",
				Body:      "",
			},
			err: ErrInvalidBody,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			repository := memory.NewNotificationRepository()
			service := NewNotificationService(repository)

			notification, err := service.Create(
				context.Background(),
				tt.input,
			)

			require.Error(t, err)
			require.ErrorIs(t, err, tt.err)
			require.Nil(t, notification)
		})
	}
}

func TestNotificationService_GetByID(t *testing.T) {
	repository := memory.NewNotificationRepository()
	service := NewNotificationService(repository)

	input := CreateNotificationInput{
		UserID:    "42",
		Channel:   domain.ChannelEmail,
		Recipient: "user@example.com",
		Subject:   "Welcome",
		Body:      "Hello",
	}

	created, err := service.Create(
		context.Background(),
		input,
	)

	require.NoError(t, err)

	found, err := service.GetByID(
		context.Background(),
		created.ID,
	)

	require.NoError(t, err)
	require.NotNil(t, found)

	require.Equal(t, created.ID, found.ID)
	require.Equal(t, created.UserID, found.UserID)
	require.Equal(t, created.Channel, found.Channel)
	require.Equal(t, created.Status, found.Status)
	require.Equal(t, created.Recipient, found.Recipient)
	require.Equal(t, created.Subject, found.Subject)
	require.Equal(t, created.Body, found.Body)
}
