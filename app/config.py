# config.py

# Bot設定
BOT_VERSION = "2.1.0 (Modular)"
TOKEN = "MTQ0NzgzODY3MTAwNzkwNzg2MQ.GI4rnD.S1u0BtUQ-SE_w-Sj8L3hLdltq1_BSa-4fGj6KU"

# チャンネルID
STARTUP_CHANNEL_ID = 1447846598574084218    # 起動ログ
WELCOME_CHANNEL_ID = 1447032050577182763    # 歓迎通知
ALLOWED_DL_CHANNEL_ID = 1447846598574084218 # DL許可

# ファイルパス
DOWNLOAD_DIR = "temp_downloads"
VERSION_FILE = "version_history.txt"
BOOKMARK_FILE = "bookmarks.json"
ROLE_KEEP_FILE = "role_keep.json"

# 設定値
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB
COOLDOWN_SECONDS = 30

# メッセージ集
STARTUP_MESSAGES = [
    "ご主人様！宮本ちゃん、準備万端ですっ！🎀 (System Online)",
    "お掃除完了！いつでも命令してくださいねっ！✨ (System Online)",
    "本日の業務を開始します！張り切っていきましょー！💪 (System Online)",
]

DL_START_MESSAGES = [
    "あっ！URLですねっ！👀✨ 宮本が走って取ってきますー！🏃‍♀️💨",
    "かしこまりました！光の速さで取ってきますねっ！⚡️",
    "お任せください！落とさないように慎重に、でも急いで運びますっ！📦💦",
]

PRAISE_MESSAGES = [
    "えへへ…っ/// ご主人様に褒められちゃった…！✨",
    "わぁい！ご主人様だーいすきっ！❤️ もっともっと頑張っちゃいますね！",
    "ご主人様のためなら、これくらいお安い御用ですっ！エッヘン！😤✨"
]

COMFORT_MESSAGES = [
    "うぅ…ご主人様ぁ…優しいですね…😢💕 慰めてもらえて元気出ましたっ！",
    "あうぅ…ドジっ子メイドですみません…💦 でも、よしよししてくれてありがとうございます…///",
]

NAO_ADD_MESSAGES = [
    "べ、別にあんたのために覚えたわけじゃないんだからね！勘違いしないでよね！😤",
    "はいはい、書いておけばいいんでしょ？ ……ほら、ちゃんと保存したわよ。感謝しなさい！📕",
    "もう…すぐ忘れちゃうんだから。私が管理してあげるから、ありがたく思いなさいよね！"
]

NAO_LIST_MESSAGES = [
    "ちょっと！あんたが保存しろって言ったリストでしょ？ ほら、見せてあげるわよ！📱",
    "これが『あんたの』ブックマークよ。……ふん、趣味がわかるわね。",
    "ほら、リストよ！ みんなに見られても知らないからね！"
]

NAO_DELETE_MESSAGES = [
    "ふん、やっと要らないって気づいたの？ 消しておいたわよ！🗑️",
    "はいはい、削除ね。……少しはスッキリしたんじゃない？",
    "消したわよ。もう間違えて追加しないでよね！バカご主人！"
]

UPDATE_NOTE = (
    "🔔 **システム再構築のお知らせ**\n"
    "・Botの中身を整理整頓（リファクタリング）しました！\n"
    "・機能ごとにファイルを分けたので、メンテナンスもバッチリですっ！✨"
)