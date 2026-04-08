import discord
from discord.ui import Button, View, Modal, TextInput
from discord import ButtonStyle, Interaction, Member, Guild
from datetime import datetime, timezone, timedelta
import logging
import random
import string
import asyncio

import config
from utils.database import get_player_data, is_on_cooldown, db_write, is_user_verified, save_data_to_json, load_data_from_json, get_master_player_record
from utils.helpers import get_uuid_from_ign, get_base_region_key, create_ticket, get_bust_url, ping_testers_for_queue
from utils.embeds import create_ticket_user_info_embed
from utils.constants import high_testing_tiers, tier_ranking

class VerifyAccountModal(Modal):
    def __init__(self):
        super().__init__(title="Verify Minecraft Account")
        self.add_item(TextInput(label="Minecraft Username", placeholder="Enter your Minecraft username", custom_id="mc_username_verify"))

    async def on_submit(self, interaction: Interaction):
        mc_username = self.children[0].value.strip()
        await interaction.response.defer(ephemeral=True, thinking=True)
        uuid = await get_uuid_from_ign(mc_username)
        if not uuid:
            return await interaction.followup.send(f"❌ Could not retrieve UUID for `{mc_username}`. Please double-check the spelling.", ephemeral=True)

        mc_skin_url = get_bust_url(uuid)
        embed = discord.Embed(
            title="✅ Confirm Minecraft Account",
            description=(
                f"**In-Game Name:** `{mc_username}`\n"
                f"**UUID:** `{uuid}`\n\n"
                "If this is your correct account, click **Confirm** below."
            ),
            color=discord.Color.blue()
        )
        if mc_skin_url:
            embed.set_thumbnail(url=mc_skin_url)

        view = ConfirmVerificationView(interaction.user.id, mc_username, uuid)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

class ConfirmVerificationView(View):
    def __init__(self, discord_id: int, mc_username: str, uuid: str):
        super().__init__(timeout=None) 
        self.add_item(ConfirmButton(discord_id, mc_username, uuid))
        self.message = None

class ConfirmButton(Button):
    def __init__(self, discord_id: int, mc_username: str, uuid: str):
        super().__init__(style=ButtonStyle.green, label="Confirm", custom_id=f"confirm_verify_{discord_id}")
        self.discord_id = discord_id
        self.mc_username = mc_username
        self.uuid = uuid

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != self.discord_id:
            return await interaction.followup.send("You cannot confirm this verification.", ephemeral=True)
        
        existing_player = await get_master_player_record(self.uuid, by_uuid=True)
        if existing_player and existing_player['discord_id'] != self.discord_id:
            for item in self.view.children:
                item.disabled = True
            await interaction.edit_original_response(view=self.view)
            
            return await interaction.followup.send(
                f"❌ This Minecraft account (`{self.mc_username}`) is already linked to another Discord user. "
                "If you believe this is a mistake, please contact staff.",
                ephemeral=True
            )

        await db_write("INSERT INTO players (discord_id, minecraft_username, uuid) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE minecraft_username = VALUES(minecraft_username), uuid = VALUES(uuid)", (self.discord_id, self.mc_username, self.uuid))
        await db_write("INSERT INTO tiers (discord_id, minecraft_username, uuid) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE minecraft_username = VALUES(minecraft_username), uuid = VALUES(uuid)", (self.discord_id, self.mc_username, self.uuid))

        for item in self.view.children:
            item.disabled = True
        await interaction.edit_original_response(view=self.view)
        
        await interaction.followup.send(f"✅ Your Minecraft account `{self.mc_username}` has been successfully verified!", ephemeral=True)

