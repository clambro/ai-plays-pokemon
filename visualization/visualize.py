from pathlib import Path
from unittest.mock import MagicMock

from agent.graph import build_agent_graph


def main() -> None:
    """Visualize all the Junjo graphs."""
    graph = build_agent_graph(MagicMock())  # We don't need a real emulator to visualize the graph.
    out_dir = Path("visualization/agent_graph/")
    graph.export_graphviz_assets(out_dir=out_dir)


if __name__ == "__main__":
    main()
