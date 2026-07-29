# Project Philosophy

## Philosophy

### A Spectrum of Pokémon Solvers

There is a long history of people trying to solve Pokémon programatically. I'd like to frame these attempts on a spectrum of the degree of autonomy that the various approaches allow.

On the low end of the autonomy spectrum, you have tool assisted speedrun bots [like this one](https://github.com/alexkara15/PokeBot/tree/master), or [MartSnack's](https://www.youtube.com/@martsnack) extremely cool attempts to play Pokémon using a predefined series of button presses. The defining feature here is a kind of fatalism. The whole arc of the game is known in advance and proceeds exactly as planned from the initial state to the end of the game. There may be some tolerance for randomness, but the bigger picture is nearly identical every time.

Slightly higher in autonomy are reinforcement learning (RL) algorithms like the [PokeRL](https://drubinstein.github.io/pokerl/) project, which splits the game into "episodes," defines a route between them, and uses RL and a swarm of agents to find an optimal policy for each episode. This has much higher tolerance for uncertainty than the fatalistic approaches we discussed before, but still requires a high level plan that has to be optimized in stages.

At the high end of the autonomy spectrum sits the holy grail: A totally autonomous agent that interacts in real time with the emulator in a recurrent loop, with no parsing, tools, or information beyond what's currently visible on screen. This, I believe, was the original goal of the [Claude Plays Pokémon](https://www.twitch.tv/claudeplaysPokémon) (CPP) benchmark, but modern LLMs are nowhere near capable of this feat. To make any progress at all, CPP required access to the ROM state, a memory system, a summarizer for long context, and a simple navigation tool. [Gemini Plays Pokémon](https://www.twitch.tv/gemini_plays_Pokémon) (GPP) went further still and incorporated a minimap to help with the model's lack of spatial awareness. GPP was [criticized by some](https://arstechnica.com/ai/2025/05/why-google-geminis-Pokémon-success-isnt-all-its-cracked-up-to-be/) for this "harness" that it used to beat the game, but my contention in this project is that GPP's harness didn't go far enough!

### My Approach

My approach to solving Pokémon Yellow Legacy combines freedom with constraint, sitting firmly in the middle of the autonomy spectrum. I want the LLM to make all the high-level decisions, but I don't need it to determine every individual button press. The flow of the game remains entirely unpredictable, but the AI is tightly bound in a workflow to keep it focused and safe. The idea here is that of a production application. LLMs are expensive and a source of uncertainty. You only want to use them when you have to, and in a way where their output space is bounded and can be validated.

An example will make this more clear: The first decision you make in Pokémon is what to name your character. Entering even a short name requires dozens of button presses. Asking a vision model to handle the entire sequence would require repeated screenshots and button selections, with each step creating another opportunity for a mistake.

My approach to the above problem is to simply ask the model for the name, since that's the decision we care about, then use a deterministic algorithm to submit the required button presses to the emulator. This reduces the task to one model call, guarantees that a valid response is entered correctly, and runs much faster and more cheaply.

Naming is a trivial example that doesn't happen that often in game, but the same logic applies for navigation and selecting options in battles. We don't need the AI to take every single step, just tell us where it wants to go. We don't need the AI to press seven buttons to throw a PokéBall, just tell us to throw it. Breaking down the gameplay into these discrete units of activity allows us to use smaller models, making the project cheaper overall. These cheaper model also run faster, thus making for a better viewing experience. The final advantage to this approach is that these discrete actions are far, far easier to test and tweak than monolithic agentic prompts, and their side effects are limited by the constraints we build around them.

Fundamentally the approach here is to let the agent do the thinking and offload the mechanical work to safe, deterministic algorithms. The rest of this page will discuss the core design decisions that were made to build this workflow and overcome the inherent limitations of LLMs.

## Core Design Concerns

Given that the core philosophy here is "freedom within constraint," we need an orchestration system to control the state of our AI agent. This orchestration system needs to meet the following criteria:

- It must run asynchronously so slow model calls, navigation, database access, and other application work do not interrupt emulation. PyBoy is not natively async, so a dedicated worker thread owns the emulator and exposes a small asynchronous controller to the rest of the application.
- Interfaces between the various layers of the application need to be validated and type-safe or the application will fall into chaos. These interfaces include:
  - The [parsers](/emulator/parsers/) that read the raw game memory and turn it into the usable game state object.
  - Pydantic AI's typed agent contexts, function-tool arguments, and structured model responses.
  - The [repository pattern](/database/) used to read objects from and write objects to the SQLite database.
  - The [backup service](/common/backup_service.py) that serializes states to and deserializes states from the disk.
  - The [background server](/streaming/server.py) that displays the workflow and game states on an HTML page.
- It must be lightweight and promote modular code. We need to be able to add or rearrange agents, tools, and deterministic services as our understanding of the game evolves.

The application is migrating from Junjo graphs to Pydantic AI agents organized around three gameplay domains: overworld navigation, battles, and text interactions. Shared deterministic preparation loads the memory, goals, game state, and other context needed by a domain before its agent runs. Each agent has its own typed context and a focused registry of tools. Those tools expose a thin model-facing interface while separate deterministic services handle the underlying game mechanics.

An agent may use several tools within its domain before returning control to the outer workflow. Tool results provide fresh observations for the next decision, while only information useful beyond that local loop becomes durable memory. Work that involves no meaningful model decision remains ordinary deterministic code. The migration is phased so the application remains usable as each domain adopts this structure; the [workflow documentation](/docs/workflow.md) describes the current hybrid implementation.

## Overcoming the LLM's Flaws

LLMs have various shortcomings that prevent them from reaching the holy grail of perfect autonomy described above. The two greatest issues we have to deal with are a limited context window, and a lack of spatial reasoning ability. Like CPP and GPP then, we must create some tools and structures to overcome these deficiencies.

### Rolling and Long-Term Memory

The first issue we will tackle is the LLM's finite context window, which stops it from holding an entire playthrough in detail. Replaying every previous action in every prompt would grow continuously more expensive, while simply discarding old actions would eventually erase important context. The project handles these two needs with rolling memory for chronological history and long-term memory for agent-maintained notes.

Note: Pretty much all the constants I mention below are default values that can be edited in [`common/constants.py`](/common/constants.py).

#### Rolling Memory

One raw memory block represents one complete top-level workflow iteration. Every thought, observation, and tool result produced during that iteration is appended to the same mutable block in order. The block is finalized only after the workflow finishes, at which point it is written once to SQLite and the next iteration begins with a new block.

The raw table is the permanent source of truth: compaction never deletes or rewrites it. The active agent state carries the current block and the bounded view needed for the current workflow, but only the current block is serialized with the state. Because database files are included in backups, the complete history is restored without serializing it into every agent-state snapshot.

Prompts receive a chronological mixture of summaries and exact recent blocks. Once two batches of twenty raw blocks are available, the older batch is compressed into a level-one summary while the newer twenty remain exact. Adjacent summaries at the same level are later combined into a parent summary covering both ranges. Repeating this process creates a binary hierarchy in which older history occupies progressively less space and recent history retains full detail. Every entry includes the iteration or iteration range it covers, so the prompt view remains ordered and gap-free.

The live HTML activity log uses only the exact raw working set and the unfinished current block. It updates whenever memory is appended and never displays the derived summaries, so compaction does not replace the recent on-screen log.

#### The Long-Term Memory

The final kind of memory given to the model is the long-term memory. This is effectively a database table of documents that the model can create and update every ten iterations. Each document has a unique title. When refreshing its long-term memory, the model sees the available titles and chooses which documents it wants to recall. Those documents are then loaded directly by title. Long term memories are never deleted (though I may change that if it becomes a problem).

The model is encouraged to summarize memories if they go over a certain length, but there are no hard rules for what it can put in there. Common topics include notes on maps, characters, party members, goals, etc. Up to ten relevant memories are selected every ten iterations, and these memories take up roughly 2000 tokens in total.

### Mapping

Aside from memory, the other major shortcoming of LLMs in Pokémon is their lack of spatial reasoning ability. The key difference that allowed GPP to beat Pokémon where CPP failed (and the reason it was criticized) was the inclusion of a minimap that generated itself as the player walked around any given map. My approach here is somewhat similar to what I imagine GPP did, though, as mentioned in the FAQ, I was not aware of GPP when I started this project.

A minimap for each map ID is constructed using ASCII characters and stored in the database. The map is initialized as a rectangle of undiscovered territory the same size as the map in the game's memory, and with every step the player takes in game, the map is updated using whatever information is available on screen. Here is a sample map for Pallet Town:

```
∙∙∙▓∙∙∙∙∙▓※※▓∙∙∙∙∙▓∙
▓▓▓▓▓▓▓▓▓▓※※▓▓▓▓▓▓▓▓
▓∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙▓
▓∙∙∙▓▓▓▓∙∙∙∙▓▓▓▓∙∙∙▓
▓∙∙∙▓▓▓▓∙∙∙∙▓▓▓▓∙∙∙▓
▓∙∙‼▓∞▓▓∙∙∙‼▓∞▓▓∙∙∙▓
▓∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙▓
▓∙∙∙∙∙∙∙☺♦∙∙∙∙∙∙∙∙∙▓
▓∙∙∙◆∙∙∙∙∙▓▓▓▓▓▓∙∙∙▓
▓∙∙∙▓▓▓‼∙∙▓▓▓▓▓▓∙∙∙▓
▓∙∙∙∙∙∙∙∙∙▓▓▓▓▓▓∙∙∙▓
▓∙∙∙∙∙∙∙∙∙▓▓∞▓▓▓∙∙∙▓
▓∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙▓
▓∙∙∙∙∙∙∙∙∙▓▓▓‼▓▓∙∙∙▓
▓∙∙∙≈≈≈≈◆∙∙∙∙∙∙∙∙∙∙▓
░░░∙≈≈≈≈∙∙∙∙∙∙∙∙∙∙∙▓
░░░∙≈≈≈≈∙∙∙∙∙∙∙∙∙∙∙▓
░░░∙≈≈≈≈▓▓▓▓▓▓▓▓▓▓▓▓

Legend:
░ Undiscovered
∙ Free tile
☺ Player
♦ Pikachu
▓ Barrier/wall
≈ Water
※ Tall grass
◆ Sprite
∞ Warp
‼ Sign
```

This map (plus a plethora of additional notes in the [overworld map prompt](/overworld_map/prompts.py)) helps the AI understand its surroundings far better than by simply looking at the game screen. It also comes with an index of all the sprites, signs, and warp tiles that the player has currently seen on it. The workflow has the ability to add persistent notes to each of these entities as it approaches and interacts with them.

You will notice that the tile characters chosen above are unusual Unicode characters, and there is a reason for this: Each tile must be exactly one token that doesn't combine with any of its neighbours. LLMs read tokens, not individual characters. If I were to use "w" to represent water, then three water tiles "www" would get consolidated into a single token, different from the original "w" token. This completely breaks the model's ability to count tiles, so we have to ensure that the tiles don't combine. [There is a test](/common/tests/integration/test_enums.py) that validates this for us.

### What About Vision?

Attentive readers will note that I have not said anything about editing the emulator's screenshot with additional information to improve the model's performance. This is something that other projects have included (e.g. by adding coordinates, colour coding, or borders to each tile in the image), but I did not find that it was necessary for my approach. The model sees the raw screenshot from the game in nearly every prompt, but it is borderline useless for most of them given the huge amount of information provided to it by the overworld map described above. I may go back and edit the screenshot logic to increase the information it contains if I find that the model is struggling somewhere, but thus far it hasn't seemed necessary to justify the level of work required.

## Conclusion

Kudos to you if you've actually read this far. I don't have much in the way of concluding remarks except to say that this project was tremendously fun to work on. I got to dig into the deepest levels of one of my favourite games and experience all of its insane idiosyncrasies first-hand. I've pushed the limits of my own work experience and delivered something that I feel truly proud of. Hopefully you learned a little something from digging through this project. I certainly did.
