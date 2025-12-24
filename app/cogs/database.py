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

# ▼▼▼【重要】ログチャンネルのID設定 ▼▼▼
# 再起動で設定が消える場合は、ここに直接ID（数字）を書いてください。
LOG_CHANNEL_ID = 0 

def load_config():
    if not os.path.exists(CONFIG_FILE): return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(config, f, indent=4, ensure_ascii=False)

async def send_log(bot, guild_id, config, message, user=None):
    target_id = LOG_CHANNEL_ID
    if not target_id:
        target_id = config.get(str(guild_id), {}).get("ログ")
        
    if target_id:
        channel = bot.get_channel(int(target_id))
        if channel:
            embed = discord.Embed(title="🛡️ 操作ログ", description=message, color=discord.Color.dark_gray())
            if user:
                embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
            embed.set_footer(text=f"発生時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            await channel.send(embed=embed)

# --- 作品登録モーダル ---
class WorkRegistrationModal(discord.ui.Modal, title='作品登録'):
    title_input = discord.ui.TextInput(label='タイトル', placeholder='作品名を入力...', required=True)
    author_input = discord.ui.TextInput(label='作者/制作', placeholder='作者名を入力...', required=False)
    
    def __init__(self, bot, config, media_type, sub_type, genre, tags, rating, target_channel):
        super().__init__()
        self.bot, self.config = bot, config
        self.media_type, self.sub_type, self.genre, self.tags, self.rating, self.target_channel = media_type, sub_type, genre, tags, rating, target_channel

    async def on_submit(self, interaction: discord.Interaction):
        # 荒らし対策: NGユーザーのチェックのみ行う
        guild_id = str(interaction.guild_id)
        guild_config = self.config.get(guild_id, {})
        blacklist = guild_config.get("NGユーザー", [])

        if interaction.user.id in blacklist:
            await send_log(self.bot, interaction.guild_id, self.config, f"🚫 **投稿拒否 (NGユーザー)**\n内容: {self.title_input.value}", user=interaction.user)
            return await interaction.response.send_message("⚠️ 投稿権限がありません（NG設定されています）。", ephemeral=True)
        
        # 投稿内容の作成
        author_text = self.author_input.value or '不明'
        tags_text = " ".join([f"`{t}`" for t in self.tags]) if self.tags else "タグなし"
        
        entry_text = (
            f"> 🔖 **{self.title_input.value}**\n"
            f"> └ 👤 **作者**: {author_text} ｜ ⭐ **評価**: {self.rating}\n"
            f"> └ 🏷️ **ジャンル**: {self.genre} ｜ 💭 **特徴**: {tags_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━" 
        )
        
        header_text = f"📂 **【 {self.sub_type} 】**"

        target_msg = None
        
        # 最新のボットメッセージを確認
        async for msg in self.target_channel.history(limit=20):
            if msg.author == self.bot.user and msg.embeds:
                embed = msg.embeds[0]
                desc = embed.description or ""
                
                # 「コレクション」というタイトルの埋め込みのみ対象
                if "コレクション" in (embed.title or ""):
                    # 10件埋まっているか、文字数限界なら新規作成へ
                    if desc.count("🔖") >= 10 or len(desc) > 3500:
                        target_msg = None 
                    else:
                        target_msg = msg
                    break

        if target_msg:
            # 追記処理
            embed = target_msg.embeds[0]
            desc = embed.description

            if header_text in desc:
                # 既存の種別ブロックの末尾に追加
                pattern = re.escape(header_text) + r"(.*?)(\n\n📂 \*\*【|$)"
                def replacer(match):
                    return f"{header_text}{match.group(1)}\n{entry_text}{match.group(2)}"
                new_desc = re.sub(pattern, replacer, desc, count=1, flags=re.DOTALL)
                embed.description = new_desc
            else:
                # 新しい種別として一番下に追加
                embed.description = desc.strip() + f"\n\n{header_text}\n{entry_text}"
            
            await target_msg.edit(embed=embed)
        else:
            # 新規メッセージ作成
            embed = discord.Embed(
                title=f"📚 {self.media_type} コレクション", 
                description=f"{header_text}\n{entry_text}", 
                color=discord.Color.from_rgb(44, 47, 51)
            )
            await self.target_channel.send(embed=embed)

        await send_log(self.bot, interaction.guild_id, self.config, f"✅ **作品登録**\nタイトル: {self.title_input.value}\nユーザー: {interaction.user.display_name}", user=interaction.user)
        await interaction.response.send_message(f"✅ 「{self.title_input.value}」をデータベースに追加しました！", ephemeral=True)

# --- 評価タグ選択View ---
class TagSelectView(discord.ui.View):
    def __init__(self, bot, config, media, sub_type, genre, target_channel):
        super().__init__(timeout=600)
        self.bot, self.config = bot, config
        self.media, self.sub_type, self.genre = media, sub_type, genre
        self.target_channel = target_channel
        self.tags = []

    @discord.ui.select(
        placeholder="4. 作品の魅力を選択 (複数可)", min_values=1, max_values=5, row=0,
        options=[
            # 視覚・演出
            discord.SelectOption(label="絵が綺麗", emoji="🎨"),
            discord.SelectOption(label="作画崩壊なし", emoji="✨"),
            discord.SelectOption(label="演出が神", emoji="🎬"),
            discord.SelectOption(label="キャラデザが良い", emoji="👗"),
            discord.SelectOption(label="世界観が美しい", emoji="🌏"),
            # ストーリー・構成
            discord.SelectOption(label="ストーリーが深い", emoji="📖"),
            discord.SelectOption(label="伏線回収がすごい", emoji="🧩"),
            discord.SelectOption(label="展開が熱い", emoji="🔥"),
            discord.SelectOption(label="テンポが良い", emoji="⏩"),
            discord.SelectOption(label="結末が衝撃的", emoji="⚡"),
            # 感情・体験
            discord.SelectOption(label="泣ける", emoji="😭"),
            discord.SelectOption(label="笑える", emoji="🤣"),
            discord.SelectOption(label="キュンとする", emoji="🫰"),
            discord.SelectOption(label="恐怖を感じる", emoji="😱"),
            discord.SelectOption(label="考えさせられる", emoji="🤔"),
            discord.SelectOption(label="癒される", emoji="🌿"),
            discord.SelectOption(label="鬱展開", emoji="💀"),
            discord.SelectOption(label="爽快感がある", emoji="💨"),
            # キャラクター
            discord.SelectOption(label="主人公が推せる", emoji="🦸"),
            discord.SelectOption(label="ヒロインが可愛い", emoji="💕"),
            discord.SelectOption(label="敵キャラが魅力的", emoji="😈"),
            discord.SelectOption(label="声優が豪華", emoji="🎙️"),
            # その他・おすすめ
            discord.SelectOption(label="初心者におすすめ", emoji="🔰"),
            discord.SelectOption(label="玄人向け", emoji="🕶️"),
            discord.SelectOption(label="隠れた名作", emoji="💎"),
        ]
    )
    async def tag_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.tags = select.values
        await interaction.response.edit_message(content=f"**{self.media} ＞ {self.sub_type} ＞ {self.genre}**\n選択タグ: {', '.join(self.tags)}\n最後に満足度を選んでください。")

    @discord.ui.select(
        placeholder="5. 総合満足度を選択", row=1,
        options=[
            discord.SelectOption(label="🏆 殿堂入り (文句なしの神作)", value="👑 殿堂入り"),
            discord.SelectOption(label="⭐⭐⭐⭐⭐ (超おすすめ)", value="⭐⭐⭐⭐⭐"),
            discord.SelectOption(label="⭐⭐⭐⭐ (面白い)", value="⭐⭐⭐⭐"),
            discord.SelectOption(label="⭐⭐⭐ (普通)", value="⭐⭐⭐"),
            discord.SelectOption(label="⭐⭐ (微妙)", value="⭐⭐"),
            discord.SelectOption(label="⭐ (時間の無駄)", value="⭐"),
            discord.SelectOption(label="🚫 閲覧注意", value="🚫 閲覧注意"),
        ]
    )
    async def rating_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.send_modal(WorkRegistrationModal(
            self.bot, self.config, self.media, self.sub_type, self.genre, self.tags, select.values[0], self.target_channel
        ))

# --- ジャンル選択View（25種類拡張版） ---
class GenreSelectView(discord.ui.View):
    def __init__(self, bot, config, media, target_channel):
        super().__init__(timeout=600)
        self.bot, self.config, self.media, self.target_channel = bot, config, media, target_channel
        self.sub_type = "未指定"

        self.type_map = {
            "小説": [
                ("長編小説", "📖"), ("短編小説", "📄"), ("ショートショート", "⚡"), ("連作短編", "🔗"), ("Web連載", "🌐"),
                ("ライトノベル", "🦄"), ("新文芸/なろう系", "🏰"), ("ライト文芸", "🍃"), ("一般文芸", "📘"), ("純文学", "🖋️"),
                ("児童文学", "🎈"), ("絵本", "🎨"), ("詩集/短歌/俳句", "🎋"), ("エッセイ/随筆", "✍️"), ("ノンフィクション", "🌍"),
                ("脚本/戯曲", "🎭"), ("TRPGリプレイ", "🎲"), ("ケータイ小説", "📱"), ("ゲームブック", "🗺️"), ("アンソロジー", "💐"),
                ("ノベライズ", "🎬"), ("評論/批評", "🗣️"), ("実用書/ビジネス", "📊"), ("同人誌", "🤝"), ("その他", "📁")
            ],
            "漫画": [
                ("長編連載", "📚"), ("短期連載", "📉"), ("読み切り", "🎯"), ("4コマ漫画", "🍀"), ("1ページ漫画", "🖼️"),
                ("Web漫画/縦読み", "📱"), ("少年漫画", "⚔️"), ("青年漫画", "🚬"), ("少女漫画", "🎀"), ("女性漫画", "💄"),
                ("BL漫画", "💎"), ("百合/GL漫画", "🌸"), ("コミックエッセイ", "🤣"), ("学習まんが", "🎓"), ("アメコミ/海外", "🦸"),
                ("同人誌(オリジナル)", "✨"), ("同人誌(二次創作)", "💞"), ("アンソロジー", "🍱"), ("完全版/愛蔵版", "📦"), ("スピンオフ", "🌪️"),
                ("コミカライズ", "🎞️"), ("画集/イラスト集", "🎨"), ("ファンブック", "📒"), ("成人向け", "🔞"), ("その他", "📁")
            ],
            "アニメ": [
                ("TVアニメ(30分)", "📺"), ("TVアニメ(ショート)", "⏲️"), ("劇場版アニメ", "🎬"), ("OVA", "📀"), ("Webアニメ", "💻"),
                ("パイロット版", "✈️"), ("MV/PV", "🎵"), ("自主制作アニメ", "🔨"), ("ストップモーション", "🧶"), ("3DCGアニメ", "🧊"),
                ("クレイアニメ", "🏺"), ("特撮ドラマ", "💥"), ("人形劇", "🧸"), ("キッズ/ファミリー", "👨‍👩‍👧"), ("深夜アニメ", "🌙"),
                ("海外アニメ", "🇺🇸"), ("2.5次元舞台", "💃"), ("声優イベント", "🎙️"), ("ドラマCD", "💿"), ("特典映像", "🎁"),
                ("再放送/リマスター", "✨"), ("予告/CM", "📢"), ("Vtuber関連", "🤖"), ("教育/知育", "📛"), ("その他", "📁")
            ],
            "映画": [
                ("実写邦画", "🗾"), ("実写洋画", "🇺🇸"), ("アニメ映画(邦画)", "🦁"), ("アニメ映画(洋画)", "🐼"), ("3DCG映画", "👓"),
                ("ドキュメンタリー", "📹"), ("短編映画", "⏳"), ("インディーズ", "🎸"), ("韓流/アジア映画", "🌏"), ("ヨーロッパ映画", "🏰"),
                ("インド/ボリウッド", "👳"), ("ミュージカル", "💃"), ("時代劇", "🏯"), ("特撮映画", "🦕"), ("モノクロ/無声", "📽️"),
                ("ライブビューイング", "🎫"), ("4DX/IMAX系", "🎢"), ("オムニバス", "🧩"), ("Vシネマ/OV", "📼"), ("テレビ映画/SP", "📺"),
                ("配信限定作品", "📶"), ("学生映画", "🎓"), ("舞台/演劇", "🎭"), ("成人映画", "🔞"), ("その他", "📁")
            ]
        }
        
        # 選択されたメディアに対応する選択肢を設定（安全のため25個でカット）
        options = [discord.SelectOption(label=n, emoji=e) for n, e in self.type_map.get(media, [("その他", "📁")])]
        self.sub_type_select.options = options[:25]

    @discord.ui.select(placeholder="1. 種別を選択", row=0)
    async def sub_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.sub_type = select.values[0]
        await interaction.response.edit_message(content=f"**{self.media} ＞ {self.sub_type}**\n次にジャンルを選択してください。")

    @discord.ui.select(
        placeholder="2. ジャンルを選択", row=1,
        options=[
            # ジャンル25種類
            discord.SelectOption(label="アクション/バトル", emoji="⚔️"),
            discord.SelectOption(label="冒険/ダンジョン", emoji="🗺️"),
            discord.SelectOption(label="ファンタジー", emoji="🧙"),
            discord.SelectOption(label="異世界/転生", emoji="🏰"),
            discord.SelectOption(label="SF/サイバーパンク", emoji="🚀"),
            
            discord.SelectOption(label="恋愛/ロマンス", emoji="💖"),
            discord.SelectOption(label="ラブコメ", emoji="💞"),
            discord.SelectOption(label="学園/青春", emoji="🏫"),
            discord.SelectOption(label="日常/ほのぼの", emoji="☕"),
            discord.SelectOption(label="ヒューマンドラマ", emoji="😢"),

            discord.SelectOption(label="ミステリー/推理", emoji="🔍"),
            discord.SelectOption(label="サスペンス/スリラー", emoji="🔪"),
            discord.SelectOption(label="ホラー/オカルト", emoji="👻"),
            discord.SelectOption(label="鬱/シリアス", emoji="🌧️"),

            discord.SelectOption(label="コメディ/ギャグ", emoji="🤣"),
            discord.SelectOption(label="スポーツ/競技", emoji="⚽"),
            discord.SelectOption(label="音楽/アイドル", emoji="🎤"),
            discord.SelectOption(label="グルメ/料理", emoji="🍳"),
            discord.SelectOption(label="動物/生き物", emoji="🐾"),

            discord.SelectOption(label="歴史/時代劇", emoji="🏯"),
            discord.SelectOption(label="戦争/ミリタリー", emoji="🪖"),
            discord.SelectOption(label="ビジネス/社会派", emoji="📊"),
            discord.SelectOption(label="百合/GL", emoji="🌸"),
            discord.SelectOption(label="BL", emoji="💎"),
            discord.SelectOption(label="R-18/成人向け", emoji="🔞"),
        ]
    )
    async def genre_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.edit_message(
            content=f"**{self.media} ＞ {self.sub_type} ＞ {select.values[0]}**\n作品の特徴（タグ）を選んでください。",
            view=TagSelectView(self.bot, self.config, self.media, self.sub_type, select.values[0], self.target_channel)
        )

# --- 媒体選択View ---
class RegistrationView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
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

    @app_commands.command(name="db_menu", description="登録メニューを表示します")
    async def db_menu(self, interaction: discord.Interaction):
        await interaction.response.send_message("📚 **作品登録パネル**", view=RegistrationView(self.bot))

    @app_commands.command(name="db_delete", description="作品をタイトル指定で削除します（管理者のみ）")
    @app_commands.checks.has_permissions(administrator=True)
    async def db_delete(self, interaction: discord.Interaction, channel: discord.TextChannel, title: str):
        # 削除は管理者のみ実行可能
        await interaction.response.defer(ephemeral=True)
        found = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                desc = msg.embeds[0].description
                if f"**{title}**" in desc:
                    # 1件分のブロックを削除する正規表現
                    pattern = r"> 🔖 \*\*" + re.escape(title) + r"\*\*.*?" + re.escape("━━━━━━━━━━━━━━━━━━━━━━") + r"\n?"
                    new_desc = re.sub(pattern, "", desc, flags=re.DOTALL)
                    
                    # 空になった見出し（カテゴリ）が残っていたら消す
                    new_desc = re.sub(r"(📂 \*\*【[^】]+】\*\*)\n+(?=\n📂|$)", "", new_desc, flags=re.DOTALL)
                    new_desc = new_desc.strip()

                    if not new_desc: 
                        await msg.delete()
                    else:
                        msg.embeds[0].description = new_desc
                        await msg.edit(embed=msg.embeds[0])
                    found = True
                    break
        
        if found:
            await send_log(self.bot, interaction.guild_id, load_config(), f"🗑️ **作品削除**\nタイトル: {title}", user=interaction.user)
            await interaction.followup.send("✅ 作品を削除しました。", ephemeral=True)
        else:
            await interaction.followup.send("❌ 指定されたタイトルの作品が見つかりませんでした。", ephemeral=True)

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

async def setup(bot):
    bot.add_view(RegistrationView(bot))
    await bot.add_cog(DatabaseCog(bot))
