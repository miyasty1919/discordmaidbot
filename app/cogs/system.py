# cogs/system.py
import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import config

class System(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not os.path.exists(config.DOWNLOAD_DIR):
            os.makedirs(config.DOWNLOAD_DIR)
        print(f'{self.bot.user} システム準備完了。')

        channel = self.bot.get_channel(config.STARTUP_CHANNEL_ID)
        if not channel: return

        last_version = ""
        if os.path.exists(config.VERSION_FILE):
            with open(config.VERSION_FILE, "r", encoding="utf-8") as f:
                last_version = f.read().strip()

        if last_version != config.BOT_VERSION:
            try:
                msg = f"🎉 **アップデート完了 (ver {config.BOT_VERSION})** 🎉\n{config.UPDATE_NOTE}"
                await channel.send(msg)
                with open(config.VERSION_FILE, "w", encoding="utf-8") as f:
                    f.write(config.BOT_VERSION)
            except Exception as e:
                print(f"通知エラー: {e}")
        else:
            await channel.send(random.choice(config.STARTUP_MESSAGES))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.bot.get_channel(config.WELCOME_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🔔 ご主人様のご帰宅です！",
                description=f"お帰りなさいませ、ご主人様！🎀\n今日も一日お疲れ様でした！",
                color=discord.Color.pink()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="お名前", value=f"{member.mention}", inline=True)
            embed.add_field(name="会員番号 (ID)", value=f"`{member.id}`", inline=True)
            embed.set_footer(text="ゆっくりしていってくださいね！☕")
            await channel.send(content=f"{member.mention} 様、いらっしゃいませ！", embed=embed)

    @app_commands.command(name="read", description="このBotの使い方を教えます")
    async def slash_read(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 メイドBot 取扱説明書",
            description="ご主人様、こちらができることの一覧です！✨",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📥 ダウンロード機能 (`/dl`)",
            value=f"YouTube等のURLから保存します！\n※ <#{config.ALLOWED_DL_CHANNEL_ID}> 限定",
            inline=False
        )
        embed.add_field(
            name="📚 作品データベース (`/db_menu`)",
            value="皆さんの視聴・閲覧した作品を記録できます！ボタンで媒体を選んで入力してください。",
            inline=False
        )
        embed.set_footer(text="困ったときは宮本にお任せください！🎀")
        await interaction.response.send_message(embed=embed)

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_command(self, ctx):
        await ctx.send("コマンドを整理してます…🔄")
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"{len(synced)}個のコマンドを同期しました！✨")
        except Exception as e:
            await ctx.send(f"エラー発生: `{e}`")

async def setup(bot):
    await bot.add_cog(System(bot))