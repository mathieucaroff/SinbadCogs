import discord
import logging
from discord.ext import commands

from redbot.core import Config, RedContext
from redbot.core import checks
from redbot.core.utils.chat_formatting import pagify
from .serialize import deserialize_embed, serialize_embed
from .yaml_parse import embed_from_userstr

log = logging.getLogger('redbot.sinbadcogs.embedmaker')


class EmbedMaker:
    """
    Storable, recallable, embed maker
    """

    __author__ = 'mikeshardmind'
    __version__ = '2.1.1'

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160,
            force_registration=True
        )
        self.config.register_custom('EMBED', embed={}, owner=None)
        self.config.register_guild(active=True)

    @commands.group(name="embed")
    async def _embed(self, ctx: RedContext):
        """
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @_embed.command(name='advmake', hidden=True)
    async def make_adv(self, ctx: RedContext, name: str, *, data: str):
        """
        makes an embed from valid yaml

        Note: Fields should be provided as nested key: value pairs,
        keys indicating position.
        """
        name = name.lower()
        group = self.config.custom('EMBED', ctx.guild.id, name)
        if await group.owner() not in (ctx.author.id, None):
            return await ctx.maybe_send_embed(
                "An embed with that name already exists!")
        try:
            e = await embed_from_userstr(ctx, data)
            await ctx.send("Here's how that's gonna look", embed=e)
        except Exception:
            await ctx.maybe_send_embed(
                'There was something wrong with that input')
        except (discord.Forbidden, discord.HTTPException):
            await ctx.maybe_send_embed("Discord didn't like that embed")
        else:
            await ctx.tick()
            await group.owner.set(ctx.author.id)
            await group.embed.set(serialize_embed(e))

    @commands.bot_has_permissions(embed_links=True)
    @checks.is_owner()
    @_embed.command(name='advmakeglobal', hidden=True)
    async def make_global_adv(self, ctx: RedContext, name: str, *, data: str):
        """
        makes an embed from valid yaml

        Note: Fields should be provided as nested key: value pairs,
        keys indicating position.
        """
        try:
            name = name.lower()
            e = await embed_from_userstr(ctx, data)
            await ctx.send("Here's how that's gonna look", embed=e)
        except Exception:
            await ctx.maybe_send_embed(
                'There was something wrong with that input')
        except (discord.Forbidden, discord.HTTPException):
            await ctx.maybe_send_embed("Discord didn't like that embed")
        else:
            await ctx.tick()
            await self.config.custom(
                'EMBED', 'GLOBAL', name).owner.set(ctx.author.id)
            await self.config.custom(
                'EMBED', 'GLOBAL', name).embed.set(serialize_embed(e))

    @commands.guild_only()
    @_embed.command(name="make")
    async def _make(self, ctx: RedContext, name: str, *, content: str):
        """
        makes an embed
        """
        name = name.lower()
        group = self.config.custom('EMBED', ctx.guild.id, name)
        if await group.owner() not in (ctx.author.id, None):
            return await ctx.maybe_send_embed(
                "An embed with that name already exists!")

        e = discord.Embed(description=content)
        try:
            await ctx.send("Here's how that's gonna look", embed=e)
        except (discord.Forbidden, discord.HTTPException):
            await ctx.maybe_send_embed("Discord didn't like that embed")
        else:
            await ctx.tick()
            await group.owner.set(ctx.author.id)
            await group.embed.set(serialize_embed(e))

    @checks.is_owner()
    @_embed.command(name='makeglobal')
    async def make_global(self, ctx: RedContext, name: str, *, content: str):
        """
        make a global embed
        """
        name = name.lower()
        group = self.config.custom('EMBED', 'GLOBAL', name)
        try:
            e = discord.Embed(description=content)
            await ctx.send("Here's how that's gonna look", embed=e)
        except ValueError:
            await ctx.maybe_send_embed(
                'There was something wrong with that input')
        except (discord.Forbidden, discord.HTTPException):
            await ctx.maybe_send_embed("Discord didn't like that embed")
        else:
            await ctx.tick()
            await group.owner.set(ctx.author.id)
            await group.embed.set(serialize_embed(e))

    @_embed.command(name="list")
    async def _list(self, ctx: RedContext):
        """
        lists the embeds here
        """
        embed_dict = await self.config._get_base_group('EMBED')()
        if ctx.guild:
            local_embeds = list(
                sorted(embed_dict.get(str(ctx.guild.id), {}).keys()))
        else:
            local_embeds = []

        global_embeds = list(sorted(embed_dict.get('GLOBAL', {}).keys()))

        if not local_embeds and not global_embeds:
            return await ctx.maybe_send_embed('No embeds available here.')

        if local_embeds:
            local_embeds.insert(0, 'Local Embeds:')
            if global_embeds:
                local_embeds.append('\n')
        if global_embeds:
            global_embeds.insert(0, 'Global Embeds:')
        output = "\n".join(local_embeds + global_embeds)

        for page in pagify(output):
            await ctx.maybe_send_embed(page)

    @commands.guild_only()
    @_embed.command(name="remove")
    async def _remove(self, ctx: RedContext, name: str):
        """
        removes an embed
        """
        name = name.lower()
        group = self.config.custom('EMBED', ctx.guild.id, name)
        if not await group.owner():
            return await ctx.maybe_send_embed('No such embed')
        if any(  # who created, bot owner, admins, mods
            (await group.owner() == ctx.author.id,
             await ctx.bot.is_owner(ctx.author),
             await ctx.bot.db.guild(ctx.guild).admin_role() in
             [r.id for r in ctx.author.roles],
             await ctx.bot.db.guild(ctx.guild).mod_role() in
             [r.id for r in ctx.author.roles])
        ):
            await group.clear()
            await ctx.tick()

    @checks.is_owner()
    @_embed.command(name="rmglobal")
    async def remove_global(self, ctx: RedContext, name: str):
        """
        removes a global embed
        """
        name = name.lower()
        await self.config.custom('EMBED', 'GLOBAL', name).clear()

    @commands.bot_has_permissions(embed_links=True)
    @_embed.command()
    async def drop(self, ctx: RedContext, name: str):
        """
        drops an embed here
        """
        name = name.lower()
        try:
            x = await self.get_and_send(ctx.channel, ctx.guild.id, name)
        except (discord.Forbidden, discord.HTTPException) as e:
            log.error(e)
        else:
            if x is not None:
                await ctx.tick()

    @checks.is_owner()
    @_embed.command(name="dropglobal")
    async def drop_global(self, ctx: RedContext, name: str):
        """
        drop a global embed here
        """
        name = name.lower()
        x = await self.get_and_send(ctx.channel, 'GLOBAL', name)
        if x is not None:
            await ctx.tick()

    @checks.admin()
    @_embed.command()
    async def dm(self, ctx: RedContext, name: str, user: discord.Member):
        """
        DMs an embed
        """
        name = name.lower()
        try:
            x = await self.get_and_send(ctx.channel, ctx.guild.id, name)
        except discord.Forbidden as e:
            await ctx.maybe_send_embed(
                'User has disabled DMs from this server or blocked me')
        else:
            if x is not None:
                await ctx.tick()

    @checks.admin()
    @_embed.command()
    async def dmglobal(self, ctx: RedContext, name: str, user: discord.Member):
        """
        DMs a global embed
        """
        name = name.lower()
        try:
            x = await self.get_and_send(ctx.channel, 'GLOBAL', name)
        except discord.Forbidden as e:
            await ctx.maybe_send_embed(
                'User has disabled DMs from this server or blocked me')
        else:
            if x is not None:
                await ctx.tick()

    @commands.guild_only()
    @_embed.command(name='frommsg')
    async def from_message(self, ctx: RedContext, name: str, _id: int):
        """
        Store's a message's embed
        """
        name = name.lower()
        try:
            e = (await ctx.channel.get_message(_id)).embeds[0]
        except Exception:
            return

        await self.config.custom('EMBED', ctx.guild.id, name).embed.set(
            serialize_embed(e)
        )
        await self.config.custom('EMBED', ctx.guild.id, name).owner.set(
            ctx.author.id
        )
        await ctx.tick()

    @checks.is_owner()
    @_embed.command(name='globalfrommsg')
    async def global_from_message(self, ctx: RedContext, name: str, _id: int):
        """
        stores a message's embed
        """
        name = name.lower()
        try:
            e = (await ctx.channel.get_message(_id)).embeds[0]
        except Exception:
            return

        await self.config.custom('EMBED', 'GLOBAL', name).embed.set(
            serialize_embed(e)
        )
        await self.config.custom('EMBED', 'GLOBAL', name).owner.set(
            ctx.author.id
        )
        await ctx.tick()

    async def get_and_send(self, where, *identifiers):
        if await self.config.custom('EMBED', *identifiers).owner():
            data = await self.config.custom('EMBED', *identifiers).embed()
            embed = deserialize_embed(data)
            return await where.send(embed=embed)
