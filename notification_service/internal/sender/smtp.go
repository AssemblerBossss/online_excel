package sender

import (
	"context"
	"fmt"
	"mime"
	"net/smtp"
	"notification_service/internal/config"
	"notification_service/internal/domain"
)

type SMTPSender struct{ cfg config.SMTPConfig }

func (s *SMTPSender) Send(ctx context.Context, notification *domain.Notification) error {
	addr := fmt.Sprintf("%s:%d", s.cfg.Host, s.cfg.Port)
	msg := []byte("From: " + s.cfg.From + "\r\n" +
		"To: " + notification.Recipient + "\r\n" +
		"Subject: " + mime.QEncoding.Encode("utf-8", notification.Subject) + "\r\n" +
		"MIME-Version: 1.0\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n" +
		notification.Body)

	var auth smtp.Auth
	if s.cfg.Username != "" {
		auth = smtp.PlainAuth("", s.cfg.Username, s.cfg.Password, s.cfg.Host)
	}

	return smtp.SendMail(addr, auth, s.cfg.From, []string{notification.Recipient}, msg)
}
