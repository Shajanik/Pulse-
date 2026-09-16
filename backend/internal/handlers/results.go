package handlers

import (
	"context"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"pulse-backend/internal/db"
	"pulse-backend/internal/models"
	"pulse-backend/internal/utils"
)

// redisCountKey / redisTotalKey are the Redis keys used as the live vote
// counters (Section 9 of the spec: "Redis INCR - Update live counter").
func redisCountKey(code, optionID string) string {
	return fmt.Sprintf("pulse:%s:option:%s", code, optionID)
}

func redisTotalKey(code string) string {
	return fmt.Sprintf("pulse:%s:total", code)
}

// buildResultsFromRedis reads the live counters out of Redis. This is the
// fast path used right after a vote is cast.
func buildResultsFromRedis(ctx context.Context, poll *models.Poll) (models.ResultsPayload, error) {
	tallies := make([]models.OptionTally, len(poll.Options))
	texts := make([]string, len(poll.Options))
	counts := make([]int, len(poll.Options))
	total := 0

	for i, opt := range poll.Options {
		val, err := db.Redis.Get(ctx, redisCountKey(poll.Code, opt.ID.Hex())).Int()
		if err != nil {
			val = 0 // key not set yet == zero votes
		}
		counts[i] = val
		texts[i] = opt.Text
		total += val
	}

	for i, opt := range poll.Options {
		pct := 0.0
		if total > 0 {
			pct = float64(counts[i]) / float64(total) * 100
		}
		tallies[i] = models.OptionTally{
			ID:         opt.ID.Hex(),
			Text:       opt.Text,
			Votes:      counts[i],
			Percentage: pct,
		}
	}

	return models.ResultsPayload{
		Type:       "results",
		Code:       poll.Code,
		Question:   poll.Question,
		Options:    tallies,
		TotalVotes: total,
		Status:     poll.Status(),
		CrowdPulse: utils.CrowdPulseMessage(texts, counts),
	}, nil
}

// buildResultsFromMongo recomputes tallies from the permanent vote records.
// Used for the initial page load / fallback so results are correct even if
// Redis were ever flushed - MongoDB remains the permanent source of truth.
func buildResultsFromMongo(ctx context.Context, poll *models.Poll) (models.ResultsPayload, error) {
	cursor, err := db.Votes.Aggregate(ctx, bson.A{
		bson.M{"$match": bson.M{"pollId": poll.ID}},
		bson.M{"$group": bson.M{"_id": "$optionId", "count": bson.M{"$sum": 1}}},
	})
	if err != nil {
		return models.ResultsPayload{}, err
	}
	defer cursor.Close(ctx)

	countsByOption := map[string]int{}
	for cursor.Next(ctx) {
		var row struct {
			ID    interface{ Hex() string } `bson:"_id"`
			Count int                       `bson:"count"`
		}
		if err := cursor.Decode(&row); err != nil {
			continue
		}
		countsByOption[row.ID.Hex()] = row.Count
	}

	texts := make([]string, len(poll.Options))
	counts := make([]int, len(poll.Options))
	total := 0
	tallies := make([]models.OptionTally, len(poll.Options))

	for i, opt := range poll.Options {
		c := countsByOption[opt.ID.Hex()]
		counts[i] = c
		texts[i] = opt.Text
		total += c
	}
	for i, opt := range poll.Options {
		pct := 0.0
		if total > 0 {
			pct = float64(counts[i]) / float64(total) * 100
		}
		tallies[i] = models.OptionTally{ID: opt.ID.Hex(), Text: opt.Text, Votes: counts[i], Percentage: pct}
	}

	return models.ResultsPayload{
		Type:       "results",
		Code:       poll.Code,
		Question:   poll.Question,
		Options:    tallies,
		TotalVotes: total,
		Status:     poll.Status(),
		CrowdPulse: utils.CrowdPulseMessage(texts, counts),
	}, nil
}

func fetchPollByCode(ctx context.Context, code string) (*models.Poll, error) {
	c, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	var poll models.Poll
	err := db.Polls.FindOne(c, bson.M{"code": code}).Decode(&poll)
	if err != nil {
		return nil, err
	}
	return &poll, nil
}
