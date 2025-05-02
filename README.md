# Telegram Reaction Tracker

> A powerful analytics tool that helps you discover the most popular and engaging messages in any Telegram chat or channel by tracking reaction counts.

Telegram Reaction Tracker is a web application that finds and lists the most reacted messages in a Telegram chat.

## Features

- Find messages with the most reactions in Telegram groups/channels
- Search within specific time periods (7 days, 30 days, 90 days, 180 days, all time)
- Save and view search history
- English and Turkish language support
- Results sorted by reaction count
- Message links (t.me)

## Installation

1. Install required packages:
```
pip install -r requirements.txt
```

2. Create the `.env` file and edit like below:
```
API_ID=Your_Telegram_API_ID
API_HASH=Your_Telegram_API_Hash
PHONE_NUMBER=With_country_code
```

3. Create a Telegram session file by running:
```
python create_session.py
```
This will authenticate with Telegram API and create a `session.session` file necessary for the application to work.

4. Run the application:
```
python app.py
```

5. Go to `http://localhost:5001` in your browser.

## Technical Details

This application uses the following technologies:

- Flask: Web application framework
- Telethon: Telegram API communication
- SQLite: Database
- HTML, CSS: User interface

## Folder Structure

```
telegramTracker/
│
├── telegramtracker/       # Main package
│   ├── core/              # Database operations
│   ├── services/          # Telegram API communication
│   ├── utils/             # Helper functions (translations, etc.)
│   └── web/               # Web routes
│
├── static/                # Static files (CSS, JS, images, fonts)
├── templates/             # HTML templates
├── app.py                 # Application starter
├── .env                   # Environment variables
└── requirements.txt       # Dependencies
```

## Usage

1. Specify a Telegram chat or channel on the main page (by username or ID)
2. Select the time period you want to scan
3. Click the "Get Reactions" button
4. Results will be listed in descending order by reaction count 