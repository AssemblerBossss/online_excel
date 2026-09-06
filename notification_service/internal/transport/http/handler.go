package http

import (
	"encoding/json"
	"errors"
	"net/http"
	"notification_service/internal/domain"

	"notification_service/internal/service"

	"github.com/go-chi/chi/v5"
)

type Handler struct {
	service *service.NotificationService
}

func NewHandler(service *service.NotificationService) *Handler {
	return &Handler{service: service}
}

func (h *Handler) CreateNotification(w http.ResponseWriter, r *http.Request) {
	var req CreateNotificationRequest

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid request body"})
		return
	}

	if err := validateCreateNotificationRequest(req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
		return
	}

	notification, err := h.service.Create(
		r.Context(),
		service.CreateNotificationInput{
			UserID:    req.UserID,
			Channel:   domain.NotificationChannel(req.Channel),
			Recipient: req.Recipient,
			Subject:   req.Subject,
			Body:      req.Body,
		},
	)

	if err != nil {
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{
			Error: "failed to create notification",
		})
		return
	}
	writeJSON(w, http.StatusCreated, toNotificationResponse(notification))
}

func (h *Handler) GetNotification(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")

	if id == "" {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{
			Error: "invalid request body",
		})
		return
	}

	notification, err := h.service.GetByID(r.Context(), id)
	if err != nil {
		if errors.Is(err, domain.ErrNotificationNotFound) {
			writeJSON(w, http.StatusNotFound, ErrorResponse{
				Error: "notification not found",
			})
			return
		}
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{
			Error: "failed to get notification",
		})
		return
	}
	writeJSON(w, http.StatusOK, toNotificationResponse(notification))
	return
}

func (h *Handler) ListNotifications(w http.ResponseWriter, r *http.Request) {
	notifications, err := h.service.List(r.Context())
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{
			Error: "failed to list notifications",
		})
		return
	}

	items := make([]*NotificationResponse, 0, len(notifications))
	for _, notification := range notifications {
		items = append(items, toNotificationResponse(notification))
	}
	writeJSON(w, http.StatusOK, ListNotificationsResponse{Items: items})

}
func validateCreateNotificationRequest(req CreateNotificationRequest) error {
	if req.UserID == "" {
		return errors.New("missing user ID")
	}
	if req.Recipient == "" {
		return errors.New("recipient is required")
	}
	if req.Subject == "" {
		return errors.New("subject is required")
	}
	if req.Body == "" {
		return errors.New("body is required")
	}
	if req.Channel != string(domain.ChannelEmail) &&
		req.Channel != string(domain.ChannelPush) {
		return errors.New("invalid channel")
	}
	return nil
}

func toNotificationResponse(notification *domain.Notification) *NotificationResponse {
	return &NotificationResponse{
		ID:        notification.ID,
		UserID:    notification.UserID,
		Channel:   string(notification.Channel),
		Recipient: notification.Recipient,
		Subject:   notification.Subject,
		Body:      notification.Body,
		CreatedAt: notification.CreatedAt,
		SentAt:    notification.SentAt,
	}
}

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)

	_ = json.NewEncoder(w).Encode(data)
}
