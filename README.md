# ai-plays-pokemon

## TODOs in rough order of importance

### Required for Release
* Detailed subflow for battles. Battle type (e.g. trainer, safari zone, etc.) is at 0xD05A, and the move menus are at 0xCCDB
* Add tools to select moves or swap pokemon in battle, or use a ball in non-trainer battles

* Add strength boulders to map screen -- 00:d717 wBoulderSpriteIndex
* Handle surfing in navigation + tests
* Handle cut trees in navigation + tests
* Handle the bike in navigation + tests
* Handle spin tiles in navigation + tests

* Test background tile and blocking generation from game states for strength boulders and seafoam elevation

* Set up Junjo server and opentelemetry

* Add node tests for the LLM calls
    * Ensure that the player/rival names are at most 7 characters instead of 10
    * Tests for selecting tools
    * Tests for multiple button presses

* Some kind of VM to run everything on

### Nice to Have
* Put the emulator on a separate process entirely to fix the remaning async issues.
* Navigation should avoid grass tiles where possible + tests

* Add a strength puzzle solver + tests

* Add a tool for spinning around to find wild pokemon
* Add a tool to rearrange the team
* Tool to use items
* Generate the overworld map legend dynamically
* Some kind of info about PC pokemon/items?

### Backlog
* Numerical coords on screen? Dots to show past steps? A grid to show collisions? Maybe when I have tests set up. I'm convinced that the screenshot is effectively useless in the overworld.
* Some better way of doing RAG that doesn't involve reading everything into memory would be nice. Might need to switch DBs for this. Could also offer to delete LTM after 1000 iterations without retrieval to make this more efficient.
* Tool for using fly

## Junjo Thoughts
* Visualization is not idempotent because the dot file changes
* Subflow visualizations don't have consistent file names
* Trivial subgraphs with a single node and no edges don't display anything
