# Ticket: Replace the Junjo Root with Pydantic Graph

## Outcome

Replace the remaining Junjo orchestration with a small functional Pydantic
Graph that observes the game, classifies the active mode, and invokes the
completed overworld, battle, or text runner.

Completing this ticket removes Junjo from the application.

**Depends on:**

- [`pydantic-ai-03-replace-overworld-subflow.md`](pydantic-ai-03-replace-overworld-subflow.md)

## Design

Keep the graph limited to top-level routing:

```text
observe game state
        ↓
classify overworld, battle, or text
        ↓
invoke the corresponding mode runner
        ↓
return to the application loop
```

The graph must not model individual tool calls, button presses, navigation
steps, dialog boxes, or battle actions. Each mode runner continues to own its
context preparation, tool registry, agent execution, and local loop.

Make `agent/app.py` the composition root. It creates concrete application
dependencies and supplies each mode with only what it needs. Agent and tool
code must not reach outward to construct emulator, persistence, or streaming
infrastructure.

Preserve the mode boundaries established by the preceding tickets:

- one selected action ends an overworld turn;
- battle returns only when battle mode exits; and
- text returns only when the interaction exits.

Background refreshes continue at mode and tool-service boundaries so complete
battle and text loops remain visible.

Remove the temporary Junjo adapters and every remaining Junjo graph, store,
condition, visualization, and dependency integration.

## Completion

- The application loop runs the functional Pydantic Graph.
- Top-level routing invokes the three completed mode runners directly.
- `agent/app.py` assembles application dependencies without leaking concrete
  infrastructure into agents.
- No Junjo package, adapter, graph, store, condition, or visualization code
  remains.
- Application startup, all three modes, cross-mode transitions, shutdown, and
  background synchronization are covered by relevant tests.
