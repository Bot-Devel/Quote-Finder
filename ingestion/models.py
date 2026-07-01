from dataclasses import dataclass


@dataclass
class ParsedParagraph:
    number: int
    text: str
    normalized_text: str
    word_count: int


@dataclass
class ParsedChapter:
    number: int
    title: str | None
    source_path: str
    chapter_hash: str
    paragraphs: list[ParsedParagraph]
    word_count: int


@dataclass
class ParsedChunk:
    number: int
    chapter_number: int
    start_paragraph: int
    end_paragraph: int
    text: str
    normalized_text: str
    text_hash: str
    word_count: int


@dataclass
class ParsedFic:
    source_story_id: str
    title: str
    author: str | None
    epub_hash: str
    chapters: list[ParsedChapter]
    chunks: list[ParsedChunk]
    word_count: int
