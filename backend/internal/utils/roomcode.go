package utils

import (
	"crypto/rand"
	"fmt"
	"math/big"
)

// GenerateRoomCode returns a random 6-digit numeric code, e.g. "042817".
// Uniqueness against existing polls is enforced by the caller (retry loop)
// plus a unique index on polls.code as the hard backstop.
func GenerateRoomCode() (string, error) {
	n, err := rand.Int(rand.Reader, big.NewInt(1000000))
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%06d", n.Int64()), nil
}
