# ai-plays-pokemon

## Licence & Affiliation Notice

All original source code in this repository is released under the [MIT Licence](LICENSE).

This is an unofficial, fan-made project, for educational purposes only. The code in this repository is designed to work with Pokemon games but does not include any ROMs, save states, or game sprites. Users are responsible for ensuring they own legitimate copies of Pokémon games and comply with all applicable laws and terms of service.

"Pokémon", Pokémon character names, and all related marks are owned by Nintendo, Game Freak, Creatures Inc., and The Pokémon Company. I am not affiliated with, endorsed, sponsored, or specifically approved by any of these entities.

---

## TODOs in rough order of importance

### Required for Release
* Some kind of VM to run everything on
* A proper readme file
* Some kind of post about the philosophy behind this and an explanation of how it all works

### Nice to Have
* Twitch integration for dealing with ad breaks. I won't be able to schedule them myself unless I reach the affiliate tier, so for now just check if one is coming in the next ten seconds and wait if so.
* Add twitch chat integration so that viewers can talk to the AI (trivial once the twitch integration for ads is set up)

* Add a tool for spinning around to find wild pokemon
* Add a tool to rearrange the team
* Add a tool to use items
* Some kind of info about PC pokemon/items?

* Put the emulator on a separate process entirely to fix the remaning async audio issues.

* Some better way of doing RAG that doesn't involve reading everything into memory would be nice. Might need to switch DBs for this. Could also offer to delete LTM after 1000 iterations without retrieval to make this more efficient.

* Tool for using fly
