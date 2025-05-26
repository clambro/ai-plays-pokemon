UPDATE_LONG_TERM_MEMORY_PROMPT = """
You are being given the chance to update your currently available long-term memory objects with any new information that you have learned.

{raw_memory}

{summary_memory}

{long_term_memory}

{player_info}

The above memories are the only memories that you have access to at the moment. You can only update memories from the above list.

Your response must be in the JSON format described below, with the keys defined as follows:
- title: The title of the long-term memory object to update, exactly as it appears above.
- update_type: The type of update to perform on the long-term memory object, either appending your new information to the end of the existing content or rewriting the entire content.
- content: The content of the long-term memory object to update. If appending, this will be appended to the end of the existing content with a newline. If rewriting, this will replace the existing content entirely, so make sure to include all the information you want to keep.
- importance: The importance of the long-term memory object to update, on a scale from 1-3, defined as follows:
  - 3: Critical information that you expect to refer back to often (e.g. battle strategy, a core teammate, a major character, etc.).
  - 2: Important information that you expect to refer back to occasionally (e.g. a new map, enemy trainers, key-items, etc.). When in doubt, this should be your default importance score.
  - 1: Information that you don't want to forget, but don't expect to refer back to often (e.g. defeated trainers, Pokemon that you don't expect to use, etc.).

Guidelines for updating long-term memory objects:
- Never include coordinates in your content (e.g. for warp points, sprites, etc.). The game's memory will provide coordinate information as needed.
- Each piece of long-term memory is meant to be a document containing polished notes on a specific topic. Do not fill your content with useless noise straight from your raw and summary memories. Everything in your long-term memory should be useful to you.

Remember that you do not have to update any long-term memory objects here if you don't have anything to add. An empty list is a perfectly valid response, and you should certainly not update more than one long-term memory object at a time. When in doubt, don't make any updates.
"""
