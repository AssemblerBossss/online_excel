package config

import (
	"fmt"

	"github.com/spf13/viper"
)

// Load reads and parses the config file at path into a Config struct.
// Supports environment variables with NOTIFICATION_ prefix.
func Load(path string) (*Config, error) {
	v := viper.New()
	v.SetConfigFile(path)
	v.SetEnvPrefix("NOTIFICATION")
	v.AutomaticEnv()

	if err := v.ReadInConfig(); err != nil {
		return nil, err
	}

	var cfg Config

	if err := v.Unmarshal(&cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
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
