package events

import (
	"strings"
	"time"
)

type UserRegistered struct {
	EventID   string    `json:"event_id"`
	UserID    int64     `json:"user_id"`
	Email     string    `json:"email"`
	FirstName string    `json:"first_name"`
	Role      string    `json:"role"`
	Timestamp time.Time `json:"timestamp"`
}

func NormalizeRole(role string) string {
	if i := strings.LastIndex(".", role); i >= 0 {
		return role[i+1:]
	}
	return role
}
