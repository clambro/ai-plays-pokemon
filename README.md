# ai-plays-pokemon

## TODOs
### Core
* Add a grid to the overworld screen and overlay collisions
* Add summary memory with decay
* Add long term memory with retrieval and decay
* Add player/party information
* Add strength boulders to map screen
* Add automated backups
* Add the initial game state to the output folder
* Add precommits for sorting imports and linting and whatnot
* Add a critic model
* Handle surfing in navigation

### Useful
* Add tests to everything
* Subgraphs for the battle, text, and overworld conditions
* Improve separation of responsibilities
* Add a tool to rearrange the team
* Add a tool to select moves or swap pokemon in battle
* Add a tool to name things
* Debug logger for prompts with log level set in main
* Some kind of info about items and PC pokemon
* Add a strength puzzle solver?
* Add a tool for spinning around to find wild pokemon
* Token counts and telemetry
* Tool for using fly
* Tile constants should be an enum

### Notes
* Might have to drop Pikachu from the map view. I could see that maybe causing problems.
* Can we skip the file storage and do everything in memory? Or maybe sqlite?
