# The MIT License (MIT)
# Copyright (c) 2020 OctoNezd
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

import logging
from io import BytesIO

from PIL import Image
from telegram.error import BadRequest, TimedOut
import octobot

PLUGINVERSION = 2
maxwidth, maxheight = 512, 512
# Always name this variable as `plugin`
# If you dont, module loader will fail to load the plugin!
inf = octobot.PluginInfo(name=octobot.localizable("Stickers"),
                         reply_kwargs={"editable": False}
                         )
LOGGER = inf.logger

class NoImageProvided(ValueError): pass


def resize_sticker(image: Image):
    resz_rt = min(maxwidth / image.width, maxheight / image.height)
    sticker_size = [int(image.width * resz_rt), int(image.height * resz_rt)]
    if sticker_size[0] > sticker_size[1]:
        sticker_size[0] = 512
    else:
        sticker_size[1] = 512
    image = image.resize(sticker_size, Image.ANTIALIAS)
    io_out = BytesIO()
    quality = 100
    image.convert("RGBA").save(io_out, "PNG", quality=quality)
    io_out = BytesIO()
    image.save(io_out, "PNG", optimize=True)
    io_out.seek(0)
    return io_out


def create_pack_name(bot, ctx, personal):
    extra = ''
    if octobot.Database.redis is not None:
        db = ctx.user_db if personal else ctx.chat_db
        if 'packidx' in db:
            extra = db['packidx']
            LOGGER.debug('packidx: %s', extra)
    if personal:
        uid = ctx.update.message.from_user.id
        packtype = "user"
    else:
        uid = str(ctx.update.message.chat_id)[1:]
        packtype = "group"
    name = f"{packtype}_{uid}{extra}_by_{bot.getMe().username}"
    return name


def get_chat_creator(chat):
    for admin in chat.get_administrators():
        if admin.status == 'creator':
            return admin.user.id


def get_file_id_from_message(message):
    if message.photo:
        LOGGER.debug(message.photo)
        fl = message.photo[-1]
    elif message.document:
        fl = message.document
    elif message.sticker:
        fl = message.sticker
    elif message.reply_to_message:
        fl = get_file_id_from_message(message.reply_to_message)
    else:
        raise NoImageProvided()
    return fl


def get_file_from_message(bot, update):
    io = BytesIO()
    file_id = get_file_id_from_message(update.message).file_id
    fl = bot.getFile(file_id)
    fl.download(out=io)
    io.seek(0)
    return Image.open(io)


@octobot.CommandHandler(command="sticker_optimize",
                        description="Optimizes image/file for telegram sticker",
                        inline_support=False)
def sticker_optimize(bot, ctx):
    try:
        image = get_file_from_message(bot, ctx.update)
    except NoImageProvided:
        return ctx.reply(ctx.localize("No image as photo/file provided."), failed=True)
    except Image.DecompressionBombError:
        return ctx.reply(ctx.localize("Attempting to make image bombs, are we?"), failed=True)
    except OSError:
        return ctx.reply(ctx.localize("This file doesn't look like image file"), failed=True)
    sticker = resize_sticker(image)
    doc = ctx.update.message.reply_document(caption=ctx.localize("Preview:"), document=sticker)
    sticker.seek(0)
    doc.reply_sticker(sticker)


