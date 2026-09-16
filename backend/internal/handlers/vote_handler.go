package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"pulse-backend/internal/db"
	"pulse-backend/internal/models"
)

type VoteHandler struct{}

func NewVoteHandler() *VoteHandler {
	return &VoteHandler{}
}

type joinRequest struct {
	Nickname string `json:"nickname"`
}

// JoinRoom validates the room/poll and hands the audience member a fresh
// anonymous voterId. No account is created - the client just holds onto
// this id (e.g. in localStorage) to prove "I already voted" next time.
func (h *VoteHandler) JoinRoom(c *gin.Context) {
	code := c.Param("code")

	var req joinRequest
	_ = c.ShouldBindJSON(&req)
	nickname := strings.TrimSpace(req.Nickname)
	if nickname == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "nickname is required"})
		return
	}
	if len(nickname) > 24 {
		nickname = nickname[:24]
	}

	poll, err := fetchPollByCode(c, code)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "room not found"})
		return
	}
	if poll.IsExpired() {
		c.JSON(http.StatusGone, gin.H{"error": "this poll has expired"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"voterId":   uuid.NewString(),
		"nickname":  nickname,
		"code":      poll.Code,
		"question":  poll.Question,
		"options":   poll.Options,
		"expiresAt": poll.ExpiresAt,
	})
}

type castVoteRequest struct {
	OptionID string `json:"optionId"`
	VoterID  string `json:"voterId"`
	Nickname string `json:"nickname"`
}

// CastVote is the heart of the real-time pipeline described in the spec:
// validate -> permanent MongoDB write -> Redis INCR live counters ->
// Redis PUBLISH -> (elsewhere) Go subscriber -> WebSocket broadcast.
func (h *VoteHandler) CastVote(c *gin.Context) {
	code := c.Param("code")

	var req castVoteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}
	if req.VoterID == "" || req.OptionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "voterId and optionId are required"})
		return
	}

	poll, err := fetchPollByCode(c, code)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "room not found"})
		return
	}
	if poll.IsExpired() {
		c.JSON(http.StatusGone, gin.H{"error": "this poll has expired"})
		return
	}

	optionOID, err := primitive.ObjectIDFromHex(req.OptionID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid option"})
		return
	}

	// Server-side check: the option must actually belong to this poll.
	// Never trust that the client only shows valid options.
	belongs := false
	for _, opt := range poll.Options {
		if opt.ID == optionOID {
			belongs = true
			break
		}
	}
	if !belongs {
		c.JSON(http.StatusBadRequest, gin.H{"error": "that option does not belong to this poll"})
		return
	}

	ctx, cancel := context.WithTimeout(c, 5*time.Second)
	defer cancel()

	vote := models.Vote{
		PollID:    poll.ID,
		OptionID:  optionOID,
		VoterID:   req.VoterID,
		Nickname:  strings.TrimSpace(req.Nickname),
		CreatedAt: time.Now(),
	}

	// 1. Permanent write to MongoDB. The unique (pollId, voterId) index is
	// what actually stops duplicate votes - not just app logic.
	_, err = db.Votes.InsertOne(ctx, vote)
	if mongo.IsDuplicateKeyError(err) {
		c.JSON(http.StatusConflict, gin.H{"error": "you have already voted in this poll"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to record vote"})
		return
	}

	// 2. Redis INCR - live counters.
	if err := db.Redis.Incr(ctx, redisCountKey(poll.Code, optionOID.Hex())).Err(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update live counter"})
		return
	}
	if err := db.Redis.Incr(ctx, redisTotalKey(poll.Code)).Err(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update live counter"})
		return
	}

	// 3. Compute fresh standings from the counters we just updated, then
	// publish over Redis Pub/Sub. A separate subscriber goroutine (started
	// at boot) is what actually pushes this out over WebSocket - this
	// handler never touches the hub directly.
	payload, err := buildResultsFromRedis(ctx, poll)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to compute results"})
		return
	}
	data, _ := json.Marshal(payload)
	if err := db.Redis.Publish(ctx, db.ResultsChannel, data).Err(); err != nil {
		// Vote is already durably stored; a publish failure only delays
		// the live update, so we log-equivalent via response but still 200.
	}

	c.JSON(http.StatusOK, gin.H{"success": true})
}