class UpdateIGNModal(Modal):
    def __init__(self):
        super().__init__(title="Update Minecraft IGN")
        self.add_item(TextInput(label="New Minecraft Username", placeholder="Enter your new IGN", custom_id="new_mc_username"))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        new_mc_username = self.children[0].value.strip()
        new_uuid = await get_uuid_from_ign(new_mc_username)

        if not new_uuid:
            return await interaction.followup.send(f"❌ Could not retrieve UUID for `{new_mc_username}`. Please check the spelling.", ephemeral=True)
      
        existing_player = await get_master_player_record(new_uuid, by_uuid=True)
        if existing_player and existing_player['discord_id'] != interaction.user.id:
            return await interaction.followup.send(
                f"❌ This Minecraft account (`{new_mc_username}`) is already linked to another Discord user.",
                ephemeral=True
            )

        await db_write("UPDATE players SET uuid = %s, minecraft_username = %s WHERE discord_id = %s", (new_uuid, new_mc_username, interaction.user.id))
        await db_write("UPDATE tiers SET uuid = %s, minecraft_username = %s WHERE discord_id = %s", (new_uuid, new_mc_username, interaction.user.id))
        
        await interaction.followup.send(f"✅ Successfully updated your Minecraft IGN to `{new_mc_username}`!", ephemeral=True)

class UpdateIGNView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(UpdateIGNButton())
        self.message = None

class UpdateIGNButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.secondary, label="Update IGN", custom_id="update_ign_button")

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(UpdateIGNModal())

class VerifyAccountButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="Verify Account", custom_id="persistent_verify_account")

    async def callback(self, interaction: Interaction):
        player_data = await get_player_data(interaction.user.id)

        if player_data and player_data.get('uuid'):
            mc_skin_url = get_bust_url(player_data.get('uuid'))
            embed = discord.Embed(
                title="⚠️ Already Verified",
                description=(
                    f"You have already verified the Minecraft account:\n\n"
                    f"**IGN:** `{player_data.get('minecraft_username', 'N/A')}`\n"
                    f"**UUID:** `{player_data.get('uuid')}`\n\n"
                    "If you changed your IGN, you can update it below."
                ),
                color=discord.Color.orange()
            )
            if mc_skin_url:
                embed.set_thumbnail(url=mc_skin_url)
            
            view = UpdateIGNView()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            view.message = await interaction.original_response()
        else:
            await interaction.response.send_modal(VerifyAccountModal())

class RegionSelectionModal(Modal):
    def __init__(self, guild: discord.Guild):
        super().__init__(title="Join Testing Waitlist")
        self.guild = guild
        self.add_item(TextInput(label="Region (NA, EU, AS, AU, etc.)", placeholder="Enter your region", required=True))
        self.add_item(TextInput(label="Preferred Server", placeholder="Server you play on", required=True))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        
        if not await is_user_verified(user.id):
            return await interaction.followup.send("You must verify your Minecraft account first! Click the 'Verify Account' button.", ephemeral=True)

        is_cooldown, time_remaining = await is_on_cooldown(user.id)
        if is_cooldown:
            cooldown_end = datetime.now(timezone.utc) + time_remaining
            return await interaction.followup.send(f"You are on cooldown. It ends <t:{int(cooldown_end.timestamp())}:R>.", ephemeral=True)
        
        region = self.children[0].value.strip().lower()
        server = self.children[1].value.strip()
        base_region = get_base_region_key(region)

        if not base_region:
            return await interaction.followup.send("Invalid region provided. Please use a valid region code (e.g., NA, EU, AS).", ephemeral=True)
        
        player_data = await get_player_data(user.id) or {}
        tier = player_data.get("tier", "Unranked")
        
        await db_write("UPDATE tiers SET region = %s, server = %s WHERE discord_id = %s", (region, server, user.id))
        
        if tier in high_testing_tiers:
            ticket_channel, error_msg = await create_ticket(interaction.guild, user, None, "High Tier Test")
            
            if error_msg:
                return await interaction.followup.send(f"Failed to create high-tier ticket: {error_msg}", ephemeral=True)

            updated_player_data = await get_player_data(user.id)
            info_embed = await create_ticket_user_info_embed(user, updated_player_data, "N/A")
            
            await ticket_channel.send(embed=info_embed)

            return await interaction.followup.send(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

        target_role_id = config.REGION_DATA[base_region]["waitlist_role_id"]
        waitlist_role = self.guild.get_role(target_role_id)
        
        if not waitlist_role:
             return await interaction.followup.send(f"Error: Waitlist role for region `{base_region.upper()}` not found.", ephemeral=True)

        if waitlist_role in user.roles:
            return await interaction.followup.send("You are already in a waitlist.", ephemeral=True)
            
        await user.add_roles(waitlist_role)
        await interaction.followup.send(f"You have been added to the {waitlist_role.name} waitlist.", ephemeral=True)

class JoinWaitlistButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="Enter Waitlist", custom_id="persistent_join_waitlist")

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(RegionSelectionModal(interaction.guild))
class ViewCooldownButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="View Cooldown",
            style=discord.ButtonStyle.blurple,
            custom_id="persistent_view_cd"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        on_cd, remaining = await is_on_cooldown(interaction.user.id)

        if on_cd:
            end_ts = int((datetime.now(timezone.utc) + remaining).timestamp())
            await interaction.followup.send(content=f"You are on testing cooldown. You can test again <t:{end_ts}:R>.", ephemeral=True)
        else:
            await interaction.followup.send(content="You are not on testing cooldown.", ephemeral=True)         
