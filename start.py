import sys
import discord
from discord.ext import commands
import dotenv
import os
import googleauth
import logging
import asyncio
from logging.handlers import RotatingFileHandler
from termcolor import colored, cprint

intents = discord.Intents.default()
intents.message_content = True
global google_auth
dotenv.load_dotenv()
from googleapiclient.discovery import build, MutualTLSChannelError
from google.oauth2.credentials import Credentials

# setup logging
grey = "\x1b[38;20m"
yellow = "\x1b[33;20m"
red = "\x1b[31;20m"
bold_red = "\x1b[31;1m"
reset = "\x1b[0m"

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.INFO)

handler = RotatingFileHandler(
    filename='discord.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,
    backupCount=5,
)

date_format = '%Y-%m-%d %H:%M:%S'


formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', datefmt=date_format, style='{')

handler.setFormatter(formatter)
logger.addHandler(handler)

async def create_calendar_event(service, event: discord.ScheduledEvent):
    """Creates a google calendar event from a discord scheduled event

    Args:
        service (googleapiclient.discovery.Resource): the google calendar service
        event (discord.ScheduledEvent): the discord scheduled event to convert to a google calendar event

    Returns:
        result (Tuple[bool, Error or str]): a tuple of a boolean and an error object or None if unsuccessful, true if successful, 
        and the url to the google calendar event
    """
    try:
        result = (False, None)
        event_details = {
            "calendarId": "primary",
            "id": event.id,
            "summary": event.name,
            "location": event.location,
            "description": event.description,
            "start": {
                "dateTime": event.start_time.isoformat(),
                "timeZone": "UTC",
            },
        }
        if event.end_time is not None:
            print(f'end time for event: {event.end_time.isoformat()}')
            event_details["end"] = {
                "dateTime": event.end_time.isoformat(),
                "timeZone": "UTC",
            }
        else:
            event_details["endTimeUnspecified"] = True

        google_event = service.events().insert(calendarId="primary",
                                               body=event_details).execute()

        if google_event.get("htmlLink") is not None:
            result = (True, google_event)

        return result
    except Exception as err:
        return (None, str(err))

async def update_calendar_event(service, event: discord.ScheduledEvent):
    """Updates a google calendar event from a discord scheduled event

    Args: 
        service (googleapiclient.discovery.Resource): the google calendar service
        event (discord.ScheduledEvent): the discord scheduled event to convert to a google calendar event
    
    returns:
        result (Tuple[bool, Error or None]): a tuple of a boolean and an error object or None if successful
    """
    try:
        result = (False, None)
        event_details = {
            "calendarId": "primary",
            "id": event.id,
            "summary": event.name,
            "location": event.location,
            "description": event.description,
            "start": {
                "dateTime": event.start_time.isoformat(),
                "timeZone": "UTC",
            },
        }
        if event.end_time is not None:
            print(f'end time for event: {event.end_time.isoformat()}')
            event_details["end"] = {
                "dateTime": event.end_time.isoformat(),
                "timeZone": "UTC",
            }
        else:
            event_details["endTimeUnspecified"] = True

        google_event = service.events().update(calendarId="primary", eventId=str(event.id), body=event_details).execute()

        if google_event.get("htmlLink") is not None:
            result = (True, google_event) 
        return result

    except Exception as err:
        return (None, str(err))

async def add_user_to_calendar_event(service, event: discord.ScheduledEvent,
                                     member_id: str):
    """Adds a user to a google calendar event

    Args:
        service (googleapiclient.discovery.Resource): the google calendar service
        event (discord.ScheduledEvent): the discord scheduled event to convert to a google calendar event
        email (str): the email of the user to add to the event
    
    Returns:
        result (Tuple[bool, Error or None]): a tuple of a boolean and an error object or None if successful
    """
    try:
        user_emails = await google_auth.get_user_emails(event.guild.id)
        if user_emails is None:
            return user_emails
        member_email = user_emails[0].get(member_id)    
        if member_email is None:
            return (None, 'User has not added their email to the bot')

        cal_event = service.events().get(calendarId='primary', eventId=str(event.id)).execute()
        cal_event['attendees'].append({'email': member_email})

        updated_cal_event = service.events().update(calendarId='primary', eventId=cal_event['id'], body=cal_event).execute()
        if updated_cal_event.get("htmlLink") is None:
            return (None, 'Failed to add user to calendar event')
        return (True, updated_cal_event)    
    except Exception as e:
        return (None, str(e))

async def remove_user_from_calendar_event(service,
                                          event: discord.ScheduledEvent,
                                          member_id: str):
    """Removes a user from a google calendar event

    Args:
        service (googleapiclient.discovery.Resource): the google calendar service
        event (discord.ScheduledEvent): the discord scheduled event to convert to a google calendar event
        email (str): the email of the user to add to the event

    Returns:
        result (Tuple[bool, Error or None]): a tuple of a boolean and an error object or None if successful
    """
    try:
        cal_event = service.events().get(calendarId='primary', eventId=str(event.id)).execute()
        guild_users = await google_auth.get_user_emails(event.guild.id)
        if guild_users[0] is None:
            return guild_users
        member_email = guild_users[0].get(member_id)
        if member_email is None:
            return (None, 'User has not added their email to the bot')

        cal_event['attendees'] = [attendee for attendee in cal_event['attendees'] if attendee['email']!= member_email]

        updated_cal_event = service.events().update(calendarId='primary', eventId=cal_event['id'], body=cal_event).execute()
        if updated_cal_event.get("htmlLink") is None:
            return (None, 'Failed to remove user from calendar event')
        return (True, updated_cal_event)
    except Exception as e:
        return (None, str(e))

async def delete_calendar_event(service, event: discord.ScheduledEvent):
    """Deletes a google calendar event

    Args:
        service (googleapiclient.discovery.Resource): the google calendar service
        event (discord.ScheduledEvent): the discord scheduled event to convert to a google calendar event

    Returns:
        result (Tuple[bool, Error or None]): a tuple of a boolean and an error object or None if successful
    """
    try:
        service.events().delete(calendarId='primary', eventId=str(event.id)).execute()
        return (True, None)
    except Exception as e:
        return (None, str(e))

def print_log(message: str):
    cprint('===============================================================================================', 'cyan')
    cprint(message, 'yellow')
    cprint('===============================================================================================', 'cyan')

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.command()
async def addEmail(ctx):
    """Adds an email address for a guild user to use in event invites

    Args: ctx (discord.ext.commands.Context): the context of the command invocation
    """
    print_log(f'addEmail command invoked by {ctx.author}')
    await ctx.send('Enter the email address you would like to add to your calendar')
    def check(m):
        return m.author == ctx.author
    try:
        msg = await bot.wait_for('message', check=check, timeout=60)
        print_log(f'addEmail command received email address {msg.content}')
        result = google_auth.add_user_email(guild_id=ctx.guild.id, email=msg.content.strip(), user_id=str(ctx.author.id))
        if result[0]:
            await ctx.send(f'you will now recieve calendar invites for events in this guild to the google account associated with the given email')
            print_log(f'addEmail added email address for user {ctx.author} in guild {ctx.guild.id}')
        else:
            await ctx.send(f'failed to add email address')
            print_log(f'addEmail failed to add email address for user {ctx.author} reason {result[1]}')

    except asyncio.TimeoutError:
        await ctx.send('Timed out, please try again')

@bot.event
async def on_ready():
    global google_auth
    print(colored('''
 ______   ______ _______ _______ _______ ______  _______  _____  __   _
 |     \\ |_____/    |    |______ |______ |_____] |______ |     | | \\  |
 |_____/ |    \\_ .  |    |______ |______ |_____] ______| |_____| |  \\_|
''', 'light_blue'))
    print(f'We have logged in as {colored(bot.user, 'light_magenta')}')
    google_auth = googleauth.GoogeAuthConnect()
    print(colored(f'google auth initialized', 'light_yellow'))


@bot.command
async def login(ctx):
    if ctx.author.guild_permissions.administrator and ctx.guild:
        await ctx.send(
            'Check your DM for the authorization uri')
        auth_url = await google_auth.get_auth_url(ctx.guild.id)

        await ctx.author.send(
            f'Hello {ctx.author}! here is the google authorization url {auth_url} open '
            f'the url in a browser and follow the prompt to give me access to your google calendar info.'
        )

        return 


@bot.event
async def on_scheduled_event_create(event):
    if event.guild:
        if event.creator_id == event.guild.owner_id or event.guild.get_member(
                event.creator_id).guild_permissions.administrator is True:

            print_log(f'Event {event.name} created in {event.guild.name} with id: {event.id}')
            credentials_dict = await google_auth.get_linked_credentials(
                str(event.guild.id))

            if credentials_dict is None:
                print_log(f'No credentials found for guild {event.guild.name}')
                return
            try:
                credentials = Credentials.from_authorized_user_info(
                    credentials_dict)
                result = await create_calendar_event(
                    build('calendar', 'v3', credentials=credentials), event)
                if result[0] is True:
                    print_log(
                        f'Event {event.name} : {event.id} added to calendar with url {result[1]["htmlLink"]} and id {result[1]["id"]}'
                    )
                else:
                    if result[1] is not None:
                        print_log(
                            f'Event {event.name} : {event.id} failed to add to calendar with error {result[1]}'
                        )
            except MutualTLSChannelError as err:
                print(err)
            except Exception as err:
                raise err


@bot.event
async def on_scheduled_event_delete(event):
    if event.guild:
        print_log(
            f'Event {event.name} deleted in {event.guild.name} with id: {event.id}'
        )

        credentials_dict = await google_auth.get_linked_credentials(str(event.guild.id))
        if credentials_dict is None:
            print_log(f'No credentials found for guild {event.guild.name}')
            return
        
        try:
            credentials = Credentials.from_authorized_user_info(credentials_dict)
            result = await delete_calendar_event(
                build('calendar', 'v3', credentials=credentials), event)
            if result[0] is True:
                print_log(
                    f'Event {event.name} : {event.id} deleted from calendar'
                )
            else:
                if result[1] is not None:
                    print_log(
                        f'Event {event.name} : {event.id} failed to delete from calendar with error {result[1]}'
                    )
        except MutualTLSChannelError as err:
            print(err)
        except Exception as err:
            raise err


@bot.event
async def on_scheduled_event_update(before, after):
    if after.guild:
        print_log(
            f'Event {after.name} updated in {after.guild.name} with id: {after.id}'
        )

        credentials_dict = await google_auth.get_linked_credentials(str(after.guild.id))

        if credentials_dict is None:
            print_log(f'No credentials found for guild {after.guild.name}')
            return
        
        try:
            credentials = Credentials.from_authorized_user_info(credentials_dict)
            result = await update_calendar_event(
                build('calendar', 'v3', credentials=credentials), before, after)
            if result[0] is True:
                print_log(
                    f'Event {after.name} : {after.id} updated in calendar with url {result[1]["htmlLink"]} and id {result[1]["id"]}'
                )
            else:
                if result[1] is not None:
                    print_log(
                        f'Event {after.name} : {after.id} failed to update in calendar with error {result[1]}'
                    )
        except MutualTLSChannelError as err:
            print(err)
        except Exception as err:
            raise err


@bot.event
async def on_scheduled_event_user_add(event: discord.ScheduledEvent,
                                      user: discord.User):
    if event.guild:
        print_log(
            f'User {user} added to event {event.name} in {event.guild} with id: {event.id}'
        )
        credentials_dict = await google_auth.get_linked_credentials(str(event.guild.id))

        if credentials_dict is None:
            print_log(f'No credentials found for guild {event.guild.name}')
            return

        try:
            credentials = Credentials.from_authorized_user_info(credentials_dict)
            result = await add_user_to_calendar_event(service=build('calendar', 'v3', credentials=credentials), event=event, member_id=str(user.id))
            if result[0] is True:
                print_log(
                    f'User {user.id} added to event {event.name} : {event.id} in calendar with url {result[1]["htmlLink"]} and id {result[1]["id"]}'
                )
            else:
                print_log(
                    f'User {user.id} added to event {event.name} : {event.id} in calendar with error {result[1]}'
                )
        except MutualTLSChannelError as err:
            print(err)
        except Exception as err:
            raise err

@bot.event
async def on_scheduled_event_user_remove(event, user):
    if event.guild:
        print_log(
            f'User {user.id} removed from event {event.name} in {event.guild} with id: {event.id}'
        )

        credentials_dict = await google_auth.get_linked_credentials(str(event.guild.id))
        if credentials_dict is None:
            print_log(f'No credentials found for guild {event.guild.name}')
            return
        
        try:
            credentials = Credentials.from_authorized_user_info(credentials_dict)
            result = await remove_user_from_calendar_event(service=build('calendar', 'v3', credentials=credentials), event=event, member_id=str(user.id))
            if result[0] is True:
                print_log(
                    f'User {user.id} removed from event {event.name} : {event.id} in calendar with url {result[1]["htmlLink"]} and id {result[1]["id"]}'
                )
            else:
                print_log(
                    f'User {user.id} failed to be removed from event {event.name} : {event.id} in calendar with error {result[1]}'
                )
        except MutualTLSChannelError as err:
            print(err)
        except Exception as err:
            raise err


bot.run(os.getenv('DISCORD_TOKEN'), log_handler=None)
