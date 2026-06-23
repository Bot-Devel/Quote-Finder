import asyncio
import re
import discord
from discord.ext import commands
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from loguru import logger

import config
from database.models.job import Job
from database.models.fic import Fic, FicGuild
from ingestion.worker import JobWorker

class StatusPaginationView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=300)
        self.embeds = embeds
        self.current_page = 0
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.current_page == 0
        self.next_btn.disabled = self.current_page == len(self.embeds) - 1

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.job_semaphore = asyncio.Semaphore(1)

    async def _track_job(self, message: discord.Message, job_id: str, prefix_text: str):
        last_content = ""
        while True:
            await asyncio.sleep(3)
            
            async with self.bot.session_maker() as session:
                stmt = select(Job).where(Job.id == job_id)
                job = (await session.execute(stmt)).scalars().first()
                
                if not job:
                    try:
                        await message.edit(content=f"{prefix_text}\n❌ Job vanished from database!")
                    except Exception:
                        pass
                    break
                    
                status_emoji = "⏳"
                if job.status == "running":
                    status_emoji = "▶️"
                elif job.status in ("completed", "no_changes"):
                    status_emoji = "✅"
                elif job.status == "failed":
                    status_emoji = "❌"
                    
                stage = job.current_stage or "Waiting for processing..."
                
                progress = ""
                if job.progress_total and job.progress_total > 0:
                    progress = f" ({job.progress_current}/{job.progress_total})"
                    
                content = f"{prefix_text}\n{status_emoji} Status: **{job.status.title()}**\n🔄 Stage: {stage}{progress}"
                
                if job.status == "failed" and job.failure_message:
                    content += f"\n⚠️ Error: {job.failure_message}"
                    
                if content != last_content:
                    try:
                        await message.edit(content=content)
                        last_content = content
                    except discord.NotFound:
                        break
                    except Exception as e:
                        logger.error(f"Failed to edit tracking message: {e}")
                        
                if job.status in ("completed", "failed", "stale", "no_changes"):
                    break

    async def _process_job_background(self, message, job_id, prefix_text):
        # We start the UI tracker loop immediately
        tracker_task = self.bot.loop.create_task(self._track_job(message, job_id, prefix_text))
        
        async with self.job_semaphore:
            worker = JobWorker(
                self.bot.session_maker,
                self.bot.fichub_adapter,
                self.bot.embedding_provider,
                self.bot.vector_store
            )
            await worker.process_job_by_id(job_id)
            
        await tracker_task

    async def ingest(self, ctx, target: str):
        if ctx.author.id != config.ROOT_USER_ID:
            await ctx.send("Permission denied.")
            return

        if not (target.isdigit() or "fanfiction.net/s/" in target.lower()):
            await ctx.send("Invalid target. Please provide an FFN story ID or URL.")
            return

        source_id = target
        if "fanfiction.net" in target:
            match = re.search(r"/s/(\d+)", target)
            if match:
                source_id = match.group(1)

        async with self.bot.session_maker() as session:
            stmt = select(Fic).where(Fic.source_story_id == source_id)
            existing = (await session.execute(stmt)).scalars().first()
            if existing:
                await ctx.send(f"Fic already exists with ID: {existing.id}")
                return
            
            job = Job(
                job_type="ingest",
                target_url=target,
                guild_id=ctx.guild.id if ctx.guild else None
            )
            session.add(job)
            await session.commit()
            job_id = job.id
            
        msg = await ctx.send(f"Ingestion queued for FFN story {source_id}.\nJob ID: `{job_id}`\n⏳ Waiting for local worker...")
        
        # Dispatch background task immediately
        self.bot.loop.create_task(self._process_job_background(msg, job_id, f"**Ingesting {source_id}** (Job: `{job_id[-8:]}`)"))

    async def rebuild(self, ctx, target: str):
        if ctx.author.id != config.ROOT_USER_ID:
            await ctx.send("Permission denied.")
            return

        async with self.bot.session_maker() as session:
            stmt = select(Fic).where(or_(
                Fic.id == target,
                Fic.source_story_id == target
            ))
            fic = (await session.execute(stmt)).scalars().first()
            
            if not fic:
                await ctx.send(f"Fic not found matching identifier: {target}")
                return
                
            stmt_job = select(Job).where(
                Job.fic_id == fic.id,
                Job.job_type == "rebuild",
                Job.status.in_(["queued", "running"])
            )
            existing_job = (await session.execute(stmt_job)).scalars().first()
            if existing_job:
                await ctx.send(f"A rebuild job is already active for {fic.title}.\nJob ID: {existing_job.id}")
                return

            job = Job(
                job_type="rebuild",
                fic_id=fic.id,
                target_url=fic.source_url,
                guild_id=ctx.guild.id if ctx.guild else None
            )
            session.add(job)
            await session.commit()
            job_id = job.id
            fic_title = fic.title
            
        msg = await ctx.send(f"Rebuild queued for {fic_title}.\nJob ID: `{job_id}`\n⏳ Waiting for local worker...")
        
        # Dispatch background task immediately
        self.bot.loop.create_task(self._process_job_background(msg, job_id, f"**Rebuilding {fic_title}** (Job: `{job_id[-8:]}`)"))

    async def refresh(self, ctx, target: str):
        if ctx.author.id != config.ROOT_USER_ID:
            await ctx.send("Permission denied.")
            return

        async with self.bot.session_maker() as session:
            stmt = select(Fic).where(or_(
                Fic.id == target,
                Fic.source_story_id == target
            ))
            fic = (await session.execute(stmt)).scalars().first()
            
            if not fic:
                await ctx.send(f"Fic not found matching identifier: {target}")
                return
                
            stmt_job = select(Job).where(
                Job.fic_id == fic.id,
                Job.job_type == "refresh",
                Job.status.in_(["queued", "running"])
            )
            existing_job = (await session.execute(stmt_job)).scalars().first()
            if existing_job:
                await ctx.send(f"A refresh job is already active for {fic.title}.\nJob ID: {existing_job.id}")
                return

            job = Job(
                job_type="refresh",
                fic_id=fic.id,
                target_url=fic.source_url,
                guild_id=ctx.guild.id if ctx.guild else None
            )
            session.add(job)
            await session.commit()
            job_id = job.id
            fic_title = fic.title
            
        msg = await ctx.send(f"Delta refresh queued for {fic_title}.\nJob ID: `{job_id}`\n⏳ Waiting for local worker...")
        
        # Dispatch background task immediately
        self.bot.loop.create_task(self._process_job_background(msg, job_id, f"**Delta Refreshing {fic_title}** (Job: `{job_id[-8:]}`)"))

    async def connect(self, ctx, target: str, guild_id: int):
        if ctx.author.id != config.ROOT_USER_ID:
            await ctx.send("Permission denied.")
            return

        async with self.bot.session_maker() as session:
            stmt = select(Fic).where(or_(
                Fic.id == target,
                Fic.source_story_id == target
            ))
            fic = (await session.execute(stmt)).scalars().first()
            if not fic:
                await ctx.send(f"❌ Fic not found matching identifier: `{target}`.")
                return

            stmt_link = select(FicGuild).where(FicGuild.fic_id == fic.id, FicGuild.guild_id == guild_id)
            if (await session.execute(stmt_link)).scalar_one_or_none():
                await ctx.send(f"⚠️ Fic `{fic.title}` is already connected to server `{guild_id}`.")
                return

            link = FicGuild(fic_id=fic.id, guild_id=guild_id)
            session.add(link)
            await session.commit()
            
            await ctx.send(f"✅ Successfully connected Fic **{fic.title}** to server `{guild_id}`!")

    async def status(self, ctx):
        if ctx.author.id != config.ROOT_USER_ID:
            await ctx.send("Permission denied.")
            return

        async with self.bot.session_maker() as session:
            stmt = select(Fic).options(selectinload(Fic.guilds))
            fics = (await session.execute(stmt)).scalars().all()
            
            if not fics:
                await ctx.send("No fics are currently tracked.")
                return

            embeds = []
            current_embed = discord.Embed(title="Quote Finder Status", color=discord.Color.blue())
            embeds.append(current_embed)
            field_count = 0
            
            for fic in fics:
                if field_count == 25:
                    current_embed = discord.Embed(color=discord.Color.blue())
                    embeds.append(current_embed)
                    field_count = 0
                    
                guild_names = []
                for g_link in fic.guilds:
                    guild = self.bot.get_guild(g_link.guild_id)
                    if guild:
                        guild_names.append(f"{guild.name}")
                    else:
                        guild_names.append(f"Unknown (`{g_link.guild_id}`)")
                guilds_str = ", ".join(guild_names) if guild_names else "None"
                
                last_fetched = fic.last_refreshed_at.strftime("%Y-%m-%d %H:%M UTC") if fic.last_refreshed_at else "Never"
                
                val = f"**Chapters:** {fic.chapter_count}\n**Last Fetched:** {last_fetched}\n**Guilds:** {guilds_str}"
                current_embed.add_field(name=f"{fic.title} ({fic.source_story_id})", value=val, inline=False)
                field_count += 1
                
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                for i, e in enumerate(embeds):
                    e.set_footer(text=f"Page {i+1} of {len(embeds)}")
                view = StatusPaginationView(embeds)
                await ctx.send(embed=embeds[0], view=view)

async def setup(bot):
    cog = Admin(bot)
    await bot.add_cog(cog)
    
    qf = bot.get_command("qf")
    if qf:
        @qf.command(name="ingest")
        async def ingest_cmd(ctx, target: str):
            await cog.ingest(ctx, target)
            
        @qf.command(name="rebuild")
        async def rebuild_cmd(ctx, target: str):
            await cog.rebuild(ctx, target)
            
        @qf.command(name="refresh")
        async def refresh_cmd(ctx, target: str):
            await cog.refresh(ctx, target)
            
        @qf.command(name="connect")
        async def connect_cmd(ctx, target: str, guild_id: int):
            await cog.connect(ctx, target, guild_id)
            
        @qf.command(name="status")
        async def status_cmd(ctx):
            await cog.status(ctx)
