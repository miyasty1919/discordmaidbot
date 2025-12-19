# main.py
import discord
from discord.ext import commands
import asyncio
import os
import config
import random
from datetime import datetime

# --- 追加: ヘルスチェック用サーバーのためのインポート ---
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- 追加: ヘルスチェック用サーバーの設定 ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    """Koyebからの生存確認(GETリクエスト)に応答するクラス"""
    def do_GET(self):
        self.send_response(200) # 正常を意味する 200 を返す
        self.end_headers()
        self.wfile.write(b"Miyamoto-chan is online!")

def run_health_server():
    """別スレッドで実行するためのサーバー起動関数"""
    # ポート番号は Dockerfile の EXPOSE で指定した 8000 に合わせます
    server = HTTPServer(('0.0.0.0', 8000), HealthCheckHandler)
    print("[System] Health check server started on port 8000")
    server.serve_forever()

# --- 既存の設定読み込み ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

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
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    
    bot.remove_command("say")
    bot.tree.remove_command("say")
    bot.tree.remove_command("bm")
    
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Successfully synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"⚠️ Failed to sync commands: {e}")

    channel = bot.get_channel(config.STARTUP_CHANNEL_ID)
    if channel:
        greet_text = random.choice(config.STARTUP_MESSAGES)
        embed = discord.Embed(
            title="System Online",
            description=f"{greet_text}\n\n{config.UPDATE_NOTE}",
            color=0xffc0cb,
            timestamp=datetime.now()
        )
        embed.set_author(
            name=f"{bot.user.name} v{config.BOT_VERSION}", 
            icon_url=bot.user.display_avatar.url
        )
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
    # ★ 追加: Bot起動前にヘルスチェックサーバーを別スレッドで開始
    # これにより、Botが接続中であってもKoyebへの応答が可能になります
    threading.Thread(target=run_health_server, daemon=True).start()

    async with bot:
        await load_extensions()
        
        try:
            from cogs.database import RegistrationView
            from cogs.anonymous import PostView, Anonymous
            bot.add_view(RegistrationView(bot))
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
