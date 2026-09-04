package config

import "time"

type Config struct {
	Server ServerConfig `yaml:"server"`
	Logger LoggerConfig `yaml:"logger"`

	Postgres PostgresConfig `yaml:"postgres"`
	RabbitMQ RabbitMQConfig `yaml:"rabbitmq"`
}

type ServerConfig struct {
	Host            string        `yaml:"host" env:"SERVER_HOST" env-default:"localhost"`
	Port            int           `yaml:"port" env:"SERVER_PORT", env-default:"8080"`
	ShutdownTimeout time.Duration `yaml:"shutdown_timeout" env:SERVER_SHUTDOWN_TIMEOUT" env-default:"10s""`
}

type LoggerConfig struct {
	Level       string `yaml:"level" env:"LOG_LEVEL" env-default:"info"`
	Development bool   `yaml:"development" env:"LOG_DEVELOPMENT" env-default:"false"`
}

type PostgresConfig struct {
	Host           string `yaml:"host" env:"POSTGRES_HOST" env-default:"localhost"`
	Port           int    `yaml:"port" env:"POSTGRES_PORT" env-default:"5432"`
	Database       string `yaml:"database" env:"POSTGRES_DB" env-default:"notification_db"`
	Username       string `yaml:"username" env:"POSTGRES_USER" env-default:"postgres"`
	Password       string `yaml:"password" env:"POSTGRES_PASSWORD" env-default:"postgres"`
	SSLMode        string `yaml:"ssl_mode" env:"POSTGRES_SSL_MODE" env-default:"disable"`
	MaxConnections int32  `yaml:"max_connections" env:"POSTGRES_MAX_CONNECTIONS" env-default:"20"`
	MinConnections int32  `yaml:"min_connections" env:"POSTGRES_MIN_CONNECTIONS" env-default:"1"`
}

type RabbitMQConfig struct {
	Host       string `yaml:"host" env:"RABBITMQ_HOST" env-default:"localhost"`
	Port       int    `yaml:"port" env:"RABBITMQ_PORT" env-default:"5672"`
	Username   string `yaml:"username" env:"RABBITMQ_USER" env-default:"guest"`
	Password   string `yaml:"password" env:"RABBITMQ_PASSWORD" env-default:"guest"`
	Exchange   string `yaml:"exchange" env-default:"user.events"`
	Queue      string `yaml:"queue" env-default:"notification.events"`
	RoutingKey string `yaml:"routing_key" env-default:"user.*"`
}
