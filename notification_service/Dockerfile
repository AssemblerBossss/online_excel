FROM golang:1.26 AS builder

WORKDIR /app

COPY go.mod .
COPY go.sum .

RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-s -w" \
    -o notification-service \
    ./cmd/server


FROM gcr.io/distroless/static-debian12

WORKDIR /

COPY --from=builder /app/notification-service .
COPY --from=builder /app/configs /configs
COPY --from=builder /app/migrations /migrations
EXPOSE 8003

ENTRYPOINT ["/notification-service"]