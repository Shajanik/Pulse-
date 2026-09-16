package models

import (
	"time"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

type User struct {
	ID           primitive.ObjectID `bson:"_id,omitempty" json:"id"`
	Email        string             `bson:"email" json:"email"`
	PasswordHash string             `bson:"passwordHash" json:"-"`
	CreatedAt    time.Time          `bson:"createdAt" json:"createdAt"`
}

type Option struct {
	ID   primitive.ObjectID `bson:"id" json:"id"`
	Text string             `bson:"text" json:"text"`
}

// PollStatus is derived at read time from ExpiresAt, but we also store it
// so queries (e.g. "my active polls") don't need to recompute per-row.
type PollStatus string

const (
	StatusActive  PollStatus = "active"
	StatusExpired PollStatus = "expired"
)

type Poll struct {
	ID        primitive.ObjectID `bson:"_id,omitempty" json:"id"`
	HostID    primitive.ObjectID `bson:"hostId" json:"hostId"`
	Code      string             `bson:"code" json:"code"`
	Question  string             `bson:"question" json:"question"`
	Options   []Option           `bson:"options" json:"options"`
	CreatedAt time.Time          `bson:"createdAt" json:"createdAt"`
	ExpiresAt time.Time          `bson:"expiresAt" json:"expiresAt"`
}

// IsExpired computes live status - the single source of truth for whether
// a poll can still accept votes.
func (p *Poll) IsExpired() bool {
	return time.Now().After(p.ExpiresAt)
}

func (p *Poll) Status() PollStatus {
	if p.IsExpired() {
		return StatusExpired
	}
	return StatusActive
}

type Vote struct {
	ID        primitive.ObjectID `bson:"_id,omitempty" json:"id"`
	PollID    primitive.ObjectID `bson:"pollId" json:"pollId"`
	OptionID  primitive.ObjectID `bson:"optionId" json:"optionId"`
	VoterID   string             `bson:"voterId" json:"voterId"`
	Nickname  string             `bson:"nickname" json:"nickname"`
	CreatedAt time.Time          `bson:"createdAt" json:"createdAt"`
}

// ResultsPayload is what gets published over Redis Pub/Sub and broadcast
// to every connected client over the poll's WebSocket room.
type ResultsPayload struct {
	Type       string        `json:"type"`
	Code       string        `json:"code"`
	Question   string        `json:"question"`
	Options    []OptionTally `json:"options"`
	TotalVotes int           `json:"totalVotes"`
	Status     PollStatus    `json:"status"`
	CrowdPulse string        `json:"crowdPulse"`
}

type OptionTally struct {
	ID         string  `json:"id"`
	Text       string  `json:"text"`
	Votes      int     `json:"votes"`
	Percentage float64 `json:"percentage"`
}
