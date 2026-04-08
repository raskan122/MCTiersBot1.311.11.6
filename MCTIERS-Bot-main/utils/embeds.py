import discord
from discord import Color, Member, User, Guild, Interaction
from datetime import datetime, timezone
import pytz

import config
from utils.constants import rank_full_names

def set_footer(embed: discord.Embed):
    embed.set_footer(text="Testing Bot", icon_url=config.FOOTER_ICON_URL)
    return embed

def create_permission_denied_embed() -> discord.Embed:
    embed = discord.Embed(title="You do not have permission to do this!", color=Color.red())
    set_footer(embed)
    return embed

def create_command_log_embed(interaction: Interaction, options: list[str]) -> discord.Embed:
    command_name = interaction.command.qualified_name
    description = (
        f"**Command:** `/{command_name}`\n"
        f"**User:** {interaction.user.mention} (`{interaction.user.id}`)\n"
        f"**Channel:** {interaction.channel.mention}"
    )
    if options:
        description += "\n**Options:**\n" + "\n".join(options)
    
    embed = discord.Embed(
        title="Command Executed",
        description=description,
        color=Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )
    return embed

async def generate_queue_embed(region_queue: list, region: str, active_tester_ids: list, queue_open: bool, guild: Guild, last_session_time: str = None) -> discord.Embed:
    active_testers = [member for user_id in active_tester_ids if (member := guild.get_member(user_id))]
    
    if queue_open:
        embed = discord.Embed(title="Tester(s) Available!", color=Color.blurple())
        embed.description = "⏱️ The queue updates every 10 seconds.\nUse `/leave` if you wish to be removed from the waitlist or queue."
        
        queue_count = len(region_queue)

        if queue_count > 0:
            queue_title = f"__**Queue:**__ ({queue_count}/{config.MAX_QUEUE_SIZE})"
            queue_text = "\n".join(f"{i + 1}. <@{user}>" for i, user in enumerate(region_queue))
        else:
            queue_title = "__**Queue:**__"
            queue_text = "Empty"

        active_text = "\n".join(f"{i + 1}. {tester.mention}" for i, tester in enumerate(active_testers)) or "None"
        
        embed.add_field(name=queue_title, value=queue_text, inline=False)
        embed.add_field(name="**Active Testers:**", value=active_text, inline=False)
    else:
        last_session = datetime.now(pytz.timezone("CET"))
        if last_session_time:
            try:
                last_session = datetime.fromisoformat(last_session_time)
            except (ValueError, TypeError):
                pass
        unix_timestamp = int(last_session.timestamp())
        
        embed = discord.Embed(title="**No Testers Online**", color=Color.red())
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.description = f"No testers for your region are available at this time.\nYou will be pinged when a tester is available.\nCheck back later!\n\nLast testing session: <t:{unix_timestamp}:f>"
        
    return embed

def generate_waitlist_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📝 Evaluation Testing Waitlist",
        description=(
            "\u200b\nUpon applying, you will be added to a waitlist channel.\n"
            "Here you will be pinged when a tester of your region is available.\n"
            "If you are HT3 or higher, a high ticket will be created.\n\n"
            "• Region should be the region of the server you wish to test on.\n\n"
            "• Username should be the name of the account you will be testing on.\n\n"
            "🛑 **Failure to provide authentic information will result in a denied test.**"
        ),
        color=Color.from_rgb(255, 45, 45)
    )
    return embed

async def create_ticket_user_info_embed(user: Member | User, player_data: dict, last_test_date: str) -> discord.Embed:
    description_lines = []
    
    user_tier = player_data.get('tier', 'Unranked')
    ign = player_data.get('minecraft_username', 'N/A')
    
    description_lines.append(f"**User:** {user.mention}")
    description_lines.append(f"**Region:** {player_data.get('region', 'N/A').upper()}")
    description_lines.append(f"**Minecraft Username:** `{ign}`")
    description_lines.append(f"**Server:** {player_data.get('server', 'N/A')}")
    description_lines.append(f"**Previous Rank:** {rank_full_names.get(user_tier, 'Unranked')}")
    
    if last_test_date and last_test_date.lower() != "n/a":
        description_lines.append(f"**Last Test Date:** {last_test_date}")

    description = "\n".join(description_lines)
    
    embed = discord.Embed(color=Color.blurple(), description=description)
    embed.set_author(name=f"{ign}'s Information", icon_url=user.display_avatar.url)
    return embed

def create_stats_embed(member: Member, ign: str, uuid: str, region: str, monthly: int, all_time: int) -> discord.Embed:
    from utils.helpers import get_bust_url
    description = (
        f"**Minecraft Username:** `{ign}`\n"
        f"**Region:** {region.upper()}\n\n"
        f"**Tests This Month:** {monthly}\n"
        f"**All-Time Tests:** {all_time}"
    )
    
    embed = discord.Embed(description=description, color=Color.blue())
    embed.set_author(name=f"Tester Stats for {ign}", icon_url=member.display_avatar.url)
    if bust_url := get_bust_url(uuid):
        embed.set_thumbnail(url=bust_url)
    set_footer(embed)
    return embed

async def create_profile_embed(player_data: dict, discord_user: User | None) -> discord.Embed | None:
    from utils.helpers import get_bust_url, get_ign_from_uuid
    
    if not player_data:
        return None
    
    uuid = player_data.get('uuid')
    ign = player_data.get('minecraft_username') or await get_ign_from_uuid(uuid) or "Unknown"
    
    current_tier = player_data.get('tier', 'Unranked')
    peak_tier = player_data.get('peak_tier', 'Unranked')

    description_lines = []
    
    if discord_user:
        author_name = f"{(discord_user.global_name or discord_user.name)}'s Profile"
        author_icon = discord_user.display_avatar.url
    else:
        author_name = f"{ign}'s Profile"
        author_icon = None

    description_lines.append(f"**Minecraft Username:** `{ign}`")
    description_lines.append(f"**Current Tier:** {rank_full_names.get(current_tier)}")
    
    if current_tier != peak_tier:
        description_lines.append(f"**Peak Tier:** {rank_full_names.get(peak_tier)}")
    
    description_lines.append(f"**Region:** {player_data.get('region', 'N/A').upper()} • **Points:** {player_data.get('points', 0)}")
    
    embed = discord.Embed(description="\n".join(description_lines), color=Color.blue())
    embed.set_author(name=author_name, icon_url=author_icon)
    
    if bust_url := get_bust_url(uuid):
        embed.set_thumbnail(url=bust_url)

    set_footer(embed) 
    return embed