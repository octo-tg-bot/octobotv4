import octobot
from octobot.handlers import BaseHandler
from typing import Union


class CommandHandler(BaseHandler):
    """
    Command handler. Handles commands in chat and commands in inline queries.

    .. note:: Prefix will not be checked in case of inline queries

    :param command: Command to handle
    :type command: list,str
    :param description: Command description
    :type description: str
    :param long_description: Command long description, appears in help for that specific command
    :type long_description: str
    :param prefix: Command prefix, defaults to `/`
    :type prefix: str,optional
    :param hidden: If command should be hidden from /help, defaults to `False`
    :type hidden: bool,optional
    :param inline_support: If command is supported in inline mode, defaults to `True`
    :type inline_support: bool,optional

    """

    def __init__(self, command: Union[list, str], description: str = "Command description not specified by developer",
                 long_description: str = "Additional info not specified by developer",
                 hidden=False, prefix="/", inline_support=True, *args, **kwargs):
        super(CommandHandler, self).__init__(*args, **kwargs)
        if isinstance(command, str):
            command = [command]
        self.inline_support = inline_support
        self.command = command
        self.description = description
        self.long_description = long_description
        self.hidden = hidden
        self.prefix = prefix

    @property
    def commandlist(self):
        for command in self.command:
            yield self.prefix + command

    def execute_function_textmode(self, bot, context):
        self.function(bot, context)

    def check_command(self, bot, context):
        if context.update_type == octobot.UpdateType.inline_query:
            if not self.inline_support:
                return False
            prefix = ''
        else:
            prefix = self.prefix
        incmd = context.text
        if incmd.startswith(prefix):
            for command in self.command:
                command = prefix + command
                state_only_command = incmd == command or incmd.startswith(
                    command + " ")
                state_word_swap = len(incmd.split(
                    "/")) > 2 and incmd.startswith(command)
                state_mention_command = incmd.startswith(
                    command + "@" + bot.me.username)
                if state_only_command or state_word_swap or state_mention_command:
                    return True
        return False

    def handle_update(self, bot, context):
        if context.update_type == octobot.UpdateType.button_press:
            return
        elif self.check_command(bot, context):
            self.execute_function_textmode(bot, context)
