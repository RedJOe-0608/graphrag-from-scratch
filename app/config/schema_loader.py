from pathlib import Path
import yaml

from app.config.graph_schema import GraphSchema


def load_graph_schema(path: str | Path) -> GraphSchema:
    with open(path, "r") as file:
        data = yaml.safe_load(file)

    return GraphSchema(
        entity_types=data["entity_types"],
        relationship_types=data["relationship_types"],
    )