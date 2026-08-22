# Project Philosophy

## Philosophy

### A Spectrum of Pokémon Solvers

There is a long history of people trying to solve Pokémon programmatically. I'd like to frame these attempts on a spectrum of the degree of autonomy that the various approaches allow.

On the low end of the autonomy spectrum, you have tool assisted speedrun bots [like this one](https://github.com/alexkara15/PokeBot/tree/master), or [MartSnack's](https://www.youtube.com/@martsnack) system to play Pokémon using a predefined series of button presses. The defining feature here is a kind of fatalism. The whole arc of the game is known in advance and proceeds exactly as planned from the initial state to the end of the game. There may be some tolerance for randomness, but the bigger picture is nearly identical every time.

Slightly higher in autonomy are reinforcement learning (RL) algorithms like the [PokeRL](https://drubinstein.github.io/pokerl/) project, which splits the game into "episodes," defines a route between them, and uses RL and a swarm of agents to find an optimal policy for each episode. This has much higher tolerance for uncertainty than the fatalistic approaches we discussed before, but still requires a high level plan that has to be optimized in stages.

At the high end of the autonomy spectrum sits the holy grail: An agent that interacts in real time with the emulator in a recurrent loop, with no parsing, tools, or information beyond what's currently visible on screen. This, I believe, was the original goal of the [Claude Plays Pokémon](https://www.twitch.tv/claudeplaysPokémon) (CPP) benchmark, but even the most expensive frontier models struggle with this task, and none of them work in anything approaching real time. To make any progress at all, CPP required access to the ROM state, a memory system, a summarizer for long context, and a simple navigation tool. [Gemini Plays Pokémon](https://www.twitch.tv/gemini_plays_Pokémon) (GPP) went further still and incorporated a minimap to help with the model's lack of spatial awareness. GPP was [criticized by some](https://arstechnica.com/ai/2025/05/why-google-geminis-Pokémon-success-isnt-all-its-cracked-up-to-be/) for this "harness" that it used to beat the game, but my contention in this project is that GPP's harness didn't go far enough!

### My Approach

My approach to solving Pokémon Yellow Legacy combines freedom with constraint, sitting firmly in the middle of the autonomy spectrum. I want the LLM to make all the high-level decisions, but I don't need it to determine every individual button press. The flow of the game remains unpredictable, but the AI is tightly bound in a workflow to keep it focused and safe. The idea here is that of a production application. LLMs are expensive and a source of uncertainty. You only want to use them when you have to, and in a way where their output space is bounded and can be validated.

An example will make this more clear: The first decision you make in Pokémon is what to name your character. Entering even a short name requires dozens of button presses. Asking a vision model to handle the entire sequence would require repeated screenshots and button selections, with each step creating another opportunity for a mistake.

My approach to this problem is to simply ask the model for the name, since that's the decision we care about, then use a deterministic algorithm to submit the required button presses to the emulator. This reduces the task to one model call, guarantees that a valid response is entered correctly, and runs much faster and more cheaply.

Naming is a trivial example, but the same logic applies for navigation and selecting options in battles. We don't need the AI to take every single step, only to tell us where it wants to go. We don't need the AI to press seven buttons to throw a PokéBall, only to tell us to throw it. Breaking down the gameplay into these discrete units of activity allows us to use smaller models, making the project cheaper overall. Cheaper models also run faster, making for a better viewing experience. The final advantage to this approach is that these discrete actions are far easier to test and tweak than monolithic agentic prompts, and their side effects are limited by the constraints we build around them.

Fundamentally the approach here is to let the agent do the thinking and offload the mechanical work to safe, deterministic algorithms. The rest of this page will discuss the core design decisions that were made to build this workflow and overcome the inherent limitations of LLMs.

## Core Design Concerns

Given that the core philosophy here is "freedom within constraint," we need an orchestration system to control the state of our AI agent. This orchestration system needs to meet the following criteria:

- It must run asynchronously so slow model calls, navigation, database access, and other application work do not interrupt emulation. PyBoy is not natively async, so a dedicated worker thread owns the emulator and exposes a small asynchronous controller to the rest of the application.
- Interfaces between the various layers of the application need to be validated and type-safe or the application will fall into chaos. These interfaces include:
  - The [parsers](/emulator/parsers/) that read the raw game memory and turn it into the usable game state object.
  - Pydantic AI's typed agent contexts, function-tool arguments, and structured model responses.
  - The [repository pattern](/database/) used to read objects from and write objects to the SQLite database.
  - The [backup service](/backup.py) that serializes states to and deserializes states from the disk.
  - The [background server](/streaming/server.py) that displays agent and game state on an HTML page.
- It must be lightweight and promote modular code. We need to be able to add or rearrange agents, tools, and deterministic services as our understanding of the game evolves.

The application is organized around three gameplay domains: overworld navigation, battles, and text interactions. A typed dispatcher selects the current domain, and all three handlers use one shared context containing live agent state and the emulator. Each handler prepares only its own run-local observations and focused tool registry. Those tools expose a thin model-facing interface, while separate deterministic services handle the underlying game mechanics.

An agent may use several tools within its domain before returning control to the dispatcher. Tool results provide fresh observations for the next decision, while only information useful beyond that local loop becomes durable memory. Work that involves no meaningful model decision remains ordinary deterministic code. The [workflow documentation](/docs/workflow.md) describes the complete runtime architecture.

## Overcoming the LLM's Flaws

LLMs have various shortcomings that prevent them from reaching the holy grail of perfect autonomy described above. The two biggest issues we have to deal with are a limited context window and a lack of spatial reasoning ability. We must therefore create some structures to overcome these deficiencies.

### Rolling Memory

The first issue we will tackle is the LLM's finite context window. The agent produces a new memory every iteration, but we cannot keep feeding the entire playthrough back to it forever: the prompt would grow linearly, and so would the cost of every new decision. We also cannot simply delete old memories, because something learned hundreds of iterations ago may still be relevant. The solution is a hierarchical rolling memory that keeps the recent past intact and compresses older history more aggressively as it recedes. If the agent failed to cross a warp thirty seconds ago, it needs the exact details so it doesn't immediately repeat the same mistake. If it crossed Viridian Forest several hours ago, it probably only needs to remember that it reached Pewter City. Older memories can therefore become less detailed without becoming useless.

Each iteration produces a short record of what the model intended to do and what actually happened. The most recent hundred or so records are included in the prompt verbatim. Once this exact tail gets too long, the oldest twenty records are compressed into a single summary. Two twenty-iteration summaries are later compressed into one forty-iteration summary, two forty-iteration summaries become one eighty-iteration summary, and so on.

```
OLD                                                                      NEW
[1-160 summary] [161-240 summary] [241-280 summary] [281-300 summary] [301] [302] ... [400]
      160               80                40                20             exact memories
```

This means the amount of memory included in the prompt grows logarithmically while the detailed recent tail stays roughly the same size. This does tend to increase API costs over time, but the growth is negligible compared to the total size of all the other context in the prompt.

### Mapping

The other major shortcoming of LLMs in Pokémon is their lack of spatial reasoning ability. The key difference that allowed GPP to beat Pokémon where CPP failed (and the reason it was criticized) was the inclusion of a minimap that generated itself as the player walked around. My approach here is similar to what I imagine GPP did.

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

This map helps the AI understand its surroundings far better than by simply looking at the game screen. It also comes with an index of all the sprites, signs, objects, and warp tiles that the player has currently seen on it.

You will notice that the tile characters chosen above are unusual Unicode characters, and there is a reason for this: Each tile must be exactly one token that doesn't combine with any of its neighbours. LLMs read tokens, not individual characters. If I were to use "w" to represent water, then three water tiles "www" would get consolidated into a single token, different from the original "w" token. This messes with the model's ability to recognize and count tiles, so we have to ensure that the tiles don't combine. [There is a test](/common/tests/integration/test_enums.py) that validates this for us.

### What About Vision?

Attentive readers will note that I have not said anything about editing the emulator's screenshot with additional information to improve the model's performance. This is something that other projects have included (e.g. by adding coordinates, colour coding, or borders to each tile in the image), but I did not find that it was necessary for my approach. The model sees the raw screenshot from the game in every prompt, but its inclusion doesn't seem to make much difference given the huge amount of information provided by the game state and overworld map.

## Conclusion

This project uses Pokémon to illustrate the difference between intelligence and execution. The relevant question is not whether an agent has a harness, but what decisions that harness takes away. A predefined route produces reliable gameplay precisely by eliminating meaningful choice, whereas our agent is free to decide its own route, relying on the rest of the application only to carry out those decisions correctly. Asking a model to perform every low-level action does not make it more autonomous; it only makes the system slower, more expensive, and less reliable. The real work is finding the correct boundary between what the model should decide and what ordinary software should execute. Finding that boundary was extremely fun, leading me into the deepest levels of one of my favourite games and exposing me to all of its insane idiosyncrasies first-hand. That process pushed the limits of my own understanding, and I am tremendously proud of the result.
