# bot.py

import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# --- Bot Setup ---
# Define the intents your bot needs
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.voice_states = True     # Required for voice state info

# Create a bot instance with a command prefix and intents
bot = commands.Bot(command_prefix='!', intents=intents)

# --- Global Queue ---
# This list will hold the songs to be played
song_queue = []

# --- YouTube-DL Options ---
# We REMOVED 'noplaylist': 'True' to allow playlists
# --- YouTube-DL Options ---
# --- YouTube-DL Options ---
# --- YouTube-DL Options ---
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtoconsole': True,  # Changed to True so we can see the login code!
    'quiet': False,        # Changed to False so we can see the login code!
    'no_warnings': True,
    'default_search': 'scsearch',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt',
  
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- Helper Function to Play Next Song ---

async def play_next(ctx):
    """
    Plays the next song in the global queue.
    This is called by `play` and by `on_song_end`.
    """
    if song_queue:
        voice_client = ctx.guild.voice_client
        if not voice_client:
            # Bot might have been disconnected
            song_queue.clear()
            return
        
        # Get the next song's data
        data = song_queue.pop(0)
        url = data['url']
        title = data['title']
        
        # Create the player
        player = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        
        # Start playing. The 'after' callback ensures this function runs again
        # when the song is over, creating the queue loop.
        voice_client.play(player, after=lambda e: on_song_end(e, ctx))
        
        await ctx.send(f'🎶 **Now playing:** {title}')
    else:
        # Queue is empty
        await ctx.send("The queue is now empty.")

def on_song_end(error, ctx):
    """
    Callback function for when a song finishes playing.
    It safely schedules `play_next` to run in the bot's event loop.
    """
    if error:
        print(f'Player error: {error}')
    
    # We need to run an async function (play_next) from this
    # synchronous callback.
    asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)


# --- Bot Events ---
@bot.event
async def on_ready():
    """Prints a message to the console when the bot is online and ready."""
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')

# --- Bot Commands ---
@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    """Joins the voice channel of the user who issued the command."""
    if not ctx.author.voice:
        await ctx.send(f"{ctx.author.name} is not connected to a voice channel.")
        return
    else:
        channel = ctx.author.voice.channel
        # Check if already connected
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"Joined **{channel}**")

@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    """Leaves the current voice channel, stops music, and clears the queue."""
    global song_queue
    voice_client = ctx.message.guild.voice_client
    
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        song_queue.clear() # Clear the queue
        await ctx.send("Left the voice channel and cleared the queue.")
    else:
        await ctx.send("I am not connected to a voice channel.")

@bot.command(name='play', help='To play a song or playlist from YouTube, Spotify, JioSaavn, etc.')
async def play(ctx, *, search: str):
    """
    Plays from a URL (YouTube, Spotify, JioSaavn, etc.) or searches YouTube.
    If nothing is playing, it starts the queue.
    """
    global song_queue
    voice_client = ctx.guild.voice_client

    # Ensure bot is in a voice channel
    if not voice_client:
        if ctx.author.voice:
            await join(ctx) # Use the join command
            voice_client = ctx.guild.voice_client
        else:
            await ctx.send("You are not in a voice channel, and I'm not sure where to go!")
            return

    await ctx.send(f"🔎 **Processing:** `{search}`...")

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            
            # --- THIS IS THE NEW, SIMPLIFIED LOGIC ---
            # We just pass the 'search' string directly.
            # - If it's a URL (YouTube, JioSaavn, SoundCloud), it extracts it.
            # - If it's a Spotify URL, it uses 'default_search' (ytsearch) to find it.
            # - If it's a search term, it uses 'default_search' (ytsearch).
            info = ydl.extract_info(search, download=False)
            
            playlist_entries = None 

            if 'entries' in info:
                # This means it's a PLAYLIST or a SEARCH RESULT
                
                if not info['entries']:
                    await ctx.send("Could not find any results for that search.")
                    return

                # Check if it's a playlist
                if info.get('_type') == 'playlist' or info['entries'][0].get('_type') == 'playlist':
                    if info.get('_type') == 'playlist':
                        playlist_entries = info['entries']
                        playlist_title = info.get('title', 'Unnamed Playlist')
                    else: 
                        playlist_entries = info['entries'][0]['entries']
                        playlist_title = info['entries'][0].get('title', 'Unnamed Playlist')
                    await ctx.send(f"Adding playlist **{playlist_title}** to the queue...")

                else: 
                    # It's a list of SEARCH results, just add the first one
                    first_video = info['entries'][0] # This is safe now
                    song_queue.append({
                        'url': first_video['url'], 
                        'title': first_video.get('title', 'Unknown Title')
                    })
                    await ctx.send(f"Added **{first_video.get('title')}** to the queue.")

                # If we found playlist entries, add them
                if playlist_entries:
                    for entry in playlist_entries:
                        if entry.get('url'): 
                            song_queue.append({
                                'url': entry['url'], 
                                'title': entry.get('title', 'Unknown Title')
                            })
                    await ctx.send(f"Added **{len(playlist_entries)}** songs to the queue.")

            else:
                # It's a single video (from a direct URL like JioSaavn or YouTube)
                song_queue.append({
                    'url': info['url'], 
                    'title': info.get('title', 'Unknown Title')
                })
                await ctx.send(f"Added **{info.get('title')}** to the queue.")

        # If the bot isn't already playing, start playing the queue
        if not voice_client.is_playing() and not voice_client.is_paused():
            await play_next(ctx)

    except Exception as e:
        await ctx.send("An error occurred. It might be an age-restricted, private, or unsupported link.")
        print(f"Error in play command: {e}")
        
