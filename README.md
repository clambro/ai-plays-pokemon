# ai-plays-pokemon

## TODOs in rough order of importance

### Core Functionality
Done?

### Clean-Up, Refactoring, and Testing
* Include the inventory in the player info or it will buy pokeballs forever
* In the overworld warp, mention if the player has not visted a given map yet.
* Move the check for animations to finish into the press buttons method and make it only do one button press at a time instead of a list. More stable, and I'm not using the list logic anyway.

* Add unit/integration tests
    * Test background tile and blocking generation from game states for strength boulders and seafoam elevation
    * Test navigation for surfing and cutting trees

* Set up Junjo server and opentelemetry

* Add node tests for the LLM calls
    * Ensure that the player/rival names are at most 7 characters instead of 10
    * Tests for selecting tools
    * Tests for multiple button presses

### Useful Tools and Additions
* Detailed subflow for battles. Battle type (e.g. trainer, safari zone, etc.) is at 0xD05A, and the move menus are at 0xCCDB
* Add tools to select moves or swap pokemon in battle, or use a ball in non-trainer battles

* Add a tool for spinning around to find wild pokemon
* Add a tool to rearrange the team
* Tool to use items
* Generate the overworld map legend dynamically
* Some kind of info about PC pokemon/items?

### Longer-Term Issues that I'll Have to Tackle Eventually
* Add strength boulders to map screen -- 00:d717 wBoulderSpriteIndex
* Tool for using fly
* Handle surfing in navigation
* Navigation should avoid grass tiles where possible
* Add a strength puzzle solver
* Add team rocket spin puzzle tiles to navigation
* Does riding the bike break navigation?

* Custom music player to avoid the little async issues?

## Notes
* Numerical coords on screen? Dots to show past steps? A grid to show collisions? Maybe when I have tests set up. I'm convinced that the screenshot is effectively useless in the overworld.
* Some better way of doing RAG that doesn't involve reading everything into memory would be nice. Might need to switch DBs for this. Could also offer to delete LTM after 1000 iterations without retrieval to make this more efficient.

## Junjo Thoughts
* If I edit a list in place does it change it in the state?
* Visualization is not idempotent because the dot file changes
* Subflow visualizations don't have consistent file names
* Trivial subgraphs with a single node and no edges don't display anything
