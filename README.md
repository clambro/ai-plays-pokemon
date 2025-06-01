# ai-plays-pokemon

## TODOs in rough order of importance

### Core Functionality
Done?

### Clean-Up, Refactoring, and Testing
* Parallelize nodes that belong in parallel
* In the overworld handler, we should have one node for loading the map and another node for updating it. The logic is weirdly split at the moment. Also rename the UpdateAgentStoreNode to PrepareAgentStoreNode.

* Make long term memory retrieval and updates happen either every ten iterations, or when the handler changes
* The summary memory keeps adding duplicates. Stop that.
* I think the raw memory is way too long. It's 75% of the whole prompt and full of noise.

* Add names to all the prompts

* Get Gemini to give some general architecture refactoring suggestions

* Set up Junjo server and opentelemetry

* Add tests to everything

* Fix the navigation tool: When Pikachu is on screen, bumping into it breaks the existing flow.

* Use proper init files and relative imports within packages

### Useful Tools and Additions
* Add a tool to name things

* Detailed subflow for battles
* Make the critic tool part of the overworld navigation step? Includes functionality for determining which tools are available at any given iteration.
* Add a tool to select moves or swap pokemon in battle, or use a ball in non-trainer battles
* Add a tool for spinning around to find wild pokemon
* Some kind of info about items and PC pokemon
* Add a tool to rearrange the team
* Tool to use items
* Add a grid to the overworld screen and overlay collisions
* Generate the overworld map legend dynamically

### Longer-Term Issues that I'll Have to Tackle Eventually
* Subgraphs for different battle types (e.g. Safari Zone)? Battle type is at 0xD05A, and the move menus are at 0xCCDB

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
* Some better way of doing RAG that doesn't involve reading everything into memory would be nice. Might need to switch DBs for this.

## Junjo Thoughts
* If I edit a list in place does it change it in the state?
* Visualization is not idempotent because the dot file changes
* Subflow visualizations don't have consistent file names
* Trivial subgraphs with a single node and no edges don't display anything