def sticker_add(bot, ctx, personal):
    print("aaaa")
    args = ctx.args
    pack_name = create_pack_name(bot, ctx, personal=personal)
    if personal:
        display_name = f"{ctx.user.first_name[:32]} by @{bot.getMe().username}"
        creator_id = ctx.user.id
    else:
        display_name = f"{ctx.update.message.chat.title[:32]} by @{bot.getMe().username}"
        creator_id = get_chat_creator(ctx.update.message.chat)
    if len(args) > 0:
        emoji = args[0]
    else:
        emoji = "🤖"
    try:
        try:
            image = resize_sticker(get_file_from_message(bot, ctx.update))
        except NoImageProvided:
            return ctx.reply(ctx.localize("No image as photo/file provided."), failed=True)
        except OverflowError:
            return ctx.reply(ctx.localize("Failed to compress image after 8 tries"), failed=True)
        except Image.DecompressionBombError:
            return ctx.reply(ctx.localize("Attempting to make image bombs, are we?"), failed=True)
        except OSError:
            return ctx.reply(ctx.localize("This file doesn't look like image file"), failed=True)
        try:
            sticker_result = bot.addStickerToSet(user_id=get_chat_creator(ctx.update.message.chat),
                                name=pack_name,
                                png_sticker=image, emojis=emoji)
            LOGGER.info("addStickerToSet result for %s: %s", pack_name, sticker_result)
        except BadRequest as e:
            LOGGER.info("Bad Request during addStickerToSet: %s", e)
            image.seek(0)
            if str(e).lower() == "stickers_too_much":
                if personal:
                    db = ctx.user_db
                else:
                    db = ctx.chat_db
                currentidx = int(db.get("packidx", '0'))
                db['packidx'] = currentidx + 1
                LOGGER.debug("increasing packidx...")
                ctx.reply(ctx.localize("This pack has too much stickers already! Creating new pack..."))
                return sticker_add(bot, ctx, personal)
            else:
                try:
                    bot.createNewStickerSet(user_id=creator_id,
                                            name=pack_name,
                                            title=display_name,
                                            png_sticker=image,
                                            emojis=emoji)
                except BadRequest as e:
                    if str(e).lower() == "peer_id_invalid":
                        return ctx.reply(
                            ctx.localize(
                                "Sorry, but I can't create group pack right now. Ask group creator to PM me and try again."),
                            failed=True)
                    else:
                        raise e
        sticker = bot.getStickerSet(pack_name).stickers[-1]
        return ctx.update.message.reply_sticker(sticker.file_id)
    except TimedOut:
        return ctx.reply(
            ctx.localize("It seems like I got timed out when creating sticker, that is Telegram-side error. Please try again."),
            failed=True)


@octobot.CommandHandler("group_pack_add", octobot.localizable("Adds sticker to group stickerpack"), inline_support=False)
@octobot.supergroup_only
@octobot.permissions(is_admin=True)
def gsticker_add(bot, ctx):
    sticker_add(bot, ctx, False)


@octobot.CommandHandler("pack_add", octobot.localizable("Adds sticker to personal stickerpack"), inline_support=False)
def usticker_add(bot, ctx):
    sticker_add(bot, ctx, True)


@octobot.CommandHandler("pack_del", octobot.localizable("Removes sticker from group/user stickerpack"), inline_support=False)
def sticker_del(bot: octobot.OctoBot, ctx: octobot.Context):
    reply = ctx.update.message.reply_to_message
    if reply and reply.sticker:
        sticker = reply.sticker
        stickerset = str(sticker.set_name)
        if_owned_by_bot = stickerset.endswith(f"by_{bot.me.username}")
        if_personal = stickerset.startswith(f"personal_{ctx.user.id}")
        if_group = stickerset.startswith(f"group_{ctx.chat.id * -1}")
        print(stickerset, if_owned_by_bot, if_personal, if_group, f"group_{ctx.chat.id * -1}")
        if if_owned_by_bot and (if_personal or if_group):
            if if_group and not octobot.check_permissions(ctx.chat, ctx.user, {"is_admin"}, bot)[0]:
                return ctx.reply(ctx.localize("You can't delete this chat stickers cause you are not an admin."))
            bot.deleteStickerFromSet(sticker.file_id)
            return ctx.reply(ctx.localize("🚮Sticker deleted."))
        return ctx.reply(ctx.localize("You can't delete stickers in this stickerpack"))
    ctx.reply(ctx.localize("Please reply to sticker from group/user pack"))
