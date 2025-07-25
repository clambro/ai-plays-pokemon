# Project Philosophy

## Philosophy

### A Spectrum of Pokemon Solvers

There is a long history of people trying to solve Pokemon autonomously. I'd like to frame these attempts on a spectrum of autonomy that the various approaches allow.

On the low end of the autonomy spectrum, you have projects like [MartSnack's extremely cool attempts to play Pokemon using a pre-defined series of button presses](https://www.youtube.com/@martsnack). Tool assisted speedrun bots [like this one](https://github.com/alexkara15/PokeBot/tree/master) also fall on this side of the spectrum. The defining feature on this end of the spectrum is determinism. The whole arc of the game is more or less known in advance.

Slightly higher in autonomy than that live the reinforcement learning (RL) algorithms like the very impressive [PokeRL](https://drubinstein.github.io/pokerl/) project, which splits the game into "episodes", defines a route between them, and uses RL and a swarm of agents to find an optimal policy for each episode. This has much higher tolerance for uncertainty than the deterministic approaches we discussed before, but still requires a high level plan that has to be optimized in stages.

At the peak of the autonomy spectrum sits the holy grail: A totally autonomous agent that interacts in real time with the emulator in a recurrent loop, with no game state parsing, tools, or additional information beyond what's currently visible on screen. This, I believe, was the original goal of the [Claude Plays Pokemon](https://www.twitch.tv/claudeplayspokemon) (CPP) benchmark, but modern LLMs are nowhere near capable of this feat. To make any progress at all, CPP required access to the game state, a knowledge base, a summarizer for long content, and a simple navigation tool. [Gemini Plays Pokemon](https://www.twitch.tv/gemini_plays_pokemon) (GPP) went further still and incorporated a minimap to help with the model's (lack of) spatial awareness. GPP was [criticized by some for this "harness" that it used to beat the game](https://arstechnica.com/ai/2025/05/why-google-geminis-pokemon-success-isnt-all-its-cracked-up-to-be/), but my contention in this project is that GPP's harness didn't go far enough!

### My Approach

My approach to solving Pokemon Yellow Legacy combines freedom with constraint, sitting firmly in the middle of the autonomy spectrum. I want the LLM to make all the high-level decisions, but I don't need it to determine every individual button press. The flow of the game is not limited in any way, but the AI is tightly bound in a workflow to keep it focused and predictable.

The model here is that of a production LLM application. LLMs are expensive, and inherently a source of uncertainty. Thus, you only want to use them when you absolutely must, and in a way where their output space can be bounded and validated.

An example will make this more clear: The very first decision you make in Pokemon is what name you want to give your character. Let's say the AI wants to name itself "GEMINI." The shortest sequence to enter this name involves 29 button presses. To do this whole thing with a Gemini model, you would have to use Gemini Pro (because Flash isn't good enough at interpreting the screen), and even if you allowed the model to press multiple buttons per iteration, it would still require several iterations, probably a dozen or so in total. And this is assuming that it didn't make a mistake and have to go back, which it almost certainly would, or worse, make a mistake and carry on with submitting the name.

My approach to the above problem is to simply ask the model for the name, since that's the decision we care about, then use a deterministic algorithm to enter it. Naming is a task that Gemini Flash Lite can handle no problem, and it takes only one iteration at one-twelfth the price of Gemini Pro. If we assume the naive approach took a dozen iterations, then this approach is nearly 150x cheaper overall!

Naming is a somewhat trivial example that doesn't happen all that often in game, but the exact same logic applies for navigation and selecting options in battles. Breaking down the gameplay into these discrete units of activity allows us to use smaller, cheaper models, and moreover they run faster, making for a better viewing experience. Critically as well, discrete actions are far, far easier to test than monolithic agentic prompts.

Fundamentally the approach here is to let the agent do the cool stuff, but offload the boring, tedious stuff to safe, deterministic algorithms. The rest of this page will discuss the core design decisions that were made to build this workflow and overcome the inherent limitations of LLMs.

## Core Design Concerns

- Async emulator/LLM interaction
- Type safety with Pydantic for game state, LLM, and DB interfaces
- Modular design to easily add new nodes/features/solutions. This is where Junjo comes in.
- [Link to workflow document](docs/workflow.md)
- Link to Junjo
- The cheapest model you can get away with. Evals would be nice here, but alas

## Overcoming the LLM's Flaws

### Using the Right Tool for the Job

- Not using an LLM to enter one button press at a time

### Three Kinds of Memory

### Map Memory & Navigation

### What About Vision?

- LLM is basically useless here. There are easier ways.

## Auditing and Testing

### LLM Telemetry

- Reading the prompts and responses is non-optional
- Junjo Server still in alpha, but will be cool someday

### Integration Testing with Game States

### Live Game State Visualization

### Backup and Restore Logic
