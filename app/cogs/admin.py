import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- 既存の post コマンド ---
    @app_commands.command(
        name="post", 
        description="【管理者限定】改行を含めたメッセージを投稿します"
    )
    @app_commands.describe(
        content="内容を入力してください（Shift+Enterで改行、または \\n と入力）", 
        title="メッセージの見出し（任意）"
    )
    @app_commands.default_permissions(administrator=True)
    async def post(self, interaction: discord.Interaction, content: str, title: str = None):
        await interaction.response.defer(ephemeral=True)
        formatted_content = content.replace("\\n", "\n")
        try:
            embed = discord.Embed(description=formatted_content, color=discord.Color.blue())
            if title: embed.title = title
            await interaction.channel.send(embed=embed)
            await interaction.followup.send("✅ メッセージを投稿いたしましたわ。")
        except Exception as e:
            await interaction.followup.send(f"❌ エラーが発生しました: {e}")

    # --- 新規追加コマンド ---

    @app_commands.command(name="purge", description="【管理者限定】指定した数のメッセージを一括削除します")
    @app_commands.describe(amount="削除するメッセージ数（1-100）")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        """メッセージをまとめて削除するコマンド"""
        await interaction.response.defer(ephemeral=True)
        if amount < 1 or amount > 100:
            return await interaction.followup.send("❌ 1から100の間で指定してください。")
        
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 {len(deleted)}件のメッセージを掃除いたしましたわ。")

    @app_commands.command(name="kick", description="【管理者限定】メンバーをサーバーから追放します")
    @app_commands.describe(member="対象のメンバー", reason="追放の理由")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "理由なし"):
        """メンバーをキックするコマンド"""
        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(f"✅ {member.mention} を追放いたしましたわ。理由: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"❌ 実行できませんでした: {e}", ephemeral=True)

    @app_commands.command(name="ban", description="【管理者限定】メンバーをBAN（出禁）にします")
    @app_commands.describe(member="対象のメンバー", reason="BANの理由")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "理由なし"):
        """メンバーをBANするコマンド"""
        try:
            await member.ban(reason=reason)
            await interaction.response.send_message(f"🔨 {member.mention} をBANいたしましたわ。二度と来ないでくださいませ。理由: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"❌ 実行できませんでした: {e}", ephemeral=True)

    @app_commands.command(name="server_info", description="【管理者限定】サーバーの詳細情報を表示します")
    @app_commands.default_permissions(administrator=True)
    async def server_info(self, interaction: discord.Interaction):
        """サーバーの統計情報を表示するコマンド"""
        guild = interaction.guild
        embed = discord.Embed(title=f"🏰 {guild.name} 統計情報", color=discord.Color.gold())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="オーナー", value=guild.owner.mention)
        embed.add_field(name="メンバー数", value=f"{guild.member_count}名")
        embed.add_field(name="作成日", value=guild.created_at.strftime("%Y/%m/%d"))
        embed.add_field(name="チャンネル数", value=f"テキスト: {len(guild.text_channels)}\nボイス: {len(guild.voice_channels)}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slowmode", description="【管理者限定】チャンネルの低速モードを設定します")
    @app_commands.describe(seconds="秒数（0で解除）")
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        """低速モードを設定するコマンド"""
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            status = f"{seconds}秒に設定しました" if seconds > 0 else "解除しました"
            await interaction.response.send_message(f"⏲️ 低速モードを{status}わ。")
        except Exception as e:
            await interaction.response.send_message(f"❌ 変更できませんでした: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))