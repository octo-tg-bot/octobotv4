from octobot.database import Database
import telegram
import json


def create_db_entry_name(chat: telegram.Chat):
    return f"admcache:{chat.id}"


def reset_cache(chat: telegram.Chat):
    return Database.redis.delete(create_db_entry_name(chat))


def check_perms(chat: telegram.Chat, user: telegram.User, permissions_to_check: set):
    if chat.type != "supergroup":
        return True, []
    db_entry = create_db_entry_name(chat)
    if Database.redis is not None and Database.redis.exists(db_entry) == 1:
        adm_list = json.loads(Database.redis.get(db_entry).decode())
    else:
        adm_list_t = chat.get_administrators()
        adm_list = []
        for admin in adm_list_t:
            adm_list.append(admin.to_dict())
        if Database.redis is not None:
            Database.redis.set(db_entry, json.dumps(adm_list))
            Database.redis.expire(db_entry, 240)
    print(adm_list)
    for member in adm_list:
        if member["user"]["id"] == user.id:
            if member["status"] == "creator":
                return True, permissions_to_check
            if "is_admin" in permissions_to_check:
                permissions_to_check.remove("is_admin")
            for user_permission in permissions_to_check.copy():
                print(member[user_permission], user_permission)
                if member[user_permission]:
                    permissions_to_check.remove(user_permission)
            break
    return len(permissions_to_check) == 0, permissions_to_check


def permissions(**perms):
    """
    Decorator to check permissions.

    :param perms: Valid permissions that can be found on :class:`telegram.ChatMember` + is_admin. Example: `@permissions(can_delete_messages=True)`. The value does not matter.
    """
    perms = set(perms.keys())

    def decorator(function):
        def wrapper(bot, context):
            if context.chat is not None:
                res, missing_perms = check_perms(context.chat, context.user, perms.copy())
                if res:
                    function(bot, context)
                else:
                    context.reply(context.localize(
                        "Sorry, you can't execute this command cause you lack following permissions: {}").format(
                        ', '.join(perms)))

        return wrapper

    return decorator


def my_permissions(**perms):
    """
    Decorator to check bots own permissions.

    :param perms: Valid permissions that can be found on :class:`telegram.ChatMember` + is_admin. Example: `@my_permissions(can_delete_messages=True)`. The value does not matter.
    """
    perms = set(perms.keys())

    def decorator(function):
        def wrapper(bot, context):
            if context.chat is not None:
                res, missing_perms = check_perms(context.chat, bot.me, perms.copy())
                if res:
                    function(bot, context)

        return wrapper

    return decorator
