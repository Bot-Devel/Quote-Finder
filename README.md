# Quote Finder

Quote Finder is a high-performance Discord bot that provides instant exact, fuzzy, and semantic search for fanfictions ingested from FanFiction.net/FicHub.

## Architecture

The project runs natively using a two-process architecture powered by `systemd`:
1. **`quote-finder-bot.service` (Continuous):** The main Discord bot process. It handles public search queries, pagination, and manual `!qf ingest` / `!qf refresh` commands. Heavy workloads initiated manually are securely offloaded to background threads.
2. **`quote-finder-maintenance.timer` (Nightly):** A `systemd` timer running `quote-finder-maintenance.service` every night at 03:00. This one-shot process scans for any fics due for updates, downloads the latest version if changed, generates embeddings (lazily loaded), and cleanly exits to release memory.

Both processes communicate and prevent concurrent operations using atomic Postgres job locks (`SELECT ... FOR UPDATE SKIP LOCKED`).

## Ingestion Pipeline

The bot safely imports and processes massive fanfictions using a sophisticated background pipeline:
1. **Source & Validation**: Fetches the latest EPUB format from FicHub. The EPUB is strictly validated and parsed to extract chapter titles and raw paragraph text, while explicitly ignoring structural HTML wrapper bloat.
2. **Chunking**: Paragraphs are assembled into contiguous, overlapping text chunks (e.g., 200 words, 50-word overlap). This ensures semantic meaning and narrative context aren't lost at paragraph boundaries.
3. **Vectorization**: Uses local embedding models (e.g., `BAAI/bge-small-en-v1.5`) running asynchronously on the host machine to generate dense vector representations of each chunk.
4. **Storage Integration**:
   - **Neon Postgres**: Stores raw textual data, chapters, and normalized paragraph text.
   - **Qdrant Cloud**: Stores the dense chunk vectors for semantic similarity search.
5. **Differential Updates**: When tracking ongoing fics, the nightly maintenance job calculates chapter-level hashes. It performs a "Delta Refresh" by identifying and re-vectorizing *only* the chapters that were modified or added, saving massive amounts of compute.

## Retrieval Pipeline

When a user searches for a quote, the bot seamlessly routes queries through specialized retrieval flows:
1. **Exact Search (`!qfe`)**: Executes a fast SQL `LIKE` query against normalized text in Postgres to find exact, verbatim matches.
2. **Fuzzy Search (`!qff`)**: Uses Postgres Trigram indices (`pg_trgm`) to rapidly filter a candidate pool, then applies Python's `rapidfuzz` to rank candidates based on partial ratio string similarity.
3. **Semantic Search (`!qfs`)**: Encodes the user's query into a vector and performs a fast k-NN search via Qdrant to find chunks with high Cosine Similarity, ideal for finding scenes based on vague descriptions.
4. **Context Assembly**: Once matching paragraphs or chunks are identified, the system automatically fetches adjacent paragraphs from Postgres to present seamless, flowing context in the UI.
5. **Presentation**: Results are rendered using interactive pagination Views, complete with hit highlighting and direct markdown hyperlinks to the exact FanFiction.net chapter.

## Commands


**Public Search:**
- `!qfe <query>`: Exact substring matching
- `!qff <query>`: Fuzzy lexical searching
- `!qfs <query>`: Semantic scene search (uses local embedding models)

**Maintenance (Root Only):**
- `!qf ingest <ffn_id_or_url>`: Queues a fic for ingestion and processes it safely in the background.
- `!qf refresh <fic_id_or_alias>`: Forces a manual refresh check for a specific fic.
- `!qf connect <source_story_id> <guild_id>`: Connects an already ingested fic to a specific Discord server so it can be searched there.
- `!qf status`: Displays a dashboard of all tracked fics, their latest chapter counts, last fetch times, and connected Discord servers.

## Deployment

To deploy Quote Finder to a production Linux server, follow these steps to link and enable the `systemd` units:

```bash
# 1. Link the service files to systemd
sudo ln -s /path/to/Quote-Finder/quote-finder-bot.service /etc/systemd/system/
sudo ln -s /path/to/Quote-Finder/quote-finder-maintenance.service /etc/systemd/system/
sudo ln -s /path/to/Quote-Finder/quote-finder-maintenance.timer /etc/systemd/system/

# 2. Reload the daemon to register the units
sudo systemctl daemon-reload

# 3. Start and enable the continuously running bot
sudo systemctl enable --now quote-finder-bot.service

# 4. Start and enable the nightly timer
# DO NOT enable the maintenance.service directly
sudo systemctl enable --now quote-finder-maintenance.timer
```

*Note: Update the `/path/to/Quote-Finder` paths inside the `.service` files and the symlink commands to point to your actual repository clone path before running.*
