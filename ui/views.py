import discord
import asyncio
from ui.render import SearchResultRenderer
import re

class SearchResultView(discord.ui.LayoutView):
    def __init__(self, data: list[dict], title: str, author_id: int):
        super().__init__(timeout=1200)
        self.data = data
        self.title = title
        self.author_id = author_id
        self.current_index = 0
        self.rebuild()

    def rebuild(self):
        self.clear_items()
        
        page_data = self.data[self.current_index] if self.data else {"text": "No results.", "url": None}
        content = page_data["text"]
        
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(content))
        self.add_item(container)
        
        nav_row = discord.ui.ActionRow()
        
        btn_first = discord.ui.Button(label="First", style=discord.ButtonStyle.secondary, disabled=self.current_index == 0)
        btn_first.callback = self._on_first
        nav_row.add_item(btn_first)
        
        btn_prev = discord.ui.Button(label="Previous", style=discord.ButtonStyle.primary, disabled=self.current_index == 0)
        btn_prev.callback = self._on_prev
        nav_row.add_item(btn_prev)
        
        page_indicator = discord.ui.Button(label=f"{self.current_index + 1} / {len(self.data)}", style=discord.ButtonStyle.secondary, disabled=True)
        nav_row.add_item(page_indicator)
        
        btn_next = discord.ui.Button(label="Next", style=discord.ButtonStyle.primary, disabled=self.current_index == len(self.data) - 1)
        btn_next.callback = self._on_next
        nav_row.add_item(btn_next)
        
        btn_last = discord.ui.Button(label="Last", style=discord.ButtonStyle.secondary, disabled=self.current_index == len(self.data) - 1)
        btn_last.callback = self._on_last
        nav_row.add_item(btn_last)
        
        self.add_item(nav_row)
        
        action_row = discord.ui.ActionRow()
        if page_data.get("url"):
            btn_open = discord.ui.Button(label="Open Chapter", style=discord.ButtonStyle.link, url=page_data["url"])
            action_row.add_item(btn_open)
            
        btn_close = discord.ui.Button(label="Close", style=discord.ButtonStyle.danger)
        btn_close.callback = self._on_close
        action_row.add_item(btn_close)
        self.add_item(action_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This search belongs to another user.", ephemeral=True)
            return False
        return True
        
    async def _update_page(self, interaction: discord.Interaction, target_index: int):
        self.current_index = target_index
        self.rebuild()
        await interaction.response.edit_message(view=self, allowed_mentions=discord.AllowedMentions.none())

    async def _on_first(self, interaction: discord.Interaction):
        await self._update_page(interaction, 0)

    async def _on_prev(self, interaction: discord.Interaction):
        await self._update_page(interaction, max(0, self.current_index - 1))

    async def _on_next(self, interaction: discord.Interaction):
        await self._update_page(interaction, min(len(self.data) - 1, self.current_index + 1))

    async def _on_last(self, interaction: discord.Interaction):
        await self._update_page(interaction, len(self.data) - 1)

    async def _on_close(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=None)
        self.stop()
