package ws

import (
	"context"
	"encoding/json"
	"log"

	"github.com/redis/go-redis/v9"
	"pulse-backend/internal/models"
)

// StartRedisSubscriber is the "Go receives Redis event" leg of the
// real-time pipeline. It subscribes once to the shared results channel and
// forwards every published ResultsPayload to the correct WebSocket room.
// Vote handlers never call hub.Broadcast directly - they only publish to
// Redis - this is what makes Redis Pub/Sub genuinely load-bearing rather
// than decorative.
func StartRedisSubscriber(ctx context.Context, rdb *redis.Client, channel string, hub *Hub) {
	sub := rdb.Subscribe(ctx, channel)

	go func() {
		defer sub.Close()
		ch := sub.Channel()
		for msg := range ch {
			var payload models.ResultsPayload
			if err := json.Unmarshal([]byte(msg.Payload), &payload); err != nil {
				log.Printf("failed to unmarshal results payload: %v", err)
				continue
			}
			hub.Broadcast(payload.Code, []byte(msg.Payload))
		}
	}()

	log.Println("redis subscriber listening on", channel)
}
