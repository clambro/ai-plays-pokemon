# Project Philosophy

## Philosophy

### A Spectrum of Pokémon Solvers

There is a long history of people trying to solve Pokémon programatically. I'd like to frame these attempts on a spectrum of the degree of autonomy that the various approaches allow.

On the low end of the autonomy spectrum, you have tool assisted speedrun bots [like this one](https://github.com/alexkara15/PokeBot/tree/master), or [MartSnack's](https://www.youtube.com/@martsnack) extremely cool attempts to play Pokémon using a predefined series of button presses. The defining feature here is a kind of fatalism. The whole arc of the game is known in advance and proceeds exactly as planned from the initial state to the end of the game. There may be some tolerance for randomness, but the bigger picture is nearly identical every time.

Slightly higher in autonomy are reinforcement learning (RL) algorithms like the [PokeRL](https://drubinstein.github.io/pokerl/) project, which splits the game into "episodes," defines a route between them, and uses RL and a swarm of agents to find an optimal policy for each episode. This has much higher tolerance for uncertainty than the fatalistic approaches we discussed before, but still requires a high level plan that has to be optimized in stages.

At the high end of the autonomy spectrum sits the holy grail: A totally autonomous agent that interacts in real time with the emulator in a recurrent loop, with no parsing, tools, or information beyond what's currently visible on screen. This, I believe, was the original goal of the [Claude Plays Pokémon](https://www.twitch.tv/claudeplaysPokémon) (CPP) benchmark, but modern LLMs are nowhere near capable of this feat. To make any progress at all, CPP required access to the ROM state, a memory system, a summarizer for long context, and a simple navigation tool. [Gemini Plays Pokémon](https://www.twitch.tv/gemini_plays_Pokémon) (GPP) went further still and incorporated a minimap to help with the model's lack of spatial awareness. GPP was [criticized by some](https://arstechnica.com/ai/2025/05/why-google-geminis-Pokémon-success-isnt-all-its-cracked-up-to-be/) for this "harness" that it used to beat the game, but my contention in this project is that GPP's harness didn't go far enough!

### My Approach

My approach to solving Pokémon Yellow Legacy combines freedom with constraint, sitting firmly in the middle of the autonomy spectrum. I want the LLM to make all the high-level decisions, but I don't need it to determine every individual button press. The flow of the game remains entirely unpredictable, but the AI is tightly bound in a workflow to keep it focused and safe. The idea here is that of a production application. LLMs are expensive and a source of uncertainty. You only want to use them when you have to, and in a way where their output space is bounded and can be validated.

An example will make this more clear: The first decision you make in Pokémon is what to name your character. Let's say the AI wants to name itself "GEMINI." The shortest sequence to enter this name involves 29 button presses. To do this whole thing with a Gemini model, you would have to use Gemini Pro (because Flash isn't good enough at interpreting the screen). Even if you allowed the model to press multiple buttons per iteration, it would still require several iterations, probably a dozen or so in total. And this is assuming that it didn't make a mistake and have to go back, which it almost certainly would. Or worse, make a mistake and carry on with submitting the name.

My approach to the above problem is to simply ask the model for the name, since that's the decision we care about, then use a deterministic algorithm to submit the required button presses to the emulator. Naming is a task that Gemini Flash Lite can handle no problem, and it takes only one prompt at one-twelfth the price of Gemini Pro. If we assume that the naive approach took a dozen iterations, then this approach is nearly 150x cheaper overall! It also gives a guaranteed correct result and runs much faster.

Naming is a trivial example that doesn't happen that often in game, but the same logic applies for navigation and selecting options in battles. We don't need the AI to take every single step, just tell us where it wants to go. We don't need the AI to press seven buttons to throw a PokéBall, just tell us to throw it. Breaking down the gameplay into these discrete units of activity allows us to use smaller models, making the project cheaper overall. These cheaper model also run faster, thus making for a better viewing experience. The final advantage to this approach is that these discrete actions are far, far easier to test and tweak than monolithic agentic prompts, and their side effects are limited by the constraints we build around them.

Fundamentally the approach here is to let the agent do the thinking and offload the mechanical work to safe, deterministic algorithms. The rest of this page will discuss the core design decisions that were made to build this workflow and overcome the inherent limitations of LLMs.

## Core Design Concerns

Given that the core philosophy here is "freedom within constraint," we need an orchestration system to control the state of our AI agent. This orchestration system needs to meet the following criteria:

- It must run asynchronously. It will be running on the same thread as the PyBoy emulator itself, so we have to make sure it doesn't block emulation.
  - Pyboy is not natively async, so we had to [do some additional work](/emulator/emulator.py) to make it async-safe.
  - This was more of a self-imposed challenge. I could have run PyBoy on a separate thread entirely and added a communication layer between it and the agent, but I wanted the whole thing to run together as if it were a single application.
- Its states must be compatible with Pydantic. The interfaces between the various layers of our application all need to be validated and type-safe or the application will fall into chaos. These interfaces are:
  - The [parsers](/emulator/parsers/) that read the raw game memory and turn it into the usable game state object.
  - The Pydantic integration [in the LLM service](/llm/service.py) that converts the raw JSON string output of the LLMs into validated schemas.
  - The [repository pattern](/database/) used to read objects from and write objects to the SQLite database.
  - The [backup service](/common/backup_service.py) that serializes states to and deserializes states from the disk.
  - The [background server](/streaming/server.py) that displays the workflow and game states on an HTML page.
- It must be lightweight and promote modular code. We need to be able to easily add new nodes to our workflow or rearrange old ones as our needs and understanding of the game evolve. Many orchestration tools impose heavy abstractions that are difficult to debug. That won't work for us.

The orchestration flow used in this project is called [Junjo](https://github.com/mdrideout/junjo), and it meets all of the above criteria. Full disclosure: Junjo was created by a coworker and friend of mine, but he did so out of the exact needs and shortcomings of other workflow orchestrators that I described above. Junjo creates a serializable, stateful, nestable graph (read: constraint) for our AI to operate within. A node-by-node analysis of this graph [is available here](/docs/workflow.md) if you're curious about how it's constructed.

## Overcoming the LLM's Flaws

LLMs have various shortcomings that prevent them from reaching the holy grail of perfect autonomy described above. The two greatest issues we have to deal with are a limited context window, and a lack of spatial reasoning ability. Like CPP and GPP then, we must create some tools and structures to overcome these deficiencies.

### Three Kinds of Memory

The first issue we will tackle is the LLM's finite context window that stops it from holding its entire history in memory. With every iteration of the model, it gains a new memory of what it has done. LLMs have a finite context length, which is the maximum number of tokens that can be used for a single query (~1M tokens for the Gemini 2.5 series). Keeping a rolling log of as much memory as possible would get expensive fast since we pay per token in the query, and we would lose context from older memories once we rolled them over. My solution to this problem is a three-tiered memory architecture that separately handles the immediate past, short-term memories, and long-term memories.

Note: Pretty much all the constants I mention below are default values that can be edited in [`common/constants.py`](/common/constants.py).

#### The Raw Memory

The raw memory is the simplest of the three memory types. This is an ordered dictionary that maps iteration numbers to the AI workflow's raw output for each iteration. It contains 50 elements, and all older memories are simply deleted. The raw memory serves to inform the workflow of its immediate past actions (50 iterations is roughly 15 mins). Given that this raw information is bloated by a lot of the model's self talk, we clip it after relatively few iterations to keep the cost down and reduce potential distractions from excessive context. Lengths differ from iteration to iteration, but the total raw memory size is roughly 6500 tokens.

#### The Summary Memory

The summary memory is the short term memory that gets consolidated from the raw memory. Every 10 iterations, the model is given the chance to create a new summary memory from its raw memories. These are significantly condensed compared to the raw memories. As an example, fighting a trainer battle could eaily take up 20 raw memory slots (say 2500 tokens), whereas a summary of that battle like

> I defeated a SWIMMER's TENTACOOL, HORSEA, and GOLDEEN and earned ¥381. Pikachu grew to level 34 during the battle.

is only about 35 tokens. The fact that the summary memory is so much more dense than the raw memory allows its length to be much longer. We have space for 200 summary memories, and they take up roughly 4000 tokens in total.

The summary memory also has more intelligent rollover logic than the raw memory. When a piece of summary memory is created, it is given an importance score from 1 (trivial) to 5 (critical for progression). When it comes time to bump an old summary memory and add a new one, both age and importance are taken into account so that we keep important memories longer than trivial ones. [The math for that is here](/memory/summary_memory.py) if you're curious.

#### The Long-Term Memory

The final kind of memory given to the model is the long-term memory. This is effectively a database table of documents that the model can create and update every ten iterations. Long-term memories are retrieved based on a combination of semantic similarity to a query, recency, and an importance score similar to the one in the summary memory. The full retrieval algorithm [can be found here](/memory/retrieval_service.py). Long term memories are never deleted (though I may change that if it becomes a problem).

The model is encouraged to summarize memories if they go over a certain length, but there are no hard rules for what it can put in there. Common topics include notes on maps, characters, party members, goals, etc. The long term memory is refreshed with ten new memories every ten iterations, and these memories take up roughly 2000 tokens in total.

### Mapping

Aside from memory, the other major shortcoming of LLMs in Pokémon is their lack of spatial reasoning ability. The key difference that allowed GPP to beat Pokémon where CPP failed (and the reason it was criticized) was the inclusion of a minimap that generated itself as the player walked around any given map. My approach here is somewhat similar to what I imagine GPP did, though, as mentioned in the FAQ, I was not aware of GPP when I started this project.

A minimap for each map ID is constructed using ASCII characters and stored in the database. The map is initialized as a rectangle of undiscovered territory the same size as the map in the game's memory, and with every step the player takes in game, the map is updated using whatever information is available on screen. Here is a sample map for Pallet Town:

```
∙∙∙▉∙∙∙∙∙▉❀❀▉∙∙∙∙∙▉∙
▉▉▉▉▉▉▉▉▉▉❀❀▉▉▉▉▉▉▉▉
▉∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙▉
▉∙∙∙▉▉▉▉∙∙∙∙▉▉▉▉∙∙∙▉
▉∙∙∙▉▉▉▉∙∙∙∙▉▉▉▉∙∙∙▉
▉∙∙‼▉⇆▉▉∙∙∙‼▉⇆▉▉∙∙∙▉
▉∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙▉
▉∙∙∙∙∙∙∙☻◈∙∙∙∙∙∙∙∙∙▉
▉∙∙∙◆∙∙∙∙∙▉▉▉▉▉▉∙∙∙▉
▉∙∙∙▉▉▉‼∙∙▉▉▉▉▉▉∙∙∙▉
▉∙∙∙∙∙∙∙∙∙▉▉▉▉▉▉∙∙∙▉
▉∙∙∙∙∙∙∙∙∙▉▉⇆▉▉▉∙∙∙▉
▉∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙▉
▉∙∙∙∙∙∙∙∙∙▉▉▉‼▉▉∙∙∙▉
▉∙∙∙≋≋≋≋◆∙∙∙∙∙∙∙∙∙∙▉
░░░∙≋≋≋≋∙∙∙∙∙∙∙∙∙∙∙▉
░░░∙≋≋≋≋∙∙∙∙∙∙∙∙∙∙∙▉
░░░∙≋≋≋≋▉▉▉▉▉▉▉▉▉▉▉▉

Legend:
░ Undiscovered
∙ Free tile
☻ Player
◈ Pikachu
▉ Barrier/wall
≋ Water
❀ Tall grass
◆ Sprite
⇆ Warp
‼ Sign
```

This map (plus a plethora of additional notes in the [overworld map prompt](/overworld_map/prompts.py)) helps the AI understand its surroundings far better than by simply looking at the game screen. It also comes with an index of all the sprites, signs, and warp tiles that the player has currently seen on it. The workflow has the ability to add persistent notes to each of these entities as it approaches and interacts with them.

You will notice that the tile characters chosen above are unusual Unicode characters, and there is a reason for this: Each tile must be exactly one token that doesn't combine with any of its neighbours. LLMs read tokens, not individual characters. If I were to use "w" to represent water, then three water tiles "www" would get consolidated into a single token, different from the original "w" token. This completely breaks the model's ability to count tiles, so we have to ensure that the tiles don't combine. [There is a test](/common/tests/integration/test_enums.py) that validates this for us.

### What About Vision?

Attentive readers will note that I have not said anything about editing the emulator's screenshot with additional information to improve the model's performance. This is something that other projects have included (e.g. by adding coordinates, colour coding, or borders to each tile in the image), but I did not find that it was necessary for my approach. The model sees the raw screenshot from the game in nearly every prompt, but it is borderline useless for most of them given the huge amount of information provided to it by the overworld map described above. I may go back and edit the screenshot logic to increase the information it contains if I find that the model is struggling somewhere, but thus far it hasn't seemed necessary to justify the level of work required.

## Conclusion

Kudos to you if you've actually read this far. I don't have much in the way of concluding remarks except to say that this project was tremendously fun to work on. I got to dig into the deepest levels of one of my favourite games and experience all of its insane idiosyncrasies first-hand. I've pushed the limits of my own work experience and delivered something that I feel truly proud of. Hopefully you learned a little something from digging through this project. I certainly did.
