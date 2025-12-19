# cogs/database.py
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
import time
import re

CONFIG_FILE = "db_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE): return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(config, f, indent=4, ensure_ascii=False)

async def send_log(bot, guild_id, config, message, user=None):
    log_channel_id = config.get(str(guild_id), {}).get("ログ")
    if log_channel_id:
        channel = bot.get_channel(int(log_channel_id))
        if channel:
            embed = discord.Embed(title="🛡️ 操作ログ", description=message, color=discord.Color.dark_gray())
            if user:
                embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
            embed.set_footer(text=f"発生時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            await channel.send(embed=embed)

user_cooldowns = {}
def check_cooldown(user_id):
    now = time.time()
    if user_id not in user_cooldowns: user_cooldowns[user_id] = []
    user_cooldowns[user_id] = [t for t in user_cooldowns[user_id] if now - t < 60]
    if len(user_cooldowns[user_id]) >= 3: return False
    user_cooldowns[user_id].append(now)
    return True

# --- 作品登録モーダル ---
class WorkRegistrationModal(discord.ui.Modal, title='作品登録'):
    title_input = discord.ui.TextInput(label='タイトル', placeholder='作品名を入力...', required=True)
    author_input = discord.ui.TextInput(label='作者', placeholder='作者名を入力...', required=False)
    
    def __init__(self, bot, config, media_type, sub_type, genre, rating, target_channel):
        super().__init__()
        self.bot, self.config = bot, config
        self.media_type, self.sub_type, self.genre, self.rating, self.target_channel = media_type, sub_type, genre, rating, target_channel

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        blacklist = self.config.get(guild_id, {}).get("NGユーザー", [])
        if interaction.user.id in blacklist:
            await send_log(self.bot, interaction.guild_id, self.config, f"🚫 **投稿拒否 (NGユーザー)**\n内容: {self.title_input.value}", user=interaction.user)
            return await interaction.response.send_message("⚠️ 投稿権限がありません。", ephemeral=True)

        if not check_cooldown(interaction.user.id):
            return await interaction.response.send_message("⚠️ 短時間に投稿しすぎです。", ephemeral=True)

        header_text = f"**{self.sub_type}**"
        entry_text = (
            f"【{self.media_type} ＞ {self.sub_type} ＞ {self.genre}】**{self.title_input.value}** \u200b ||{interaction.user.id}||\n"
            f"└ 作者: {self.author_input.value or '未入力'} / 満足度: {self.rating}\n\n"
        )
        
        last_msg = None
        async for msg in self.target_channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if len(msg.embeds[0].description) + len(entry_text) < 3800:
                    last_msg = msg
                    break

        if last_msg:
            embed = last_msg.embeds[0]
            desc = embed.description
            if header_text in desc:
                parts = desc.split(header_text)
                new_desc = parts[0] + header_text + "\n" + entry_text + parts[1].lstrip()
            else:
                new_desc = desc.strip() + f"\n\n{header_text}\n" + entry_text
            
            embed.description = new_desc
            await last_msg.edit(embed=embed)
        else:
            embed = discord.Embed(
                title=f"📚 {self.media_type} データベース", 
                description=f"{header_text}\n{entry_text}", 
                color=discord.Color.blue()
            )
            await self.target_channel.send(embed=embed)

        await send_log(self.bot, interaction.guild_id, self.config, f"✅ **作品登録**\nタイトル: {self.title_input.value}\n階層: {self.media_type} > {self.sub_type} > {self.genre}", user=interaction.user)
        await interaction.response.send_message(f"✅ 「{self.title_input.value}」を登録しました！", ephemeral=True)

# --- ジャンル・評価選択View ---
class GenreSelectView(discord.ui.View):
    def __init__(self, bot, config, media, target_channel):
        super().__init__(timeout=600)
        self.bot, self.config, self.media, self.target_channel = bot, config, media, target_channel
        self.sub_type = "未指定"
        self.genre = "未指定"

        self.type_map = {
            "小説": [("長編", "📖"), ("短編", "📄"), ("ライトノベル", "⚡"), ("実験小説", "🧪"), ("単行本", "📕"), ("文庫", "📘"), ("Web連載", "🌐"), ("ノベルゲー", "🎮"), ("官能小説", "🔞"), ("その他", "📁")],
            "漫画": [("長編", "🎨"), ("短編", "📝"), ("アンソロジー", "📚"), ("短編集", "📋"), ("Web連載", "📱"), ("読み切り", "🎯"), ("4コマ", "🍀"), ("同人誌", "🤝"), ("フルカラー", "🌈"), ("その他", "📁")],
            "アニメ": [("TVシリーズ(1期)", "📺"), ("TVシリーズ(2期以降)", "🔁"), ("劇場版", "🎬"), ("OVA", "📀"), ("Webアニメ", "💻"), ("短編アニメ", "⏲️"), ("個人製作", "👤"), ("リマスター", "✨"), ("実写融合", "🎭"), ("その他", "📁")],
            "映画": [("邦画", "🗾"), ("洋画", "🇺🇸"), ("ドキュメンタリー", "📹"), ("実話ベース", "📰"), ("短編映画", "🎞️"), ("リバイバル", "🔙"), ("3D/IMAX", "🕶️"), ("インディーズ", "🎸"), ("オムニバス", "🧩"), ("その他", "📁")]
        }
        self.sub_type_select.options = [discord.SelectOption(label=n, emoji=e) for n, e in self.type_map.get(media, [("その他", "📁")])]

    @discord.ui.select(placeholder="1. 種別を選択", row=0)
    async def sub_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.sub_type = select.values[0]
        await interaction.response.edit_message(content=f"**{self.media} ＞ {self.sub_type}**\n次にジャンルを選択してください。")

    @discord.ui.select(
        placeholder="2. ジャンルを選択", row=1,
        options=[
            discord.SelectOption(label="アクション", emoji="⚔️"), discord.SelectOption(label="アニメ化作品", emoji="🎬"),
            discord.SelectOption(label="日常", emoji="☕"), discord.SelectOption(label="エッセイ・実録", emoji="✍️"),
            discord.SelectOption(label="オカルト", emoji="🔮"), discord.SelectOption(label="学園", emoji="🏫"),
            discord.SelectOption(label="官能", emoji="🔞"), discord.SelectOption(label="グルメ", emoji="🍳"),
            discord.SelectOption(label="コメディ", emoji="🤣"), discord.SelectOption(label="サスペンス", emoji="😨"),
            discord.SelectOption(label="時代劇・歴史", emoji="🏯"), discord.SelectOption(label="児童書・絵本", emoji="🧸"),
            discord.SelectOption(label="実用・ビジネス", emoji="📊"), discord.SelectOption(label="SF", emoji="🚀"),
            discord.SelectOption(label="スポーツ", emoji="⚽"), discord.SelectOption(label="なろう系・転生", emoji="🏰"),
            discord.SelectOption(label="ファンタジー", emoji="🧙"), discord.SelectOption(label="BL", emoji="💎"),
            discord.SelectOption(label="ホラー", emoji="👻"), discord.SelectOption(label="ミステリー", emoji="🔍"),
            discord.SelectOption(label="百合", emoji="🌸"), discord.SelectOption(label="TL", emoji="💋"),
            discord.SelectOption(label="恋愛", emoji="💖"), discord.SelectOption(label="その他", emoji="📁"),
        ]
    )
    async def genre_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.genre = select.values[0]
        await interaction.response.edit_message(content=f"**{self.media} ＞ {self.sub_type} ＞ {self.genre}**\n満足度を選んでください。")

    @discord.ui.select(
        placeholder="3. 満足度を選択", row=2,
        options=[
            discord.SelectOption(label="🏆 殿堂入り", value="👑 殿堂入り"),
            discord.SelectOption(label="⭐⭐⭐⭐⭐", value="⭐⭐⭐⭐⭐"),
            discord.SelectOption(label="⭐⭐⭐⭐", value="⭐⭐⭐⭐"),
            discord.SelectOption(label="⭐⭐⭐", value="⭐⭐⭐"),
            discord.SelectOption(label="⭐⭐", value="⭐⭐"),
            discord.SelectOption(label="⭐", value="⭐"),
            discord.SelectOption(label="🚫 二度と読まない", value="💀 二度と読まない"),
        ]
    )
    async def rating_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.send_modal(WorkRegistrationModal(self.bot, self.config, self.media, self.sub_type, self.genre, select.values[0], self.target_channel))

# --- 媒体選択View (永続化対応) ---
class RegistrationView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None) # 永続化のため timeout は None
        self.bot = bot

    async def start_registration(self, interaction: discord.Interaction, media: str):
        config_data = load_config()
        guild_id = str(interaction.guild_id)
        channel_id = config_data.get(guild_id, {}).get(media)
        if not channel_id:
            return await interaction.response.send_message(f"❌ {media} の保存先が設定されていません。", ephemeral=True)
        
        target_channel = interaction.guild.get_channel(int(channel_id))
        if not target_channel:
             return await interaction.response.send_message(f"❌ 設定されたチャンネルが見つかりません。", ephemeral=True)

        await interaction.response.send_message(f"【{media}】の登録を開始します。", view=GenreSelectView(self.bot, config_data, media, target_channel), ephemeral=True)

    @discord.ui.button(label="小説", style=discord.ButtonStyle.primary, emoji="📖", custom_id="db_persistent:novel")
    async def novel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_registration(interaction, "小説")

    @discord.ui.button(label="漫画", style=discord.ButtonStyle.primary, emoji="🎨", custom_id="db_persistent:manga")
    async def manga_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_registration(interaction, "漫画")

    @discord.ui.button(label="アニメ", style=discord.ButtonStyle.primary, emoji="📺", custom_id="db_persistent:anime")
    async def anime_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_registration(interaction, "アニメ")

    @discord.ui.button(label="映画", style=discord.ButtonStyle.primary, emoji="🎬", custom_id="db_persistent:movie")
    async def movie_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_registration(interaction, "映画")

class DatabaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="db_setup", description="保存先を設定します")
    @app_commands.choices(media=[
        app_commands.Choice(name="小説", value="小説"), app_commands.Choice(name="漫画", value="漫画"),
        app_commands.Choice(name="アニメ", value="アニメ"), app_commands.Choice(name="映画", value="映画"),
        app_commands.Choice(name="ログ出力先", value="ログ"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def db_setup(self, interaction: discord.Interaction, media: app_commands.Choice[str], channel: discord.TextChannel):
        config_data = load_config()
        guild_id = str(interaction.guild_id)
        if guild_id not in config_data: config_data[guild_id] = {}
        config_data[guild_id][media.value] = channel.id
        save_config(config_data)
        await interaction.response.send_message(f"✅ {media.name} の設定を保存しました。", ephemeral=True)

    @app_commands.command(name="db_blacklist", description="NGユーザーを登録/解除します")
    @app_commands.checks.has_permissions(administrator=True)
    async def db_blacklist(self, interaction: discord.Interaction, user: discord.User):
        config_data = load_config()
        guild_id = str(interaction.guild_id)
        if guild_id not in config_data: config_data[guild_id] = {}
        if "NGユーザー" not in config_data[guild_id]: config_data[guild_id]["NGユーザー"] = []
        if user.id in config_data[guild_id]["NGユーザー"]:
            config_data[guild_id]["NGユーザー"].remove(user.id)
            msg = f"✅ {user.mention} のNG設定を解除しました。"
        else:
            config_data[guild_id]["NGユーザー"].append(user.id)
            msg = f"🚫 {user.mention} をNGユーザーに登録しました。"
        save_config(config_data)
        await send_log(self.bot, interaction.guild_id, config_data, msg, user=interaction.user)
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="db_menu", description="登録メニューを表示します")
    async def db_menu(self, interaction: discord.Interaction):
        await interaction.response.send_message("📚 **作品登録パネル**", view=RegistrationView(self.bot))

    @app_commands.command(name="db_delete", description="作品をタイトル指定で削除します")
    @app_commands.checks.has_permissions(administrator=True)
    async def db_delete(self, interaction: discord.Interaction, channel: discord.TextChannel, title: str):
        await interaction.response.defer(ephemeral=True)
        found = False
        async for msg in channel.history(limit=100):
            if msg.author == self.bot.user and msg.embeds:
                desc = msg.embeds[0].description
                if f"**{title}**" in desc:
                    pattern = r"【[^】]+】\*\*" + re.escape(title) + r"\*\*.*?\n└.*?\n\n"
                    new_desc = re.sub(pattern, "", desc, flags=re.DOTALL)
                    new_desc = re.sub(r"\*\*[^*]+\*\*\n+(?=\*\*|$)", "", new_desc)
                    if not new_desc.strip(): await msg.delete()
                    else:
                        msg.embeds[0].description = new_desc.strip()
                        await msg.edit(embed=msg.embeds[0])
                    found = True
                    break
        await interaction.followup.send("✅ 削除しました。" if found else "❌ 見つかりません。", ephemeral=True)

    @app_commands.command(name="db_clean_user", description="指定ユーザーの投稿を一括削除します")
    @app_commands.checks.has_permissions(administrator=True)
    async def db_clean_user(self, interaction: discord.Interaction, channel: discord.TextChannel, user: discord.User):
        await interaction.response.defer(ephemeral=True)
        count, target_id = 0, f"||{user.id}||"
        async for msg in channel.history(limit=100):
            if msg.author == self.bot.user and msg.embeds:
                desc = msg.embeds[0].description
                if target_id in desc:
                    pattern = r"【[^】]+】\*\*.*?\*\* \u200b " + re.escape(target_id) + r"\n└.*?\n\n"
                    matches = re.findall(pattern, desc, flags=re.DOTALL)
                    count += len(matches)
                    new_desc = re.sub(pattern, "", desc, flags=re.DOTALL)
                    new_desc = re.sub(r"\*\*[^*]+\*\*\n+(?=\*\*|$)", "", new_desc)
                    if not new_desc.strip(): await msg.delete()
                    else:
                        msg.embeds[0].description = new_desc.strip()
                        await msg.edit(embed=msg.embeds[0])
        await send_log(self.bot, interaction.guild_id, load_config(), f"🗑️ **一括削除**\n対象: {user.mention}\n削除数: {count}", user=interaction.user)
        await interaction.followup.send(f"✅ {count}件削除しました。", ephemeral=True)

async def setup(bot):
    # 再起動時にボタンを有効化するために add_view を実行
    bot.add_view(RegistrationView(bot))
    await bot.add_cog(DatabaseCog(bot))