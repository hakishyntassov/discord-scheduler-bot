"""
In-channel /schedule UI (replaces the old DM flow).

Public message buttons (survive bot restarts via DynamicItem):
    Pick my times  -> opens a private picker grid only you can see
    Peek           -> private preview of the current best time (only after you've answered)
    Lock it in     -> creator ends it early and reveals the results

When everyone has saved, the message flips to the reveal automatically.
The reveal has Add event and Reschedule (creator moves to the next backup day).
"""
import logging

import discord

from database import (
    get_event, get_participants, get_responders, get_user_picks, get_all_picks,
    save_user_picks, close_event, claim_discord_event, set_discord_event_id, advance_choice,
)
from scheduling import (
    rank_blocks, ranked_options, day_summary, event_dates, hour_label, time_label, day_label, tz_abbrev,
)
from views.views import CooldownManager

logger = logging.getLogger(__name__)

FIELD_LIMIT = 1024


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _mentions(user_ids, empty="-", limit=FIELD_LIMIT) -> str:
    out, used = [], 0
    ids = list(user_ids)
    for i, uid in enumerate(ids):
        piece = f"<@{uid}>"
        if used + len(piece) + 20 > limit:
            out.append(f"+{len(ids) - i} more")
            break
        out.append(piece)
        used += len(piece) + 2
    return ", ".join(out) if out else empty


def _block_line(block, total: int) -> str:
    stars = f" · ⭐ {len(block.preferred)}" if block.preferred else ""
    return (
        f"> {discord.utils.format_dt(block.start_dt, 'f')} to {discord.utils.format_dt(block.end_dt, 't')}"
        f" · {len(block.people)}/{total} free{stars}"
    )


def _dates(event):
    return event_dates(event["start_timep"], event["end_timep"])


def _partial_message(client: discord.Client, event):
    channel = client.get_partial_messageable(event["channel_id"])
    return channel.get_partial_message(event["message_id"])


def _can_manage(interaction: discord.Interaction, event) -> bool:
    if interaction.user.id == event["creator_id"]:
        return True
    perms = getattr(interaction.user, "guild_permissions", None)
    return bool(perms and (perms.manage_events or perms.manage_guild))


# ---------------------------------------------------------------------------
# embeds
# ---------------------------------------------------------------------------

