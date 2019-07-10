from modules import dbhandler
from modules import docs
from modules import permissions
from modules import reputation
import discord
import asyncio

async def make_queue_channel(client, ctx, queuetype):
    guildqueuecategory = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_queue_category", str(ctx.guild.id)]])
    if guildqueuecategory:
        if not await dbhandler.query(["SELECT user_id FROM queues WHERE user_id = ? AND guild_id = ?", [str(ctx.message.author.id), str(ctx.guild.id)]]):
            try:
                await ctx.send("sure, gimme a moment")
                if not queuetype:
                    queuetype = "std"
                guild = ctx.message.guild
                channeloverwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.message.author: discord.PermissionOverwrite(
                        create_instant_invite=True,
                        manage_channels=True,
                        manage_roles=True,
                        read_messages=True,
                        send_messages=True,
                        manage_messages=True,
                        embed_links=True,
                        attach_files=True,
                        read_message_history=True,
                    ),
                    guild.me: discord.PermissionOverwrite(
                        manage_channels=True,
                        manage_roles=True,
                        read_messages=True,
                        send_messages=True,
                        embed_links=True
                    )
                }
                discordfriendlychannelname = "%s-%s-queue" % (
                    ctx.message.author.display_name.replace(" ", "_").lower(), queuetype)
                category = await reputation.validate_reputation_queues(client, ctx.message.author)
                channel = await guild.create_text_channel(discordfriendlychannelname, overwrites=channeloverwrites, category=category)
                await dbhandler.query(["INSERT INTO queues VALUES (?, ?, ?)", [str(channel.id), str(ctx.message.author.id), str(ctx.guild.id)]])
                await channel.send("%s done!" % (ctx.message.author.mention), embed=await docs.queuemanagement())
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.send("you already have a queue though. or it was deleted, in this case, ping kyuunex")
    else:
        await ctx.send("Not enabled in this server yet.")


async def queuesettings(client, ctx, action, params):
    if (await dbhandler.query(["SELECT user_id FROM queues WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (await permissions.check(ctx.message.author.id)):
        try:
            print(params)
            if params:
                if len(params) == 2:
                    embed_title = params[0] 
                    embed_desc = params[1]
                else:
                    embed_title = "Message" 
                    embed_desc = " ".join(params)
                embed = discord.Embed(title=embed_title, color=0xbd3661, description=embed_desc)
                embed.set_author(name=ctx.message.author.display_name, icon_url=ctx.message.author.avatar_url)
                await ctx.message.delete()
            else:
                embed = None
            if action == "open":
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=None, send_messages=True)
                await reputation.unarchive_queue(client, ctx, ctx.message.author)
                await ctx.send("queue open!", embed=embed)
            elif action == "close":
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=None, send_messages=False)
                await ctx.send("queue closed!", embed=embed)
            elif action == "show":
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=None, send_messages=False)
                await ctx.send("queue is visible to everyone, but it's still closed. use 'open command if you want people to post in it.", embed=embed)
            elif action == "hide":
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=False, send_messages=False)
                await ctx.send("queue hidden!", embed=embed)
        except Exception as e:
            await ctx.send(e)
    else:
        await ctx.message.delete()
        await ctx.send("%s not your queue" % (ctx.message.author.mention), delete_after=3)


async def on_guild_channel_delete(client, deleted_channel):
    try:
        await dbhandler.query(["DELETE FROM queues WHERE channel_id = ?",[str(deleted_channel.id)]])
        print("channel %s is deleted" % (deleted_channel.name))
    except Exception as e:
        print(e)