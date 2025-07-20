# AI Workflow for Pokémon Yellow Legacy: Hard Mode!

## Project Overview

This is a fully autonomous AI workflow designed to play [Pokémon Yellow Legacy](https://github.com/cRz-Shadows/Pokémon_Yellow_Legacy) on Hard Mode. Pokémon Yellow Legacy is a ROM hack of Pokémon Yellow that includes a ton of balance changes, quality of life improvements, and bug fixes, while maintaining the feel of the first generation of Pokémon. Hard mode adds level caps and blocks item use in battle, forcing the AI to strategize instead of winning by overlevelling a single Pokémon.

The AI workflow is written in Python and orchestrated by [Junjo](https://github.com/mdrideout/junjo), with custom logic for handling battles, navigating the overworld, and parsing text. It operates asynchronously with the [PyBoy emulator](https://github.com/Baekalfen/PyBoy), and is built to be modular and type-safe. The project aims to treat Pokémon as a client that can be served by a combination of classical algorithms (like A* search for navigation) with LLM powered decision making via the Google Gemini family of models.

Data from the AI workflow and the game's memory is piped into an HTML page for visualization, and the whole project is currently [streaming live on Twitch](link-to-stream). If you want to buy me a coffee to help cover the streaming costs, you can do so using the buttons below.

[paypal-button] [ko-fi-button]

If you want to learn more about how this all works, check out:
- [The philosophy behind the project](docs/philosophy.md)
- [A detailed look at the architecture](docs/architecture.md)
- [A node-by-node description of the AI workflow](docs/workflow.md)

![A screenshot of the stream](docs/images/stream_view.jpg)

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
- Can it play other Pokémon games? Will you adapt it to other games?
- Do you intend to keep working on this?
- How much does it cost to run?
- How fast does it play?
- Can I use this code?

## Licence & Affiliation Notice

All original source code in this repository is released under the [MIT Licence](LICENSE).

This is an unofficial, fan-made project, for educational purposes only. The code in this repository is designed to work with Pokémon games but does not include any ROMs, save states, or game sprites. Users are responsible for ensuring they own legitimate copies of Pokémon games and comply with all applicable laws and terms of service.

"Pokémon", Pokémon character names, and all related marks are owned by Nintendo, Game Freak, Creatures Inc., and The Pokémon Company. I am not affiliated with, endorsed, sponsored, or specifically approved by any of these entities.
