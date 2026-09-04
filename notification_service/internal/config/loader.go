package config

import (
	"fmt"

	"github.com/ilyakaznacheev/cleanenv"
)

// Load reads and parses the config file at path into a Config struct.
// Supports environment variables with NOTIFICATION_ prefix.
func Load(path string) (Config, error) {
	var cfg Config

	if err := cleanenv.ReadConfig(path, &cfg); err != nil {
		return Config{}, fmt.Errorf("read config: %w", err)
	}

	if cfg.Postgres.MaxConnections < 1 {
		return Config{}, fmt.Errorf("postgres max connections must be greater than zero")
	}

	if cfg.Postgres.MinConnections < 1 {
		return Config{}, fmt.Errorf("postgres min connections must be greater than zero")
	}

	if cfg.Postgres.MinConnections > cfg.Postgres.MaxConnections {
		return Config{}, fmt.Errorf("postgres max connections must be greater than or equal to max connections")
	}
	return cfg, nil
}

// DSN returns a PostgreSQL connection string.
func (c PostgresConfig) DSN() string {

	return fmt.Sprintf(
		"postgres://%s:%s@%s:%d/%s?sslmode=%s",
		c.Username,
		c.Password,
		c.Host,
		c.Port,
		c.Database,
		c.SSLMode,
	)
}
