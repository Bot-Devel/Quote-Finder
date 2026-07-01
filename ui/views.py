import discord
import asyncio
import re


class SearchResultView(discord.ui.LayoutView):
    def __init__(
        self, session, bot, renderer, service, store, fic_source_url, fic_title, query
    ):
        super().__init__(timeout=300)
        self.session = session
        self.bot = bot
        self.renderer = renderer
        self.service = service
        self.store = store
        self.fic_source_url = fic_source_url
        self.fic_title = fic_title
        self.query = query
        self.WINDOW_SIZE = 20
        self.PREFETCH_DISTANCE = 5
        self.rebuild()

    def _get_window_bounds(self, index: int) -> tuple[int, int]:
        window_start = (index // self.WINDOW_SIZE) * self.WINDOW_SIZE
        window_end = min(window_start + self.WINDOW_SIZE, len(self.session.result_refs))
        return window_start, window_end

    async def _fetch_window(self, start_idx: int, end_idx: int):
        try:
            ref_map = {
                i: self.session.result_refs[i]
                for i in range(start_idx, end_idx)
                if i not in self.session.page_cache
            }
            if ref_map:
                res_map = await self.service.fetch_results_context(
                    self.session.fic_id,
                    self.session.version_id,
                    self.session.search_type,
                    ref_map,
                )
                for idx, res in res_map.items():
                    self.session.page_cache[idx] = res
        finally:
            async with self.session.page_lock:
                window_key = (start_idx, end_idx)
                self.session.loading_windows.pop(window_key, None)

    async def _ensure_window_loading(
        self, start_idx: int, end_idx: int
    ) -> asyncio.Task:
        window_key = (start_idx, end_idx)
        async with self.session.page_lock:
            if window_key in self.session.loading_windows:
                return self.session.loading_windows[window_key]

            task = asyncio.create_task(self._fetch_window(start_idx, end_idx))
            self.session.loading_windows[window_key] = task
            return task

    async def _ensure_page_cached(self, index: int):
        if index in self.session.page_cache:
            return

        window_start, window_end = self._get_window_bounds(index)
        task = await self._ensure_window_loading(window_start, window_end)
        await task

    def _trigger_prefetch(self, index: int):
        window_start, window_end = self._get_window_bounds(index)

        # Check next window
        if index >= window_end - self.PREFETCH_DISTANCE:
            next_start = window_end
            if next_start < len(self.session.result_refs):
                next_end = min(
                    next_start + self.WINDOW_SIZE, len(self.session.result_refs)
                )
                asyncio.create_task(self._ensure_window_loading(next_start, next_end))

        # Check prev window
        if index <= window_start + self.PREFETCH_DISTANCE - 1:
            prev_start = window_start - self.WINDOW_SIZE
            if prev_start >= 0:
                prev_end = window_start
                asyncio.create_task(self._ensure_window_loading(prev_start, prev_end))

    def _get_chapter_url(self, base_url, chapter_number):
        if not base_url:
            return None
        if "fanfiction.net/s/" in base_url:
            match = re.search(r"(fanfiction\.net/s/\d+)(?:/\d+)?(.*)", base_url)
            if match:
                return f"https://www.{match.group(1)}/{chapter_number}{match.group(2)}"
        return base_url

    def _render_page(self, index: int) -> str:
        res = self.session.page_cache.get(index)
        if not res:
            return "Loading context window..."

        fic_url = self._get_chapter_url(self.fic_source_url, 1) or self.fic_source_url
        chapter_url = (
            self._get_chapter_url(self.fic_source_url, res.chapter_number)
            or self.fic_source_url
        )

        return self.renderer.format_page(
            search_type=self.session.search_type,
            result=res,
            current_index=index,
            returned_results=len(self.session.result_refs),
            total_matches=self.session.total_results,
            results_truncated=self.session.results_truncated,
            fic_title=self.fic_title,
            query=self.query,
            fic_url=fic_url,
            chapter_url=chapter_url,
        )

    def rebuild(self):
        self.clear_items()

        content = self._render_page(self.session.current_index)

        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(content))
        self.add_item(container)

        nav_row = discord.ui.ActionRow()

        btn_first = discord.ui.Button(
            label="First",
            style=discord.ButtonStyle.secondary,
            disabled=self.session.current_index == 0,
        )
        btn_first.callback = self._on_first
        nav_row.add_item(btn_first)

        btn_prev = discord.ui.Button(
            label="Previous",
            style=discord.ButtonStyle.primary,
            disabled=self.session.current_index == 0,
        )
        btn_prev.callback = self._on_prev
        nav_row.add_item(btn_prev)

        page_indicator = discord.ui.Button(
            label=f"{self.session.current_index + 1} / {len(self.session.result_refs)}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )
        nav_row.add_item(page_indicator)

        btn_next = discord.ui.Button(
            label="Next",
            style=discord.ButtonStyle.primary,
            disabled=self.session.current_index == len(self.session.result_refs) - 1,
        )
        btn_next.callback = self._on_next
        nav_row.add_item(btn_next)

        btn_last = discord.ui.Button(
            label="Last",
            style=discord.ButtonStyle.secondary,
            disabled=self.session.current_index == len(self.session.result_refs) - 1,
        )
        btn_last.callback = self._on_last
        nav_row.add_item(btn_last)

        self.add_item(nav_row)

        action_row = discord.ui.ActionRow()
        res = self.session.page_cache.get(self.session.current_index)
        if res:
            url = self._get_chapter_url(self.fic_source_url, res.chapter_number)
            if url:
                btn_open = discord.ui.Button(
                    label="Open Chapter", style=discord.ButtonStyle.link, url=url
                )
                action_row.add_item(btn_open)

        btn_close = discord.ui.Button(label="Close", style=discord.ButtonStyle.danger)
        btn_close.callback = self._on_close
        action_row.add_item(btn_close)
        self.add_item(action_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.owner_user_id:
            await interaction.response.send_message(
                "This search belongs to another user.", ephemeral=True
            )
            return False
        return True

    async def _update_page(self, interaction: discord.Interaction, target_index: int):
        from datetime import datetime, timezone, timedelta

        self.session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        self.session.current_index = target_index
        await interaction.response.defer()

        await self._ensure_page_cached(target_index)
        self._trigger_prefetch(target_index)

        self.rebuild()
        await interaction.edit_original_response(
            view=self, allowed_mentions=discord.AllowedMentions.none()
        )

    async def _on_first(self, interaction: discord.Interaction):
        await self._update_page(interaction, 0)

    async def _on_prev(self, interaction: discord.Interaction):
        await self._update_page(interaction, max(0, self.session.current_index - 1))

    async def _on_next(self, interaction: discord.Interaction):
        await self._update_page(
            interaction,
            min(len(self.session.result_refs) - 1, self.session.current_index + 1),
        )

    async def _on_last(self, interaction: discord.Interaction):
        await self._update_page(interaction, len(self.session.result_refs) - 1)

    async def _on_close(self, interaction: discord.Interaction):
        await self.store.remove(self.session.session_id)

        self.clear_items()
        content = self._render_page(self.session.current_index)
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(content))
        self.add_item(container)

        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self):
        await self.store.remove(self.session.session_id)
