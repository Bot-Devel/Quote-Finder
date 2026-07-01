import hashlib
import re
import unicodedata
from pathlib import Path
from bs4 import BeautifulSoup
from ebooklib import epub
from loguru import logger

from .models import ParsedParagraph, ParsedChapter, ParsedChunk


class ParagraphNormalizer:
    @staticmethod
    def normalize_text(text: str) -> str:
        # Unicode normalization
        text = unicodedata.normalize("NFKC", text)
        # Case folding
        text = text.casefold()
        # Curly quote and apostrophe normalization
        text = (
            text.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
        )
        # Dash normalization
        text = text.replace("—", "-").replace("–", "-")
        # Strip all punctuation — keep only alphanumeric and spaces
        text = re.sub(r"[^a-z0-9\s]", "", text)
        # Whitespace collapsing
        text = " ".join(text.split())
        return text

    @staticmethod
    def extract_paragraphs(html_content: str) -> list[ParsedParagraph]:
        soup = BeautifulSoup(html_content, "lxml")

        # Remove scripts, styles, etc.
        for tag in soup(["script", "style", "nav", "form", "meta", "link"]):
            tag.decompose()

        paragraphs = []
        para_number = 1

        # Elements to treat as paragraphs
        for element in soup.find_all(
            ["p", "div", "blockquote", "h1", "h2", "h3", "h4"]
        ):
            # Skip if this element contains block children (prevents outer <div> wrappers from duplicating content)
            if element.name == "div" and element.find(
                ["p", "div", "blockquote", "h1", "h2", "h3", "h4"]
            ):
                continue

            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

            # Collapse repeated whitespace
            text = " ".join(text.split())
            word_count = len(text.split())

            if word_count == 0:
                continue

            normalized = ParagraphNormalizer.normalize_text(text)

            paragraphs.append(
                ParsedParagraph(
                    number=para_number,
                    text=text,
                    normalized_text=normalized,
                    word_count=word_count,
                )
            )
            para_number += 1

        return paragraphs


import config


class ChunkBuilder:
    def __init__(
        self,
        target_words=config.CHUNK_TARGET_WORDS,
        min_words=config.CHUNK_MIN_WORDS,
        max_words=config.CHUNK_MAX_WORDS,
        overlap_words=config.CHUNK_OVERLAP_WORDS,
    ):
        self.target_words = target_words
        self.min_words = min_words
        self.max_words = max_words
        self.overlap_words = overlap_words

    def build_chunks(
        self,
        chapter_number: int,
        paragraphs: list[ParsedParagraph],
        starting_chunk_num: int = 1,
    ) -> list[ParsedChunk]:
        chunks = []
        chunk_number = starting_chunk_num

        current_chunk_paras = []
        current_word_count = 0

        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]

            current_chunk_paras.append(para)
            current_word_count += para.word_count

            # If we reached our target or this is the last paragraph
            if current_word_count >= self.target_words or i == len(paragraphs) - 1:
                # Build the chunk
                start_p = current_chunk_paras[0].number
                end_p = current_chunk_paras[-1].number

                text = "\\n\\n".join(p.text for p in current_chunk_paras)
                normalized = ParagraphNormalizer.normalize_text(text)
                text_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

                chunks.append(
                    ParsedChunk(
                        number=chunk_number,
                        chapter_number=chapter_number,
                        start_paragraph=start_p,
                        end_paragraph=end_p,
                        text=text,
                        normalized_text=normalized,
                        text_hash=text_hash,
                        word_count=current_word_count,
                    )
                )
                chunk_number += 1

                # Setup overlap for next chunk
                overlap_count = 0
                overlap_paras = []
                for p in reversed(current_chunk_paras):
                    if overlap_count + p.word_count <= self.overlap_words:
                        overlap_paras.insert(0, p)
                        overlap_count += p.word_count
                    else:
                        break

                if not overlap_paras and current_chunk_paras:
                    last_p = current_chunk_paras[-1]
                    if last_p.word_count <= self.max_words:
                        overlap_paras = [last_p]
                        overlap_count = last_p.word_count

                if i < len(paragraphs) - 1:
                    current_chunk_paras = overlap_paras.copy()
                    current_word_count = sum(p.word_count for p in current_chunk_paras)
                else:
                    current_chunk_paras = []
                    current_word_count = 0

            i += 1

        return chunks


class ChapterExtractor:
    def __init__(self):
        self.normalizer = ParagraphNormalizer()

    def extract_chapter(
        self, item: epub.EpubHtml, chapter_number: int
    ) -> ParsedChapter:
        html_content = item.get_body_content().decode("utf-8", errors="replace")

        soup = BeautifulSoup(html_content, "lxml")

        # Priority 1: heading tags
        title = None
        heading = soup.find(["h1", "h2", "h3"])
        if heading:
            title = heading.get_text(strip=True)

        if not title:
            title = f"Chapter {chapter_number}"

        paragraphs = self.normalizer.extract_paragraphs(html_content)
        word_count = sum(p.word_count for p in paragraphs)

        # Generate chapter hash
        normalized_title = self.normalizer.normalize_text(title)
        hash_input = normalized_title + "".join(p.normalized_text for p in paragraphs)
        chapter_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        return ParsedChapter(
            number=chapter_number,
            title=title,
            source_path=item.get_name(),
            chapter_hash=chapter_hash,
            paragraphs=paragraphs,
            word_count=word_count,
        )


class EpubParser:
    def __init__(self):
        self.chapter_extractor = ChapterExtractor()

    def _is_story_document(self, item: epub.EpubItem) -> bool:
        name = item.get_name().lower()
        non_story_keywords = ["title", "cover", "nav", "toc", "copyright", "info"]
        for kw in non_story_keywords:
            if kw in name:
                return False
        return True

    def parse(self, epub_path: Path) -> list[ParsedChapter]:
        book = epub.read_epub(str(epub_path))
        chapters = []

        chapter_number = 1

        # Parse spine to maintain reading order
        for item_id, linear in book.spine:
            if not linear:
                continue

            item = book.get_item_with_id(item_id)
            if not isinstance(item, epub.EpubHtml):
                continue

            if not self._is_story_document(item):
                logger.debug(f"Excluded document: {item.get_name()}")
                continue

            parsed_chapter = self.chapter_extractor.extract_chapter(
                item, chapter_number
            )

            if parsed_chapter.word_count == 0:
                continue

            chapters.append(parsed_chapter)
            chapter_number += 1

        if not chapters:
            raise ValueError("epub_parsing: No readable chapters found")

        return chapters
