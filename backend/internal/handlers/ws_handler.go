package handlers

import (
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"pulse-backend/internal/ws"
)

type WSHandler struct {
	Hub            *ws.Hub
	AllowedOrigins map[string]bool
}

func NewWSHandler(hub *ws.Hub, allowedOrigins []string) *WSHandler {
	set := make(map[string]bool, len(allowedOrigins))
	for _, o := range allowedOrigins {
		set[o] = true
	}
	return &WSHandler{Hub: hub, AllowedOrigins: set}
}

// RoomSocket upgrades the connection and joins the caller to the room
// identified by the :code path param. The room must exist; expired rooms
// can still be watched (so late viewers see final results) but no votes
// can be cast against them (enforced in CastVote, not here).
func (h *WSHandler) RoomSocket(c *gin.Context) {
	code := c.Param("code")

	poll, err := fetchPollByCode(c, code)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "room not found"})
		return
	}

	upgrader := websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			origin := r.Header.Get("Origin")
			if origin == "" {
				return true
			}
			return h.AllowedOrigins[origin]
		},
	}

	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("ws upgrade failed: %v", err)
		return
	}

	h.Hub.Register(poll.Code, conn)
	defer h.Hub.Unregister(poll.Code, conn)

	// Keep reading (and discarding) messages so we detect client
	// disconnects; this app is broadcast-only, clients don't send data
	// over the socket.
	for {
		if _, _, err := conn.ReadMessage(); err != nil {
			break
		}
	}
}
