# AI Workflow for Pokémon Yellow Legacy: Hard Mode!

## Project Overview

This is a fully autonomous AI workflow designed to play [Pokémon Yellow Legacy](https://github.com/cRz-Shadows/Pokémon_Yellow_Legacy) on Hard Mode. Pokémon Yellow Legacy is a ROM hack of Pokémon Yellow that includes a ton of balance changes, quality of life improvements, and bug fixes, while maintaining the feel of the first generation of Pokémon. Hard mode adds level caps and blocks item use in battle, forcing the AI to strategize instead of winning by overlevelling a single Pokémon.

The AI workflow is written in Python and combines [Pydantic AI](https://ai.pydantic.dev/) agents with deterministic gameplay tools organized around the three major parts of the game: exploring the overworld, handling text/menus, and battling. The application operates asynchronously with the [PyBoy emulator](https://github.com/Baekalfen/PyBoy), and is built to be modular and type-safe. The project aims to treat Pokémon as a client that can be served by a combination of classical algorithms and LLM-powered decision making. It features hierarchical rolling memory and an ASCII map renderer with A* search navigation to help with the inherent limitations of working with LLMs. The goal was to have the AI make the decisions, while keeping the gameplay as close to human speed as possible.

Data from the AI workflow and the game's memory is piped into an HTML page for visualization, and the whole project [streams live on Twitch](https://www.twitch.tv/clambr0).

If you want to learn more about how this all works, check out:
- [A deeper look into the philosophy and design of the project](docs/philosophy.md)
- [A description of the AI architecture and its tools](docs/workflow.md)

Note: This is the improved v2 iteration of this project. If you want to see the original workflow-based version that streamed in Aug 2025, [you can find that here](https://github.com/clambro/ai-plays-pokemon/tree/v1.0.0).

![A screenshot of the stream](docs/images/stream_view.jpg)

## Installation and Setup

### Prerequisites

- Python 3.14
- [The uv package manager](https://docs.astral.sh/uv/) for installing dependencies
- [An OpenAI API key](https://platform.openai.com/api-keys) for calling the LLM
- The Pokémon Yellow Legacy ROM (I am not licensed to distribute this; you'll have to get it yourself)

### Installation

1. Clone this repository

2. Install the dependencies with `uv sync`

3. Make a copy of the `.env.example` file and name it `.env`. Add your OpenAI API key there.

4. Put a compatible ROM at `resources/ylegacy.gbc`. If you build from the Yellow Legacy decomp, you can optionally apply [`pokeyellow.patch`](pokeyellow.patch) for two minor bug fixes.

5. (Optional) Add a [Logfire](https://logfire.pydantic.dev/) write token as `LOGFIRE_TOKEN`. Without telemetry, you will have very little visibility into what the agent is doing behind the scenes.

**Note:** If you try to run the integration tests, many of them will fail because they depend on save states that I am not licensed to distribute. Similarly, if you try to run the game state visualization server, you'll get an error that the sprites are unavailable for the same reason.

## Running the Workflow

### Basic Usage

Run the AI workflow with the default settings using

```bash
uv run python -m main
```

This will:
- Use the ROM at `resources/ylegacy.gbc` (default)
- Start a fresh game session
- Launch the live-updating background display at `http://localhost:8080`
- Create automatic backups every 10 minutes
- Send telemetry to Logfire when `LOGFIRE_TOKEN` is configured

### Command Line Options

- `--rom-path PATH`: Specify a custom path to your ROM file
- `--backup-folder PATH`: Load a specific backup state
- `--load-latest`: Load the most recent backup (mutually exclusive with `--backup-folder`)
- `--mute-sound`: Mute the emulator sound

Other relevant constants can be edited in `common/constants.py`.

### Backup and Restore

The system automatically creates backups every 10 minutes in the `outputs/` folder. Each backup contains the AI workflow state, the game state, and a copy of the SQLite database so that you can resume play from the moment the backup was taken. Caught workflow errors also trigger a backup when the emulator remains available.

## FAQs

### Why Yellow Legacy?

Partly nostalgia since Pokémon Yellow was the first video game I ever played, but largely because its hard mode prevents the AI from winning by grinding a single Pokémon to level 100. I also think that the team behind Yellow Legacy did a great job with this hack and I wanted to highlight their excellent work.

### What does the AI know?

Only what would be accessible to a human player. It can see the screen, and it has memories of the sprites and warps that it has seen in the past. It has no internet access, and the prompts do not contain any progression hints. When battling Pokémon, it can only see the enemy's health as a percentage with a resolution that matches the resolution of the in-game health bar.

### Why combine agents with deterministic tools?

The model should make decisions, not laboriously reproduce mechanics that ordinary code can handle faster and more reliably. The agent decides what it wants to accomplish, while deterministic code validates the request against the game state and handles details such as navigation, menu input, and state persistence. This keeps decision-making with the model and predictable mechanical work in testable Python services. The boundary between model judgment and deterministic execution is the central subject of the [project philosophy](docs/philosophy.md#my-approach).

### Why GPT-5.6 Luna?

It was the cheapest, fastest frontier model at the time of writing. A big part of this project is the idea that a smaller model, properly orchestrated to do specific tasks, can outperform a larger model. Smaller models also have lower latency, making for a more enjoyable viewing experience.

### Can it play other Pokémon games?

Not natively. You could adapt this code to another Gen 1 or Gen 2 game, but you would have to create new parsers for the memory locations in the new ROM, and probably tweak some of the timing and navigation logic. PyBoy, unfortunately, only runs GameBoy and GameBoy Color games, so you would need to find another emulator to go beyond Gen 2.

### Do you intend to keep working on this?

I'd like to see it beat the game, and I'll try to support it so that it does. After that, I'm unsure. I've always wanted to build something like this, but I also have other project ideas that I'd like to work on.

### How long did it take to build this?

[The first complete version](https://github.com/clambro/ai-plays-pokemon/tree/v1.0.0) took a good chunk of my free time for 2-3 months. The current version benefited from advances in vibe coding and was built on top of the first in a few weeks of my spare time.

### How much does it cost to run?

Short answer: Roughly $0.60 USD per hour for the GPT-5.6 Luna API calls based on initial testing.

Longer answer: The rolling memory grows logarithmically over time, meaning the hourly rate should technically be more like `0.6 + ε log t`, but this logarithmic contribution proved too small to measure even after several hours of play.

### How fast does it play?

I put a lot of effort into making its reactions as close to human speed as I could. It usually gets the Pokedex in around 20 mins, and it usually gets to Brock in around 90 mins, but this fluctuates depending on how it decides to explore in the early game.

## Licence & Affiliation Notice

All original source code in this repository is released under the [MIT Licence](LICENSE).

This is an unofficial, fan-made project, for educational purposes only. The code in this repository is designed to work with Pokémon games but does not include any ROMs, save states, or game sprites. Users are responsible for ensuring they own legitimate copies of Pokémon games and comply with all applicable laws and terms of service.

"Pokémon", Pokémon character names, and all related marks are owned by Nintendo, Game Freak, Creatures Inc., and The Pokémon Company. I am not affiliated with, endorsed, sponsored, or specifically approved by any of these entities.
