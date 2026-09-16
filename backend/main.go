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

	db.ConnectMongo(cfg.MongoURI, cfg.MongoDBName)
	db.ConnectRedis(cfg.RedisURL)

	hub := ws.NewHub()
	ws.StartRedisSubscriber(context.Background(), db.Redis, db.ResultsChannel, hub)

	allowedOrigins := strings.Split(cfg.AllowedOrigins, ",")
	for i := range allowedOrigins {
		allowedOrigins[i] = strings.TrimSpace(allowedOrigins[i])
	}

	router := gin.Default()

	// Root route - confirms that the backend is running
	router.GET("/", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"message": "Pulse backend is running",
		})
	})

	// CORS
	router.Use(cors.New(cors.Config{
		AllowOrigins:     allowedOrigins,
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Authorization"},
		AllowCredentials: true,
	}))

	// Handlers
	authHandler := handlers.NewAuthHandler(cfg.JWTSecret)
	pollHandler := handlers.NewPollHandler()
	voteHandler := handlers.NewVoteHandler()
	wsHandler := handlers.NewWSHandler(hub, allowedOrigins)

	// API routes
	api := router.Group("/api")
	{
		// Authentication
		auth := api.Group("/auth")
		auth.POST("/signup", authHandler.Signup)
		auth.POST("/login", authHandler.Login)
		auth.GET("/me", middleware.AuthRequired(cfg.JWTSecret), authHandler.Me)

		// Polls
		polls := api.Group("/polls")
		polls.POST("", middleware.AuthRequired(cfg.JWTSecret), pollHandler.CreatePoll)
		polls.GET("/mine", middleware.AuthRequired(cfg.JWTSecret), pollHandler.MyPolls)
		polls.GET("/:code", pollHandler.GetPollByCode)
		polls.GET("/:code/results", pollHandler.GetResults)

		// Rooms / voting
		rooms := api.Group("/rooms")
		rooms.POST("/:code/join", voteHandler.JoinRoom)
		rooms.POST("/:code/vote", voteHandler.CastVote)
	}

	// WebSocket
	router.GET("/ws/room/:code", wsHandler.RoomSocket)

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status": "ok",
		})
	})

	// Render provides the PORT environment variable.
	// Use 10000 as the fallback for Render.
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
