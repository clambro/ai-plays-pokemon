from pydantic import BaseModel


class SelectToolResponse(BaseModel):
    """
    The response from the overworld tool selector prompt.

    We have to use a string instead of the enum for the `tool` parameter because only a subset of
    the full tool set is available to the model. If we use the enum, the model will see tool names
    in the JSON schema that it does not have access to, and can thus use them illegally.
    """

    thoughts: str
    tool: str
