# cogs/bookmark.py
import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
import config
import utils

class BookmarkGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="bm", description="【担当：なお】ブックマークを管理してあげるわよ")

    @app_commands.command(name="add", description="URLやメモを登録します")
    async def bookmark_add(self, interaction: discord.Interaction, url: str = None, title: str = None):
        if not url and not title:
            await interaction.response.send_message("はぁ？ URLもタイトルもないのに何を保存するのよ！😠", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=False)

        fetched = False
        if url and not title:
            found = await utils.fetch_url_title(url)
            if found:
                title = found
                fetched = True
            else:
                title = "（タイトルなし）"
        if not title and url: title = url

        data = utils.load_json(config.BOOKMARK_FILE)
        uid = str(interaction.user.id)
        if uid not in data: data[uid] = []

        if url and any(bm.get('url') == url for bm in data[uid]):
            await interaction.followup.send("そのURLはもう保存してるじゃない！😠")
            return

        data[uid].append({"title": title, "url": url, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
        utils.save_json(config.BOOKMARK_FILE, data)

        msg = random.choice(config.NAO_ADD_MESSAGES)
        if fetched: msg += "\n(わざわざタイトルまで調べてあげたんだからね！)"
        
        embed = discord.Embed(title="📕 ブックマーク追加", color=discord.Color.magenta())
        embed.set_author(name=f"{interaction.user.display_name} のコレクション", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="タイトル", value=title)
        if url: embed.add_field(name="URL", value=url)
        embed.set_footer(text="担当: メイドなお")
        await interaction.followup.send(content=msg, embed=embed)

    @app_commands.command(name="list", description="一覧を表示")
    async def bookmark_list(self, interaction: discord.Interaction):
        data = utils.load_json(config.BOOKMARK_FILE)
        bookmarks = data.get(str(interaction.user.id), [])
        if not bookmarks:
            await interaction.response.send_message("まだ何も保存してないじゃない。……私の出番、ないわけ？😠", ephemeral=False)
            return

        msg = random.choice(config.NAO_LIST_MESSAGES)
        embed = discord.Embed(title=f"📚 {interaction.user.display_name} のブックマーク", color=discord.Color.magenta())
        text = ""
        for i, bm in enumerate(bookmarks):
            line = f"**[{i+1}] [{bm['title']}]({bm.get('url')})**" if bm.get('url') else f"**[{i+1}] {bm['title']}**"
            if len(text) + len(line) > 3500:
                text += "\n...(省略)"
                break
            text += line + "\n"
        embed.description = text
        await interaction.response.send_message(content=msg, embed=embed)

    @app_commands.command(name="delete", description="削除")
    async def bookmark_delete(self, interaction: discord.Interaction, index: int):
        data = utils.load_json(config.BOOKMARK_FILE)
        uid = str(interaction.user.id)
        bookmarks = data.get(uid, [])
        
        if 0 <= index-1 < len(bookmarks):
            removed = bookmarks.pop(index-1)
            utils.save_json(config.BOOKMARK_FILE, data)
            msg = random.choice(config.NAO_DELETE_MESSAGES)
            await interaction.response.send_message(f"{msg}\n(削除: **{removed['title']}**)", ephemeral=False)
        else:
            await interaction.response.send_message(f"その番号 ({index}) はないわよ！😠", ephemeral=False)

class BookmarkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.add_command(BookmarkGroup())

async def setup(bot):
    await bot.add_cog(BookmarkCog(bot))