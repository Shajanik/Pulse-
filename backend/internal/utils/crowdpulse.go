package utils

import "sort"

// CrowdPulseMessage deterministically derives a short live commentary
// string from vote percentages. No AI/LLM involved - just simple rules
// over the current standings.
//
//   - Nobody has voted yet            -> waiting message
//   - Leader way out ahead of #2      -> "<Leader> is dominating!"
//   - Leader and #2 nearly tied       -> "It's getting competitive!"
//   - Spread roughly evenly overall   -> "The crowd is divided!"
//   - Anything else                   -> "It's getting competitive!"
func CrowdPulseMessage(optionTexts []string, votes []int) string {
	total := 0
	for _, v := range votes {
		total += v
	}
	if total == 0 {
		return "Waiting for the first vote..."
	}

	type stat struct {
		text string
		pct  float64
	}
	stats := make([]stat, len(votes))
	minPct, maxPct := 100.0, 0.0
	for i, v := range votes {
		pct := float64(v) / float64(total) * 100
		stats[i] = stat{text: optionTexts[i], pct: pct}
		if pct < minPct {
			minPct = pct
		}
		if pct > maxPct {
			maxPct = pct
		}
	}

	sort.Slice(stats, func(i, j int) bool { return stats[i].pct > stats[j].pct })

	if len(stats) == 1 {
		return stats[0].text + " is dominating!"
	}

	gap := stats[0].pct - stats[1].pct
	spread := maxPct - minPct

	switch {
	case gap >= 25:
		return stats[0].text + " is dominating!"
	case spread <= 15:
		return "The crowd is divided!"
	case gap <= 8:
		return "It's getting competitive!"
	default:
		return "It's getting competitive!"
	}
}
