package ws

import (
	"log"
	"sync"

	"github.com/gorilla/websocket"
)

// Hub keeps track of which client connections belong to which room (poll
// code) and fans out broadcast messages to everyone in that room.
type Hub struct {
	mu    sync.RWMutex
	rooms map[string]map[*websocket.Conn]bool
}

func NewHub() *Hub {
	return &Hub{rooms: make(map[string]map[*websocket.Conn]bool)}
}

func (h *Hub) Register(code string, conn *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if h.rooms[code] == nil {
		h.rooms[code] = make(map[*websocket.Conn]bool)
	}
	h.rooms[code][conn] = true
}

func (h *Hub) Unregister(code string, conn *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if conns, ok := h.rooms[code]; ok {
		delete(conns, conn)
		if len(conns) == 0 {
			delete(h.rooms, code)
		}
	}
	_ = conn.Close()
}

// Broadcast sends the given message to every client currently connected
// to the given room code.
func (h *Hub) Broadcast(code string, message []byte) {
	h.mu.RLock()
	conns := make([]*websocket.Conn, 0, len(h.rooms[code]))
	for c := range h.rooms[code] {
		conns = append(conns, c)
	}
	h.mu.RUnlock()

	for _, conn := range conns {
		if err := conn.WriteMessage(websocket.TextMessage, message); err != nil {
			log.Printf("ws write error, dropping client: %v", err)
			h.Unregister(code, conn)
		}
	}
}
