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

    async def _get_active_fic(self, session, guild_id: int) -> Fic:
        stmt = select(Fic).join(FicGuild).where(FicGuild.guild_id == guild_id, Fic.active_version_id != None)
        result = await session.execute(stmt)
        fic = result.scalars().first()
        if not fic:
            raise ValueError("No active fic configured for this server. Run `!qf ingest` first!")
        return fic

    def _format_result(self, result) -> str:
        desc = f"**Chapter {result.chapter_number}**"
        if result.chapter_title:
            desc += f": {result.chapter_title}"

        # We use an ANSI code block to allow green text highlighting
        desc += "\n```ansi\n"

        if result.context_before:
            desc += f"\u001b[0;30m{result.context_before}\u001b[0m\n\n"

        # Highlight the matched paragraph in Green
        desc += f"\u001b[0;32m{result.matched_text}\u001b[0m"

        if result.context_after:
            desc += f"\n\n\u001b[0;30m{result.context_after}\u001b[0m"

        desc += "\n```\n"

        if result.result_type == "fuzzy":
            desc += f"_Match Score: {result.fuzzy_score:.1f}_"
        elif result.result_type == "semantic":
            desc += f"_Semantic Match_"

        if len(desc) > 3500:
            desc = desc[:3500] + "..."

        return desc

    async def _handle_search(self, query: str, search_type: str, ctx=None, interaction: discord.Interaction=None):
        if len(query) < 2:
            msg = "Query too short! Must be at least 2 characters."
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        guild_id = interaction.guild_id if interaction else ctx.guild.id
        loading_text = f"Searching for {search_type} matches..."

        if interaction:
            await interaction.response.send_message(loading_text)
            message = await interaction.original_response()
        else:
            message = await ctx.send(loading_text)

        try:
            async with self.bot.session_maker() as session:
                fic = await self._get_active_fic(session, guild_id)

                repo = QuoteSearchRepository(session)
                service = SearchService(
                    repository=repo,
                    vector_store=self.bot.vector_store,
                    embedding_provider=self.bot.embedding_provider
                )

                if search_type == "exact":
                    results = await service.search_exact(fic.id, fic.active_version_id, query)
                elif search_type == "fuzzy":
                    results = await service.search_fuzzy(fic.id, fic.active_version_id, query)
                else:
                    results = await service.search_semantic(fic.id, fic.active_version_id, query)

                if not results.results:
                    empty_msg = f"No results found for your {search_type} search."
                    await message.edit(content=empty_msg)
                    return

                import re
                def get_chapter_url(base_url, chapter_number):
                    if not base_url:
                        return None
                    if "fanfiction.net/s/" in base_url:
                        match = re.search(r'(fanfiction\.net/s/\d+)(?:/\d+)?(.*)', base_url)
                        if match:
                            return f"https://www.{match.group(1)}/{chapter_number}{match.group(2)}"
                    return base_url

                data = []
                for i, r in enumerate(results.results):
                    page_text = self.renderer.format_page(
                        search_type=search_type,
                        result=r,
                        current_index=i,
                        returned_results=results.returned_results,
                        total_matches=results.total_matches,
                        results_truncated=results.results_truncated,
                        fic_title=fic.title,
                        query=query
                    )
                    url = get_chapter_url(fic.source_url, r.chapter_number)
                    data.append({"text": page_text, "url": url})
                    
                title = f"{search_type.capitalize()} Search"
                author_id = interaction.user.id if interaction else ctx.author.id
                view = SearchResultView(data=data, title=title, author_id=author_id)

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

    @commands.command(name="qf", help="Shows search command usage")
    async def qf_help(self, ctx, *, query: Optional[str] = None):
        msg = (
            "⚠️ **The `!qf` command has been split!** Please use one of the following:\n"
            "`!qfe <query>` - Exact Search\n"
            "`!qff <query>` - Fuzzy Search\n"
            "`!qfs <query>` - Semantic Scene Search"
        )
        await ctx.send(msg)

    @commands.command(name="qs", aliases=["qfs", "semantic"], help="Semantic scene search")
    async def qs(self, ctx, *, query: str):
        await self._handle_search(query, "semantic", ctx=ctx)

async def setup(bot):
    await bot.add_cog(SearchCog(bot))