def build_open_embed(event, participants: list[int], responders: list[int]) -> discord.Embed:
    dates = _dates(event)
    intro = event["description"] or f"This event was created by <@{event['creator_id']}>"
    embed = discord.Embed(
        title=f"Event: **{event['title']}**",
        description=(
            f"{intro}\n\n"
            "**How it works**\n"
            "> Hit **Pick my times** and tap the hours you're free\n"
            "> Tap twice for ⭐ preferred\n"
            "> Nobody sees anyone's picks until the reveal\n"
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="**Schedule Period**",
        value=(
            f">>> {day_label(dates[0])} to {day_label(dates[-1])}\n"
            f"{time_label(event['day_start_hour'])} to {time_label(event['day_end_hour'])} ({tz_abbrev()})"
        ),
        inline=False,
    )
    responded = set(responders)
    waiting = [u for u in participants if u not in responded]
    embed.add_field(
        name=f"☑️ Responded ({len(responded)}/{len(participants)})",
        value=_mentions(responders),
        inline=False,
    )
    embed.add_field(name="⏳ Waiting on", value=_mentions(waiting, empty="nobody!"), inline=False)
    return embed


def get_options(event, participants: list[int], rows):
    blocks = rank_blocks(rows, _dates(event), event["day_start_hour"], event["day_end_hour"])
    return ranked_options(blocks, len(participants))


def build_final_embed(event, participants: list[int], rows) -> tuple[discord.Embed, list]:
    """Returns (embed, options). options[event['choice']] is the current pick."""
    dates = _dates(event)
    total = len(participants)
    options = get_options(event, participants, rows)

    if not options:
        embed = discord.Embed(
            title=f"Event: **{event['title']}**",
            description="Results are in... and nobody overlapped 😿\nTry a different date range?",
            color=discord.Color.red(),
        )
        return embed, options

    choice = min(event["choice"] or 0, len(options) - 1)
    best = options[choice]
    if choice:
        headline = "🔁 Rescheduled!"
    elif len(best.people) == total:
        headline = "🎉 Good news! Everybody is free :)"
    else:
        headline = "🎉 Results are in!"
    embed = discord.Embed(
        title=f"Event: **{event['title']}**",
        description=(
            f"{headline}\n\n"
            "**Best time**\n"
            f"> {discord.utils.format_dt(best.start_dt, 'F')}\n"
            f"> to {discord.utils.format_dt(best.end_dt, 't')} ({best.hours} hr)"
        ),
        color=discord.Color.green(),
    )
    embed.add_field(name=f"✅ Free ({len(best.people)}/{total})", value=_mentions(best.people), inline=True)
    if best.preferred:
        embed.add_field(name="⭐ Preferred", value=_mentions(best.preferred), inline=True)
    missing = [u for u in participants if u not in best.people]
    if missing:
        embed.add_field(name="❌ Can't make it", value=_mentions(missing), inline=True)

    runner_ups = options[choice + 1:choice + 4]
    if runner_ups:
        embed.add_field(
            name="**Runner-ups**",
            value="\n".join(_block_line(b, total) for b in runner_ups),
            inline=False,
        )
    fell = options[:choice]
    if fell:
        embed.add_field(
            name="**Fell through**",
            value="\n".join(f"> ~~{_block_line(b, total)[2:]}~~" for b in fell),
            inline=False,
        )

    summary = day_summary(rows, dates, event["day_start_hour"], event["day_end_hour"])[:14]
    bar_len = min(total, 10)
    lines = []
    for d, n in summary:
        filled = round(n / total * bar_len) if total else 0
        lines.append(f"`{day_label(d):<9}` {'▰' * filled}{'▱' * (bar_len - filled)} {n}/{total}")
    embed.add_field(name="**Day by day** (most free at once)", value="\n".join(lines), inline=False)
    return embed, options


# ---------------------------------------------------------------------------
# public message flow
# ---------------------------------------------------------------------------

def open_view(event_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(PickTimesButton(event_id))
    view.add_item(PeekButton(event_id))
    view.add_item(LockInButton(event_id))
    return view


def final_view(event_id: int, added: bool = False, backups_left: bool = False) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    if added:
        view.add_item(discord.ui.Button(
            label="Event added", emoji="📅", style=discord.ButtonStyle.secondary,
            disabled=True, custom_id=f"sched:added:{event_id}",
        ))
    else:
        view.add_item(AddEventButton(event_id))
    if backups_left:
        view.add_item(RescheduleButton(event_id))
    else:
        view.add_item(discord.ui.Button(
            label="No backups left", emoji="🔁", style=discord.ButtonStyle.secondary,
            disabled=True, custom_id=f"sched:nobackups:{event_id}",
        ))
    return view


def final_view_for(event, options) -> discord.ui.View:
    added = event["discord_event_id"] is not None
    backups_left = (event["choice"] or 0) < len(options) - 1
    return final_view(event["id"], added=added, backups_left=backups_left)


async def refresh_open_message(client: discord.Client, event_id: int):
    event = await get_event(event_id)
    participants = await get_participants(event_id)
    responders = await get_responders(event_id)
    try:
        await _partial_message(client, event).edit(embed=build_open_embed(event, participants, responders))
    except discord.HTTPException:
        logger.warning("couldn't update schedule message for event %s", event_id, exc_info=True)


async def finalize(client: discord.Client, event_id: int) -> bool:
    """Reveal results on the public message. Returns False if it was already finalized."""
    event = await get_event(event_id)
    participants = await get_participants(event_id)
    rows = await get_all_picks(event_id)
    options = get_options(event, participants, rows)
    best = options[0] if options else None

    if not await close_event(event_id, best.start_dt if best else None, best.end_dt if best else None):
        return False

    event = await get_event(event_id)
    embed, options = build_final_embed(event, participants, rows)
    message = _partial_message(client, event)
    try:
        await message.edit(
            content=f"> {_mentions(participants)} results are in :)",
            embed=embed,
            view=final_view_for(event, options) if options else None,
        )
        await message.reply(f"> Results are in for **{event['title']}**! {_mentions(participants)}")
    except discord.HTTPException:
        logger.warning("couldn't post results for event %s", event_id, exc_info=True)
    logger.info("Finalized schedule event %s", event_id)
    return True


async def after_save(client: discord.Client, event_id: int):
    participants = set(await get_participants(event_id))
    responders = set(await get_responders(event_id))
    if participants and participants <= responders:
        await finalize(client, event_id)
    else:
        await refresh_open_message(client, event_id)


# ---------------------------------------------------------------------------
# public buttons (persistent: custom_id carries the event id)
# ---------------------------------------------------------------------------

class PickTimesButton(discord.ui.DynamicItem[discord.ui.Button], template=r"sched:pick:(?P<event_id>\d+)"):
    def __init__(self, event_id: int):
        super().__init__(discord.ui.Button(
            label="Pick my times", emoji="🗓️", style=discord.ButtonStyle.success,
            custom_id=f"sched:pick:{event_id}",
        ))
        self.event_id = event_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["event_id"]))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        event = await get_event(self.event_id)
        if event is None or event["status"] != "open":
            await interaction.followup.send("> This one's already wrapped up.", ephemeral=True)
            return
        if interaction.user.id not in await get_participants(self.event_id):
            await interaction.followup.send("> Sorry, you're not on the list for this event.", ephemeral=True)
            return
        picks = await get_user_picks(self.event_id, interaction.user.id)
        view = PickerView(event, interaction.user.id, picks)
        await interaction.followup.send(view.content(), view=view, ephemeral=True)


