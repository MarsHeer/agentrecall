class MemoryCompressor:
    """Compress multiple related memories into fewer, richer summaries."""

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def compress(self, texts: list[str], max_summaries: int = 2) -> list[str]:
        """Group related texts and create summaries."""
        if len(texts) <= max_summaries:
            return texts

        # Group by topic (simple keyword matching)
        groups = self._group_by_topic(texts)

        compressed = []
        for group in groups:
            summary = self._summarize_group(group)
            compressed.append(summary)

        return compressed[:max_summaries]

    def _group_by_topic(self, texts: list[str]) -> list[list[str]]:
        """Group texts that share common words."""
        groups = []
        used = set()

        for i, t1 in enumerate(texts):
            if i in used:
                continue
            group = [t1]
            used.add(i)
            words1 = set(t1.lower().split())

            for j, t2 in enumerate(texts):
                if j in used:
                    continue
                words2 = set(t2.lower().split())
                overlap = len(words1 & words2) / max(len(words1 | words2), 1)
                if overlap > 0.3:
                    group.append(t2)
                    used.add(j)

            groups.append(group)

        return groups

    def _summarize_group(self, texts: list[str]) -> str:
        """Simple extractive summary: keep the most unique info from each."""
        if len(texts) == 1:
            return texts[0]

        # Extract key phrases (words that appear in only one text = unique info)
        all_words = {}
        for t in texts:
            for word in set(t.lower().split()):
                if word not in all_words:
                    all_words[word] = 0
                all_words[word] += 1

        # Keep sentences with unique words
        key_sentences = []
        for t in texts:
            words = set(t.lower().split())
            unique_ratio = sum(1 for w in words if all_words.get(w, 0) == 1) / max(len(words), 1)
            if unique_ratio > 0.2:
                key_sentences.append(t)

        return ". ".join(key_sentences) if key_sentences else texts[0]
