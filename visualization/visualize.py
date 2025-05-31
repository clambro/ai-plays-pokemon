from pathlib import Path
from unittest.mock import MagicMock

from agent.graph import build_agent_graph


def main() -> None:
    """Visualize all the Junjo graphs."""
    graph = build_agent_graph(MagicMock())  # We don't need a real emulator to visualize the graph.
    out_dir = Path("visualization/agent_graph/")
    # PNG is preferable to SVG because we can directly visualize the diff in Git.
    graph.export_graphviz_assets(out_dir=out_dir, fmt="png")


if __name__ == "__main__":
    main()
