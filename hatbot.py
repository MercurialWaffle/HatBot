import asyncio
import discord
import random
import time
import copy
from discord import Game
from discord.ext.commands import Bot

#The token is used to connect to the Discord API; I've censored it for privacy reasons.
TOKEN = '-----------------------------------------------------------'

#The bot will respond to any message that starts with a "!".
BOT_PREFIX = ("!")
client = Bot(command_prefix=BOT_PREFIX)

#The Game class stores all of the game data for a single server.
class Game:
    def __init__(self, guild):
        #The server the game is being played in.  (Ensures one game per server.)
        self.guild = guild
        
        #Current mode (SETUP, ADDWORDS, INGAME, or ENDGAME)
        self.MODE = "SETUP"

        #Dictionary that maps players to their private channels.
        self.members = {}
        
        #Number of words entered per person.
        self.wpp = 4
        
        #Dictionary that maps players to the player they give clues to.
        self.giving = {}
        
        #Dictionary that maps players to the player they get clues from.
        self.getting = {}
        
        #List of words in the hat
        self.wordList = []
        
        #List of players who have entered words
        self.entered_words = []
        
        #List of players in random order, to determine gameplay order
        self.playerOrder = []
        
        #Current clue-giver
        self.curPlayer = 0
        
        #Words yet unplayed (subset of wordList, replenished at end of round)
        self.unplayedWords = []
        
        #Round (0 = no game, 1, 2, or 3)
        self.curRound = 0
        
        #Indicates which player's turn it is, or False if it's nobody's turn
        self.curTurn = False
        
        #The word that's currently being guessed.
        self.curWord = None

#This dictionary keeps track of which servers have active games.
GAMES = {}
        
#Given a list of players, match each player to another to give clues to and another to get clues from.
#If there are an even number of players, the giver and getter are the same.  This creats two-pereson teams.
#If there are an odd number of players, each player gets from the player behind them and gives to the player in front of them.
def match_players(players):
    giving = {}
    getting = {}
    random.shuffle(players)
    n = len(players)
    if n % 2 == 0:
        for i in range(0, n, 2):
            giving[players[i]] = players[i+1]
            giving[players[i+1]] = players[i]
            getting[players[i]] = players[i+1]
            getting[players[i+1]] = players[i]
    else:
        for i in range(n):
            giving[players[i]] = players[(i + 1) % n]
            getting[players[i]] = players[(i - 1) % n]
    return giving, getting

#Start the setup process.  Commands won't work until !start is called.
@client.command()
async def start(ctx):
    
    global GAMES
    game = Game(ctx.guild)
    GAMES[ctx.guild] = game
    await ctx.channel.send("Welcome to Hat!")
    await ctx.channel.send("Join using the !join command. You can also use the !wpp command to set the number of words per person (defaults to 4). Type !done when everyone has joined.")

#Adds a player to the member dictionary.  Doesn't actually create their private channel yet.  Only works in setup mode.
@client.command()
async def join(ctx):
    
    global GAMES
    game = GAMES[ctx.guild]
    if not game.MODE == "SETUP":
        await ctx.channel.send("That command is not valid.")
        return
    game.members[ctx.message.author] = None
    await ctx.channel.send("{} joined!".format(ctx.message.author.display_name))

#Sets the number of words per person.  Only works in setup mode.
@client.command()
async def wpp(ctx, words):
    
    global GAMES
    game = GAMES[ctx.guild]
    if not game.MODE == "SETUP":
        await ctx.channel.send("That command is not valid.")
        return
    game.wpp = int(words)
    await ctx.channel.send("We'll play with {} words per person.".format(game.wpp))

