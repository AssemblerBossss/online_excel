package main

import (
	"context"
	"errors"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/jackc/pgx/v5/stdlib"
	"github.com/pressly/goose/v3"
	"go.uber.org/zap"
	"golang.org/x/sync/errgroup"

	"notification_service/internal/config"
	"notification_service/internal/logger"
	"notification_service/internal/repository/postgres"
	"notification_service/internal/sender"
	"notification_service/internal/service"
	"notification_service/internal/storage"
	transporthttp "notification_service/internal/transport/http"
	"notification_service/internal/transport/rabbitmq"
	"notification_service/migrations"
)

func main() {
	configPath := os.Getenv("CONFIG_PATH")
	if configPath == "" {
		configPath = "configs/config.yaml"
	}

	cfg, err := config.Load(configPath)
	if err != nil {
		panic(err)
	}

	log, err := logger.New(
		cfg.Logger.Level,
		cfg.Logger.Development,
	)
	if err != nil {
		panic(err)
	}
	defer func() {
		_ = log.Sync()
	}()

	ctx, stop := signal.NotifyContext(
		context.Background(),
		os.Interrupt,
		syscall.SIGTERM,
	)
	defer stop()

	pool, err := storage.NewPostgres(ctx, cfg.Postgres)
	if err != nil {
		log.Fatal("postgres connection failed", zap.Error(err))
	}
	defer pool.Close()

	if err := runMigrations(pool); err != nil {
		log.Fatal("migrations failed", zap.Error(err))
	}

	repository := postgres.NewNotificationRepository(pool)

	notificationService := service.NewNotificationService(
		repository,
	)
	smtpSender := sender.NewSMTPSender(cfg.SMTP)
	eventHandler := service.NewEventHandler(notificationService, smtpSender)
	consumer := rabbitmq.NewConsumer(cfg.RabbitMQ, eventHandler, log)

	handler := transporthttp.NewHandler(
		notificationService,
	)

	router := transporthttp.NewRouter(handler)

	server := &http.Server{
		Addr:              cfg.Server.Address(),
		Handler:           router,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	g, gctx := errgroup.WithContext(ctx)

	g.Go(func() error {
		log.Info("rabbitmq consumer started")
		consumer.Run(gctx)
		return nil
	})

	g.Go(func() error {
		log.Info(
			"HTTP server started",
			zap.String("address", server.Addr),
		)

		if err := server.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
			return err
		}
		return nil
	})

	g.Go(func() error {
		<-gctx.Done()
		log.Info("shutdown signal received")

		shutdownCtx, cancel := context.WithTimeout(
			context.Background(),
			cfg.Server.ShutdownTimeout,
		)
		defer cancel()

		return server.Shutdown(shutdownCtx)
	})

	if err := g.Wait(); err != nil {
		log.Fatal("notification service failed", zap.Error(err))
	}

	log.Info("notification service stopped")
}

func runMigrations(pool *pgxpool.Pool) error {
	db := stdlib.OpenDBFromPool(pool)
	defer db.Close()

	goose.SetBaseFS(migrations.FS)
	if err := goose.SetDialect("postgres"); err != nil {
		return err
	}

	return goose.Up(db, ".")
}
