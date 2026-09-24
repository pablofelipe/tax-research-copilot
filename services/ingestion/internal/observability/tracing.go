// Package observability configures OpenTelemetry tracing for the
// ingestion CLI. Call Setup once from main, never from a package a unit
// test imports — those never call it and rely on the OpenTelemetry SDK's
// default no-op tracer instead.
package observability

import (
	"context"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
)

const DefaultOTLPEndpoint = "localhost:4318"

// Setup configures the global TracerProvider to export spans over OTLP.
// The returned shutdown function flushes and closes the exporter; call
// it (deferred) before the process exits.
func Setup(ctx context.Context, serviceName, otlpEndpoint string) (func(context.Context) error, error) {
	exporter, err := otlptracehttp.New(
		ctx,
		otlptracehttp.WithEndpoint(otlpEndpoint),
		otlptracehttp.WithInsecure(),
	)
	if err != nil {
		return nil, err
	}

	res, err := resource.Merge(
		resource.Default(),
		resource.NewSchemaless(semconv.ServiceName(serviceName)),
	)
	if err != nil {
		return nil, err
	}

	provider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(provider)

	return provider.Shutdown, nil
}