#Finishes the setup process and makes each player's private channel.  Switches to word-adding mode.  Only works in setup mode.
@client.command()
async def done(ctx):
    
    global GAMES
    game = GAMES[ctx.guild]
    if not game.MODE == "SETUP":
        await ctx.channel.send("That command is not valid.")
        return
    game.MODE = "ADDWORDS"
    await ctx.channel.send("Great!  There are {} players: {}".format(len(game.members), ", ".join(list(map(lambda x: x.display_name, game.members)))))
    
    guild = ctx.guild
    for player in game.members:
        print(player.display_name)
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), guild.me: discord.PermissionOverwrite(read_messages=True), player: discord.PermissionOverwrite(read_messages=True)}
        game.members[player] = await guild.create_text_channel(player.display_name, overwrites=overwrites)

    game.giving, game.getting = match_players(list(game.members.keys()))
        
    await ctx.channel.send("Each player now has their own private text channel.  Please go there for more instructions.")
    for player in game.members:
        await game.members[player].send("Welcome to your private text channel, **{}**!".format(player.display_name))
        await game.members[player].send("You will be giving clues to **{}**".format(game.giving[player].display_name))
        await game.members[player].send("You will be receiving clues from **{}**".format(game.getting[player].display_name))
        await game.members[player].send("Please use the !words command to enter {} space-separated words.".format(game.wpp))

#Collects space-seperated words from players. Won't work unless the right amount of words are entered.  Only works in word-adding mode.
#Once all players have entered words, triggers the game to start.
@client.command()
async def words(ctx):
    
    global GAMES
    game = GAMES[ctx.guild]
    if not game.MODE == "ADDWORDS":
        await ctx.channel.send("That command is not valid.")
        return
    
    words = ctx.message.content[7:].split()
    if ctx.message.author in game.entered_words:
        await ctx.channel.send("You already entered words!")
        return
    
    if len(words) != game.wpp:
        await ctx.channel.send("Please enter exactly {} words.".format(game.wpp))
        return
    
    game.entered_words.append(ctx.message.author)
    game.wordList.extend(words)
    await ctx.channel.send("The words {} have been added to the hat.".format(", ".join(words)))
    if len(game.entered_words) == len(game.members):
        await start_game(ctx.guild)

#Sets up and starts a new round, then triggers the turn loop.
#If past round 3, end the game.
async def start_game(guild):

    global GAMES
    game = GAMES[guild]
    game.MODE = "INGAME"
    game.curRound += 1
    
    if game.curRound > 3:
        await end_game(guild)
        return
    
    for channel in guild.text_channels:
        if not channel.name == "general":
            await channel.send("Beginning round {}".format(game.curRound))
            
    game.unplayedWords = copy.copy(game.wordList)
    if game.curRound == 1:
        game.playerOrder = list(game.members.keys())
        random.shuffle(game.playerOrder)
    game.curPlayer = (game.curPlayer + 1) % len(game.playerOrder)
    await run_turn(guild)

#Handles the turn loop and lets players know whose turn it is.
async def run_turn(guild):

    global GAMES
    game = GAMES[guild]

    giver = game.playerOrder[game.curPlayer]
    await game.members[giver].send("It's your turn!  You are giving clues to **{}**.".format(game.giving[giver].display_name))
    await game.members[giver].send("Type !begin to start recieving words and start your 30-second timer.  Once **{}** guesses the word, type !n to get the next word.  Or, type !skip to skip a word.".format(game.giving[giver].display_name))
    await game.members[game.giving[giver]].send("Get ready! **{}** is giving you clues.".format(giver.display_name))

#Begins the players turn and starts their 30-second timer.  Only works in in-game mode, and if the caller is the current player.
@client.command()
async def begin(ctx):

    global GAMES
    game = GAMES[ctx.guild]
    
    if not game.MODE == "INGAME":
        await ctx.channel.send("That command is not valid.")
        return
    
    if not game.playerOrder[game.curPlayer] == ctx.message.author:
        await ctx.channel.send("It's not your turn!")
        return
    
    game.curTurn = game.playerOrder[game.curPlayer]
    timeLeft = 30
    timer = await ctx.channel.send("Time Remaining: 30")
    game.curWord = random.choice(game.unplayedWords)
    game.unplayedWords.remove(game.curWord)
    
    await ctx.channel.send("First word: {}".format(game.curWord))
    while timeLeft > 0:
        time.sleep(1)
        timeLeft -= 1
        await timer.edit(content="Time Remaining: {}".format(timeLeft))
        if not game.curTurn:
            return
        
    await ctx.channel.send("Time's up!")
    game.curTurn = False
    game.unplayedWords.append(game.curWord)
    game.curPlayer = (game.curPlayer + 1) % len(game.playerOrder)
    await run_turn(ctx.guild)

