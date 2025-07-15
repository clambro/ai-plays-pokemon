# AI Workflow for Pokemon Yellow Legacy: Hard Mode!

## Project Overview

- What is this?
- What is Yellow Legacy? What is hard mode?
- [Link to philosophy document](docs/philosophy.md)
- Link to live stream
- Buy me a coffee

## Technical Architecture

- Modular, production architecture: Async, type-safe
- Junjo workflow and server
- Google Gemini LLMs
- Emulator: PyBoy-based emulator with custom game state parsing
- Memory Systems: Multi-tier memory (raw, summary, long-term) with RAG retrieval
- Backup and restore logic
- Decision Making: Modular subflows for battle, text, and overworld handling
- Live Streaming: Real-time web interface showing agent progress
- [Link to architecture deep dive](docs/architecture.md)

## Installation and Setup

- Python and uv (note that the tests will fail without the save states that I can't share)
- Getting the ROM
- Env variables for Gemini and Junjo Server

## Usage

- Explain main.py and all its parameters
- Backup/restore functionality
- Live streaming server on localhost:8080

## FAQs

- Why Yellow Legacy?
- Didn't GPP already do this?
- Why use Junjo over other frameworks?
- Why are you using Gemini Flash instead of Pro?
- Why are the tests failing?
- Can it play other Pokemon games? Will you adapt it to other games?
- Do you intend to keep working on this?
- How much does it cost to run?
- How fast does it play?
- Can I use this code?

## Licence & Affiliation Notice

All original source code in this repository is released under the [MIT Licence](LICENSE).

This is an unofficial, fan-made project, for educational purposes only. The code in this repository is designed to work with Pokemon games but does not include any ROMs, save states, or game sprites. Users are responsible for ensuring they own legitimate copies of Pokémon games and comply with all applicable laws and terms of service.

"Pokémon", Pokémon character names, and all related marks are owned by Nintendo, Game Freak, Creatures Inc., and The Pokémon Company. I am not affiliated with, endorsed, sponsored, or specifically approved by any of these entities.
