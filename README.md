# ai-plays-pokemon

## TODOs in rough order of importance

### Core Functionality
Done?

### Clean-Up, Refactoring, and Testing
* Make entity memories into a single DB table?

* Fix navigation when Pikachu is on screen. I think bumping into it breaks the existing flow.

* Find some better way to handle the fact that the three memory types almost always appear together
* Subgraphs for the battle, text, and overworld conditions
* Add proper source/sink nodes for graphs that need them
* Add names to all the prompts
* Improve separation of responsibilities and general refactor
* Set up Junjo server and opentelemetry
* Add tests to everything

### Useful Tools and Additions
* Detailed subflow for battles
* Make the critic tool part of the overworld navigation step? Includes functionality for determining which tools are available at any given iteration.
* Add a tool to select moves or swap pokemon in battle, or use a ball in non-trainer battles
* Add a tool for spinning around to find wild pokemon
* Some kind of info about items and PC pokemon
* Add a tool to rearrange the team
* Add a tool to name things
* Tool to use items
* Add a grid to the overworld screen and overlay collisions
* Generate the overworld map legend dynamically

### Longer-Term Issues that I'll Have to Tackle Eventually
* Subgraphs for different battle types (e.g. Safari Zone)? Battle type is at 0xD05A, and the move menus are at 0xCCDB

* Add strength boulders to map screen
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
* Look into these:
  * 00:d717 wBoulderSpriteIndex
* Test Junjo for editing state lists in place
* Some better way of doing RAG that doesn't involve reading everything into memory. Might need to switch DBs for that.
