from modules import db
from cogs.Docs import Docs
from modules import permissions
from modules import reputation
import discord
from discord.ext import commands


class Queue(commands.Cog, name="Queue Management Commands"):
    def __init__(self, bot):
        self.bot = bot
        self.docs = Docs(bot)
        self.queue_owner_default_permissions = discord.PermissionOverwrite(
            create_instant_invite=True,
            manage_channels=True,
            manage_roles=True,
            read_messages=True,
            send_messages=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
        )
        self.queue_bot_default_permissions = discord.PermissionOverwrite(
            manage_channels=True,
            manage_roles=True,
            read_messages=True,
            send_messages=True,
            embed_links=True
        )

    @commands.command(name="request_queue", brief="Request a queue", description="")
    async def make_queue_channel(self, ctx, queue_type=None):
        guild_queue_category = db.query(["SELECT value FROM config "
                                         "WHERE setting = ? AND parent = ?",
                                         ["guild_mapper_queue_category", str(ctx.guild.id)]])
        if guild_queue_category:
            member_already_has_a_queue = db.query(["SELECT channel_id FROM queues "
                                                   "WHERE user_id = ? AND guild_id = ?",
                                                   [str(ctx.author.id), str(ctx.guild.id)]])
            if member_already_has_a_queue:
                already_existing_queue = self.bot.get_channel(int(member_already_has_a_queue[0][0]))
                if already_existing_queue:
                    await ctx.send("you already have one <#%s>" % str(already_existing_queue.id))
                    return
                else:
                    db.query(["DELETE FROM queues WHERE channel_id = ?", [str(member_already_has_a_queue[0][0])]])

            try:
                await ctx.send("sure, gimme a moment")
                if not queue_type:
                    queue_type = "std"
                guild = ctx.guild
                channel_overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.message.author: self.queue_owner_default_permissions,
                    guild.me: self.queue_bot_default_permissions
                }
                channel_name = "%s-%s-queue" % (
                    ctx.author.display_name.replace(" ", "_").lower(), queue_type)
                category = await reputation.get_queue_category(self.bot, ctx.author)
                channel = await guild.create_text_channel(channel_name,
                                                          overwrites=channel_overwrites, category=category)
                db.query(["INSERT INTO queues VALUES (?, ?, ?)",
                          [str(channel.id), str(ctx.author.id), str(ctx.guild.id)]])
                await channel.send("%s done!" % ctx.author.mention, embed=await self.docs.queue_management())
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.send("Not enabled in this server yet.")

    @commands.command(name="open", brief="Open the queue", description="")
    async def open(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=True)
            await reputation.unarchive_queue(self.bot, ctx, ctx.author)
            await ctx.send("queue open!")

    @commands.command(name="close", brief="Close the queue", description="")
    async def close(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=False)
            await ctx.send("queue closed!")

    @commands.command(name="show", brief="Show the queue", description="")
    async def show(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=False)
            await ctx.send("queue is visible to everyone, but it's still closed. "
                           "use `'open` command if you want people to post in it.")

    @commands.command(name="hide", brief="Hide the queue", description="")
    async def hide(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
            await ctx.send("queue hidden!")

    @commands.command(name="recategorize", brief="Recategorize the queue", description="")
    async def recategorize(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if queue_owner_check and is_queue_channel:
            await ctx.channel.edit(reason=None, category=await reputation.get_queue_category(self.bot, ctx.author))

    @commands.command(name="archive", brief="Archive the queue", description="")
    async def archive(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            guild_archive_category_id = db.query(["SELECT value FROM config "
                                                  "WHERE setting = ? AND parent = ?",
                                                  ["guild_archive_category", str(ctx.guild.id)]])
            if guild_archive_category_id:
                archive_category = self.bot.get_channel(int(guild_archive_category_id[0][0]))
                await ctx.channel.edit(reason=None, category=archive_category)
                await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
                await ctx.send("queue archived!")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, deleted_channel):
        try:
            db.query(["DELETE FROM queues WHERE channel_id = ?", [str(deleted_channel.id)]])
            print("channel %s is deleted. maybe not a queue" % deleted_channel.name)
        except Exception as e:
            print(e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        queue_id = db.query(["SELECT channel_id FROM queues WHERE user_id = ?", [str(member.id)]])
        if queue_id:
            queue_channel = self.bot.get_channel(int(queue_id[0][0]))
            if queue_channel:
                await queue_channel.set_permissions(target=member, overwrite=self.queue_owner_default_permissions)
                await queue_channel.send("the queue owner has returned. "
                                         "next time you open the queue, it will be unarchived.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        queue_id = db.query(["SELECT channel_id FROM queues WHERE user_id = ?", [str(member.id)]])
        if queue_id:
            queue_channel = self.bot.get_channel(int(queue_id[0][0]))
            if queue_channel:
                await queue_channel.send("the queue owner has left")
                guild_archive_category_id = db.query(["SELECT value FROM config "
                                                      "WHERE setting = ? AND parent = ?",
                                                      ["guild_archive_category", str(queue_channel.guild.id)]])
                if guild_archive_category_id:
                    archive_category = self.bot.get_channel(int(guild_archive_category_id[0][0]))
                    await queue_channel.edit(reason=None, category=archive_category)
                    await queue_channel.set_permissions(queue_channel.guild.default_role,
                                                        read_messages=False,
                                                        send_messages=False)
                    await queue_channel.send("queue archived!")


def setup(bot):
    bot.add_cog(Queue(bot))
