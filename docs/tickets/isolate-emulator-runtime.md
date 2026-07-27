# Ticket: Isolate the Emulator Runtime

## Outcome

Move PyBoy and its real-time tick loop onto a dedicated owner thread. Expose a
small async emulator API to the rest of the application so LLM calls,
telemetry, persistence, streaming, and other application work cannot directly
stall emulation or access PyBoy concurrently.

## Motivation

The current emulator tick loop is an asyncio task on the main application
thread. Although save-state capture is moved to a worker thread, it operates on
the same PyBoy instance while that task continues ticking. Other synchronous
work on the event loop can also delay frames and cause audible stuttering.

PyBoy is a stateful, real-time dependency and should have one clear owner.

## Design

A dedicated emulator runtime thread owns the complete PyBoy lifecycle,
including construction, ticking, input, memory reads, screenshots, save-state
capture, and shutdown. No other thread may access the PyBoy instance or its
memory view.

The application-facing emulator service remains asynchronous. It sends typed
commands to the runtime and awaits their results without polling or blocking
the asyncio event loop. Commands are processed at safe boundaries between
frames.

Game-state parsing happens within the emulator runtime. Results returned to the
application are immutable snapshots detached from live emulator memory. When a
consumer needs related state, screenshot, and frame information, the runtime
must capture them coherently so the agent and HTML background do not observe
different moments accidentally.

Save-state capture also runs on the owner thread rather than concurrently with
the tick loop. PyBoy may still pause briefly while producing a save state;
checkpoint frequency is a separate policy and should not complicate this
runtime boundary.

Keep the boundary narrow enough that a separate process could replace the
thread-backed implementation later without changing agent or tool code. A
separate process is not part of this ticket.

## Scope

- Introduce the dedicated thread-owned emulator runtime and its async
  application interface.
- Route all current PyBoy operations through that interface.
- Preserve button ordering, animation waiting, screenshots, parsed game state,
  save-state loading and capture, sound, window selection, and clean shutdown.
- Prevent direct PyBoy and live-memory access outside the emulator package.
- Make runtime failures and unexpected termination visible to awaiting callers
  instead of leaving them blocked.
- Update tests and documentation that assume PyBoy shares the application
  thread.

## Completion

- PyBoy is created, used, and stopped exclusively by its owner thread.
- Slow application work does not delay the emulator tick loop through the
  asyncio event loop.
- Save-state capture cannot race with ticking or other emulator operations.
- Agent, streaming, and persistence code use only detached snapshots and the
  async emulator interface.
- Existing emulator behavior remains covered by bounded tests, including
  command ordering, failure propagation, and shutdown.