#Skips the current word.  If there is at least one unplayed word left, give a different word.  Only works in in-game mode, and the caller's turn is in progress.
@client.command()
async def skip(ctx):

    global GAMES
    game = GAMES[ctx.guild]
    
    if not game.MODE == "INGAME":
        await ctx.channel.send("That command is not valid.")
        return
    
    if not game.curTurn == ctx.message.author:
        await ctx.channel.send("It's not your turn!")
        return
    
    if len(game.unplayedWords) > 0:
        oldWord = game.curWord
        game.curWord = random.choice(game.unplayedWords)
        game.unplayedWords.remove(game.curWord)
        game.unplayedWords.append(oldWord)
    await ctx.channel.send("Next word: {}".format(game.curWord))

#Sends the next word.  If no words are left, trigger a new round. Only works in in-game mode, and the caller's turn is in progress.
@client.command()
async def n(ctx):

    global GAMEs
    game = GAMES[ctx.guild]
    
    if not game.MODE == "INGAME":
        await ctx.channel.send("That command is not valid.")
        return
    
    if not game.curTurn == ctx.message.author:
        await ctx.channel.send("It's not your turn!")
        return
    
    if len(game.unplayedWords) > 0:
        game.curWord = random.choice(game.unplayedWords)
        game.unplayedWords.remove(game.curWord)
        await ctx.channel.send("Next word: {}".format(game.curWord))
    else:
        game.curTurn = False
        for channel in ctx.guild.text_channels:
            if not channel.name == "general":
                await channel.send("End of round {}".format(game.curRound))  
        await start_game(ctx.guild)

#Handle the end of the game, and give options to play again.
async def end_game(guild):
    
    global GAMES
    game = GAMES[guild]
    game.MODE = "ENDGAME"
    game.wordList = []
    game.entered_words = []
    game.curRound = 0
    for channel in guild.text_channels:
            if channel.name == "general":
                await channel.send("The game is over!  To play another game with the same people, type !restart.  To end the game, type !finish.")  

#Restart the game with the same people and words per person.  Only works in end-game mode.
#To play with different people or words per person, you have to !finish and re-!start the game.
@client.command()
async def restart(ctx):

    global GAMES
    game = GAMES[ctx.guild]
    
    if not game.MODE == "ENDGAME":
        await ctx.channel.send("That command is not valid.")
        return
    
    game.giving, game.getting = match_players(list(game.members.keys()))
    game.MODE = "ADDWORDS"
    for player in game.members:
        await game.members[player].send("You will be giving clues to **{}**".format(game.giving[player].display_name))
        await game.members[player].send("You will be recieving clues from **{}**".format(game.getting[player].display_name))
        await game.members[player].send("Please use the !words command to enter {} space-seperated words.".format(game.wpp))
            
#Ends the game and cleans up (deletes all private channels).  Only works while the game is running.  Afterwards, have to use !start again to restart the game.   
@client.command()
async def finish(ctx):
    
    global GAMES
    game = GAMES[ctx.guild]
    
    if not game.MODE:
        await ctx.channel.send("That command is not valid.")
        return
    for channel in ctx.guild.text_channels:
        if not channel.name == "general":
            await channel.delete()
        else:
            await channel.send("Thanks for playing!")
    game.MODE = False
    del GAMES[ctx.guild]

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run(TOKEN)
