import discord
from discord import Interaction, Member, Color, TextChannel
import logging
import aiohttp
from datetime import datetime, timezone
import asyncio
import io
import chat_exporter

import config
from utils.database import db_write, get_player_data, load_data_from_json, save_data_to_json
from utils.constants import tier_ranking
from utils.embeds import set_footer, create_permission_denied_embed

def has_required_roles(user: discord.Member, *role_ids: int) -> bool:
    user_role_ids = {role.id for role in user.roles}
    return user_role_ids.intersection(set(role_ids))

async def check_permission(interaction: Interaction, *role_ids: int) -> bool:
    if interaction.user.guild_permissions.administrator or has_required_roles(interaction.user, *role_ids):
        return True
    
    embed = create_permission_denied_embed()
    if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(embed=embed, ephemeral=True)
    return False

def get_base_region_key(region_input: str | None) -> str | None:
    region_key = (region_input or 'na').lower()
    if region_key not in config.REGION_DATA:
        return 'na' 
    region_info = config.REGION_DATA[region_key]
    return region_info.get("maps_to", region_key)

async def get_uuid_from_ign(ign: str) -> str | None:
    if not ign or len(ign) < 3: return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.mojang.com/users/profiles/minecraft/{ign}") as r:
                if r.status == 200: return (await r.json()).get('id')
    except Exception as e:
        logging.error(f"Error fetching UUID for {ign}: {e}")
    return None

async def get_ign_from_uuid(uuid: str) -> str | None:
    if not uuid: return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}") as r:
                if r.status == 200: return (await r.json()).get('name')
    except Exception as e: logging.error(f"Error fetching IGN for {uuid}: {e}")
    return None
    
def get_bust_url(uuid: str) -> str | None:
    if not uuid: return None
    return f"https://render.crafty.gg/3d/bust/{uuid}"

async def create_transcript(channel: TextChannel, bot: discord.Client) -> discord.File | None:
    try:
        transcript_html = await chat_exporter.export(
            channel,
            limit=None,
            tz_info="UTC",
            military_time=True
        )

        if not transcript_html:
            return None

        file = discord.File(
            io.BytesIO(transcript_html.encode()),
            filename=f"transcript-{channel.name}.html"
        )
        return file
    except Exception as e:
        logging.error(f"Failed to create transcript for channel {channel.id}: {e}")
        return None

async def handle_ticket_close(interaction: Interaction, with_results: bool = False, **kwargs):
    transcripts_channel = interaction.guild.get_channel(config.TRANSCRIPTS_CHANNEL_ID)
    await interaction.channel.send("Generating transcript, this channel will be deleted shortly...")
    transcript_file = await create_transcript(interaction.channel, bot=interaction.client)

    if transcript_file and transcripts_channel:
        result_info = ""
        if with_results:
            result_info = (f"\n**Tester:** {kwargs.get('tester').mention}"
                         f"\n**Tested User:** {kwargs.get('tested_user_mention')}"
                         f"\n**Rank Given:** {kwargs.get('rank_name')}")
        
        embed = discord.Embed(
            title=f"Transcript for: #{interaction.channel.name}",
            description=f"Ticket closed by {interaction.user.mention}.{result_info}",
            color=discord.Color.gold() if with_results else discord.Color.light_grey(),
            timestamp=datetime.now(timezone.utc)
        )
        await transcripts_channel.send(embed=embed, file=transcript_file)
    
    await asyncio.sleep(5)
    try:
        await interaction.channel.delete(reason="Ticket closed.")
    except discord.NotFound:
        pass

async def update_queue_display(bot: discord.Client, region_key: str, ping: bool = False):
    from utils.ui import QueueView
    from utils.embeds import generate_queue_embed
    
    guild = bot.get_guild(config.GUILD_ID)
    if not guild: return

    region_data = config.REGION_DATA.get(region_key)
    if not region_data or 'maps_to' in region_data: return

    channel_id = region_data.get('channel_id')
    if not channel_id or not (channel := guild.get_channel(channel_id)): return

    active_testers = await load_data_from_json("active_testers.json", {})
    queue_data = await load_data_from_json("queue_data.json", {})
    last_session_times = await load_data_from_json("last_session_times.json", {})
    
    region_queue = queue_data.get(region_key, [])
    active_ids = active_testers.get(region_key, [])
    is_open = bool(active_ids)

    if is_open:
        last_session_times[region_key] = datetime.now(timezone.utc).isoformat()
        await save_data_to_json("last_session_times.json", last_session_times)
    
    last_session = last_session_times.get(region_key)
    embed = await generate_queue_embed(region_queue, region_key, active_ids, is_open, guild, last_session)
    view = QueueView(region=region_key, queue_open=is_open)
    
    msg_file = f"queue_message_{region_key}.json"
    queue_message_data = await load_data_from_json(msg_file, {})
    msg_id = queue_message_data.get("id")
    
    message_to_edit = None
    if msg_id:
        try:
            message_to_edit = await channel.fetch_message(msg_id)
        except (discord.NotFound, discord.Forbidden):
            pass

    try:
        content = "@here" if is_open else None

        if ping and message_to_edit:
            try:
                await message_to_edit.delete()
            except:
                pass
            message_to_edit = None

        if message_to_edit:
            await message_to_edit.edit(content=content, embed=embed, view=view)
        else:
            new_msg = await channel.send(content=content, embed=embed, view=view)
            await save_data_to_json(msg_file, {"id": new_msg.id})
            
    except Exception as e:
        logging.error(f"Failed to update queue display for {region_key}: {e}")

