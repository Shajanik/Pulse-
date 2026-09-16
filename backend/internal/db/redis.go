package db

import (
	"context"
	"log"

	"github.com/redis/go-redis/v9"
)

var Redis *redis.Client

const ResultsChannel = "pulse:results"

// ConnectRedis dials Redis (used for live vote counters via INCR and for
// broadcasting result updates via Pub/Sub) and verifies the connection.
func ConnectRedis(redisURL string) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatalf("invalid REDIS_URL: %v", err)
	}

	client := redis.NewClient(opts)
	if err := client.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("redis ping error: %v", err)
	}

	Redis = client
	log.Println("connected to Redis")
}
