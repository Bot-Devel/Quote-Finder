import re
from search.models import SearchResult


class SearchResultRenderer:
    def format_page(
        self,
        search_type: str,
        result: SearchResult,
        current_index: int,
        returned_results: int,
        total_matches: int,
        results_truncated: bool,
        fic_title: str,
        query: str,
        fic_url: str = None,
        chapter_url: str = None,
    ) -> str:
        # 1. Metadata
        title_text = self._escape_md(fic_title)
        if fic_url:
            title_md = f"**[{title_text}]({fic_url})**"
        else:
            title_md = f"**{title_text}**"

        chapter_text = f"Chapter {result.chapter_number}"
        if result.chapter_title:
            chapter_text += f" - {self._escape_md(result.chapter_title)}"

        if chapter_url:
            chapter_md = f"**[{chapter_text}]({chapter_url})**"
        else:
            chapter_md = f"**{chapter_text}**"

        metadata = f"{title_md}\n{chapter_md}"

        # 2. Passage
        passage = ""
        if search_type == "semantic":
            highlighted_match = self._highlight_matches(
                result.matched_text, query, "fuzzy"
            )
            if result.context_before:
                passage += f"{result.context_before}\n\n"
            passage += f"{highlighted_match}\n\n"
            if result.context_after:
                passage += f"{result.context_after}"
        else:
            # Exact & fuzzy word highlighting
            highlighted_match = self._highlight_matches(
                result.matched_text, query, search_type
            )
            passage += highlighted_match
            if result.context_after:
                passage += f"\n\n{result.context_after}"

        # Clean any backticks to avoid codeblock breakage, but preserve standard markdown
        passage = self._escape_md(passage)

        # Build final markdown
        layout = f"{metadata}\n\n{passage}"

        # Enforce application level text limits (fallback safety)
        if len(layout) > 4000:
            layout = layout[:3990] + "\n\n[...]"

        return layout

    def _highlight_matches(self, text: str, query: str, search_type: str) -> str:
        if not text or not query:
            return text

        if search_type == "exact":
            # Case insensitive exact match highlighting
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            return pattern.sub(lambda m: f"__**{m.group(0)}**__", text)

        if search_type == "fuzzy":
            # Highlight individual query words > 2 characters
            words = [w for w in re.split(r"\W+", query) if len(w) > 2]
            if not words:
                pattern = re.compile(re.escape(query), re.IGNORECASE)
                return pattern.sub(lambda m: f"__**{m.group(0)}**__", text)

            highlighted = text
            for word in words:
                # Use word boundaries so we don't highlight substrings of unrelated words
                pattern = re.compile(r"\b(" + re.escape(word) + r")\b", re.IGNORECASE)
                highlighted = pattern.sub(
                    lambda m: f"__**{m.group(0)}**__", highlighted
                )
            return highlighted

        return text

    def _escape_md(self, text: str) -> str:
        """Escapes discord markdown characters to prevent formatting breakage."""
        if not text:
            return ""
        # Neutralize triple backticks to avoid escaping out of blocks
        text = text.replace("```", "\\`\\`\\`")
        return text
