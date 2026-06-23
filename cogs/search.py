import discord
from discord.ext import commands
from loguru import logger
from sqlalchemy import select

from database.models import FicGuild, Fic
from search.repository import QuoteSearchRepository
from search.service import SearchService
from typing import Optional
from ui.views import SearchResultView
from ui.render import SearchResultRenderer

class SearchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.renderer = SearchResultRenderer()
        from ui.store import SearchSessionStore
        self.session_store = SearchSessionStore()

    async def _get_active_fic(self, session, guild_id: int) -> Fic:
        stmt = select(Fic).join(FicGuild).where(FicGuild.guild_id == guild_id, Fic.active_version_id != None)
        result = await session.execute(stmt)
        fic = result.scalars().first()
        if not fic:
            raise ValueError("No active fic configured for this server. Run `!qf ingest` first!")
        return fic

    async def _handle_search(self, query: str, search_type: str, ctx=None, interaction: discord.Interaction=None):
        if len(query) < 2:
            msg = "Query too short! Must be at least 2 characters."
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.reply(msg, mention_author=False)
            return

        guild_id = interaction.guild_id if interaction else ctx.guild.id
        loading_text = f"Searching for {search_type} matches..."

        if interaction:
            await interaction.response.send_message(loading_text)
            message = await interaction.original_response()
        else:
            message = await ctx.reply(loading_text, mention_author=False)

        try:
            async with self.bot.session_maker() as session:
                fic = await self._get_active_fic(session, guild_id)

                repo = QuoteSearchRepository(session)
                service = SearchService(
                    repository=repo,
                    vector_store=self.bot.vector_store,
                    embedding_provider=self.bot.embedding_provider,
                    reranker=self.bot.reranker_provider
                )
                
                import uuid
                from ui.models import SearchSession, SearchResultRef
                
                if search_type == "exact":
                    refs, total, truncated = await service.search_exact_ids(fic.id, fic.active_version_id, query)
                elif search_type == "fuzzy":
                    refs, total, truncated = await service.search_fuzzy_ids(fic.id, fic.active_version_id, query)
                else:
                    sem_res = await service.search_semantic(fic.id, fic.active_version_id, query)
                    refs = [SearchResultRef(result_id=str(i), chunk_id=r.source_chunk_id, semantic_score=r.semantic_score) for i, r in enumerate(sem_res.results)]
                    total = sem_res.total_matches
                    truncated = sem_res.results_truncated

                if not refs:
                    empty_msg = f"No results found for your {search_type} search."
                    await message.edit(content=empty_msg)
                    return
                    
                session_id = uuid.uuid4().hex
                user_id = interaction.user.id if interaction else ctx.author.id
                
                search_session = SearchSession(
                    session_id=session_id,
                    owner_user_id=user_id,
                    guild_id=guild_id,
                    channel_id=interaction.channel_id if interaction else ctx.channel.id,
                    message_id=message.id,
                    fic_id=fic.id,
                    version_id=fic.active_version_id,
                    search_type=search_type,
                    result_refs=refs,
                    total_results=total,
                    results_truncated=truncated
                )
                
                # Fetch initial windows
                if search_type != "semantic":
                    to_fetch_indices = set()
                    WINDOW_SIZE = 20
                    if len(refs) <= 40:
                        to_fetch_indices.update(range(len(refs)))
                    else:
                        to_fetch_indices.update(range(min(WINDOW_SIZE, len(refs))))
                        last_start = max(0, len(refs) - WINDOW_SIZE)
                        to_fetch_indices.update(range(last_start, len(refs)))
                        
                    ref_map = {idx: refs[idx] for idx in to_fetch_indices}
                    res_map = await service.fetch_results_context(fic.id, fic.active_version_id, search_type, ref_map)
                    
                    for idx, res in res_map.items():
                        search_session.page_cache[idx] = res
                else:
                    for i, r in enumerate(sem_res.results):
                        search_session.page_cache[i] = r
                        
                await self.session_store.add(search_session)
                
                view = SearchResultView(
                    session=search_session,
                    bot=self.bot,
                    renderer=self.renderer,
                    service=service,
                    store=self.session_store,
                    fic_source_url=fic.source_url,
                    fic_title=fic.title,
                    query=query
                )
                
                # View already populates the TextDisplay component during init (via rebuild)
                await message.edit(content=None, embed=None, view=view, allowed_mentions=discord.AllowedMentions.none())

        except Exception as e:
            logger.exception("Search failed")
            await message.edit(content=f"Error during search: {str(e)}")

    @commands.command(name="qe", aliases=["qfe", "exact"], help="Exact literal quote search")
    async def qe(self, ctx, *, query: str):
        await self._handle_search(query, "exact", ctx=ctx)

    @commands.command(name="qff", aliases=["fuzzy"], help="Fuzzy lexical quote search")
    async def qff(self, ctx, *, query: str):
        await self._handle_search(query, "fuzzy", ctx=ctx)

    @commands.group(name="qf", invoke_without_command=True, help="Shows search command usage")
    async def qf_base(self, ctx, *, query: Optional[str] = None):
        msg = (
            "⚠️ **The `!qf` command has been split!** Please use one of the following:\n"
            "`!qfe <query>` - Exact Search\n"
            "`!qff <query>` - Fuzzy Search\n"
            "`!qfs <query>` - Semantic Scene Search"
        )
        await ctx.reply(msg, mention_author=False)

    @commands.command(name="qs", aliases=["qfs", "semantic"], help="Semantic scene search")
    async def qs(self, ctx, *, query: str):
        await self._handle_search(query, "semantic", ctx=ctx)

async def setup(bot):
    await bot.add_cog(SearchCog(bot))
