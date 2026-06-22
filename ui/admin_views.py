import os
import time
import discord
from loguru import logger
from sqlalchemy import select, text
from database.models import Fic, FicGuild
from database.models.job import Job


def is_root(user_id: int) -> bool:
    root_id = os.getenv("QUOTE_FINDER_ROOT_USER_ID") or os.getenv("ROOT_USER_ID")
    if not root_id:
        return False
    return str(user_id) == root_id

class AdminBaseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=1200)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_root(interaction.user.id):
            await interaction.response.send_message("You are not authorized to use Quote Finder administration.", ephemeral=True)
            return False
        return True

class AdminDashboardView(AdminBaseView):
    def __init__(self, bot, job_worker):
        super().__init__()
        self.bot = bot
        self.job_worker = job_worker

    async def _generate_content(self) -> str:
        async with self.bot.session_maker() as session:
            fic_count = (await session.execute(select(Fic))).scalars().all()
            guild_count = (await session.execute(select(FicGuild))).scalars().all()
            jobs = (await session.execute(select(Job))).scalars().all()
            
            active_jobs = sum(1 for j in jobs if j.status in ("queued", "running"))
            failed_jobs = sum(1 for j in jobs if j.status == "failed")
            
            return (
                "## Quote Finder Administration\n\n"
                f"**Fics:** {len(fic_count)}\n"
                f"**Connected guilds:** {len(guild_count)}\n"
                f"**Active jobs:** {active_jobs}\n"
                f"**Failed jobs:** {failed_jobs}\n"
            )

    @discord.ui.button(label="Fics", style=discord.ButtonStyle.primary)
    async def fics_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdminFicsView(self.bot, self.job_worker)
        await interaction.response.edit_message(content="## Fics Management\nManage your fanfictions here.", view=view)

    @discord.ui.button(label="Guilds", style=discord.ButtonStyle.primary)
    async def guilds_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdminGuildsView(self.bot, self.job_worker)
        await interaction.response.edit_message(content=await view._generate_content(), view=view)

    @discord.ui.button(label="Jobs", style=discord.ButtonStyle.primary)
    async def jobs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdminJobsView(self.bot, self.job_worker)
        await interaction.response.edit_message(content=await view._generate_content(), view=view)

    @discord.ui.button(label="System", style=discord.ButtonStyle.primary)
    async def system_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdminSystemView(self.bot, self.job_worker)
        await interaction.response.edit_message(content=await view._generate_content(), view=view)

    @discord.ui.button(label="Refresh Dashboard", style=discord.ButtonStyle.secondary, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=await self._generate_content(), view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Admin session closed.", view=None)
        self.stop()

class FicIngestModal(discord.ui.Modal, title='Ingest New Fic'):
    url = discord.ui.TextInput(
        label='FanFiction.net story ID or URL',
        placeholder='https://www.fanfiction.net/s/1234567',
        required=True
    )

    def __init__(self, session_maker, job_worker, guild_id: int):
        super().__init__()
        self.session_maker = session_maker
        self.job_worker = job_worker
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with self.session_maker() as session:
            job = Job(
                job_type="ingest",
                target_url=self.url.value,
                guild_id=self.guild_id
            )
            session.add(job)
            await session.commit()
            job_id = job.id
            
        await self.job_worker.start_ingestion(job_id, self.url.value, self.guild_id)
        
        await interaction.followup.send(f"✅ Ingestion job `{job_id}` queued! You can track it in the Jobs panel.", ephemeral=True)


class AdminFicsView(AdminBaseView):
    def __init__(self, bot, job_worker):
        super().__init__()
        self.bot = bot
        self.job_worker = job_worker

    @discord.ui.button(label="Ingest New Fic", style=discord.ButtonStyle.success)
    async def ingest_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # We need the current guild_id. If used in DMs, this might be None.
        guild_id = interaction.guild_id
        if not guild_id:
            await interaction.response.send_message("You must be in a server to ingest a fic (so we can connect it).", ephemeral=True)
            return
            
        modal = FicIngestModal(self.bot.session_maker, self.job_worker, guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Back to Dashboard", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdminDashboardView(self.bot, self.job_worker)
        await interaction.response.edit_message(content=await view._generate_content(), view=view)

class AdminJobsView(AdminBaseView):
    def __init__(self, bot, job_worker):
        super().__init__()
        self.bot = bot
        self.job_worker = job_worker

    async def _generate_content(self) -> str:
        async with self.bot.session_maker() as session:
            stmt = select(Job).order_by(Job.created_at.desc()).limit(5)
            result = await session.execute(stmt)
            jobs = result.scalars().all()
            
            if not jobs:
                return "## Jobs Panel\nNo recent jobs found."
                
            lines = ["## Jobs Panel\n"]
            for job in jobs:
                emoji = "⏳" if job.status == "queued" else "▶️" if job.status == "running" else "✅" if job.status == "completed" else "❌"
                lines.append(f"**{emoji} Job `{job.id[-8:]}`** ({job.job_type})")
                lines.append(f"> Target: {job.target_url or job.fic_id}")
                lines.append(f"> Stage: {job.current_stage or 'Waiting...'}")
                if job.progress_total and job.progress_total > 0:
                    lines.append(f"> Progress: {job.progress_current} / {job.progress_total}")
                if job.status == "failed":
                    lines.append(f"> ❌ Error: {job.failure_message}")
                lines.append("")
            
            return "\n".join(lines)

    @discord.ui.button(label="Refresh Jobs", style=discord.ButtonStyle.primary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=await self._generate_content(), view=self)

    @discord.ui.button(label="Back to Dashboard", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdminDashboardView(self.bot, self.job_worker)
        await interaction.response.edit_message(content=await view._generate_content(), view=view)

class GuildConnectModal(discord.ui.Modal, title='Connect Fic to Server'):
    source_id = discord.ui.TextInput(
        label='Fic Source ID (e.g. 1234567)',
        placeholder='1234567',
        required=True
    )
    guild_id = discord.ui.TextInput(
        label='Discord Server (Guild) ID',
        placeholder='000000000000000000',
        required=True
    )

    def __init__(self, session_maker):
        super().__init__()
        self.session_maker = session_maker

    async def on_submit(self, interaction: discord.Interaction):
        target_guild = int(self.guild_id.value)
        sid = self.source_id.value

        async with self.session_maker() as session:
            stmt = select(Fic).where(Fic.source_story_id == sid)
            result = await session.execute(stmt)
            fic = result.scalar_one_or_none()
            if not fic:
                await interaction.response.send_message(f"❌ Fic with Source ID `{sid}` not found in database.", ephemeral=True)
                return
                
            stmt = select(FicGuild).where(FicGuild.fic_id == fic.id, FicGuild.guild_id == target_guild)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                await interaction.response.send_message(f"⚠️ Fic `{fic.title}` is already connected to server `{target_guild}`.", ephemeral=True)
                return
                
            link = FicGuild(fic_id=fic.id, guild_id=target_guild)
            session.add(link)
            await session.commit()
            
            await interaction.response.send_message(f"✅ Successfully connected Fic **{fic.title}** to server `{target_guild}`!", ephemeral=True)


class AdminGuildsView(AdminBaseView):
    def __init__(self, bot, job_worker):
        super().__init__()
        self.bot = bot
        self.job_worker = job_worker

    async def _generate_content(self) -> str:
        async with self.bot.session_maker() as session:
            stmt = select(FicGuild)
            result = await session.execute(stmt)
            links = result.scalars().all()
            
            lines = ["## Connected Guilds\n"]
            if not links:
                lines.append("No fics are currently connected to any servers.")
            else:
                for link in links:
                    lines.append(f"- Server ID `{link.guild_id}` -> Fic ID `{link.fic_id}`")
                    
            return "\n".join(lines)

    @discord.ui.button(label="Add Guild Connection", style=discord.ButtonStyle.success)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = GuildConnectModal(self.bot.session_maker)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=await self._generate_content(), view=self)

    @discord.ui.button(label="Back to Dashboard", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdminDashboardView(self.bot, self.job_worker)
        await interaction.response.edit_message(content=await view._generate_content(), view=view)


class AdminSystemView(AdminBaseView):
    def __init__(self, bot, job_worker):
        super().__init__()
        self.bot = bot
        self.job_worker = job_worker

    async def _generate_content(self) -> str:
        # Check Postgres
        try:
            start = time.perf_counter()
            async with self.bot.session_maker() as session:
                await session.execute(text("SELECT 1"))
            pg_latency = f"{(time.perf_counter() - start) * 1000:.1f}ms"
            pg_status = "✅ Connected"
        except Exception as e:
            pg_status = f"❌ Error: {e}"
            pg_latency = "N/A"
            
        # Check Qdrant
        try:
            start = time.perf_counter()
            await self.bot.vector_store.client.get_collections()
            qd_latency = f"{(time.perf_counter() - start) * 1000:.1f}ms"
            qd_status = "✅ Connected"
        except Exception as e:
            qd_status = f"❌ Error: {e}"
            qd_latency = "N/A"
            
        return (
            "## System Health\n\n"
            f"**Neon Postgres Database:** {pg_status} ({pg_latency})\n"
            f"**Qdrant Cloud Vector Store:** {qd_status} ({qd_latency})\n"
            f"**Discord WebSocket:** ✅ Connected ({self.bot.latency * 1000:.1f}ms)\n"
        )

    @discord.ui.button(label="Refresh System Check", style=discord.ButtonStyle.primary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=await self._generate_content(), view=self)

    @discord.ui.button(label="Back to Dashboard", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdminDashboardView(self.bot, self.job_worker)
        await interaction.response.edit_message(content=await view._generate_content(), view=view)

