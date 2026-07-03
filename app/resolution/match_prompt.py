from app.graph.entity import Entity


def build_match_prompt(
    entity: Entity,
    entity_relationships: list[str],
    source_text: str,
    candidates: list[dict],
    candidate_relationships: dict[str, list[str]],
) -> str:
    """
    Build the multi-candidate matching prompt: the new entity (with its chunk
    relationships and source passage) against a numbered list of candidates,
    each labeled with its graph id. The LLM returns the id of the matching
    candidate, or "none".
    """
    new_rels = "; ".join(entity_relationships) or "(none)"

    lines = []
    for c in candidates:
        rels = candidate_relationships.get(c["id"], [])
        rels_str = "; ".join(rels) or "(none)"
        lines.append(
            f"  id: {c['id']}\n"
            f"    Name: {c['name']}\n"
            f"    Aliases: {c.get('aliases') or []}\n"
            f"    Description: {c['description'] or ''}\n"
            f"    Relationships: {rels_str}"
        )
    candidates_block = "\n".join(lines)

    return (
        "A new entity was extracted from a document. Decide which existing "
        "candidate, if any, refers to the SAME real-world entity. The candidates "
        "were retrieved because they are similar, so one of them may well be the "
        "same entity — but only choose one if it genuinely is. Records that share "
        "a name but have a real conflict (for example a different employer, or a "
        "different city) are DIFFERENT entities. Differing but non-conflicting "
        "facts are normal for the same entity (a person can work somewhere and "
        "also create things).\n\n"
        "The new entity was extracted from this passage:\n"
        f'"""\n{source_text}\n"""\n\n'
        "NEW entity:\n"
        f"  Name: {entity.name}\n"
        f"  Type: {entity.entity_type}\n"
        f"  Description: {entity.description or ''}\n"
        f"  Relationships: {new_rels}\n\n"
        "CANDIDATES:\n"
        f"{candidates_block}\n\n"
        "Return the id of the candidate that refers to the same real-world "
        'entity as the new entity, or "none" if none of them do.'
    )