class PeekButton(discord.ui.DynamicItem[discord.ui.Button], template=r"sched:peek:(?P<event_id>\d+)"):
    _cooldown = CooldownManager(5.0)

    def __init__(self, event_id: int):
        super().__init__(discord.ui.Button(
            label="Peek", emoji="👀", style=discord.ButtonStyle.secondary,
            custom_id=f"sched:peek:{event_id}",
        ))
        self.event_id = event_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["event_id"]))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        remaining = self._cooldown.check(interaction.user.id)
        if remaining:
            await interaction.followup.send(f"> You're clicking too fast. Try again in **{remaining:.1f}s**.", ephemeral=True)
            return

        event = await get_event(self.event_id)
        participants = await get_participants(self.event_id)
        responders = await get_responders(self.event_id)
        if interaction.user.id not in responders and not _can_manage(interaction, event):
            await interaction.followup.send(
                "> Save your own times first, then you can peek. Keeps the preview from swaying your answer :)",
                ephemeral=True,
            )
            return

        rows = await get_all_picks(self.event_id)
        blocks = rank_blocks(rows, _dates(event), event["day_start_hour"], event["day_end_hour"])
        embed = discord.Embed(
            title="👀 Sneak peek",
            description=f"{len(responders)}/{len(participants)} responded so far. Only you can see this.",
            color=discord.Color.blurple(),
        )
        if blocks:
            embed.add_field(
                name="**Best so far**",
                value="\n".join(_block_line(b, len(participants)) for b in blocks[:3]),
                inline=False,
            )
        else:
            embed.add_field(name="**Best so far**", value="> No overlap yet", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)


class LockInButton(discord.ui.DynamicItem[discord.ui.Button], template=r"sched:lock:(?P<event_id>\d+)"):
    def __init__(self, event_id: int):
        super().__init__(discord.ui.Button(
            label="Lock it in", emoji="🔒", style=discord.ButtonStyle.danger,
            custom_id=f"sched:lock:{event_id}",
        ))
        self.event_id = event_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["event_id"]))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        event = await get_event(self.event_id)
        if event is None or event["status"] != "open":
            await interaction.followup.send("> This one's already wrapped up.", ephemeral=True)
            return
        if not _can_manage(interaction, event):
            await interaction.followup.send("> Only the event creator can lock it in early.", ephemeral=True)
            return
        if not await get_responders(self.event_id):
            await interaction.followup.send("> Nobody has answered yet.", ephemeral=True)
            return
        await finalize(interaction.client, self.event_id)
        await interaction.followup.send("> Locked in! Results are posted.", ephemeral=True)


