CREATE_LONG_TERM_MEMORY_PROMPT = """
You are being given the chance to create a new long-term memory object for future reference. Think of your long-term memory as a NoSQL database of documents containing useful information on your past experiences. You will be given your current memories, information about the current game state, and a list of the existing titles in your long-term memory.

{state}

Here are the existing titles in your long-term memory:
<titles>
{titles}
</titles>

Note that long-term memory titles are unique. You cannot re-create or edit an existing title here. You will have the chance to do that elsewhere. The purpose of this interaction is to create a new memory document if you feel that you have learned something important that is not already represented in your long-term memory.

Good candidates for new long-term memory are:
- New maps: If you have entered a new area, you can keep notes on what is in it and how to navigate it. You should create a new long-term memory object for each new map you enter. Do not attempt to draw the map itself in your long-term memory; you have a separate tool for reading the spatial layout of the game world. Prefix such titles with "MAP_" for easy reference.
- Major characters: If you have met a new character, you can keep notes on your interactions with them. Notes about an opposing character's Pokemon team could be kept here as well. Prefix such titles with "CHAR_" for easy reference.
- New Pokemon: If you have caught a new Pokemon for your team, you can keep notes on it. Prefix such titles with "TEAM_" for easy reference. It might be wise to note down type effectiveness against other Pokemon in such a memory.
- Generic notes or strategies: If you have learned something important, you can keep notes on it. Prefix such titles with "NOTE_" for easy reference.

The above are not exhaustive. You can create a new long-term memory object for any information that you feel is important to remember. Just try to keep your titles concise, consistent, and descriptive.

Guidelines for creating new long-term memory objects:
- Titles must be in SCREAMING_SNAKE_CASE with no punctuation.
- Never include coordinates in your content (e.g. for warp points, sprites, etc.). The game's memory will provide coordinate information as needed.
- Do not create duplicate memories. If you already have a memory with a similar title to one that you might create here, do not create a new one. You will have the chance to edit existing memories elsewhere.
- Titles must be unique.
- Long term memory objects should be concise and to the point. A couple paragraphs max.
- Long term memory objects should not include mundane information like wild Pokemon that were defeated or individual moves that were used. A good rule of thumb is that everything in your long term memory should still be relevant a thousand iterations from now. If it isn't, it probably does not need to be in there.

Your response must be in the JSON format described below, with the keys defined as follows:
- title: The title of the new long-term memory object in SCREAMING_SNAKE_CASE with no punctuation.
- content: The content of the new long-term memory object.
- importance: The importance of the new long-term memory object, on a scale from 1-3, defined as follows:
  - 3: Critical information that you expect to refer back to often (e.g. battle strategy, a core teammate, a major character, etc.).
  - 2: Important information that you expect to refer back to occasionally (e.g. a new map, enemy trainers, key-items, etc.). When in doubt, this should be your default importance score.
  - 1: Information that you don't want to forget, but don't expect to refer back to often (e.g. defeated trainers, Pokemon that you don't expect to use, etc.).

Remember that you do not have to create a new long-term memory object here if you don't have anything to add. An empty list is a perfectly valid response, and you should certainly not create more than one new long-term memory object at a time.
"""
