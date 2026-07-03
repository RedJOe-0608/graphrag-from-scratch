from pathlib import Path
import yaml

from app.config.graph_schema import GraphSchema, RelationshipEndpoints


def load_graph_schema(path: str | Path) -> GraphSchema:
    with open(path, "r") as file:
        data = yaml.safe_load(file)

    relationships = data["relationship_types"]

    return GraphSchema(
        entity_types=data["entity_types"],
        relationship_types=list(relationships.keys()),
        relationship_endpoints={
            name: RelationshipEndpoints(
                source=endpoints["source"],
                target=endpoints["target"],
            )
            for name, endpoints in relationships.items()
        },
    )
