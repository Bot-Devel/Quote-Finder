# Quote Finder

Quote Finder is a high-performance Discord bot that provides instant exact, fuzzy, and semantic search for fanfictions ingested from FanFiction.net/FicHub.

## Architecture

The project runs natively using a two-process architecture powered by `systemd`:
1. **`quote-finder-bot.service` (Continuous):** The main Discord bot process. It handles public search queries, pagination, and manual `!qf ingest` / `!qf refresh` commands. Heavy workloads initiated manually are securely offloaded to background threads.
2. **`quote-finder-maintenance.timer` (Nightly):** A `systemd` timer running `quote-finder-maintenance.service` every night at 03:00. This one-shot process scans for any fics due for updates, downloads the latest version if changed, generates embeddings (lazily loaded), and cleanly exits to release memory.

Both processes communicate and prevent concurrent operations using atomic Postgres job locks (`SELECT ... FOR UPDATE SKIP LOCKED`).

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
