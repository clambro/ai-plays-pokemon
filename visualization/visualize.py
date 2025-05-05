from agent.graph import build_agent_graph
from graphviz import Graph
from unittest.mock import MagicMock


def main() -> None:
    """Visualize all the Burr graphs."""
    dummy_emulator = MagicMock()  # We don't need a real emulator to visualize the graph.
    names_and_graphs = [
        ("Top Level Agent", build_agent_graph(dummy_emulator)),
    ]

    for name, burr_graph in names_and_graphs:
        # The file extension is added by graphviz.
        filename = f"visualization/{name.lower().replace(' ', '_')}"

        graph: Graph = burr_graph.visualize(filename)  # type: ignore -- Burr issue.
        graph.attr(label=name)
        graph.attr(fontsize="20")
        graph.attr(labeljust="c")
        graph.attr(labelloc="t")
        graph.render(filename, format="png", cleanup=True)


if __name__ == "__main__":
    main()
