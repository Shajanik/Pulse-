package main

import (
	"context"
	"log"
	"os"
	"strings"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"

	"pulse-backend/internal/config"
	"pulse-backend/internal/db"
	"pulse-backend/internal/handlers"
	"pulse-backend/internal/middleware"
	"pulse-backend/internal/ws"
)

func main() {
	cfg := config.Load()

	// Connect to databases.
	db.ConnectMongo(cfg.MongoURI, cfg.MongoDBName)
	db.ConnectRedis(cfg.RedisURL)

	// Initialize WebSocket hub and Redis subscriber.
	hub := ws.NewHub()
	ws.StartRedisSubscriber(
		context.Background(),
		db.Redis,
		db.ResultsChannel,
		hub,
	)

	// Configure allowed origins.
	allowedOrigins := strings.Split(cfg.AllowedOrigins, ",")
	for i := range allowedOrigins {
		allowedOrigins[i] = strings.TrimSpace(allowedOrigins[i])
	}

	// Ensure the production frontend is allowed.
	frontendOrigin := "https://pulse-live-poll.vercel.app"
	found := false

	for _, origin := range allowedOrigins {
		if origin == frontendOrigin {
			found = true
			break
		}
	}

	if !found {
		allowedOrigins = append(allowedOrigins, frontendOrigin)
	}

	router := gin.Default()

	// CORS MUST be registered before all routes.
	router.Use(cors.New(cors.Config{
		AllowOrigins: allowedOrigins,
		AllowMethods: []string{
			"GET",
			"POST",
			"PUT",
			"PATCH",
			"DELETE",
			"OPTIONS",
		},
		AllowHeaders: []string{
			"Origin",
			"Content-Type",
			"Authorization",
		},
		AllowCredentials: true,
	}))

	// Root route.
	router.GET("/", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"message": "Pulse backend is running",
		})
	})

	// Initialize handlers.
	authHandler := handlers.NewAuthHandler(cfg.JWTSecret)
	pollHandler := handlers.NewPollHandler()
	voteHandler := handlers.NewVoteHandler()
	wsHandler := handlers.NewWSHandler(hub, allowedOrigins)

	// API routes.
	api := router.Group("/api")
	{
		// Authentication.
		auth := api.Group("/auth")
		{
			auth.POST("/signup", authHandler.Signup)
			auth.POST("/login", authHandler.Login)
			auth.GET(
				"/me",
				middleware.AuthRequired(cfg.JWTSecret),
				authHandler.Me,
			)
		}

		// Polls.
		polls := api.Group("/polls")
		{
			polls.POST(
				"",
				middleware.AuthRequired(cfg.JWTSecret),
				pollHandler.CreatePoll,
			)
			polls.GET(
				"/mine",
				middleware.AuthRequired(cfg.JWTSecret),
				pollHandler.MyPolls,
			)
			polls.GET("/:code", pollHandler.GetPollByCode)
			polls.GET("/:code/results", pollHandler.GetResults)
		}

		// Rooms and voting.
		rooms := api.Group("/rooms")
		{
			rooms.POST("/:code/join", voteHandler.JoinRoom)
			rooms.POST("/:code/vote", voteHandler.CastVote)
		}
	}

	// WebSocket endpoint.
	router.GET("/ws/room/:code", wsHandler.RoomSocket)

	// Health check.
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status": "ok",
		})
	})

	// Render port configuration.
	port := os.Getenv("PORT")
	if port == "" {
		port = cfg.Port
	}
	if port == "" {
		port = "10000"
	}

	log.Printf("Pulse backend listening on 0.0.0.0:%s", port)

	if err := router.Run("0.0.0.0:" + port); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}
