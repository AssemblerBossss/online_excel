package rabbitmq

import (
	"context"
	"errors"
	"notification_service/internal/config"
	"notification_service/internal/service"

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

	q, err := ch.QueueDeclare(c.cfg.Queue, true, false, false, false, amqp091.Table{"x-dead-letter-exchange": dlx})

	if err != nil {
		return err
	}

	for _, key := range c.cfg.RoutingKeys {
		if err := ch.QueueBind(q.Name, key, q.Name, false, nil); err != nil {
			return err
		}
	}

	if err := ch.Qos(
		10,    // prefetchCount: макс. неподтверждённых сообщений на консьюмера одновременно
		0,     // prefetchSize: лимит по байтам, 0 = без ограничения (RabbitMQ игнорирует ненулевой)
		false, // global: false = лимит на каждого консьюмера отдельно, true = на весь канал суммарно
	); err != nil {
		return err
	}

	msgs, err := ch.Consume(q.Name, "notification-service", false, false, false, false, nil)
	if err != nil {
		return err
	}
	closed := conn.NotifyClose(make(chan *amqp091.Error, 1))

	for {
		select {
		case <-ctx.Done():
			return nil
		case e, ok := <-closed:
			if !ok || e == nil {
				return errors.New("connection closed")
			}
		case m, ok := <-msgs:
			if !ok {
				return errors.New("delivery channel closed")
			}
			c.process(ctx, m)

		}
	}
}

func (c *Consumer) process(ctx context.Context, msg amqp091.Delivery) {
	eventType := msg.Type
	if eventType == "" {
		eventType = msg.RoutingKey
	}

	err := c.handler.Handle(ctx, eventType, msg.Body)
	switch {
	case err == nil, errors.Is(err, service.ErrUnsupportedEventType):
		msg.Ack(false)

		c.log.Error("malformed event -> DLQ", zap.String("type", eventType), zap.Error(err))
		_ = msg.Nack(false, false)

	default:
		// временная ошибка (БД недоступна и т.п.)
		c.log.Error("event handling failed, requeue", zap.String("type", eventType), zap.Error(err))
		_ = msg.Nack(false, true)
	}

}
