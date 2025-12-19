# main.py
import discord
from discord.ext import commands
import asyncio
import os
import config
import random
from datetime import datetime

# 設定読み込み
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# commands.Bot を使用
bot = commands.Bot(command_prefix="!", intents=intents)

EXTENSIONS = [
    "cogs.system",
    "cogs.downloader",
    "cogs.role_manager",
    "cogs.database",
    "cogs.anonymous",
    "cogs.admin"
]

@bot.event
async def on_ready():
    # 1. コンソールログ
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    
    # 2. 不要なコマンドの同期解除
    bot.remove_command("say")
    bot.tree.remove_command("say")
    bot.tree.remove_command("bm")
    
    # 3. スラッシュコマンドを同期
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Successfully synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"⚠️ Failed to sync commands: {e}")

    # 4. 起動完了メッセージ（埋め込み型）の送信
    channel = bot.get_channel(config.STARTUP_CHANNEL_ID)
    if channel:
        # config.py からランダムな挨拶を選択
        greet_text = random.choice(config.STARTUP_MESSAGES)
        
        embed = discord.Embed(
            title="System Online",
            description=f"{greet_text}\n\n{config.UPDATE_NOTE}",
            color=0xffc0cb, # 宮本ちゃんカラー（ピンク系）
            timestamp=datetime.now()
        )
        
        # 左上にBotのアイコンを表示
        embed.set_author(
            name=f"{bot.user.name} v{config.BOT_VERSION}", 
            icon_url=bot.user.display_avatar.url
        )
        
        # フッターの設定
        embed.set_footer(text="宮本ちゃんメイドシステム 稼働中")
        
        await channel.send(embed=embed)
    
    print("------")
    print("宮本ちゃん、お仕事開始します！")

async def load_extensions():
    for ext in EXTENSIONS:
        try:
            if ext in bot.extensions:
                await bot.unload_extension(ext)
            await bot.load_extension(ext)
            print(f"✅ Loaded: {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

async def main():
    async with bot:
        # 先に拡張機能を読み込む
        # ここで各Cogの setup() が呼ばれ、bot.add_view が実行されます
        await load_extensions()
        
        # 匿名機能の永続ビューをここで再登録（setupでやっていない場合の保険）
        # 各Cog側のsetup内で適切に add_view されている場合はこれらは不要です
        try:
            from cogs.database import RegistrationView
            from cogs.anonymous import PostView, Anonymous
            bot.add_view(RegistrationView(bot))
            # 匿名投稿用の全パターン登録
            anon_cog = bot.get_cog("Anonymous")
            if anon_cog:
                bot.add_view(PostView(anon_cog, is_anon=True, is_image=False))
                bot.add_view(PostView(anon_cog, is_anon=False, is_image=False))
                bot.add_view(PostView(anon_cog, is_anon=True, is_image=True))
                bot.add_view(PostView(anon_cog, is_anon=False, is_image=True))
        except Exception as e:
            print(f"ℹ️ Persistent views info: {e}")

        await bot.start(config.TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("停止します")