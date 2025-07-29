# Project Philosophy

## Philosophy

### A Spectrum of Pokémon Solvers

There is a long history of people trying to solve Pokémon autonomously. I'd like to frame these attempts on a spectrum of autonomy that the various approaches allow.

On the low end of the autonomy spectrum, you have projects like [MartSnack's extremely cool attempts to play Pokémon using a pre-defined series of button presses](https://www.youtube.com/@martsnack). Tool assisted speedrun bots [like this one](https://github.com/alexkara15/PokeBot/tree/master) also fall on this side of the spectrum. The defining feature on this end of the spectrum is determinism. The whole arc of the game is more or less known in advance.

Slightly higher in autonomy than that live the reinforcement learning (RL) algorithms like the very impressive [PokeRL](https://drubinstein.github.io/pokerl/) project, which splits the game into "episodes", defines a route between them, and uses RL and a swarm of agents to find an optimal policy for each episode. This has much higher tolerance for uncertainty than the deterministic approaches we discussed before, but still requires a high level plan that has to be optimized in stages.

At the other extreme of the autonomy spectrum sits the holy grail: A totally autonomous agent that interacts in real time with the emulator in a recurrent loop, with no parsing, tools, or information beyond what's currently visible on screen. This, I believe, was the original goal of the [Claude Plays Pokémon](https://www.twitch.tv/claudeplaysPokémon) (CPP) benchmark, but modern LLMs are nowhere near capable of this feat. To make any progress at all, CPP required access to the game state, a knowledge base, a summarizer for long content, and a simple navigation tool. [Gemini Plays Pokémon](https://www.twitch.tv/gemini_plays_Pokémon) (GPP) went further still and incorporated a minimap to help with the model's (lack of) spatial awareness. GPP was [criticized by some](https://arstechnica.com/ai/2025/05/why-google-geminis-Pokémon-success-isnt-all-its-cracked-up-to-be/) for this "harness" that it used to beat the game, but my contention in this project is that GPP's harness didn't go far enough!

### My Approach

My approach to solving Pokémon Yellow Legacy combines freedom with constraint, sitting firmly in the middle of the autonomy spectrum. I want the LLM to make all the high-level decisions, but I don't need it to determine every individual button press. The flow of the game is not limited in any way, but the AI is tightly bound in a workflow to keep it focused and predictable. The model here is that of a production application. LLMs are expensive and inherently a source of uncertainty. Thus, you only want to use them when you absolutely must, and in a way where their output space is bounded and can be validated.

An example will make this more clear: The very first decision you make in Pokémon is what name you want to give your character. Let's say the AI wants to name itself "GEMINI." The shortest sequence to enter this name involves 29 button presses. To do this whole thing with a Gemini model, you would have to use Gemini Pro (because Flash isn't good enough at interpreting the screen), and even if you allowed the model to press multiple buttons per iteration, it would still require several iterations, probably a dozen or so in total. And this is assuming that it didn't make a mistake and have to go back, which it almost certainly would, or worse, make a mistake and carry on with submitting the name.

My approach to the above problem is to simply ask the model for the name, since that's the decision we care about, then use a deterministic algorithm to submit the required button presses to the emulator. Naming is a task that Gemini Flash Lite can handle no problem, and it takes only one prompt at one-twelfth the price of Gemini Pro. If we assume that the naive approach took a dozen iterations, then this approach is nearly 150x cheaper overall!

Naming is a somewhat trivial example that doesn't happen all that often in game, but the exact same logic applies for navigation and selecting options in battles. We don't need the AI to take every single step; just tell us where it wants to go. We don't need the AI to press seven buttons to throw a PokeBall; just tell us to throw it. Breaking down the gameplay into these discrete units of activity allows us to use smaller, cheaper models, making the project cheaper overall. These cheaper model also run faster, thus making for a better viewing experience. The final advantage to this approach is that these discrete actions are far, far easier to test and tweak than monolithic agentic prompts, and their side effects are limited by the constraints we build around them.

Fundamentally the approach here is to let the agent do the thinking and offload the mechanical work to safe, deterministic algorithms. The rest of this page will discuss the core design decisions that were made to build this workflow and overcome the inherent limitations of LLMs.

## Core Design Concerns

Given that the core philosophy here is "freedom within constraints," we need an orchestration system to control the state of our AI agent. This orchestration system needs to meet the following criteria:

- It must run asynchronously. It will be running on the same thread as the PyBoy emulator itself, so we have to make sure it doesn't block emulation. Pyboy itself is unfortunately not natively async, so we had to [do some additional work](/emulator/emulator.py) to make it async-safe.
  - This was more of a self-imposed challenge. I could have run PyBoy on a separate thread entirely and added a communication layer between it and the agent, but I wanted the whole thing to run asynchronously together as if it were a single application.
- Its states must be compatible with Pydantic. The interfaces between the various layers of our application all need to be validated and type-safe or the application will fall into chaos. These interfaces are:
  - The [parsers](/emulator/parsers/) that read the raw game memory and turn it into the usable game state object.
  - The Pydantic integration [in the LLM service](/llm/service.py) that converts the raw JSON string output of the LLMs into validated schemas.
  - The [repository pattern](/database/) used to read objects from and write objects to the SQLite database.
  - The [backup service](/common/backup_service.py) that serializes states to and deserializes states from the disk.
- It must be lightweight and promote modular code. We need to be able to easily add new nodes to our workflow or rearrange old ones as our needs and understanding of the game evolve. Many orchestration tools impose heavy abstractions that are difficult to debug. That won't work for us.

The orchestration flow used in this project is called [Junjo](https://github.com/mdrideout/junjo), and it meets all of the above criteria. Full disclosure: Junjo was created by a coworker and friend of mine, but he did so out of the exact needs and shortcomings of other workflow orchestrators that I described above. Junjo creates a serializable, stateful, nestable graph (read: constraint) for our AI to operate within. A node-by-node analysis of this graph [is available here](/docs/workflow.md) if you're curious about how it's constructed.

## Overcoming the LLM's Flaws

LLMs have various shortcomings that prevent them from reaching the holy grail of perfect autonomy described above. The two greatest issues we have to deal with are a limited context window, and a lack of spatial reasoning ability. Like CPP and GPP then, we must create some tools and structures to overcome these deficiencies.

### Three Kinds of Memory

The first issue we will tackle is the LLM's finite context window that stops it from holding the whole game in memory. With every iteration of the model, it gains a new memory of what it has done. LLMs all have a finite context length, which is the maximum number of tokens that can be used for a single query (~1M tokens for the Gemini 2.5 series). Keeping a rolling log of as much memory as possible would get expensive fast since we pay per token in the query, and we would lose context from older memories once we roll them over. My solition to this problem is a three-tiered memory architecture that separately handles the immediate past, short term memory, and long term memory.

#### The Raw Memory

The raw memory is the simplest of the three memory types. This is an ordered dictionary that maps iteration numbers to the AI workflow's raw output for each iteration. It has a fixed length (50 iterations by default), and all older memories are simply deleted. The raw memory serves to inform the workflow of its immediate past actions (50 iterations is roughly 15 mins). Given that this raw information is bloated by a lot of the model's self talk, we clip it after relatively few iterations to keep the cost down and reduce potential distractions from excessive context. Lengths differ from iteration to iteration, but the total raw memory size is roughly 6500 tokens.

#### The Summary Memory

The summary memory is the short term memory that gets consolidated from the raw memory. Every few iterations (10 by default), the model is given the chance to create a new summary memory from its raw memories. These are significantly condensed compared to the raw memories. As an example, fighting a trainer battle could eaily take up 20 raw memory slots (say 2500 tokens), whereas a summary of that battle like "I defeated a SWIMMER's TENTACOOL, HORSEA, and GOLDEEN and earned ¥381. Pikachu grew to level 34 during the battle." is only about 35 tokens. The fact that the summary memory is so much more dense than the raw memory allows its length to be much longer. We have space for 200 summary memories by default, and they take up roughly 4000 tokens in total.

The summary memory also has more intelligent rollover logic than the raw memory. When a piece of summary memory is created, it is given an importance score from 1 (trivial) to 5 (critical for progression). When it comes time to bump an old summary memory and add a new one, both age and importance are taken into account so that we keep important memories longer than trivial ones. [The math for that is here](/memory/summary_memory.py) if you're curious.

#### The Long-Term Memory

The final kind of memory given to the model is the long-term memory. This is effectively a database table full of documents that the model can create and update every (by default) ten iterations. Long term memory retrieval is based on a combination of semantic similarity based on a query, memory recency, and an importance score similar to the one in the summary memory. The full retrieval algorithm [can be found here](/memory/retrieval_service.py). Long term memories are never deleted (though I may change that if it becomes a problem).

The model is encouraged to summarize memories if they go over a certain length, but there are no hard rules for what it can put in there. Common topics include notes on maps, characters, party members, goals, etc. By default, the long term memory is refreshed with ten new memories every ten iterations, and these memories take up roughly 2000 tokens.

### Mapping

Aside from memory, the other major shortcoming of LLMs in Pokémon is their lack of spatial reasoning ability. The key difference that allowed GPP to beat Pokémon where CPP failed (and the reason it was criticized) was the inclusion of a minimap that generated itself as the player walked around any given map. My approach here is somewhat similar to what I imagine GPP did, though, as mentioned in the FAQ, I was not aware of GPP when I started this project.

A minimap for each map ID is constructed using ASCII characters and stored in the database. The map is initialized as a rectangle of undiscovered territory the same size as the map in the game's memory, and with every step the player takes in game, the map is updated using whatever information is available on screen. Here is a sample map for Pallet Town:

```
∙∙∙▉∙∙∙∙∙▉❀☻▉∙∙∙∙∙▉∙
▉▉▉▉▉▉▉▉▉▉❀◈▉▉▉▉▉▉▉▉
▉∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙▉
▉∙∙∙▉▉▉▉∙∙∙∙▉▉▉▉∙∙∙▉
▉∙∙∙▉▉▉▉∙∙∙∙▉▉▉▉∙∙∙▉
▉∙∙‼▉⇆▉▉∙∙∙‼▉⇆▉▉∙∙∙▉
▉∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙▉
▉∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙▉
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

This map (plus a plethora of additional notes in the [overworld map prompt](/overworld_map/prompts.py)) helps the AI understand its surroundings far better than by simply looking at the game screen.

This ASCII map also comes with an index of all the sprites, signs, and warp tiles that the player has currently seen on it. The workflow has the ability to add persistent notes to each of these entities as it approaches and interacts with them.

You will notice that all the tile characters chosen above are unusual unicode characters, and there is a reason for this: Each tile must be exactly one token that doesn't combine with any of its neighbours. These LLMs read tokens, not individual characters. If I were to use "w" to represent water, then three water tiles "www" would get consolidated into a single token, different from the original "w" token. This completely breaks the model's ability to count tiles, so we have to ensure that the tiles don't combine. [There is a test](/common/tests/integration/test_enums.py) that validates this for us.

### What About Vision?

Attentive readers will note that I have not said anything about editing the emulator's screenshot with additional information to improve the model's performance. This is indeed something that other projects have included (e.g. by adding coordinates, colour coding, or borders to each tile in the image), but I did not find that it was necessary for my approach. The model does see the raw screenshot from the game in nearly every prompt, but it is borderline useless for most of them given the huge amount of information provided to it by the overworld map described above. I may go back and edit the screenshot logic to increase the information it contains if I find that the model is struggling somewhere, but thus far it hasn't seemed necessary to justify the level of work required.

## Auditing and Testing

It is one thing to build the workflow, but it is another thing entirely to be confident that it works. Testing is something you can rarely overdo, and I admit that I could have done more here, but here are several levels on which the project was validated before launch.

### Pytest

The most standard form of validation is writing code tests. I used the Pytest framework for this since it is by far the most popular and mature testing framework for Python. Unit tests are there to validate niche pieces of complex logic, primarily in the navigation and naming tools. Integration tests check multi-step processes, ensuring that discrete pieces of logic work correctly when chained together. We even have integration tests in this repository that run directly on game states and validate that tools enter the right commands and read correct information from the game's memory. There is even [a meta-test](/tests/unit/test_tests.py) that validates the way we organize our tests.

Despite what does exist in the repo, there are certainly glaring holes in my tests. Coverage is relatively low, but the worst issue is the lack of LLM tests. The point of LLM tests is to ensure that your prompts give the correct output for expected inputs so that you can pick the cheapest model that works and edit your prompts without fear of breaking key behaviour. They are more stochastic than traditional unit/integration/emd-to-end tests, but they help you track down and eliminate common failure modes of your prompts.

My excuse for not having LLM tests is a bit of a lame one: They're hard. My workflow is recursive, meaning the states (and therefore the inputs to all my prompts) depend on everything that came before them. This means that in a perfect world, a change to my workflow would necessitate regenerating all my test cases. Practically speaking, I should have included *something* to validate the prompts even if it was a bunch of synthetic inputs, but I was lazy. Mea culpa. I may do this if the project requires further validation it as it runs. In the mean time, there were other (less rigorous) ways that I evaluated my prompts.

### LLM Telemetry

As anyone who has ever worked with LLMs can tell you, your first attempt at a prompt will never be good enough. You will make mistakes. The LLM will fail in ways you could never have predicted. It will hook onto a single word you used and generate all kinds of unexpected pathologies. The only way to know that your LLM is responding reliably is to actually read its responses. Indeed, this is where you source the LLM test cases that I mentioned above.

This application logs every single LLM prompt and response to the same SQLite database that contains the long-term memories and map info. (This is also how I track the LLM costs over time.) I have spent hours reading these logs, tweaking prompts, reading them again, tweaking again, etc. If my workflow does something unexpected, this database table is the first place I go to start debugging. **There is no substitute for reading your own LLM logs.**

Some more mature applications may use proper telemetry providers over a crude database logging approach like mine. Junjo actually has a sister package called [Junjo Server](https://github.com/mdrideout/junjo-server) for exactly this purpose. It integrates with OpenTelemetry and renders interactable visualizations of your workflows with all the input states, output states, and LLM calls for each node. The project is still in alpha and struggles a bit with my massive workflow states, so it is turned off by default in the app, but I encourage you to check it out as it has a lot of potential.

![Junjo Server](/docs/images/junjo_server.jpg)

### Live Game State Visualization

The other obvious approach to testing and debugging the LLM is to simply watch it play the game! This project comes with an HTML page that visualizes the workflow's raw memory and goals, along with information about the current game state. The page is hosted locally and runs asynchronously with the emulator and AI workflow. Updates to the page are pushedW every time the raw memory is updated, and again at the end of each agent loop. The main purpose of this page is, of course, to support the live stream, but it was instrumental in validating aspects of the game state parsing and auditing the LLM's thought process.

![Game state visualization](/docs/images/stream_view.jpg)

### Backup and Restore Logic

All this testing and validation would be nothing without a way to go back and try again. This application contains a backup system that automatically snapshots the database, workflow state, and game state every (by default) 100 iterations (~30 mins). It will also automatically snapshot the last healthy iteration if the application crashes for any reason. The workflow can be restarted from any of these snapshot states, and this proved critical for debugging.

## Conclusion

Kudos to you if you've actually read this far. I don't have much in the way of concluding remarks except to say that this project was tremendously fun to work on. I got to dig into the deepest levels of one of my favourite games and experience all of its insane idiosyncracies first-hand. I've pushed the limits of my own work experience and delivered something that I feel truly proud of. Hopefully you learned a little something from digging through this project. I certainly did.
