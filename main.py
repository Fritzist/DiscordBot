import asyncio
import datetime

import aiohttp
import humanfriendly as humanfriendly
import requests
from nextcord.ext import commands
from discord.ext import commands
import json
import nextcord
import wavelink
import random
import io
import discord


intents = nextcord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix="$", intents=intents)
#client.remove_command("help")


@client.event
async def on_ready():
    print('Bin endlich wieder Online, Yeah Yeah')
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"$allCommands $helpDE $helpEN"),
                                 status=discord.Status.online)
    client.loop.create_task(node_connect())


@client.event
async def on_wavelink_node_connect(node: wavelink.Node):
    print(f"Node {node.identifier} is ready")


async def node_connect():
    await client.wait_until_ready()
    await wavelink.NodePool.create_node(bot=client, host="node2.gglvxd.tk", port=443, password="free", https=True)



class ControlPanel(nextcord.ui.View):
    def __init__(self, vc, ctx):
        super(ControlPanel, self).__init__()
        self.vc = vc
        self.ctx = ctx

    @nextcord.ui.button(label="Resume/Pause", style=nextcord.ButtonStyle.blurple)
    async def resume_and_pause(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not interaction.user == self.ctx.author:
            return await interaction.response.send_message(f"<@{self.ctx.message.author.id}> Nutze die Buttons um das zu machen ($pannel)", ephemeral=True)
        for child in self.children:
            child.disabled = False
        if self.vc.is_paused():
            await self.vc.resume()
            await interaction.message.edit(content="Resumed", view=self)
        else:
            await self.vc.pause()
            await interaction.message.edit(content="Paused", view=self)

    @nextcord.ui.button(label="Queue", style=nextcord.ButtonStyle.blurple)
    async def queue(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not interaction.user == self.ctx.author:
            return await interaction.response.send_message(f"<@{self.ctx.message.author.id}> Nutze die Buttons um das zu machen ($pannel)", ephemeral=True)
        for child in self.children:
            child.disabled = False
        button.disabled = True

        if self.vc.queue.is_empty:
            return interaction.response.send_message(f"Die queue ist leer D: <@{self.ctx.message.author.id}>", ephemeral=True)

        em = nextcord.Embed(titel=":musical_note: Music :musical_note:")
        queue = self.vc.queue.copy()
        song_count = 0

        for song in queue:
            song_count += 1
            em.add_field(name=f"Song Num {song_count}", value=f"`{song.title}`")
            await interaction.message.edit(embed=em, view=self)

        #return await interaction.response.send_message(embed=em)

    @nextcord.ui.button(label="Skip", style=nextcord.ButtonStyle.blurple)
    async def skip(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not interaction.user == self.ctx.author:
            return await interaction.response.send_message(
                f"<@{self.ctx.message.author.id}> Nutze die Buttons um das zu machen ($pannel)", ephemeral=True)
        for child in self.children:
            child.disabled = False
        button.disabled = True

        if self.vc.queue.is_empty:
            return interaction.response.send_message(f"Die queue ist leer D: <@{self.ctx.message.author.id}>",
                                                     ephemeral=True)

        try:
            next_song = self.vc.queue.get()
            await self.vc.play(next_song)
            await interaction.response.send_message(content=f"Now Playing `{next_song}`", view=self)

        except Exception:
            return await interaction.response.send_message(f"<@{self.ctx.message.author.id}> Die Queue ist leer", ephemeral=True)

    @nextcord.ui.button(label="Disconnect", style=nextcord.ButtonStyle.red)
    async def disconnect(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not interaction.user == self.ctx.author:
            return await interaction.response.send_message(
                f"<@{self.ctx.message.author.id}> Nutze die Buttons um das zu machen ($pannel)", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await self.vc.disconnect()
        await interaction.response.send_message(content=f"Disconnected", view=self)

@client.event
async def on_wavelink_track_end(player: wavelink.Player, track: wavelink.Track, reason):
    ctx = player.ctx
    vc: player = ctx.voice_client

    if vc.loop:
        return await vc.play(track)

    next_song = vc.queue.get()
    await vc.play(next_song)
    await ctx.send(f"now playing {next_song.title}")

@client.command()
async def panel(ctx: commands.Context):
    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(f"Gehe erst in ein Voice channel rein <@{ctx.message.author.id}>")
    elif not ctx.author.voice != ctx.me.voice:
        return await ctx.send(f"<@{ctx.message.author.id}> wir müssen in dem selben voice Channel sein")
    else:
        vc: wavelink.Player = ctx.voice_client
    if not vc.is_playing():
        return await ctx.send(f"<@{ctx.message.author.id}> Starte zuerst einen Song!")

    em = nextcord.Embed(title="Music Panel", description="Shortcuts für die Musik commands")
    view = ControlPanel(vc, ctx)
    await ctx.send(embed=em, view=view)

@client.command()
async def play(ctx: commands.Context, *, search: wavelink.YouTubeTrack):
    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(f"Gehe erst in ein Voice channel rein <@{ctx.message.author.id}>")
    elif not ctx.author.voice != ctx.me.voice:
        return await ctx.send(f"<@{ctx.message.author.id}> wir müssen in dem selben voice Channel sein")
    else:
        vc: wavelink.Player = ctx.voice_client

    if vc.queue.is_empty and not vc.is_playing():
        await vc.play(search)
        await ctx.send(f"`{search.title}` läuft jetzt :D <@{ctx.message.author.id}>")

    else:
        await vc.queue.put_wait(search)
        await ctx.send(f"`{search.title}` wird bald abgespielt :D <@{ctx.message.author.id}>")
    vc.ctx = ctx
    try:
        if vc.loop: return
    except Exception:
        setattr(vc, "loop", False)

@client.command()
async def pause(ctx: commands.Context):
    if not ctx.voice_client:
       return await ctx.send(f"Wie soll ich Musik stoppen, wenn es keine gibt? <@{ctx.message.author.id}>")
    elif not getattr(ctx.author.voice, "channel", None):
       return await ctx.send(f"Gehe erst in ein Voice channel rein <@{ctx.message.author.id}>")
    elif not ctx.author.voice != ctx.me.voice:
        return await ctx.send(f"<@{ctx.message.author.id}> wir müssen in dem selben voice Channel sein")
    else:
        vc: wavelink.Player = ctx.voice_client

    await vc.pause()
    await ctx.send(f"Die Muisk wurde gestoppt :D <@{ctx.message.author.id}>")

@client.command()
async def resume(ctx: commands.Context):
    if not ctx.voice_client:
       return await ctx.send(f"Wie soll ich Musik stoppen, wenn es keine gibt? <@{ctx.message.author.id}>")
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(f"Gehe erst in ein Voice channel rein <@{ctx.message.author.id}>")
    elif not ctx.author.voice != ctx.me.voice:
        return await ctx.send(f"<@{ctx.message.author.id}> wir müssen in dem selben voice Channel sein")
    else:
        vc: wavelink.Player = ctx.voice_client

    await vc.resume()
    await ctx.send(f"Die Muisk läuft wieder :D <@{ctx.message.author.id}>")

@client.command()
async def stop(ctx: commands.Context):
    if not ctx.voice_client:
       return await ctx.send(f"Wie soll ich Musik stoppen, wenn es keine gibt? <@{ctx.message.author.id}>")
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(f"Gehe erst in ein Voice channel rein <@{ctx.message.author.id}>")
    elif not ctx.author.voice != ctx.me.voice:
        return await ctx.send(f"<@{ctx.message.author.id}> wir müssen in dem selben voice Channel sein")
    else:
        vc: wavelink.Player = ctx.voice_client

    await vc.stop()
    await ctx.send(f"Die Muisk wurde beendet D: <@{ctx.message.author.id}>")

@client.command()
async def leave(ctx: commands.Context):
    if not ctx.voice_client:
       return await ctx.send(f"Wie soll ich Musik stoppen, wenn es keine gibt? <@{ctx.message.author.id}>")
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(f"Gehe erst in ein Voice channel rein <@{ctx.message.author.id}>")
    elif not ctx.author.voice != ctx.me.voice:
        return await ctx.send(f"<@{ctx.message.author.id}> wir müssen in dem selben voice Channel sein")
    else:
        vc: wavelink.Player = ctx.voice_client

    await vc.disconnect()
    await ctx.send(f"Die Musikstunde ist nun beendet! D: <@{ctx.message.author.id}>")

@client.command()
async def loop(ctx: commands.Context):
    if not ctx.voice_client:
       return await ctx.send(f"Wie soll ich Musik stoppen, wenn es keine gibt? <@{ctx.message.author.id}>")
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(f"Gehe erst in ein Voice channel rein <@{ctx.message.author.id}>")
    elif not ctx.author.voice != ctx.me.voice:
        return await ctx.send(f"<@{ctx.message.author.id}> wir müssen in dem selben voice Channel sein")
    else:
        vc: wavelink.Player = ctx.voice_client

    try:
        vc.loop ^= True
    except Exception:
        setattr(vc, "loop", False)

    if vc.loop:
        return await ctx.send(f"Die Loop funktion wurde aktiviert :D <@{ctx.message.author.id}>")

    else:
        return await ctx.send(f"Die Loop funktion wurde deaktiviert D: <@{ctx.message.author.id}>")

@client.command()
async def queue(ctx: commands.Context):
    if not ctx.voice_client:
        return await ctx.send(f"Wie soll ich Musik in die queue schieben, wenn es keine gibt? <@{ctx.message.author.id}>")
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(f"Gehe erst in ein Voice channel rein <@{ctx.message.author.id}>")
    vc: wavelink.Player = ctx.voice_client

    if vc.queue.is_empty:
        return await ctx.send(f"Die queue ist leer D: <@{ctx.message.author.id}>")

    em = nextcord.Embed(title=":musical_note: Music :musical_note:")

    queue = vc.queue.copy()
    songCount = 0
    for song in queue:
        songCount += 1
        em.add_field(name=f"Song Num {str(songCount)}", value=f"`{song}`")

    await ctx.send(embed=em)

@client.command()
async def nowplaying(ctx: commands.Context):
    if not ctx.voice_client:
        return await ctx.send("im not even in a vc... so how will I see whats playing")
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send("join a voice channel first lol")
    else:
        vc: wavelink.Player = ctx.voice_client

    if not vc.is_playing():
        return await ctx.send("nothing is playing")

    em = nextcord.Embed(title=f"Now Playing {vc.track.title}", description=f"Artist: {vc.track.author}")
    em.add_field(name="Duration", value=f"`{str(datetime.timedelta(seconds=vc.track.length))}`")
    em.add_field(name="Extra Info", value=f"Song URL: [Click Me]({str(vc.track.uri)})")
    return await ctx.send(embed=em)

@client.command()
async def volume(ctx: commands.Context, volume: int):
    if not ctx.voice_client:
        return await ctx.send("im not even in a vc... so how will I change the volume on anything")
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send("join a voice channel first lol")
    else:
        vc: wavelink.Player = ctx.voice_client
    if not vc.is_playing():
        return await ctx.send("first play some music")

    if volume > 1000:
        return await ctx.send('thats wayy to high')
    elif volume < 0:
        return await ctx.send("thats way to low")
    await ctx.send(f"Set the volume to `{volume}%`")
    return await vc.set_volume(volume)

@client.command()
async def skip(ctx: commands.Context):
    if not ctx.voice_client:
        return await ctx.send("im not even in a vc... so how will I pause anything")
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send("join a voice channel first lol")
    else:
        vc: wavelink.Player = ctx.voice_client
    if not vc.is_playing():
        return await ctx.send("first play some music")

    try:
        next_song = vc.queue.get()
        await vc.play(next_song)
        await ctx.send(content=f"Now Playing `{next_song}`")
    except Exception:
        return await ctx.send("The queue is empty!")

    await vc.stop()
    await ctx.send("stopped the song")

# send the lyrics of the song with google search and replace the spaces with +

@client.command()
async def lyrics(ctx: commands.Context):
    if not ctx.voice_client:
        return await ctx.send("im not even in a vc... so how will I pause anything")
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send("join a voice channel first lol")
    else:
        vc: wavelink.Player = ctx.voice_client
    if not vc.is_playing():
        return await ctx.send("first play some music")

    await ctx.send(f"The lyrics of      `{vc.track.title}`: https://www.google.com/search?q={vc.track.title.replace(' ', '+')}+lyrics")
                            #TTT

player1 = ""
player2 = ""
turn = ""
gameOver = True

board = []

winningConditions = [
    [0, 1, 2],
    [3, 4, 5],
    [6, 7, 8],
    [0, 3, 6],
    [1, 4, 7],
    [2, 5, 8],
    [0, 4, 8],
    [2, 4, 6]
]

@client.command()
async def ttt(ctx, p1: discord.Member, ):
    global count
    global player1
    global player2
    global turn
    global gameOver

    if gameOver:
        global board
        board = [":white_large_square:", ":white_large_square:", ":white_large_square:",
                 ":white_large_square:", ":white_large_square:", ":white_large_square:",
                 ":white_large_square:", ":white_large_square:", ":white_large_square:"]
        turn = ""
        gameOver = False
        count = 0

        player1 = p1
        player2 = ctx.author

        # print the board

        line = ""
        for x in range(len(board)):
            if x == 2 or x == 5 or x == 8:
                line += " " + board[x]
                await ctx.send(line)
                line = ""
            else:
                line += " " + board[x]

        # determine who goes first
        num = random.randint(1, 2)
        if num == 1:
            turn = player1
            await ctx.send("<@" + str(player1.id) + "> fängt an /turn")
        elif num == 2:
            turn = player2
            await ctx.send("<@" + str(player2.id) + "> fängt an / turn")
    else:
        await ctx.send('''Es wird bereits gespielt bitte warte kurz. \n
        somebody is playing please wait''')


@client.command()
async def place(ctx, pos: int):
    global turn
    global player1
    global player2
    global board
    global count
    global gameOver

    if not gameOver:
        mark = ""
        if turn == ctx.author:
            if turn == player1:
                mark = ":regional_indicator_x:"
            elif turn == player2:
                mark = ":o2:"
            if 0 < pos < 10 and board[pos - 1] == ":white_large_square:" :
                board[pos - 1] = mark
                count += 1

                # print the board
                line = ""
                for x in range(len(board)):
                    if x == 2 or x == 5 or x == 8:
                        line += " " + board[x]
                        await ctx.send(line)
                        line = ""
                    else:
                        line += " " + board[x]

                checkWinner(winningConditions, mark)
                print(count)
                if gameOver == True:
                    await ctx.send(mark + " " "won the game!")
                elif count >= 9:
                    gameOver = True
                    await ctx.send("It's a tie!")



                                #switch turns
                if turn == player1:
                    turn = player2
                elif turn == player2:
                    turn = player1
            else:
                await ctx.send('''Nutze bitte nur Zahlen von 1-9 und die noch nicht belegt sind. \n
                please use only numbers from 1-9 and wich are not used jet''')
        else:
            await ctx.send('''Du bist noch nicht dran bitte warte kurz. \n
            its not ur turn please wait.''')
    else:
        await ctx.send('''Starte bitte ein neues Spiel mit $ttt. \n
        start a new game with $ttt''')


def checkWinner(winningConditions, mark):
    global gameOver
    for condition in winningConditions:
        if board[condition[0]] == mark and board[condition[1]] == mark and board[condition[2]] == mark:
            gameOver = True

@ttt.error
async def ttt_error(ctx, error):
    print(error)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('''Bitte makiere die Person mit der du spielen willst. \n
        Please tag the person you want to play with''')

    elif isinstance(error, commands.BadArgument):
        await ctx.send('''Bitte ping die Person an mit der du spielen willst. \n
        Please tag the person you want to play with''')

@place.error
async def place_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('''Bitte schreib die Position  wo du dein Marker hinsetzten willst. \n 
        Please write the position where ur marker should be''')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('''Bitte schreib nur 1 Zahl und ganze Zahlen. \n
        please write only 1 number and full numbers''')

                    #Münzenwurf

@client.command()
async def coinflip(ctx):
    bid = ctx.message.content.split(' ')[1]
    bid_param = -3
    if bid.lower() == "tail":
        bid_param = -1
    elif bid.lower() == "head":
        bid_param = -2
    else:
        try:
            bid_param = int(bid)
        except:
            bid_param = -3
    if bid_param == -3:
        await ctx.channel.send('wrong entry')
        return
    result = random.randint(0,36)
    if bid_param == -1:
        won = result%2 == 0 and not result == 0
    elif bid_param == -2:
        won = result%2 == 1
    else:
        won = result == bid_param
    if result%2 == 0:
        diedatei = open("Head_Coin.png", "rb")
        fp = io.BytesIO(diedatei.read())
        await ctx.send(file=discord.File(fp, "Head_Coin.png"))
        diedatei.close()
    else:
        diedatei = open("140px-1_euro_coin_Eu_serie_1.png", "rb")
        fp = io.BytesIO(diedatei.read())
        await ctx.send(file=discord.File(fp, "140px-1_euro_coin_Eu_serie_1.png"))
        diedatei.close()

    #if won:
        #await ctx.channel.send('$$$You won but it was luck$$$')
    #else:
        #await ctx.channel.send('You Lost XD be better next Time')


        #await ctx.channel.send(f"You got :) <@{ctx.message.author.id}>")

                        #Roulette

@client.command()
async def roulette(ctx):
    bid = ctx.message.content.split(' ')[1]
    bid_param = -3
    if bid.lower() == "red":
        bid_param = -1
    elif bid.lower() == "black":
        bid_param = -2
    else:
        try:
            bid_param = int(bid)
        except:
            bid_param = -3
    if bid_param == -3:
        await ctx.channel.send('wrong entry')
        return
    result = random.randint(0,36)
    if bid_param == -1:
        won = result%2 == 0 and not result == 0
    elif bid_param == -2:
        won = result%2 == 1
    else:
        won = result == bid_param
    if result % 2 == 0:
        await ctx.channel.send('$$$ Du hast gewonnen!!! $$$')

    else:
        await ctx.channel.send('Leider verloren :(')

                    #Help

@client.command()
async def helpDE(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''Hier sind alle Commands die man nutzten kann wenn man Hilfe braucht \n
                        $musicHelp \n
                        $rouletteHelp \n
                        $tttHelp \n 
                        $pingHelp \n
                        $helpDE \n
                        $helpEN \n
                        $bcHelp \n
                        $coinHelp \n
                        $ppHelp \n
                        $adminHelp \n
                        $createdHelp \n
                        $dmHelp \n
                        $avatarHelp \n
                        $memeHelp \n
                        $info \n
                        $whoisHelp \n
                        $joke \n
                        Wenn das alles nicht gehen sollte schreibt <@488378492396765205> an ''')

    embed.title = ':loudspeaker:HelpDE:loudspeaker:'
    await ctx.send(embed=embed)


@client.command()
async def helpEN(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''These are all commands for the bot \n
                        $musicHelp \n
                        $rouletteHelp \n
                        $tttHelp \n 
                        $pingHelp \n
                        $helpDE \n
                        $helpEN \n
                        $bcHelp \n                    
                        $coinHelp \n
                        $ppHelp \n
                        $adminHelp \n
                        $createdHelp \n
                        $dmHelp \n
                        $avatarHelp \n
                        $memeHelp \n
                        $info \n
                        $whoisHelp \n
                        $joke \n
                        If this don't work ask <@488378492396765205> for help''')

    embed.title = ':loudspeaker:HelpEN:loudspeaker:'
    await ctx.send(embed=embed)



@client.command()
async def musicHelp (ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description =('''Schreibe $join um den Bot in den voicechannel einzuladen. $play und dann ein Songname oder Link. $stop um den Song zu stoppen $resume um das gestoppte Lied wieder zu spielen und $queue um deine queue zu sehen.Schreibe $nowplaying um den song namen zu sehen der gerade gespielt wird, schreibe $loop um dein song in einem loop zu spielen. Nutze $lyrics um die Lyrics per Link zu bekommen \n
    Write $join to invite the bot into the voicechannel. $play and then a song name or link. $stop to stop the song $resume to play the stopped song again and $queue to see your queue.Write  $nowplaying to see the song name being played, write  $loop to play your song in a loop. Use $lyrics to get the lyrics per link''')
    embed.title = ':loudspeaker:Music:loudspeaker:'
    await ctx.send(embed=embed)


@client.command()
async def rouletteHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''Schreibe $roulette und red oder black um anzufangen also zb. $roulette black. \n
    Write $roulette and red or black to get started and for example $roulette black.''')
    embed.title = ':game_die:Roulette:game_die:'
    await ctx.send(embed=embed)


@client.command()
async def tttHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''Schreibe $ttt und makiere mit @ die Person mit der du spielen willst. Um zu platzieren nutzte $place und den Platzt. \n
    Write $ttt and tag the person you want to play with. Use $place and the number of the field you want to place.''')
    embed.title = ':o2:TicTacToe:regional_indicator_x:'
    await ctx.send(embed=embed)


@client.command()
async def pingHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''Nutze $ping um den Ping des Bot anzuzeigen lassen. \n
    Use $ping to display the ping from the bot.''')
    embed.title = ':ping_pong: Ping:ping_pong: '
    await ctx.send(embed=embed)


@client.command()
async def bcHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''Wenn du einen Bot-command Channel haben willst nutzte $bc um einen zu erstellen. \n
    If you need a Bot-command Channel use $bc to create one.''')
    embed.title = ':robot:Bot-Channel:robot:'
    await ctx.send(embed=embed)


@client.command()
async def coinHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''Nutzte $coinflip mit tail oder head um das Spiel zu starten. \n
    Use $coinflip tail or head to start the game''')
    embed.title = ':moneybag:Coinflip:moneybag:'
    await ctx.send(embed=embed)


@client.command()
async def ppHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''Nutze $pp und deine pp größe wird angezeigt. \n
    Use $pp and your pp size will be displayed.''')
    embed.title = ':eggplant:PP Size:eggplant:'
    await ctx.send(embed=embed)


@client.command()
async def adminHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''The admin commands are: \n
    $kick @user \n
    $ban @user \n
    $unban @user \n
    $clear number \n
    $timeout @user time reason \n
    $untimeout @user reason \n''')

    embed.title = ':nerd:Admin Commands:nerd:'
    await ctx.send(embed=embed)


@client.command()
async def createdHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''Nutze $created um zu sehen wann dein Account erstellt wurde. \n Use $created to see when your account was created.''')
    embed.title = ':loudspeaker:Created:loudspeaker:'
    await ctx.send(embed=embed)

@client.command()
async def dmHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = (
        '''Nutze $dm @user und dann deine Nachricht um eine Nachricht an den User zu senden. \n Use $dm @user and then your message to send a message to the user.''')
    embed.title = ':loudspeaker:Direct Message:loudspeaker:'
    await ctx.send(embed=embed)

@client.command()
async def avatarHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = (
        '''Nutze $avatar @user um das Profilbild des Users zu sehen. \n Use $avatar @user to see the profile picture of the user.''')
    embed.title = ':lav_pet:Avatar:lav_pet:'
    await ctx.send(embed=embed)

@client.command()
async def memeHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''Nutze $meme um ein Meme zu sehen. \n Use $meme to see a meme.''')
    embed.title = ':joy:Meme:joy:'
    await ctx.send(embed=embed)

@client.command()
async def whoisHelp(ctx):
    embed = discord.Embed()
    embed.color = random.randint(0x000000, 0x999999)
    embed.description = ('''Nutze $whois @user um die Informationen des Users zu sehen. \n Use $whois @user to see the information of the user.''')
    embed.title = ':question:Whois:grey_question:'
    await ctx.send(embed=embed)

    #Ayuwoki Bild & Gif

@client.command()
async def ayuwoki(ctx):
        diedatei = open("ayuwoki.jpeg.jpg", "rb")
        fp = io.BytesIO(diedatei.read())
        await ctx.send(file=discord.File(fp, "ayuwoki.jpeg.jpg"))
        diedatei.close()

@client.command()
async def tanzwoki(ctx):
        diedatei = open("tanzwoki.gif", "rb")
        fp = io.BytesIO(diedatei.read())
        await ctx.send(file=discord.File(fp, "tanzwoki.gif"))
        diedatei.close()

                            #Ping

@client.command(aliases = ['p', 'q'])
async def ping(ctx, arg=None):
    if arg == "pong":
        await ctx.send("Nice Job, you ponged ur self")

    else:
        await ctx.send(f'Pong:ping_pong:! Here is my Ping ik its trash lol: {round(client.latency * 1000)}ms <@{ctx.message.author.id}>')


@client.command()
async def pp(ctx, member: discord.Member = None):
    ppSize = ["8D", "8=D", "8==D", "8===D", "8====D", "8=====D", "8======D", "8=======D", "8========D",
              "8=========D", "8==========D", "8===========D", "8============D", "8=============D"]
    #await ctx.send(f'<@{ctx.message.author.id}> pp size is: {random.choice(ppSize)}')

    if member:
        await ctx.send(f'<@{member.id}>\'s pp size is: {random.choice(ppSize)}')

    else:
        await ctx.send(f'<@{ctx.message.author.id}>\'s pp size is: {random.choice(ppSize)}')

# if the command is wrong it will send a message to the user

@client.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f'Command not found use `$helpDE or $helpEN`, <@{ctx.message.author.id}>')

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'Please enter all required arguments, <@{ctx.message.author.id}>')

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f'You are missing the permissions to use this command, <@{ctx.message.author.id}>')

    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f'I am missing the permissions to use this command, <@{ctx.message.author.id}>')

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f'This command is on cooldown, <@{ctx.message.author.id}>')

    if isinstance(error, commands.MissingRole):
        await ctx.send(f'You are missing the role to use this command, <@{ctx.message.author.id}>')

    if isinstance(error, commands.BotMissingRole):
        await ctx.send(f'I am missing the role to use this command, <@{ctx.message.author.id}>')

# make a bann command

@client.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'Banned {member.mention}')

#create a command to unban users with their id

@client.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, id: int):
    user = await client.fetch_user(id)
    await ctx.guild.unban(user)
    await ctx.send(f'Unbanned {user.mention}')

# make a kick command

@client.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'Kicked {member.mention}')


#erstelle einen timeout command wo ich die zeit angeben kann und lass den user nichts tun dürfen für die zeit und zeige dem user an wie lange er noch getimedout ist

@client.command()
@commands.has_permissions(manage_messages=True)
async def timeout(ctx, member: nextcord.Member, time, *, reason):
    time = humanfriendly.parse_timespan(time)
    await member.edit(timeout=nextcord.utils.utcnow() + datetime.timedelta(seconds=time))
    await ctx.send(f"{member.mention} has been timeouted because {reason}")
    await member.send(f"You have been timeouted for {time} because {reason}")


@client.command()
@commands.has_permissions(manage_messages=True)
async def untimeout(ctx, member: nextcord.Member, *, reason):
    await member.edit(timeout=None)
    await ctx.send(f"{member.mention} has been untimeouted because {reason}")
    await member.send(f"You have been untimeouted because {reason}")

# make a clear command

@client.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount=5):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f'Cleared {amount} messages')

DISCORD_EPOCH = 1420070400000

# Converts a snowflake ID string into a unix timestamp
def convert_snowflake(snowflake):
    # https://discord.com/developers/docs/reference#snowflakes
    milliseconds = snowflake >> 22
    return milliseconds + DISCORD_EPOCH


@client.command()
async def created(ctx, member: discord.Member = None):
    if member:
        await ctx.send(f'<@{member.id}> created his account at: {datetime.datetime.fromtimestamp(int(convert_snowflake(member.id) / 1000))}')

    else:
        await ctx.send(f'<@{ctx.message.author.id}> created your account at: {datetime.datetime.fromtimestamp(int(convert_snowflake(ctx.message.author.id) / 1000))}')


@client.command()
async def gayrate(ctx, member: discord.Member = None):
    if member:
        await ctx.send(f'<@{member.id}> you are {random.randint(0, 100)}% gay')

    else:
        await ctx.send(f'<@{ctx.message.author.id}> you are {random.randint(0, 100)}% gay')


@client.command()
async def feet(ctx):
    await ctx.send(f'https://tenor.com/view/bloxnuts-feet-gif-21235154')


@client.command()
async def dm(ctx, member: discord.Member = None, *, message):
    await member.send(f'{message}')
    await ctx.send(f'Your message has been sent to {member.mention}')


@client.event
async def on_message(message):
    print("--------------------")
    print(f'{message.channel}: {message.author}: {message.author.name}: {message.content}')

    await client.process_commands(message)

@client.command()
async def avatar(ctx, *, member: discord.Member = None):
    if member == None:
        member = ctx.message.author

    memberAvatar = member.display_avatar

    embed = discord.Embed(title=f"{member.name}'s avatar")
    embed.color = random.randint(0x000000, 0x999999)
    embed.set_image(url=memberAvatar)
    await ctx.send(embed=embed)


@client.command()
async def meme(ctx):
    async with aiohttp.ClientSession() as cs:
        async with cs.get('https://www.reddit.com/r/memes/new.json?sort=hot') as r:
            res = await r.json()
            await ctx.send(res['data']['children'][random.randint(0, 25)]['data']['url'])


@client.command()
async def allCommands(ctx):
    embed = discord.Embed(title="All commands", description="All commands of the bot", color=0x00ff00)
    embed.color = random.randint(0x000000, 0x999999)
    embed.add_field(name="$help", value="Shows this message", inline=True)
    embed.add_field(name="$gayrate", value="Shows how gay you are", inline=True)
    embed.add_field(name="$avatar", value="Shows the avatr of the tagged user", inline=True)
    embed.add_field(name="$ayuwoki", value="Sends a picture of ayuwoki", inline=True)
    embed.add_field(name="$coinflip", value="Basic head or tail game", inline=True)
    embed.add_field(name="$created", value="Shows when you created you account or the tagged person", inline=True)
    embed.add_field(name="$dm", value="Direct the tagged person", inline=True)
    embed.add_field(name="$feet", value="Sends a nice gif", inline=True)
    embed.add_field(name="$meme", value="Sends a random meme", inline=True)
    embed.add_field(name="$ping", value="Shows the ping of the bot", inline=True)
    embed.add_field(name="$panel", value="Shortcuts for music commands", inline=True)
    embed.add_field(name="TicTacToe commands: \n $ttt @user \n $place", value="Self explained", inline=True)
    embed.add_field(name="$pp", value="Shows your pp size or from the tagged person", inline=True)
    embed.add_field(name="$roulette black or red", value="Basic roulette game", inline=True)
    embed.add_field(name="$tanzwoki", value="Shows a Ayuwoki dance video", inline=True)
    embed.add_field(name="$helpDE and $helpEN", value="Help for all the commands in english and german", inline=True)
    embed.add_field(name="$info", value="Sends informations about the bot", inline=True)
    embed.add_field(name="$whois", value="Sends informations about the tagged user", inline=True)
    embed.add_field(name="$joke", value="Tells a joke", inline=True)
    embed.add_field(name="Music commands: \n $leave \n $loop \n $lyrics \n $nowplaying \n $pause \n $play \n $queue \n $resume \n $skip \n $stop \n $volume", value="All Music commands /self explained)", inline=True)
    embed.add_field(name="Moderation commands: \n $ban \n $clear \n $kick \n $timeout \n $untimeout", value="All Moderation commands (self explained)", inline=True)

    await ctx.send(embed=embed)


@client.command()
async def info(ctx):
    embed = discord.Embed(title="Info", description="Info about the bot", color=0x00ff00)
    embed.color = random.randint(0x000000, 0x999999)
    embed.add_field(name="Bot name", value="DontHaveAName", inline=True)
    embed.add_field(name="Bot owner", value="FRITZ#4221", inline=True)
    embed.add_field(name="Bot version", value="1.0", inline=True)
    embed.add_field(name="Bot language", value="Python", inline=True)
    embed.add_field(name="Bot library", value="Nextcord", inline=True)
    embed.add_field(name="Bot server count", value=f"{len(client.guilds)}", inline=True)
    embed.add_field(name="Bot ping", value=f"{round(client.latency * 1000)}ms", inline=True)
    embed.add_field(name="Bot invite", value="https://discord.com/oauth2/authorize?client_id=845662277126717461&permissions=8&scope=bot", inline=True)
    embed.add_field(name="Bot support server", value="https://discord.gg/aVKAmPphnF", inline=True)
    embed.add_field(name="Bot website", value="https://fritzist.tk", inline=True)
    embed.add_field(name="Bot github", value="https://github.com/Fritzist", inline=True)

    await ctx.send(embed=embed)

@client.command()
async def whois(ctx, member: discord.Member):
    roles = [role for role in member.roles]

    embed = discord.Embed(colour=member.color, timestamp=ctx.message.created_at)
    embed.set_author(name=f"User Info - {member}")
    embed.set_thumbnail(url=member.display_avatar)
    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar)
    embed.add_field(name="ID:", value=member.id)
    embed.add_field(name="Guild name:", value=member.display_name)
    embed.add_field(name="Created at:", value=member.created_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"))
    embed.add_field(name="Joined at:", value=member.joined_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"))
    embed.add_field(name=f"Roles ({len(roles)})", value=" ".join([role.mention for role in roles]))
    embed.add_field(name="Top role:", value=member.top_role.mention)
    embed.add_field(name="Bot?", value=member.bot)
    await ctx.send(embed=embed)


@client.command()
async def joke(ctx):
    response = requests.get("https://official-joke-api.appspot.com/random_joke")
    json_data = json.loads(response.text)
    setup = json_data['setup']
    punchline = json_data['punchline']
    await ctx.send(setup)
    await asyncio.sleep(3)
    await ctx.send(punchline)


with open("config.json", "rb") as f:
    config = json.loads(f.read().decode("utf-8"))

client.run(config["token"])
