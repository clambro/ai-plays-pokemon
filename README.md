# ai-plays-pokemon

## TODOs in rough order of importance

### Core Functionality
* Add automated backups
* Add the initial game state to the output folder

### Clean-Up, Refactoring, and Testing
* Make entity memories into a single DB table?

* Add player/party information, including the current level cap (remove from system prompt)

* Fix navigation when Pikachu is on screen. I think bumping into it breaks the existing flow.

* Add a grid to the overworld screen and overlay collisions

* Combine memories into a single object so you're not adding them all to prompts separately
* Subgraphs for the battle, text, and overworld conditions
* Add proper source/sink nodes for graphs that need them
* Add names to all the prompts
* Improve separation of responsibilities
* Add tests to everything
* Make the critic tool part of the overworld navigation step? Includes functionality for determining which tools are available at any given iteration.

### Useful Tools and Additions
* Detailed subflow for battles
* Add a tool to select moves or swap pokemon in battle, or use a ball in non-trainer battles
* Add a tool for spinning around to find wild pokemon
* Some kind of info about items and PC pokemon
* Add a tool to rearrange the team
* Add a tool to name things
* Tool to use items

### Longer-Term Issues that I'll Have to Tackle Eventually
* Subgraphs for different battle types (e.g. Safari Zone)? Battle type is at 0xD05A, and the move menus are at 0xCCDB

* Do we need to be able to delete long term memory? Maybe ask to delete very old files?
* Add strength boulders to map screen
* Tool for using fly
* Handle surfing in navigation
* Navigation should avoid grass tiles where possible
* Add a strength puzzle solver?
* Set up Junjo server and opentelemetry and move the LLM stuff there
* Add event flags for tracking progress (00:d746 wEventFlags -- check the decomp for details)
* Add team rocket spin puzzle tiles to navigation

* Some kind of twitch frontend

## Notes
* Might have to drop Pikachu from the map view. I could see that maybe causing problems.
* Numerical coords on screen? Dots to show past steps? Maybe when I have tests set up.
* Look into these:
  * 00:d717 wBoulderSpriteIndex
  * 00:d718 wLastBlackoutMap - Useful for a "go back for healing" tool? Could get complicated.
  * 00:d719 wDestinationMap
  * 00:cd6b wJoyIgnore - Better way of handling waits between button presses?
* Test Junjo for editing state lists in place
* Might be nice to generate the overworld map legend dynamically
* Some better way of doing RAG that doesn't involve reading everything into memory. Might need to switch DBs for that.