class AddEventButton(discord.ui.DynamicItem[discord.ui.Button], template=r"sched:addevent:(?P<event_id>\d+)"):
    def __init__(self, event_id: int):
        super().__init__(discord.ui.Button(
            label="Add event", emoji="📅", style=discord.ButtonStyle.primary,
            custom_id=f"sched:addevent:{event_id}",
        ))
        self.event_id = event_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["event_id"]))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        event = await get_event(self.event_id)
        if event is None or event["final_start"] is None:
            await interaction.followup.send("> There's no time picked for this one.", ephemeral=True)
            return
        if not await claim_discord_event(self.event_id):
            await interaction.followup.send("> Already added, check the events tab!", ephemeral=True)
            return
        try:
            scheduled = await interaction.guild.create_scheduled_event(
                name=event["title"],
                start_time=event["final_start"],
                end_time=event["final_end"],
                privacy_level=discord.PrivacyLevel.guild_only,
                entity_type=discord.EntityType.external,
                location=event["location"] or "Discord",
            )
        except discord.HTTPException as e:
            await set_discord_event_id(self.event_id, None)  # release so someone can retry
            await interaction.followup.send(f"> Couldn't create the event: {e.text or e}", ephemeral=True)
            return
        await set_discord_event_id(self.event_id, scheduled.id)
        event = await get_event(self.event_id)
        options = get_options(event, await get_participants(self.event_id), await get_all_picks(self.event_id))
        await interaction.message.edit(view=final_view_for(event, options))
        await interaction.followup.send("> I added this event, check the events tab!", ephemeral=True)


class RescheduleButton(discord.ui.DynamicItem[discord.ui.Button], template=r"sched:resched:(?P<event_id>\d+)"):
    def __init__(self, event_id: int):
        super().__init__(discord.ui.Button(
            label="Reschedule", emoji="🔁", style=discord.ButtonStyle.secondary,
            custom_id=f"sched:resched:{event_id}",
        ))
        self.event_id = event_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["event_id"]))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        event = await get_event(self.event_id)
        if event is None or event["status"] != "final":
            await interaction.followup.send("> There's nothing to reschedule yet.", ephemeral=True)
            return
        if not _can_manage(interaction, event):
            await interaction.followup.send("> Only the event creator can reschedule.", ephemeral=True)
            return
        participants = await get_participants(self.event_id)
        options = get_options(event, participants, await get_all_picks(self.event_id))
        choice = event["choice"] or 0
        if choice + 1 >= len(options):
            await interaction.followup.send("> There are no backup times left.", ephemeral=True)
            return
        nxt = options[choice + 1]
        await interaction.followup.send(
            f"> Move **{event['title']}** to the next best time?\n{_block_line(nxt, len(participants))}\n> Everyone will get pinged.",
            view=RescheduleConfirmView(self.event_id, choice),
            ephemeral=True,
        )


