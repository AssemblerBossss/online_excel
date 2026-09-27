package rabbitmq

import (
	"context"
	"notification_service/internal/config"

	"github.com/rabbitmq/amqp091-go"
	"go.uber.org/zap"
)

type Handler interface {
	Handle(cxt context.Context, eventType string, body []byte) error
}
type Consumer struct {
	cfg     config.RabbitMQConfig
	handler Handler
	log     *zap.Logger
}

func (c *Consumer) consume(ctx context.Context) error {
	conn, err := amqp091.Dial(c.cfg.URL())
	if err != nil {
		return err
	}
	defer conn.Close()

	ch, err := conn.Channel()
	if err != nil {
		return err
	}
	defer ch.Close()

	if err := ch.ExchangeDeclare(
		c.cfg.Exchange,
		"topic",
		true,
		false,
		false,
		false,
		nil,
	); err != nil {
		return err
	}

	dlx := c.cfg.Exchange + ".dlx"
	dlq := c.cfg.Queue + ".dlq"

	if err := ch.ExchangeDeclare(dlx, "fanout", true, false, false, false, nil); err != nil {
		return err
	}
	if _, err := ch.QueueDeclare(dlq, true, false, false, false, nil); err != nil {
		return err
	}
	if err := ch.QueueBind(dlq, "", dlx, false, nil); err != nil {
		return err
	}

	q, err := ch.QueueDeclare(c.cfg.Queue, true, false, false, false, amqp091.Table{"x-dead-letter-exchange": dlx}))
}
