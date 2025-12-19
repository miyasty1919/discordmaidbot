# cogs/downloader.py
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import os
import uuid
import time
import random
import asyncio
import traceback
from datetime import datetime
import config
import utils

class Downloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_last_download = {}
        # 同時実行制限（サーバー全体の負荷を抑える）
        self.download_semaphore = asyncio.Semaphore(2) 
        # 重複実行防止用のセット
        self.active_users = set()
        # 最初の1つだけを捕まえるURLパターン
        self.url_pattern = utils.re.compile(r'https?://(?:www\.)?(?:youtube\.com|youtu\.be|soundcloud\.com|bandcamp\.com|twitter\.com|x\.com|tiktok\.com|instagram\.com)[^\s]+')

    async def process_download(self, ctx_or_interaction, url, file_format, quality_kbps):
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        user = ctx_or_interaction.user if is_interaction else ctx_or_interaction.author
        user_id = user.id

        # 重複実行チェック（一人が同時に複数は不可）
        if user_id in self.active_users:
            msg = "今、あなたの分を準備中ですよ！終わるまで待ってくださいね💦"
            if is_interaction: await ctx_or_interaction.followup.send(msg, ephemeral=True)
            return

        # サーバー全体の同時実行数チェック
        if self.download_semaphore.locked():
            msg = "今、他の方のファイルを準備しています。少し待ってから送り直してください🙏"
            if is_interaction: await ctx_or_interaction.followup.send(msg, ephemeral=True)
            else: await ctx_or_interaction.channel.send(msg, delete_after=10)
            return

        async with self.download_semaphore:
            self.active_users.add(user_id)
            status_msg = None
            
            try:
                # 開始メッセージの送信
                start_msg = random.choice(config.DL_START_MESSAGES)
                if file_format == "mp4":
                    start_msg = "動画ですね！了解です。1つだけ取ってきます🏃‍♀️💨"
                
                if is_interaction:
                    status_msg = await ctx_or_interaction.followup.send(start_msg)
                else:
                    status_msg = await ctx_or_interaction.channel.send(start_msg)

                start_time = time.time()
                unique_id = str(uuid.uuid4())
                save_path_tmpl = os.path.join(config.DOWNLOAD_DIR, f"{unique_id}_%(title)s.%(ext)s")

                # 強力な単一ファイル制限オプション
                ydl_opts = {
                    'outtmpl': save_path_tmpl,
                    'writethumbnail': True,
                    'nocheckcertificate': True,
                    'quiet': True,
                    'max_filesize': config.MAX_FILE_SIZE,
                    'extractor_args': {'youtube': {'player_client': ['default']}},
                    # --- 複数ファイル・プレイリスト対策 ---
                    'noplaylist': True,            # プレイリスト全体を無視
                    'playlist_items': '1',         # 最初の1項目のみ指定
                    'ignoreerrors': False,         # 1つ失敗したら即終了（次を探さない）
                    'no_entries': False,
                    # ------------------------------------
                }

                if file_format == "mp4":
                    ydl_opts.update({
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        'merge_output_format': 'mp4',
                        'postprocessors': [{'key': 'EmbedThumbnail'}, {'key': 'FFmpegMetadata'}],
                    })
                else:
                    pp = [{'key': 'FFmpegExtractAudio', 'preferredcodec': file_format}, {'key': 'EmbedThumbnail'}, {'key': 'FFmpegMetadata'}]
                    if quality_kbps != "0": pp[0]['preferredquality'] = quality_kbps
                    ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': pp})

                loop = asyncio.get_event_loop()
                def run_dl():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # 情報を抽出（download=Trueで実処理）
                        info = ydl.extract_info(url, download=True)
                        
                        # プレイリスト形式でデータが返ってきた場合でも最初の1つだけを参照
                        if 'entries' in info:
                            target_data = info['entries'][0]
                        else:
                            target_data = info

                        raw_fname = ydl.prepare_filename(target_data)
                        base, _ = os.path.splitext(raw_fname)
                        final_path = f"{base}.{file_format}"
                        
                        # メタデータ処理
                        raw_title = target_data.get('title', 'Unknown')
                        clean_title = utils.sanitize_filename(raw_title)
                        display_name = f"{clean_title}.{file_format}"
                        
                        meta = {"title": raw_title, "artist": target_data.get('uploader'), "album": raw_title}
                        if os.path.exists(final_path):
                            utils.save_metadata_to_file(final_path, meta)
                        
                        return final_path, display_name

                file_path, display_filename = await loop.run_in_executor(None, run_dl)
                elapsed = time.time() - start_time

                # ファイル送信と後片付け
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    if size > config.MAX_FILE_SIZE:
                        err = f"サイズオーバーです！😭 ({(size/1024/1024):.1f}MB)"
                        if is_interaction: await ctx_or_interaction.followup.send(err)
                        else: await status_msg.edit(content=err)
                        os.remove(file_path)
                    else:
                        if not is_interaction and status_msg: await status_msg.delete()
                        res = f"はい、どうぞ！🎁✨\n⏱️ `{elapsed:.1f}s` / `{(size/1024/1024):.1f}MB`"
                        await ctx_or_interaction.channel.send(res, file=discord.File(file_path, filename=display_filename), view=utils.PraiseView())
                        os.remove(file_path)
                else:
                    raise Exception("File not found after download.")

            except Exception as e:
                traceback.print_exc()
                err = "ダウンロード中にエラーが起きちゃいました…💦 1動画ずつ、正しいURLで試してみてくださいね。"
                if is_interaction: await ctx_or_interaction.followup.send(err)
                elif status_msg: await status_msg.edit(content=err)
            finally:
                # ユーザーをアクティブリストから削除（次のリクエストを許可）
                self.active_users.remove(user_id)

    @app_commands.command(name="dl", description="1つの動画/音楽をダウンロードします")
    async def slash_dl(self, interaction: discord.Interaction, url: str, format: str = "mp3", quality: str = "0"):
        if interaction.channel_id != config.ALLOWED_DL_CHANNEL_ID:
            await interaction.response.send_message(f"<#{config.ALLOWED_DL_CHANNEL_ID}> で使ってくださいね🥺", ephemeral=True)
            return

        # クールダウンチェック
        user_id = interaction.user.id
        now = datetime.now()
        if user_id in self.user_last_download:
            diff = (now - self.user_last_download[user_id]).total_seconds()
            if diff < config.COOLDOWN_SECONDS:
                await interaction.response.send_message(f"連投禁止です！あと {int(config.COOLDOWN_SECONDS - diff)}秒 待ってください🙏", ephemeral=True)
                return

        self.user_last_download[user_id] = now
        await interaction.response.defer()
        await self.process_download(interaction, url, format, quality)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        match = self.url_pattern.search(message.content)
        if match:
            if message.channel.id != config.ALLOWED_DL_CHANNEL_ID: return
            
            user_id = message.author.id
            now = datetime.now()
            if user_id in self.user_last_download:
                if (now - self.user_last_download[user_id]).total_seconds() < config.COOLDOWN_SECONDS:
                    return # 静かにスルー
            
            self.user_last_download[user_id] = now
            # 見つかった最初のURLのみを渡す
            await self.process_download(message, match.group(0), "mp3", "0")

async def setup(bot):
    await bot.add_cog(Downloader(bot))