async def create_ticket(guild: discord.Guild, user_to_test: discord.Member, creator: discord.Member | None, ticket_type: str):
    player_data = await get_player_data(user_to_test.id)
    if not player_data:
        return None, "User is not verified/ranked."

    is_ht = player_data.get('tier') in config.high_testing_tiers or ticket_type == "High Tier Test"
    base_region = get_base_region_key(player_data.get('region')) or 'na'
    
    category_id = config.HIGH_TESTING_CATEGORY_ID if is_ht else config.REGION_DATA[base_region].get('category_id')
    category = guild.get_channel(category_id)
    if category and len(category.channels) >= 49:
        overflow_category = guild.get_channel(config.TESTING_OVERFLOW_CATEGORY_ID)
        if overflow_category:
            category = overflow_category
            logging.info(f"Category {category_id} is full. Using Overflow Category for {user_to_test.name}.")
        else:
            return None, "Primary category is full and Overflow category is not configured."

    if not category:
        return None, "Testing category is not configured for this region."
        
    mod_role = guild.get_role(config.MODERATOR_ROLE_ID)
    senior_tester_role = guild.get_role(config.SENIOR_TESTER_ROLE_ID)
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user_to_test: discord.PermissionOverwrite(view_channel=True),
    }
    
    if creator:
        overwrites[creator] = discord.PermissionOverwrite(view_channel=True)
    if mod_role:
        overwrites[mod_role] = discord.PermissionOverwrite(view_channel=True)
    if senior_tester_role:
        overwrites[senior_tester_role] = discord.PermissionOverwrite(view_channel=True)

    if is_ht:
        current_tier = player_data.get("tier", "Unranked")
        try:
            current_index = tier_ranking.index(current_tier)
            testing_for_tier = tier_ranking[max(0, current_index - 1)]
        except (ValueError, IndexError):
            testing_for_tier = "next" 
        channel_name_base = f"{user_to_test.name}-{testing_for_tier.lower()}"
    elif creator:
        channel_name_base = f"{user_to_test.name}-{creator.name}"
    else:
        channel_name_base = f"{user_to_test.name}-ticket"

    channel_name = f"🟢｜{channel_name_base}"

    try:
        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        creator_id = creator.id if creator else guild.me.id
        await db_write("INSERT INTO testing_tickets (channel_id, tested_user_id, created_by, creation_time) VALUES (%s, %s, %s, %s)",
                 (channel.id, user_to_test.id, creator_id, datetime.now(timezone.utc)))
        if is_ht:
            await db_write("INSERT INTO tickets (channel_id, is_exempt) VALUES (%s, TRUE) ON DUPLICATE KEY UPDATE is_exempt = TRUE", (channel.id,))
        return channel, None
    except Exception as e:
        logging.error(f"Failed to create ticket: {e}")
        return None, "An unexpected error occurred."

def _parse_options(options_list: list) -> list[str]:
    lines = []
    for opt in options_list:
        if opt.get('type') in (1, 2) and 'options' in opt:
            lines.extend(_parse_options(opt['options']))
            continue

        value = opt.get("value", "N/A")
        opt_type = opt.get('type')

        if opt_type == 6: 
            value = f"<@{value}>"
        elif opt_type == 7: 
            value = f"<#{value}>"
        elif opt_type == 8: 
            value = f"<@&{value}>"
        
        lines.append(f"`{opt['name']}`: {value}")
    return lines

async def log_command_exec(interaction: Interaction):
    from utils.embeds import create_command_log_embed
    log_channel = interaction.guild.get_channel(config.LOGGING_CHANNEL_ID)
    if not log_channel: return

    options = []
    raw_options = interaction.data.get("options")
    
    if raw_options:
        options = _parse_options(raw_options)

    await log_channel.send(embed=create_command_log_embed(interaction, options))

async def ping_testers_for_queue(bot: discord.Client, user_joined: discord.Member, region_key: str):
    ping_channel = bot.get_channel(config.QUEUE_JOIN_CHANNEL_ID)
    if not ping_channel:
        logging.warning("QUEUE_JOIN_CHANNEL_ID is not configured or not found.")
        return
        
    active_testers = (await load_data_from_json("active_testers.json", {})).get(region_key, [])
    if not active_testers:
        return 
        
    pings = ' '.join([f'<@{_id}>' for _id in active_testers])
    
    embed = discord.Embed(
        description=f"{user_joined.mention} has joined the **{region_key.upper()}** queue.",
        color=discord.Color.blue()
    )
    set_footer(embed) 
    
    try:
        await ping_channel.send(content=pings, embed=embed)
    except discord.Forbidden:
        logging.error(f"Missing permissions to send messages in the queue ping channel ({ping_channel.id})")