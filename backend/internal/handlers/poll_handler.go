package handlers

import (
	"context"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	mongoopts "go.mongodb.org/mongo-driver/mongo/options"
	"pulse-backend/internal/db"
	"pulse-backend/internal/models"
	"pulse-backend/internal/utils"
)

type PollHandler struct{}

func NewPollHandler() *PollHandler {
	return &PollHandler{}
}

var validExpirations = map[int]bool{5: true, 15: true, 30: true}

type createPollRequest struct {
	Question         string   `json:"question"`
	Options          []string `json:"options"`
	ExpiresInMinutes int      `json:"expiresInMinutes"`
}

func (h *PollHandler) CreatePoll(c *gin.Context) {
	userID := c.GetString("userID")
	hostOID, err := primitive.ObjectIDFromHex(userID)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid session"})
		return
	}

	var req createPollRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}

	question := strings.TrimSpace(req.Question)
	if question == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "question cannot be empty"})
		return
	}

	cleanOptions := make([]string, 0, len(req.Options))
	for _, o := range req.Options {
		o = strings.TrimSpace(o)
		if o != "" {
			cleanOptions = append(cleanOptions, o)
		}
	}
	if len(cleanOptions) < 2 || len(cleanOptions) > 4 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "a poll needs 2 to 4 non-empty options"})
		return
	}

	if !validExpirations[req.ExpiresInMinutes] {
		c.JSON(http.StatusBadRequest, gin.H{"error": "expiration must be 5, 15, or 30 minutes"})
		return
	}

	options := make([]models.Option, len(cleanOptions))
	for i, text := range cleanOptions {
		options[i] = models.Option{ID: primitive.NewObjectID(), Text: text}
	}

	ctx, cancel := context.WithTimeout(c, 5*time.Second)
	defer cancel()

	// Generate a unique 6-digit code, retrying on the rare collision. The
	// unique index on polls.code is the hard backstop.
	var code string
	for attempt := 0; attempt < 10; attempt++ {
		candidate, genErr := utils.GenerateRoomCode()
		if genErr != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate room code"})
			return
		}
		count, countErr := db.Polls.CountDocuments(ctx, bson.M{"code": candidate})
		if countErr == nil && count == 0 {
			code = candidate
			break
		}
	}
	if code == "" {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "could not allocate a room code, please try again"})
		return
	}

	now := time.Now()
	poll := models.Poll{
		HostID:    hostOID,
		Code:      code,
		Question:  question,
		Options:   options,
		CreatedAt: now,
		ExpiresAt: now.Add(time.Duration(req.ExpiresInMinutes) * time.Minute),
	}

	res, err := db.Polls.InsertOne(ctx, poll)
	if mongo.IsDuplicateKeyError(err) {
		c.JSON(http.StatusConflict, gin.H{"error": "room code collision, please try again"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create poll"})
		return
	}
	poll.ID = res.InsertedID.(primitive.ObjectID)

	c.JSON(http.StatusCreated, poll)
}

// GetPollByCode is public - anyone with a room code can look up the poll's
// question/options to join and vote. It intentionally omits the host ID.
func (h *PollHandler) GetPollByCode(c *gin.Context) {
	code := c.Param("code")

	poll, err := fetchPollByCode(c, code)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "room not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"code":      poll.Code,
		"question":  poll.Question,
		"options":   poll.Options,
		"status":    poll.Status(),
		"expiresAt": poll.ExpiresAt,
	})
}

// GetResults is public so both the host view and the audience results page
// can read live standings; the actual vote count comes from Redis (fast
// path) so this never falls back to client-side polling.
func (h *PollHandler) GetResults(c *gin.Context) {
	code := c.Param("code")

	poll, err := fetchPollByCode(c, code)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "room not found"})
		return
	}

	ctx, cancel := context.WithTimeout(c, 5*time.Second)
	defer cancel()

	payload, err := buildResultsFromRedis(ctx, poll)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to compute results"})
		return
	}

	c.JSON(http.StatusOK, payload)
}

// MyPolls lists the authenticated host's own polls for the dashboard.
func (h *PollHandler) MyPolls(c *gin.Context) {
	userID := c.GetString("userID")
	hostOID, err := primitive.ObjectIDFromHex(userID)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid session"})
		return
	}

	ctx, cancel := context.WithTimeout(c, 5*time.Second)
	defer cancel()

	cursor, err := db.Polls.Find(ctx, bson.M{"hostId": hostOID}, mongoopts.Find().SetSort(bson.M{"createdAt": -1}))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to load polls"})
		return
	}
	defer cursor.Close(ctx)

	var polls []models.Poll
	if err := cursor.All(ctx, &polls); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to load polls"})
		return
	}
	if polls == nil {
		polls = []models.Poll{}
	}

	c.JSON(http.StatusOK, polls)
}
