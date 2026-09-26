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
		switch {
		case errors.Is(err, service.ErrInvalidUserID),
			errors.Is(err, service.ErrInvalidChannel),
			errors.Is(err, service.ErrInvalidRecipient),
			errors.Is(err, service.ErrInvalidSubject),
			errors.Is(err, service.ErrInvalidBody):
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
		default:
			writeJSON(w, http.StatusInternalServerError, ErrorResponse{
				Error: "failed to create notification",
			})
		}
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
}

func (h *Handler) UpdateNotificationStatus(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")

	if id == "" {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{
			Error: "invalid request body",
		})
		return
	}

	var req UpdateNotificationStatusRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid request body"})
		return
	}

	notification, err := h.service.Update(r.Context(), id,
		service.UpdateNotificationStatusInput{
			Status: domain.NotificationStatus(req.Status),
			Error:  req.Error,
		})

	if err != nil {
		switch {
		case errors.Is(err, domain.ErrNotificationNotFound):
			writeJSON(w, http.StatusNotFound, ErrorResponse{
				Error: err.Error(),
			})
		case errors.Is(err, domain.ErrInvalidStatus),
			errors.Is(err, domain.ErrInvalidTransition):
			writeJSON(w, http.StatusBadRequest, ErrorResponse{
				Error: err.Error(),
			})
		default:
			writeJSON(w, http.StatusInternalServerError, ErrorResponse{
				Error: "failed to update notification",
			})
		}
		return
	}

	writeJSON(w, http.StatusOK, toNotificationResponse(notification))
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

func toNotificationResponse(notification *domain.Notification) *NotificationResponse {
	return &NotificationResponse{
		ID:        notification.ID,
		UserID:    notification.UserID,
		Channel:   string(notification.Channel),
		Recipient: notification.Recipient,
		Subject:   notification.Subject,
		Body:      notification.Body,
		Status:    string(notification.Status),
		CreatedAt: notification.CreatedAt,
		UpdatedAt: notification.UpdatedAt,
		SentAt:    notification.SentAt,
		Error:     notification.Error,
	}
}

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)

	_ = json.NewEncoder(w).Encode(data)
}
