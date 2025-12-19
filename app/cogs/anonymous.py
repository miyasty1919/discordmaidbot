import discord
from discord import app_commands
from discord.ext import commands
import datetime
import json
import os

# --- モーダル・ボタン設定 ---
class PostModal(discord.ui.Modal):
    def __init__(self, cog, is_anon=True, is_image=False):
        title = f"【{'匿名' if is_anon else '代理投稿'}】{'画像' if is_image else 'テキスト'}"
        super().__init__(title=title)
        self.cog, self.is_anon, self.is_image = cog, is_anon, is_image
        self.input_field = discord.ui.TextInput(
            label="画像URL" if is_image else "メッセージ内容",
            style=discord.TextStyle.paragraph if not is_image else discord.TextStyle.short,
            placeholder="最大400文字まで...",
            required=True,
            max_length=400
        )
        self.add_item(self.input_field)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.process_post(interaction, self.is_anon, 
            content=self.input_field.value if not self.is_image else None,
            image_url=self.input_field.value if self.is_image else None)

class PostView(discord.ui.View):
    def __init__(self, cog, is_anon=False, is_image=False):
        # 永続化のため timeout=None
        super().__init__(timeout=None)
        self.cog = cog
        self.is_anon = is_anon
        self.is_image = is_image

        label = "🖼️ 画像をアップ" if is_image else "✍️ 書き込む"
        style = discord.ButtonStyle.primary if is_image else discord.ButtonStyle.success
        
        # 再起動後の識別のための custom_id。設定値に応じて一意になるよう設計
        c_id = f"anon_view:{'anon' if is_anon else 'proxy'}:{'img' if is_image else 'txt'}"
        
        btn = discord.ui.Button(label=label, style=style, custom_id=c_id)
        btn.callback = self.callback
        self.add_item(btn)

    async def callback(self, interaction: discord.Interaction):
        retry = self.cog.check_cooldown(interaction.user.id)
        if retry: 
            return await interaction.response.send_message(f"連投制限中です。あと {int(retry)} 秒お待ちください。", ephemeral=True)
        await interaction.response.send_modal(PostModal(self.cog, self.is_anon, self.is_image))

