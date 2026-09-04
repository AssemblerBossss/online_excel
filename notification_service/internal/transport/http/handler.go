package http

import (
	"encoding/json"
	"net/http"
	"notification_service/internal/domain"

	"notification_service/internal/service"
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

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)

	_ = json.NewEncoder(w).Encode(data)
}
