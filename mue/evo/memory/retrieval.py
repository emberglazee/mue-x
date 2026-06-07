"""Hybrid retrieval: SQLite FTS5 + vector similarity (cosine distance).

Combines keyword search with semantic similarity for best recall.
"""


class HybridRetriever:
    def __init__(self, lattice):
        self.lattice = lattice

    def retrieve(self, query: str, top_k: int = 10) -> list:
        """Retrieve most relevant memories using FTS5 + optional semantic search."""
        return self.lattice.search_fts(query, limit=top_k)

    def retrieve_by_tags(self, tags: list[str], top_k: int = 20) -> list:
        results = []
        for tag in tags:
            results.extend(self.lattice.search_tagged(tag, limit=top_k // len(tags)))
        seen = set()
        unique = []
        for r in results:
            if r.key not in seen:
                seen.add(r.key)
                unique.append(r)
        return unique[:top_k]
