# cogs/role_manager.py
import discord
from discord.ext import commands
from discord import app_commands
import config
import utils

class RoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- イベント: 入室時のロール復元 ---
    @commands.Cog.listener()
    async def on_member_join(self, member):
        data = utils.load_json(config.ROLE_KEEP_FILE)
        uid = str(member.id)
        if uid in data:
            roles = []
            for rid in data[uid]:
                role = member.guild.get_role(rid)
                if role and member.guild.me.top_role > role and not role.managed:
                    roles.append(role)
            if roles:
                try:
                    await member.add_roles(*roles)
                    print(f"[Role Keep] Restored for {member.name}")
                except Exception as e:
                    print(f"[Role Keep Error] {e}")

    # --- イベント: 退室時のロール保存 ---
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        roles = [r.id for r in member.roles if not r.is_default() and not r.managed]
        if roles:
            data = utils.load_json(config.ROLE_KEEP_FILE)
            data[str(member.id)] = roles
            utils.save_json(config.ROLE_KEEP_FILE, data)
            print(f"[Role Keep] Saved for {member.name}")

    # --- コマンド: ロールパネル設置 (最大4つ) ---
    @app_commands.command(name="role_panel", description="【管理者】最大4つまでロールボタンを設置します")
    @app_commands.describe(
        title="パネルのタイトル",
        color="ボタンの色 (blue/green/red/grey)",
        role1="1つ目のロール", label1="1つ目のボタン名",
        role2="2つ目のロール", label2="2つ目のボタン名",
        role3="3つ目のロール", label3="3つ目のボタン名",
        role4="4つ目のロール", label4="4つ目のボタン名"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def role_panel(
        self, interaction: discord.Interaction, 
        title: str = "✨ ロール配布パネル",
        color: str = "green",
        role1: discord.Role = None, label1: str = None,
        role2: discord.Role = None, label2: str = None,
        role3: discord.Role = None, label3: str = None,
        role4: discord.Role = None, label4: str = None
    ):
        await interaction.response.defer(ephemeral=True)

        # 少なくとも1つはロールが必要
        if not role1 and not role2 and not role3 and not role4:
            await interaction.followup.send("ロールを少なくとも1つ選んでください💦")
            return

        try:
            # ボタンのスタイル決定
            if color == "blue": style = discord.ButtonStyle.primary
            elif color == "red": style = discord.ButtonStyle.danger
            elif color == "grey" or color == "gray": style = discord.ButtonStyle.secondary
            else: style = discord.ButtonStyle.success # green

            view = discord.ui.View(timeout=None)
            
            # 入力されたロールとラベルをリストにまとめる
            entries = [
                (role1, label1),
                (role2, label2),
                (role3, label3),
                (role4, label4)
            ]

            description_text = "以下のボタンを押すと、ロールを付けたり外したりできます！\n\n"

            # ループでボタンを作成
            for role, label in entries:
                if role is not None:
                    if not label: label = role.name
                    # ボタン追加
                    custom_id = f"role_assign:{role.id}"
                    button = discord.ui.Button(label=label, style=style, custom_id=custom_id)
                    view.add_item(button)
                    # 説明文追加
                    description_text += f"🔘 **{label}** : {role.mention}\n"

            embed = discord.Embed(
                title=title,
                description=description_text,
                color=discord.Color.gold()
            )
            
            await interaction.channel.send(embed=embed, view=view)
            await interaction.followup.send("パネルを設置しました！✨")

        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました💦\n`{e}`")

    # --- イベント: ボタンが押された時の処理 ---
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            cid = interaction.data.get("custom_id", "")
            if cid.startswith("role_assign:"):
                try:
                    rid = int(cid.split(":")[1])
                    role = interaction.guild.get_role(rid)
                    
                    if not role:
                        await interaction.response.send_message("そのロールはもう存在しないみたいです💦", ephemeral=True)
                        return
                    
                    # ロールの付与・剥奪トグル処理
                    if role in interaction.user.roles:
                        await interaction.user.remove_roles(role)
                        await interaction.response.send_message(f"🗑️ **{role.name}** を外しました！", ephemeral=True)
                    else:
                        await interaction.user.add_roles(role)
                        await interaction.response.send_message(f"✅ **{role.name}** を付けました！", ephemeral=True)
                
                except discord.Forbidden:
                    await interaction.response.send_message("権限不足です…😢 Botのロールを、配りたいロールより上に置いてください！", ephemeral=True)
                except Exception as e:
                    print(f"Role Error: {e}")
                    if not interaction.response.is_done():
                        await interaction.response.send_message("エラーが発生しちゃいました…💦", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RoleManager(bot))