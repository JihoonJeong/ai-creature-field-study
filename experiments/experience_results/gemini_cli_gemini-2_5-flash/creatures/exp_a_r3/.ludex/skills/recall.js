export default {
  "name": "recall",
  "description": "Search and recall memories by topic",
  "trigger": "when user asks to remember something or search memories",
  "steps": [
    "search episodic and semantic memories for the query",
    "rank by relevance and recency",
    "present top results with context"
  ],
  "prompt": "Search your memories for the requested topic.
Present what you remember, noting whether each memory is episodic
(a specific event) or semantic (a general fact). Be honest if you
don't remember something.",
  "requires_organs": [
    "memory"
  ],
  "uses_tools": [
    "ludex__recall_memory"
  ]
};