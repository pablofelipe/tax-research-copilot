FROM golang:1.25-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /out/ingest ./cmd/ingest

FROM alpine:3.20
RUN apk add --no-cache curl
COPY --from=build /out/ingest /usr/local/bin/ingest
ENTRYPOINT ["ingest"]