class WaitlistView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyAccountButton())
        self.add_item(JoinWaitlistButton())
        self.add_item(ViewCooldownButton())


class JoinQueueButton(Button):
    def __init__(self, region: str):
        super().__init__(label="Join Queue", style=ButtonStyle.blurple, custom_id=f"join_queue_{region}")
        self.region = region

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        active_testers_data = await load_data_from_json("active_testers.json", default_data={})
        active_testers = active_testers_data.get(self.region, [])
        if interaction.user.id in active_testers:
            return await interaction.followup.send("You are an active tester and cannot join the queue.", ephemeral=True)

        queue_data = await load_data_from_json("queue_data.json", default_data={})
        queue = queue_data.setdefault(self.region, [])
        if interaction.user.id in queue:
            return await interaction.followup.send("You are already in the queue.", ephemeral=True)

        if len(queue) >= config.MAX_QUEUE_SIZE:
            return await interaction.followup.send("The queue is full. Try again later.", ephemeral=True)

        player_data = await get_player_data(interaction.user.id)
        if not player_data or not player_data.get('uuid'):
            return await interaction.followup.send("Please verify your account first.", ephemeral=True)

        user_region = player_data.get('region')
        if not user_region or user_region.lower() == 'n/a':
            return await interaction.followup.send(
                f"❌ **Region Not Found**\nYou do not have a region assigned. Please join the waitlist in <#{config.REQUEST_TEST_CHANNEL_ID}>. If you are already in a waitlist channel, use `/leave` then join again.",
                ephemeral=True
            )

        is_cooldown, time_remaining = await is_on_cooldown(interaction.user.id)
        if is_cooldown:
            cooldown_end = datetime.now(timezone.utc) + time_remaining
            return await interaction.followup.send(f"You are on cooldown. It ends <t:{int(cooldown_end.timestamp())}:R>.", ephemeral=True)

        queue.append(interaction.user.id)
        await save_data_to_json("queue_data.json", queue_data)
        await ping_testers_for_queue(interaction.client, interaction.user, self.region)

        base_region = get_base_region_key(self.region)
        if base_region:
            waitlist_role_id = config.REGION_DATA[base_region].get("waitlist_role_id")
            if waitlist_role_id:
                role = interaction.guild.get_role(waitlist_role_id)
                if role and role in interaction.user.roles:
                    try:
                        await interaction.user.remove_roles(role, reason="Joined the active queue")
                    except discord.Forbidden:
                        pass
        
        await interaction.followup.send("You have successfully joined the queue.", ephemeral=True)

class QueueView(View):
    def __init__(self, region: str, queue_open: bool):
        super().__init__(timeout=None)
        if queue_open:
            self.add_item(JoinQueueButton(region))