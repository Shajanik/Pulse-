package db

import (
	"context"
	"log"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

var Client *mongo.Client
var Database *mongo.Database

// Users, Polls, Votes are the permanent MongoDB collections used across
// the app. MongoDB is the permanent source of truth for all three.
var Users *mongo.Collection
var Polls *mongo.Collection
var Votes *mongo.Collection

// ConnectMongo dials MongoDB, verifies the connection, and prepares the
// collections + indexes used by the app.
func ConnectMongo(uri, dbName string) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		log.Fatalf("mongo connect error: %v", err)
	}
	if err := client.Ping(ctx, nil); err != nil {
		log.Fatalf("mongo ping error: %v", err)
	}

	Client = client
	Database = client.Database(dbName)
	Users = Database.Collection("users")
	Polls = Database.Collection("polls")
	Votes = Database.Collection("votes")

	ensureIndexes(ctx)

	log.Println("connected to MongoDB")
}

func ensureIndexes(ctx context.Context) {
	_, err := Users.Indexes().CreateOne(ctx, mongo.IndexModel{
		Keys:    bson.D{{Key: "email", Value: 1}},
		Options: options.Index().SetUnique(true),
	})
	if err != nil {
		log.Fatalf("failed to create users.email index: %v", err)
	}

	_, err = Polls.Indexes().CreateOne(ctx, mongo.IndexModel{
		Keys:    bson.D{{Key: "code", Value: 1}},
		Options: options.Index().SetUnique(true),
	})
	if err != nil {
		log.Fatalf("failed to create polls.code index: %v", err)
	}

	// One vote per voter per poll - this is the hard backstop against
	// duplicate voting, enforced at the database level.
	_, err = Votes.Indexes().CreateOne(ctx, mongo.IndexModel{
		Keys:    bson.D{{Key: "pollId", Value: 1}, {Key: "voterId", Value: 1}},
		Options: options.Index().SetUnique(true),
	})
	if err != nil {
		log.Fatalf("failed to create votes unique index: %v", err)
	}
}