@bot.command(name='pause', help='Pauses the current song')
async def pause(ctx):
    """Pauses the currently playing audio."""
    voice_client = ctx.message.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Paused ⏸️")
    else:
        await ctx.send("I'm not playing anything right now.")

@bot.command(name='resume', help='Resumes the paused song')
async def resume(ctx):
    """Resumes the paused audio."""
    voice_client = ctx.message.guild.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Resuming ▶️")
    else:
        await ctx.send("I'm not paused.")

@bot.command(name='stop', help='Stops the music and clears the queue')
async def stop(ctx):
    """Stops playback and clears the entire song queue."""
    global song_queue
    voice_client = ctx.message.guild.voice_client
    
    if voice_client:
        song_queue.clear()
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
            await ctx.send("Stopped playback and cleared the queue. ⏹️")
        else:
            await ctx.send("Queue cleared.")
    else:
        await ctx.send("I'm not in a voice channel.")
        
@bot.command(name='skip', aliases=['forward'], help='Skips to the next song in the queue')
async def skip(ctx):
    """Skips the current song and plays the next one."""
    global song_queue
    voice_client = ctx.message.guild.voice_client
    
    if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
        if song_queue:
            voice_client.stop() # This will trigger on_song_end -> play_next
            await ctx.send("Skipped to the next song ⏭️")
        else:
            voice_client.stop()
            await ctx.send("This is the last song. Stopping playback.")
    else:
        await ctx.send("I'm not playing anything to skip.")

@bot.command(name='previous', aliases=['back', 'backward'], help='Goes back to the previous song')
async def previous(ctx):
    """Plays the previously played song."""
    global song_queue, played_songs, current_song_data
    voice_client = ctx.message.guild.voice_client
    
    if not voice_client:
        await ctx.send("I'm not in a voice channel.")
        return
        
    if not played_songs:
        await ctx.send("There is no song history to go back to.")
        return

    # Get the song from history
    prev_song = played_songs.pop(0) # Get most recent song
    
    # Put the current song back at the front of the queue
    if current_song_data:
        song_queue.insert(0, current_song_data)
    
    # Put the previous song at the front of the queue
    song_queue.insert(0, prev_song)
    
    # We set current_song_data to None so play_next doesn't add a duplicate
    current_song_data = None 
    
    # Stop the current song, which will trigger play_next
    voice_client.stop()
    await ctx.send(f"Going back to: **{prev_song['title']}** ⏪")        

@bot.command(name='clear', aliases=['purge'], help='Deletes a specified number of messages')
@commands.has_permissions(manage_messages=True) # Check if the user has permission
async def clear(ctx, amount: int):
    """Deletes a given number of messages from the channel."""
    if amount <= 0:
        await ctx.send("Please enter a positive number.")
        return
        
    # We add 1 to the amount to also delete the command message itself
    limit = amount + 1
    
    try:
        await ctx.channel.purge(limit=limit)
        await ctx.send(f"Deleted {amount} messages.", delete_after=5) # Send a confirmation
    except discord.Forbidden:
        await ctx.send("I don't have permission to delete messages. Please check my 'Manage Messages' permission.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        print(f"Error in clear command: {e}")

@clear.error
async def clear_error(ctx, error):
    """Error handler for the clear command."""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You need to specify an amount. Usage: `!clear [number]`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Please enter a valid number.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
        
@bot.command(name='queue', aliases=['q'], help='Shows the current song queue')
async def queue(ctx):
    """Displays the current song queue."""
    global song_queue, current_song_data
    
    # Create the initial embed
    embed = discord.Embed(
        title="🎶 Song Queue 🎶",
        color=discord.Color.blue()
    )
    
    # Add "Now Playing" field
    if current_song_data:
        embed.add_field(
            name="**Now Playing**", 
            value=f"**[{current_song_data['title']}]({current_song_data['url']})**", 
            inline=False
        )
    else:
        embed.add_field(
            name="**Now Playing**", 
            value="Nothing is currently playing.", 
            inline=False
        )
        
    # Add "Up Next" field
    if not song_queue:
        embed.add_field(
            name="**Up Next**", 
            value="The queue is empty!", 
            inline=False
        )
    else:
        # Create a formatted string for the queue list
        queue_list = ""
        # Show a max of 10 songs to prevent spam
        for i, song in enumerate(song_queue[:10]):
            queue_list += f"`{i+1}.` [{song['title']}]({song['url']})\n"
            
        if len(song_queue) > 10:
            queue_list += f"\n...and {len(song_queue) - 10} more."
            
        embed.add_field(name="**Up Next**", value=queue_list, inline=False)
    
    # Add a footer showing the total number of songs
    total_songs = len(song_queue) + (1 if current_song_data else 0)
    embed.set_footer(text=f"Total songs in queue: {total_songs}")
    
    await ctx.send(embed=embed)        

# --- Run the Bot ---
bot.run(TOKEN)





