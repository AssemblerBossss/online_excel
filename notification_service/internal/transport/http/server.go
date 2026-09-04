package http

import (
	"context"
	"errors"
	"fmt"
	"net/http"
)

type Server struct {
	server *http.Server
}

func NewServer(host string, port int, handler http.Handler) *Server {
	return &Server{
		server: &http.Server{
			Addr:    fmt.Sprintf("%s:%d", host, port),
			Handler: handler,
		},
	}
}

func (s *Server) Start() error {
	return s.server.ListenAndServe()
}

func (s *Server) Shutdown(ctx context.Context) error {
	err := s.server.Shutdown(ctx)

	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}

	return err
}
