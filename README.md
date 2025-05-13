# ai-plays-pokemon

## TODOs in rough order of importance
* Tile constants should be an enum

* Add a critic model
* Add automated backups
* Add the initial game state to the output folder

* Add summary memory with decay -- Fixed size, max(age*decay_rate) drops off first
* Add long term memory with retrieval and decay -- Asks to delete after N iterations without retrieval

* Add player/party information

* Add a grid to the overworld screen and overlay collisions

* Subgraphs for the battle, text, and overworld conditions
* Improve separation of responsibilities
* Add tests to everything

* Add a tool to select moves or swap pokemon in battle
* Add a tool for spinning around to find wild pokemon
* Some kind of info about items and PC pokemon
* Add a tool to rearrange the team
* Add a tool to name things
* Tool for using fly

* Subgraphs for different battle types (e.g. Safari Zone)? Battle type is at 0xD05A, and the move menus are at 0xCCDB

* Add strength boulders to map screen
* Handle surfing in navigation
* Add a strength puzzle solver?
* Token counts, telemetry, and better logging

* Some kind of twitch frontend

### Notes
* Might have to drop Pikachu from the map view. I could see that maybe causing problems.
* Can we skip the file storage and do everything in memory? Or maybe sqlite?
* Numerical coords on screen? Dots to show past steps? Maybe when I have tests set up.
