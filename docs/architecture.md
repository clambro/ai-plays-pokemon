# Project Architecture

## Overview

- [Link to architecture deep dive](docs/architecture.md)
- Modular, production architecture: Async, type-safe
- Junjo workflow and server [Link to workflow document](docs/workflow.md)
- Google Gemini LLMs
- Emulator: PyBoy-based emulator with custom game state parsing
- Memory Systems: Multi-tier memory (raw, summary, long-term) with RAG retrieval
- Backup and restore logic
- Decision Making: Modular subflows for battle, text, and overworld handling
- Live Streaming: Real-time web interface showing agent progress