# ai-plays-pokemon

## Licence & Affiliation Notice

All original source code in this repository is released under the [MIT Licence](LICENSE).

This is an unofficial, fan-made project, for educational purposes only. The code enclosed in this repository is designed to work with Pokemon games but does not include any ROMs, save states, or game sprites. Users are responsible for ensuring they own legitimate copies of Pokémon games and comply with all applicable laws and terms of service.

"Pokémon", Pokémon character names, and all related marks are trademarks of Nintendo, Game Freak, Creatures Inc., and The Pokémon Company. I am not affiliated with, endorsed, sponsored, or specifically approved by any of these entities.

---

## TODOs in rough order of importance

### Required for Release
* Add strength boulders to map screen -- 00:d717 wBoulderSpriteIndex
* Handle surfing in navigation + tests
* Handle the bike in navigation + tests
* Handle spin tiles in navigation + tests

* Test background tile and blocking generation from game states for strength boulders and seafoam elevation

* Set up Junjo server and opentelemetry

* Add node tests for the LLM calls
    * Ensure that the player/rival names are at most 7 characters instead of 10
    * Tests for selecting tools
    * Tests for multiple button presses

* Twitch integration for dealing with ad breaks
* Some kind of VM to run everything on

### Nice to Have
* Add a strength puzzle solver + tests

* Add twitch chat integration so that viewers can talk to the AI (trivial once the twitch integration for ads is set up)

* Add a tool for spinning around to find wild pokemon
* Add a tool to rearrange the team
* Add a tool to use items
* Generate the overworld map legend dynamically
* Some kind of info about PC pokemon/items?

* Put the emulator on a separate process entirely to fix the remaning async audio issues.

### Backlog
* Numerical coords on screen? Dots to show past steps? A grid to show collisions? Maybe when I have tests set up. I'm convinced that the screenshot is effectively useless in the overworld.
* Some better way of doing RAG that doesn't involve reading everything into memory would be nice. Might need to switch DBs for this. Could also offer to delete LTM after 1000 iterations without retrieval to make this more efficient.
* Tool for using fly

## Junjo Thoughts
* Visualization is not idempotent because the dot file changes
* Subflow visualizations don't have consistent file names
* Trivial subgraphs with a single node and no edges don't display anything
