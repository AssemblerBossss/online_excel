package main

import (
	"context"
	"errors"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"go.uber.org/zap"

	"notification_service/internal/config"
	"notification_service/internal/logger"
	"notification_service/internal/repository/memory"
	"notification_service/internal/service"
	transporthttp "notification_service/internal/transport/http"
)

func main() {
	cfg, err := config.Load("configs/config.yaml")
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

	repository := memory.NewNotificationRepository()

	notificationService := service.NewNotificationService(
		repository,
	)

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

	ctx, stop := signal.NotifyContext(
		context.Background(),
		os.Interrupt,
		syscall.SIGTERM,
	)
	defer stop()

	serverErr := make(chan error, 1)

	go func() {
		log.Info(
			"HTTP server started",
			zap.String("address", server.Addr),
		)

		serverErr <- server.ListenAndServe()
	}()

	select {
	case err := <-serverErr:
		if !errors.Is(err, http.ErrServerClosed) {
			log.Fatal(
				"HTTP server failed",
				zap.Error(err),
			)
		}

	case <-ctx.Done():
		log.Info("shutdown signal received")
	}

	shutdownCtx, cancel := context.WithTimeout(
		context.Background(),
		cfg.Server.ShutdownTimeout,
	)
	defer cancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Error(
			"HTTP server shutdown failed",
			zap.Error(err),
		)
	}

	log.Info("notification service stopped")
}
