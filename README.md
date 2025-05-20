# ai-plays-pokemon

## TODOs in rough order of importance

* Only update entities if they're new or you're standing next to them

* Add summary memory with decay -- Fixed size, max(age*decay_rate) drops off first
* Add long term memory with retrieval and decay -- Asks to delete after N iterations without retrieval

* Add automated backups
* Add the initial game state to the output folder

* Make entitie memories into a single DB table?

* Add player/party information, including the current level cap (remove from system prompt)

* Fix navigation when Pikachu is on screen. I think bumping into it breaks the existing flow.

* Add a grid to the overworld screen and overlay collisions

* Subgraphs for the battle, text, and overworld conditions
* Add proper source/sink nodes for graphs that need them
* Improve separation of responsibilities
* Add tests to everything

* Make the critic tool part of the overworld navigation step?
* Add a tool to select moves or swap pokemon in battle, or use a ball in non-trainer battles
* Add a tool for spinning around to find wild pokemon
* Some kind of info about items and PC pokemon
* Add a tool to rearrange the team
* Add a tool to name things
* Tool for using fly
* Tool to use items

* Subgraphs for different battle types (e.g. Safari Zone)? Battle type is at 0xD05A, and the move menus are at 0xCCDB

* Add strength boulders to map screen
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
  * 00:d718 wLastBlackoutMap  - Useful for a "go back for healing" tool? Could get complicated.
  * 00:d719 wDestinationMap
  * 00:cd6b wJoyIgnore - Better way of handling waits between button presses?
* Test Junjo for editing state lists in place
