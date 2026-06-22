import os

import discord
from discord.ext import commands
from loguru import logger

from discord import app_commands
from ingestion import FicRepository, IngestionService
from database.models import Fic, FicGuild
from sqlalchemy import select
from ui.admin_views import is_root, AdminDashboardView
from ingestion.worker import JobWorker

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.job_worker = JobWorker(
            bot.session_maker, 
            bot.fichub_adapter, 
            bot.embedding_provider, 
            bot.vector_store
        )

    @app_commands.command(name="qfadmin", description="Quote Finder Administration Panel (Root Only)")
    async def qfadmin(self, interaction: discord.Interaction):
        if not is_root(interaction.user.id):
            await interaction.response.send_message("You are not authorized to use Quote Finder administration.", ephemeral=True)
            return
            
        view = AdminDashboardView(self.bot, self.job_worker)
        # We must use ephemeral=True so it's only visible to the root user
        await interaction.response.send_message(
            content=await view._generate_content(),
            view=view,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Admin(bot))
