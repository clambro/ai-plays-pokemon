from unittest.mock import MagicMock

from junjo.graphviz.utils import graph_to_graphviz_image

from agent.graph import build_agent_graph


def main() -> None:
    """Visualize all the Burr graphs."""
    dummy_emulator = MagicMock()  # We don't need a real emulator to visualize the graph.
    names_and_graphs = [
        ("Top Level Agent", build_agent_graph(dummy_emulator)),
    ]

    for name, graph in names_and_graphs:
        # The file extension is added by graphviz.
        filename = f"visualization/{name.lower().replace(' ', '_')}"
        graph_to_graphviz_image(graph, filename)


if __name__ == "__main__":
    main()
