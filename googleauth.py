import json
import config
import os
import asyncio
import time
import secrets
from sqlalchemy import create_engine, text
from termcolor import colored
POLLING_INTERVAL = 5
BATCH_SIZE = 10
EXPIRATION_TIME = 500
LINKED_FILE = 'linked.json'
DATABASE_FILE = 'sqlite:///guilds.db'

engine = create_engine(DATABASE_FILE, pool_recycle=3600, echo=True)


def get_connection():
    """ gets a connection to the database
    Returns: 
        connection: an sqlalchemy connection object
    """
    connection = engine.connect()
    return connection

class GoogeAuthConnect:

    def __init__(self):
        """ initializes the GoogleAuthConnect class
        """
        self.active_sign_ins = {}
        self.linked = {}

        if os.path.exists(LINKED_FILE):
            with open(LINKED_FILE, 'r') as f:
                try:
                    self.linked = json.load(f)
                    print(colored(f'loaded {colored(len(self.linked), 'light_cyan')} {colored('linked credentials', 'green')}', 'green'))
                except json.decoder.JSONDecodeError:
                    pass
        self.loop = asyncio.get_event_loop()
        # start polling
        self.polling_task = self.loop.create_task(self.poll(), name='linking_polling')
        self.exiting = False 
    
    async def save_linked(self):
        """saves linked credentials to a json file
        Returns:
            None: None 
        """
        with open(LINKED_FILE, 'w') as f:
            json.dump(self.linked, f, indent=4)

    async def stop_polling(self):
        """ stops the polling task
        """
        self.exiting = True
        await self.poll()

    async def poll_batch(self, batch: dict[str, dict[str:str]]):
        """processes batches of login requests and links credentials

        Args: batch (dict[str, dict[str:str]]): a dictionary of guild ids to info (expire_time, state) dictionaries
        Returns:
            None: None
        """
        for guild_id, info in batch.items():
            result = await self.get_credentials(guild_id)
            if info.get('state') == result[1] and result[0] is not None and info.get('expire_time') > time.time():
                self.linked[guild_id] = result[0]
                self.active_sign_ins.pop(guild_id)
            if info.get('expire_time') <= time.time():
                self.active_sign_ins.pop(guild_id)
        await self.save_linked()

    async def poll(self):
        while True:
            for i in range(0, len(self.active_sign_ins), BATCH_SIZE):
                batch = dict(
                    list(self.active_sign_ins.items())[i:i + BATCH_SIZE])
                await self.poll_batch(batch)
            await asyncio.sleep(POLLING_INTERVAL)
            if self.exiting is True:
                self.polling_task.cancel()
                break

    async def get_credentials(self, guild_id):
        """Gets the credentials for a guild from the database.

        Args:
            guild_id: The ID of the guild to get credentials for.

        Returns:
            tuple: tuple[dict[str: str], str] A tuple containing the credentials and the state.
        """
        con = get_connection()
        result = con.execute(
            text(
                "SELECT credential, state FROM guild WHERE guild_id=:guild_id AND credential IS NOT NULL"
            ), {
                'guild_id': guild_id
            }).fetchone()
        if result is None:
            print(f'googleauthconnect: No credentials found for guild {guild_id}')
            return (None, None)

        con.close()
        return (json.loads(result[0]), result[1])
    
    async def get_auth_url(self, guild_id): 
        """Generates an authorization URL to start the OAuth flow.

        Args:
            guild_id: The ID of the discord guild to link credentials for.

        Returns:
            str: The authorization URL
        """
        state = secrets.token_urlsafe(16)
        con = get_connection()
        con.execute(
            text(
                "INSERT OR REPLACE INTO guild (guild_id, credential ,state) VALUES (:guild_id,:credential ,:state)"
            ), {
                'guild_id': guild_id,
                'credential': None,
                'state': state
            })
        con.commit()
        self.active_sign_ins[guild_id] = {
            'expire_time': time.time() + EXPIRATION_TIME,
            'state': state
        }
        con.close()
        return f'{config.AUTH_SERVER_PREFIX}authorize/{guild_id}/{state}'

    async def get_linked_credentials(self, guild_id: str):
        return self.linked.get(guild_id)
    
    async def add_user_email(self, guild_id: str, member_id: str, email: str):
        try:

            if guild_id not in self.linked:
                return (None, 'No linked credentials for guild')
    
            con = get_connection()
            con.execute(text('''
                INSERT OR REPLACE INTO linked (guild_id, member_id, email) VALUES (:guild_id, :member_id, :email)
            '''), {
                'guild_id': guild_id,
                'member_id': member_id,
                'email': email
            })

            return (True, f'Added member {member_id} to guild {guild_id}')

        except Exception as e:
            return (None, str(e))

        finally:
            con.commit()
            con.close()

    async def get_user_emails(self, guild_id: str):
        try:
            if guild_id not in self.linked:
                return (None, 'No linked credentials for guild')

            con = get_connection()
            results = con.execute(text('''
                SELECT member_id, email FROM linked WHERE guild_id=:guild_id
            '''), {
                'guild_id': guild_id
            }).fetchall()

            if results is None:
                return (None, 'guild has no linked members')

            results_dict = {row[0]:row[1] for row in results}

            return (results_dict, f'retrieved linked members for {guild_id}')

        except Exception as e:
            return (None, str(e))
        finally:
            con.close()