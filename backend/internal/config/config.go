package config

import (
	"log"
	"os"

	"github.com/joho/godotenv"
)

// Config holds all runtime configuration loaded from environment variables.
type Config struct {
	MongoURI       string
	MongoDBName    string
	RedisURL       string
	JWTSecret      string
	Port           string
	AllowedOrigins string
}

// Load reads a .env file if present (local dev) and falls back to real
// environment variables (used in production/deployment). It exits the
// process if required secrets are missing.
func Load() *Config {
	// It's fine if .env doesn't exist (e.g. in production/Render).
	_ = godotenv.Load()

	cfg := &Config{
		MongoURI:       getEnv("MONGODB_URI", ""),
		MongoDBName:    getEnv("MONGODB_DB_NAME", "pulse"),
		RedisURL:       getEnv("REDIS_URL", ""),
		JWTSecret:      getEnv("JWT_SECRET", ""),
		Port:           getEnv("PORT", "8080"),
		AllowedOrigins: getEnv("ALLOWED_ORIGINS", "http://localhost:5173"),
	}

	if cfg.MongoURI == "" {
		log.Fatal("MONGODB_URI is required")
	}
	if cfg.RedisURL == "" {
		log.Fatal("REDIS_URL is required")
	}
	if cfg.JWTSecret == "" {
		log.Fatal("JWT_SECRET is required")
	}

	return cfg
}

func getEnv(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return fallback
}