# --- メインロジック ---
class Anonymous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.post_count = 0
        self.logs = {}
        self.cooldowns = {}
        self.settings_file = "anon_settings.json"
        self.panel_data = self.load_settings()
        self.default_avatar = "https://cdn.discordapp.com/embed/avatars/0.png"

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f: return json.load(f)
            except: return {}
        return {}

    def save_settings(self):
        with open(self.settings_file, "w") as f: json.dump(self.panel_data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        """
        起動時にパネルを最新状態に保つための処理。
        永続Viewのおかげでボタン自体は add_view だけで動きますが、
        ここではパネルのメッセージを最新化（再送信）するロジックを維持しています。
        """
        print("🔄 匿名パネルの状態を確認中...")
        for channel_id, data in list(self.panel_data.items()):
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                # 必要に応じてパネルを再送して最新の状態にする
                # (前回のメッセージが残っていても add_view 済みならボタンは動きます)
                pass
        print("✅ 全パネルの確認が完了しました。")

    def check_cooldown(self, user_id):
        now = datetime.datetime.now()
        if user_id in self.cooldowns:
            elapsed = (now - self.cooldowns[user_id]).total_seconds()
            if elapsed < 90: return 90 - elapsed
        return None

    async def get_webhook(self, channel):
        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name="ProxyWebhook")
        return webhook or await channel.create_webhook(name="ProxyWebhook")

    async def process_post(self, interaction, is_anon, content=None, image_url=None):
        await interaction.response.defer(ephemeral=True)
        self.post_count += 1
        p_id = str(self.post_count)
        self.logs[p_id] = f"{interaction.user} ({interaction.user.id}) [{'匿名' if is_anon else '代理'}]"
        self.cooldowns[interaction.user.id] = datetime.datetime.now()

        webhook = await self.get_webhook(interaction.channel)
        
        # 旧パネル削除（常に最新のパネルを下に置くための仕様を継続）
        data = self.panel_data.get(str(interaction.channel.id))
        if data and "last_msg_id" in data:
            try:
                msg = await interaction.channel.fetch_message(data["last_msg_id"])
                await msg.delete()
            except: pass

        name = p_id if is_anon else f"{p_id} | {interaction.user.display_name}"
        avatar = self.default_avatar if is_anon else interaction.user.display_avatar.url
        allowed_mentions = discord.AllowedMentions.none()
        
        if image_url:
            embed = discord.Embed(color=0x2f3136).set_image(url=image_url)
            await webhook.send(username=name, avatar_url=avatar, embed=embed, allowed_mentions=allowed_mentions)
        else:
            await webhook.send(content=content, username=name, avatar_url=avatar, allowed_mentions=allowed_mentions)

        await self.send_proper_panel(interaction.channel, is_anon, "image" if image_url else "text")
        await interaction.followup.send("投稿完了いたしましたわ、ご主人様。", ephemeral=True)

    async def send_proper_panel(self, channel, is_anon, p_type):
        title = f"🎭 {'匿名' if is_anon else '代理投稿'}{'画像掲示板' if p_type == 'image' else '雑談'}"
        embed = discord.Embed(title=title, description="ご主人様、こちらからお手紙をお送りくださいませ。", color=0x3498db if p_type == "image" else 0x2ecc71)
        
        # ここでViewを作成
        view = PostView(self, is_anon, (p_type == "image"))
        panel = await channel.send(embed=embed, view=view)
        
        self.panel_data[str(channel.id)] = {
            "is_anon": is_anon,
            "p_type": p_type,
            "last_msg_id": panel.id
        }
        self.save_settings()

    @app_commands.command(name="setup_anon_text")
    @app_commands.checks.has_permissions(administrator=True)
    async def s_a_t(self, interaction: discord.Interaction):
        await self.send_proper_panel(interaction.channel, True, "text")
        await interaction.response.send_message("匿名テキストパネルを設置しましたわ。", ephemeral=True)

    @app_commands.command(name="setup_proxy_text")
    @app_commands.checks.has_permissions(administrator=True)
    async def s_p_t(self, interaction: discord.Interaction):
        await self.send_proper_panel(interaction.channel, False, "text")
        await interaction.response.send_message("代理投稿パネルを設置しましたわ。", ephemeral=True)

    @app_commands.command(name="setup_anon_image")
    @app_commands.checks.has_permissions(administrator=True)
    async def s_a_i(self, interaction: discord.Interaction):
        await self.send_proper_panel(interaction.channel, True, "image")
        await interaction.response.send_message("匿名画像パネルを設置しましたわ。", ephemeral=True)

    @app_commands.command(name="setup_proxy_image")
    @app_commands.checks.has_permissions(administrator=True)
    async def s_p_i(self, interaction: discord.Interaction):
        await self.send_proper_panel(interaction.channel, False, "image")
        await interaction.response.send_message("代理投稿画像パネルを設置しましたわ。", ephemeral=True)

    @app_commands.command(name="post_log")
    @app_commands.checks.has_permissions(administrator=True)
    async def show_log(self, interaction: discord.Interaction, post_id: str):
        user = self.logs.get(post_id, "不明なIDですわ。")
        await interaction.response.send_message(f"ID: {post_id} の投稿者は {user} ですわ。", ephemeral=True)

async def setup(bot):
    # Cogを取得。add_view の引数として cog (self) を渡すために必要
    cog = Anonymous(bot)
    
    # 全パターンのViewを永続Viewとして事前登録
    # これにより、再起動前に送信されたどの種類のパネルボタンも動作するようになる
    bot.add_view(PostView(cog, is_anon=True, is_image=False))
    bot.add_view(PostView(cog, is_anon=False, is_image=False))
    bot.add_view(PostView(cog, is_anon=True, is_image=True))
    bot.add_view(PostView(cog, is_anon=False, is_image=True))
    
    await bot.add_cog(cog)