# community-vote

this is a small, slightly over-caffeinated discord bot that helps moderators and makes moderation easier by taking help from the users.
lets say, someone posts something bad and no mods are online. users can make a poll using the bot to delete the bad content.

## libraries used

- **python 3.9+**
  - async/await is not optional here

- **discord.py**
  - core library used to interact with the discord api
  - provides:
    - `commands.Bot`
    - `app_commands` (slash commands)
    - `discord.Embed`
    - event hooks like `on_ready`
  - tested with modern discord.py versions (2.x)

- **discord.ext.tasks**
  - used for background loops (e.g. `monitor_polls`)
  - handles timed polling without blocking the event loop


## discord developer portal requirements

when creating the application in the discord developer portal, make sure the following are set:

### application settings

- create a new **application**
- add a **bot user**
- copy the bot token (keep it secret, obviously)

### privileged gateway intents

enable these under the **bot** tab if your bot logic needs them:

- **message content intent**
  - required if you read or store message text (`entry['msg_text']`)
- **server members intent**
  - only needed if voter data depends on member objects

restart the bot after changing intents.

### bot permissions

minimum recommended permissions:

- send messages
- embed links
- read message history
- use application commands

permission integer will vary depending on your setup, but embeds are non-negotiable.

### oauth2 / invite

- scope:
  - `bot`
  - `applications.commands`
- permissions:
  - match the permissions listed above

generate the invite url and add the bot to your server.
