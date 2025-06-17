# ai-plays-pokemon

## TODOs in rough order of importance

### Core Functionality
Done?

### Clean-Up, Refactoring, and Testing
* Add unit/integration tests

* Set up Junjo server and opentelemetry

* Add node tests for the LLM calls

### Useful Tools and Additions
* Get all accessible tiles in the nav tool, and point out the map boundary tiles
* Add a coords data type

* Add a grid to the overworld screen and overlay collisions

* Detailed subflow for battles. Battle type (e.g. trainer, safari zone, etc.) is at 0xD05A, and the move menus are at 0xCCDB

* Special navigation tool for moving between maps?
* Add a tool to select moves or swap pokemon in battle, or use a ball in non-trainer battles
* Add a tool for spinning around to find wild pokemon
* Some kind of info about items and PC pokemon
* Add a tool to rearrange the team
* Tool to use items
* Generate the overworld map legend dynamically
* Adding importance to goals might be helpful

### Longer-Term Issues that I'll Have to Tackle Eventually
* Add strength boulders to map screen -- 00:d717 wBoulderSpriteIndex
* Tool for using fly
* Handle surfing in navigation
* Navigation should avoid grass tiles where possible
* Add a strength puzzle solver
* Add event flags for tracking progress (00:d746 wEventFlags -- check the decomp for details)
* Add team rocket spin puzzle tiles to navigation

* Some kind of twitch frontend
* Custom music player to avoid the little async issues?

## Notes
* Numerical coords on screen? Dots to show past steps? Maybe when I have tests set up.
* Some better way of doing RAG that doesn't involve reading everything into memory would be nice. Might need to switch DBs for this. Could also offer to delete LTM after 1000 iterations without retrieval to make this more efficient.

## Junjo Thoughts
* If I edit a list in place does it change it in the state?
* Visualization is not idempotent because the dot file changes
* Subflow visualizations don't have consistent file names
* Trivial subgraphs with a single node and no edges don't display anything
