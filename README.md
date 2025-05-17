# ai-plays-pokemon

## TODOs in rough order of importance

* Add summary memory with decay -- Fixed size, max(age*decay_rate) drops off first
* Add long term memory with retrieval and decay -- Asks to delete after N iterations without retrieval

* Add player/party information
* Add connecting maps to the overworld maps
* Add signs to the overworld maps

* Add automated backups
* Add the initial game state to the output folder

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
* Set up Junjo server and opentelemetry and move the LLM stuff there

* Some kind of twitch frontend

### Notes
* Might have to drop Pikachu from the map view. I could see that maybe causing problems.
* Numerical coords on screen? Dots to show past steps? Maybe when I have tests set up.
* Maybe put the critic model on a parallel thread? It's really slow.