class RescheduleConfirmView(discord.ui.View):
    def __init__(self, event_id: int, for_choice: int):
        super().__init__(timeout=600)
        self.event_id = event_id
        self.for_choice = for_choice

    @discord.ui.button(label="Reschedule", emoji="🔁", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.stop()
        event = await get_event(self.event_id)
        participants = await get_participants(self.event_id)
        rows = await get_all_picks(self.event_id)
        options = get_options(event, participants, rows)
        nxt_index = self.for_choice + 1
        if nxt_index >= len(options) or not await advance_choice(
            self.event_id, self.for_choice, options[nxt_index].start_dt, options[nxt_index].end_dt
        ):
            await interaction.edit_original_response(
                content="> This was already rescheduled, check the post for the current time.", view=None
            )
            return

        event = await get_event(self.event_id)
        best = options[nxt_index]

        # move the Discord event if one was already added
        note = "> Rescheduled! Hit **Add event** on the post if you want it in the events tab."
        if event["discord_event_id"]:
            try:
                scheduled = await interaction.guild.fetch_scheduled_event(event["discord_event_id"])
                await scheduled.edit(start_time=best.start_dt, end_time=best.end_dt)
                note = "> Rescheduled! I moved the event in the events tab to the new time."
            except discord.HTTPException:
                logger.warning("couldn't move scheduled event for %s", self.event_id, exc_info=True)
                note = "> Rescheduled! I couldn't move the old event in the events tab, so you may need to update it by hand."

        embed, options = build_final_embed(event, participants, rows)
        message = _partial_message(interaction.client, event)
        try:
            await message.edit(embed=embed, view=final_view_for(event, options))
            await message.reply(
                f"> **{event['title']}** got rescheduled to {discord.utils.format_dt(best.start_dt, 'F')}! "
                f"{_mentions(participants)}"
            )
        except discord.HTTPException:
            logger.warning("couldn't post reschedule for %s", self.event_id, exc_info=True)
        await interaction.edit_original_response(content=note, view=None)
        logger.info("Rescheduled event %s to option %s", self.event_id, nxt_index)


# ---------------------------------------------------------------------------
# private picker grid
# ---------------------------------------------------------------------------

class SlotButton(discord.ui.Button):
    def __init__(self, hour: int, state, row: int):
        # state: None = busy, False = free, True = preferred
        if state is None:
            style, emoji = discord.ButtonStyle.secondary, None
        elif state:
            style, emoji = discord.ButtonStyle.primary, "⭐"
        else:
            style, emoji = discord.ButtonStyle.success, None
        super().__init__(label=hour_label(hour), style=style, emoji=emoji, row=row)
        self.hour = hour

    async def callback(self, interaction: discord.Interaction):
        view: PickerView = self.view
        key = (view.current_day, self.hour)
        state = view.picks.get(key)
        if state is None:
            view.picks[key] = False      # busy -> free
        elif not state:
            view.picks[key] = True       # free -> preferred
        else:
            del view.picks[key]          # preferred -> busy
        await view.redraw(interaction)


class NavButton(discord.ui.Button):
    def __init__(self, action: str, **kwargs):
        super().__init__(row=4, **kwargs)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        view: PickerView = self.view
        await getattr(view, f"on_{self.action}")(interaction)


class PickerView(discord.ui.View):
    def __init__(self, event, user_id: int, picks: dict):
        super().__init__(timeout=1800)
        self.event_id = event["id"]
        self.title = event["title"]
        self.user_id = user_id
        self.dates = _dates(event)
        self.hours = list(range(event["day_start_hour"], event["day_end_hour"]))
        self.picks = dict(picks)  # {(date, hour): preferred}
        self.page = 0
        self.render()

    @property
    def current_day(self):
        return self.dates[self.page]

    def _day_full(self) -> bool:
        return all((self.current_day, h) in self.picks for h in self.hours)

    def content(self) -> str:
        n = len(self.picks)
        return (
            f"**{self.title}** · picking your times\n"
            f"### {day_label(self.current_day)}  (day {self.page + 1} of {len(self.dates)})\n"
            f"⬜ busy · 🟩 free · ⭐ preferred · tap a time to cycle · times in {tz_abbrev()}\n"
            f"-# {n} hour{'s' if n != 1 else ''} picked across all days. Nothing counts until you hit **Save**."
        )

    def render(self):
        self.clear_items()
        for i, h in enumerate(self.hours):
            self.add_item(SlotButton(h, self.picks.get((self.current_day, h)), row=i // 5))

        last = len(self.dates) - 1
        self.add_item(NavButton("prev", emoji="◀️", style=discord.ButtonStyle.secondary, disabled=self.page == 0))
        self.add_item(NavButton("copy", label="Same as prev", style=discord.ButtonStyle.secondary, disabled=self.page == 0))
        self.add_item(NavButton(
            "fill",
            label="Clear day" if self._day_full() else "All day",
            style=discord.ButtonStyle.secondary,
        ))
        self.add_item(NavButton("next", emoji="▶️", style=discord.ButtonStyle.secondary, disabled=self.page == last))
        self.add_item(NavButton("save", label="Save", emoji="✅", style=discord.ButtonStyle.success))

    async def redraw(self, interaction: discord.Interaction):
        self.render()
        await interaction.response.edit_message(content=self.content(), view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    # nav actions
    async def on_prev(self, interaction):
        self.page = max(0, self.page - 1)
        await self.redraw(interaction)

    async def on_next(self, interaction):
        self.page = min(len(self.dates) - 1, self.page + 1)
        await self.redraw(interaction)

    async def on_fill(self, interaction):
        day = self.current_day
        if self._day_full():
            for h in self.hours:
                self.picks.pop((day, h), None)
        else:
            for h in self.hours:
                self.picks.setdefault((day, h), False)
        await self.redraw(interaction)

    async def on_copy(self, interaction):
        prev, day = self.dates[self.page - 1], self.current_day
        for h in self.hours:
            if (prev, h) in self.picks:
                self.picks[(day, h)] = self.picks[(prev, h)]
            else:
                self.picks.pop((day, h), None)
        await self.redraw(interaction)

    async def on_save(self, interaction):
        await interaction.response.defer()
        if not await save_user_picks(self.event_id, self.user_id, self.picks):
            await interaction.edit_original_response(content="> Too late, this one already wrapped up.", view=None)
            self.stop()
            return
        self.stop()
        n = len(self.picks)
        await interaction.edit_original_response(
            content=(
                f"> ✅ Saved {n} hour{'s' if n != 1 else ''} for **{self.title}**!\n"
                "> You can hit **Pick my times** again to change it before the reveal."
            ),
            view=None,
        )
        await after_save(interaction.client, self.event_id)
