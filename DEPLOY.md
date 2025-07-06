# Deployment Instructions for Railway

## Files Added for Railway Deployment

- `Procfile` - Tells Railway how to run your application
- `railway.toml` - Railway-specific configuration
- `.env.example` - Template for environment variables

## Steps to Deploy

1. **Push your code to GitHub** (make sure all the new files are included)

2. **Set up Railway project:**
   - Go to [Railway.app](https://railway.app)
   - Connect your GitHub account
   - Create a new project and select your repository

3. **Configure Environment Variables in Railway:**
   - In your Railway project dashboard, go to "Variables"
   - Add the following variables:
     - `BOT_TOKEN`: Your Telegram bot token (get from @BotFather)
     - `ADMIN_ID`: Your Telegram user ID (you can get this by messaging @userinfobot)

4. **Deploy:**
   - Railway should automatically detect the Python project and start building
   - The deployment should now work with the proper start command

## Getting Your Bot Token and Admin ID

### Bot Token:
1. Message @BotFather on Telegram
2. Use `/newbot` to create a new bot
3. Copy the token it gives you

### Admin ID:
1. Message @userinfobot on Telegram
2. It will reply with your user ID
3. Use that number as ADMIN_ID

## Local Development

1. Copy `.env.example` to `.env`
2. Fill in your actual values
3. Run: `python velasco.py`
