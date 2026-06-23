import os
from concurrent.futures import ThreadPoolExecutor

import discord
from discord.ext import commands
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from adapters.fichub import FicHub
from ingestion.embedding import AsyncEmbeddingProvider, LocalFastEmbedProvider
from ingestion.vector import QdrantStore
from search.reranker import AsyncRerankerProvider, LocalFastEmbedReranker

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Setup logging
logger.add("quote-finder.log", rotation="10 MB", retention="5 days", level="INFO")

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    DATABASE_URL = DATABASE_URL.replace("sslmode=require", "ssl=require")

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


class QuoteFinderBot(commands.Bot):
    def __init__(self):
        # Intents allow the bot to read message content for prefix commands (!quote)
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=commands.DefaultHelpCommand(),
        )

        self.engine = None
        self.session_maker = None
        self.vector_store = None
        self.embedding_provider = None
        self.reranker_provider = None
        self.fichub_adapter = None
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def setup_hook(self):
        print("Initializing services...")
        # Database setup
        if DATABASE_URL:
            self.engine = create_async_engine(DATABASE_URL, echo=False)
            self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

        # Qdrant setup
        if QDRANT_URL:
            self.vector_store = QdrantStore(url=QDRANT_URL, api_key=QDRANT_API_KEY)

        # Embedding setup (loads model, might take a moment)
        sync_provider = LocalFastEmbedProvider()
        self.embedding_provider = AsyncEmbeddingProvider(sync_provider, self.executor)

        # Reranker setup
        import config

        if config.SEMANTIC_RERANK_ENABLED:
            print("Loading cross-encoder reranker model...")
            sync_reranker = LocalFastEmbedReranker()
            self.reranker_provider = AsyncRerankerProvider(sync_reranker, self.executor)

        print("Warming up models...")
        await self.embedding_provider.embed_query("warmup")
        if self.reranker_provider:
            await self.reranker_provider.rerank("warmup", ["warmup"])

        # FicHub adapter
        self.fichub_adapter = FicHub()

        # Load the cogs
        await self.load_extension("cogs.search")
        await self.load_extension("cogs.admin")
        print("Loaded cogs.")

    async def close(self):
        if self.engine:
            await self.engine.dispose()
        self.executor.shutdown(wait=True)
        await super().close()

    async def on_ready(self):
        print("=" * 40)
        print("✅ Quote Finder Bot is Online!")
        print(f"🤖 Logged in as: {self.user} (ID: {self.user.id})")
        print(f"🌍 Connected to {len(self.guilds)} guild(s):")
        for guild in self.guilds:
            print(f"   - {guild.name} (ID: {guild.id}) - {guild.member_count} members")
        print(f"⚡ Gateway Latency: {round(self.latency * 1000)}ms")
        print("=" * 40)


def main():
    if not TOKEN or TOKEN == "<your-bot-token>":
        print("Error: DISCORD_TOKEN is missing or not set properly in the .env file.")
        return

    bot = QuoteFinderBot()
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
