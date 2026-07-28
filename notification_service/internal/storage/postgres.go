package storage

import (
	"context"
	"notification_service/internal/config"

	"github.com/jackc/pgx/v5/pgxpool"
)

func NewPostgres(
	ctx context.Context,
	cfg config.PostgresConfig,
) (*pgxpool.Pool, error) {
	poolConfig, err := pgxpool.ParseConfig(cfg.DSN())

	if err != nil {
		return nil, err
	}

	poolConfig.MaxConns = cfg.MaxConnections
	return pgxpool.NewWithConfig(ctx, poolConfig)
}
