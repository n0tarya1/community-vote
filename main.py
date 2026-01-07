import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timedelta

# you can configure the bot settings here
CONFIG = {
    'VOTES_REQUIRED': 3,        
    'LOGS_FILE': 'delete_logs.json',
    'LIMIT_FILE': 'user_limits.json',
    'MAX_VOTES_PER_DAY': 5       
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

class EmergencyView(discord.ui.View):
    def __init__(self, target_id):
        super().__init__(timeout=3600)
        self.target_id = target_id

    @discord.ui.button(label="🚨 EMERGENCY DELETE", style=discord.ButtonStyle.danger)
    async def handle_emergency(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            target = await interaction.channel.fetch_message(self.target_id)
            event_detail = f"🚨 **SPECIAL BUTTON USED by {interaction.user}**"
            
            save_event(str(target.author), target.content, [str(interaction.user)], event_detail)
            
            await target.delete()
            await interaction.message.delete() 
            await interaction.response.send_message(f"🚨 **Emergency Action Taken** by {interaction.user.mention}.", ephemeral=False)
        except discord.NotFound:
            await interaction.response.send_message("❌ Message already gone.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

def check_limit(user_id):
    if not os.path.exists(CONFIG['LIMIT_FILE']): return True, 0
    try:
        with open(CONFIG['LIMIT_FILE'], 'r') as f:
            data = json.load(f)
    except: data = {}
    
    uid = str(user_id)
    now = datetime.now()
    if uid not in data: return True, 0
    
    active_uses = [t for t in data[uid] if (now - datetime.fromisoformat(t)) < timedelta(hours=24)]
    return len(active_uses) < CONFIG['MAX_VOTES_PER_DAY'], len(active_uses)

def update_usage(user_id):
    data = {}
    if os.path.exists(CONFIG['LIMIT_FILE']):
        try:
            with open(CONFIG['LIMIT_FILE'], 'r') as f:
                data = json.load(f)
        except: data = {}
    
    uid = str(user_id)
    if uid not in data: data[uid] = []
    data[uid].append(datetime.now().isoformat())
    
    with open(CONFIG['LIMIT_FILE'], 'w') as f:
        json.dump(data, f, indent=2)

def save_event(author, text, users, outcome):
    history = []
    if os.path.exists(CONFIG['LOGS_FILE']):
        try:
            with open(CONFIG['LOGS_FILE'], 'r') as f:
                history = json.load(f)
        except: history = []
    
    history.append({
        'time': datetime.now().isoformat(),
        'target_user': author,
        'msg_text': text if text else "[Media/Link]",
        'voter_list': users, 
        'result': outcome
    })
    
    with open(CONFIG['LOGS_FILE'], 'w') as f:
        json.dump(history[-100:], f, indent=2)

def fetch_history():
    if not os.path.exists(CONFIG['LOGS_FILE']): return []
    try:
        with open(CONFIG['LOGS_FILE'], 'r') as f:
            data = json.load(f)
            day_ago = datetime.now() - timedelta(hours=24)
            return [item for item in data if datetime.fromisoformat(item['time']) > day_ago]
    except: return []

@tasks.loop(seconds=10)
async def monitor_polls():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                async for msg in channel.history(limit=20):
                    if msg.author == bot.user and msg.poll:
                        yes_side = next((a for a in msg.poll.answers if "delete" in a.text.lower()), None)
                        if yes_side and yes_side.vote_count >= CONFIG['VOTES_REQUIRED']:
                            try:
                                voters = [str(u) async for u in yes_side.voters()]
                                original_id = int(msg.content.split('/')[-1])
                                original_msg = await channel.fetch_message(original_id)
                                
                                save_event(str(original_msg.author), original_msg.content, voters, "✅ SUCCESS")
                                
                                await original_msg.delete()
                                await msg.delete() 
                            except: await msg.delete()
            except: continue

@bot.tree.context_menu(name="Vote Delete")
async def handle_context_menu(interaction: discord.Interaction, message: discord.Message):
    allowed, total = check_limit(interaction.user.id)
    if not allowed:
        await interaction.response.send_message("❌ Daily limit reached.", ephemeral=True)
        return

    if message.author == bot.user:
        await interaction.response.send_message("❌ You can't delete my own messages!", ephemeral=True)
        return

    vote_poll = discord.Poll(question=f"Delete message from {message.author.display_name}?", duration=timedelta(hours=1))
    vote_poll.add_answer(text="Yes, delete it", emoji="🗑️")
    vote_poll.add_answer(text="No, keep it", emoji="✅")

    update_usage(interaction.user.id)
    overlay = EmergencyView(target_id=message.id)

    await interaction.response.send_message(
        content=f"⚠️ **Vote to delete this message:**\n{message.jump_url}",
        poll=vote_poll,
        view=overlay
    )

@bot.tree.command(name='votedelete_logs', description='View community votes in past 24h')
async def show_logs(interaction: discord.Interaction):
    past_events = fetch_history()
    summary = discord.Embed(title="🗑️ Community Votes (Past 24h)", color=discord.Color.blue(), timestamp=datetime.now())
    
    if not past_events:
        summary.description = "*No activity logged.*"
        await interaction.response.send_message(embed=summary)
        return

    for entry in past_events[-10:]:
        raw_voters = entry.get('voter_list', "None")
        final_voters = ", ".join(raw_voters) if isinstance(raw_voters, list) else str(raw_voters)
        preview = f"||{entry['msg_text'][:250]}||" if entry['msg_text'] != "[Media/Link]" else "[Media/Link]"
        
        summary.add_field(
            name=f"User: {entry['target_user']}", 
            value=f"**Msg:** {preview}\n**Voters:** {final_voters}\n**Status:** {entry['result']}", 
            inline=False
        )
    await interaction.response.send_message(embed=summary)

@bot.event
async def on_ready():
    print(f'Ready! Logged in as {bot.user}')
    if not monitor_polls.is_running():
        monitor_polls.start()
    
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"Sync error: {e}")

if __name__ == "__main__":
    bot.run('put_ur_token_here') #don't forget your token!
