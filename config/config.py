
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Folder Configuration
LOCAL_FOLDER = os.getenv('LOCAL_FOLDER', r"C:\Users\dev\Downloads")
SYGNOLOGY_FOLDER = os.getenv('SYGNOLOGY_FOLDER', r"C:\Users\dev\SynologyDrive")

# Server Configuration
SERVER_URL = os.getenv('SERVER_URL', 'https://hub.prismgrp.com')

OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')

# Dias en lefty
DAYS_TRACK_LEFTY = int(os.getenv('DAYS_TRACK_LEFTY', '7'))
DAYS_TRACK_LEFTY_WEEK = int(os.getenv('DAYS_TRACK_LEFTY_WEEK', '7'))
DAYS_TRACK_TRAACKR = int(os.getenv('DAYS_TRACK_TRAACKR', '2'))
DAYS_TRACK_TRAACKR_WEEK = int(os.getenv('DAYS_TRACK_TRAACKR_WEEK', '7'))
# Sincronizar Seatable con Lefty
ALLOWED_MONTH = {
    "January": "Jan", "February": "Feb", "March": "Mar",
    "April": "Apr", "May": "May", "June": "Jun",
    "July": "Jul", "August": "Aug", "September": "Sep",
    "October": "Oct", "November": "Nov", "December": "Dec"
}
BATCH_ZIP_DOWNLOAD = int(os.getenv('BATCH_ZIP_DOWNLOAD', '4'))

MONTH_MAP = {
    "january":1,"jan":1,"february":2,"feb":2,"march":3,"mar":3,"april":4,"apr":4,"may":5,
    "june":6,"jun":6,"july":7,"jul":7,"august":8,"aug":8,"september":9,"sep":9,"sept":9,
    "october":10,"oct":10,"november":11,"nov":11,"december":12,"dec":12
}

YEAR = os.getenv('YEAR', '2025')
ACTIVE_YEARS = [2025, 2026]

DAYS_AFTER_MONTH=30

# ----------------------------------------------
# ENVIRONMENT CONFIGURATION
# ----------------------------------------------
# Environment options: 'production', 'development'
# Set to 'development' to disable Seatable updates and enable all email logs
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')  # Change to 'development' to disable Seatable updates

# ----------------------------------------------
# API TOKEN
# ----------------------------------------------
# API Tokens from environment variables
BRAND_PR_API_TOKEN = os.getenv('BRAND_PR_API_TOKEN')
BRAND_PR_2026_API_TOKEN = os.getenv('BRAND_PR_2026_API_TOKEN')
BRAND_PR_2027_API_TOKEN = os.getenv('BRAND_PR_2027_API_TOKEN')
LEFTY_PERFS_API_TOKEN = os.getenv('LEFTY_PERFS_API_TOKEN')
TRAACKR_PERFS_API_TOKEN = os.getenv('TRAACKR_PERFS_API_TOKEN')
TALKWALKER_PERFS_API_TOKEN = os.getenv('TALKWALKER_PERFS_API_TOKEN')
INFLUENCER_API_TOKEN = os.getenv('INFLUENCER_API_TOKEN')
CUSTOMER_SETTINGS_API_TOKEN = os.getenv('CUSTOMER_SETTINGS_API_TOKEN')
SOURCE_DIRECTORY = os.getenv('SOURCE_DIRECTORY')
API_TOKEN_YOUTUBE = os.getenv('API_TOKEN_YOUTUBE')

# ----------------------------------------------
# Credentials from environment variables
# ----------------------------------------------

# Instagram Credentials
INSTAGRAM_USER = os.getenv('INSTAGRAM_USER')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')

# Lefty Credentials
LEFTY_EMAIL = os.getenv('LEFTY_EMAIL')
LEFTY_PASSWORD = os.getenv('LEFTY_PASSWORD')

# Traackr Credentials
TRAACKR_EMAIL = os.getenv('TRAACKR_EMAIL')
TRAACKR_PASSWORD = os.getenv('TRAACKR_PASSWORD')
TOTP_SECRET_TRAACKR = os.getenv('TOTP_SECRET_TRAACKR')

# Talkwaker Credentials
TALKWAKER_EMAIL = os.getenv('TALKWAKER_EMAIL')
TALKWAKER_PASSWORD = os.getenv('TALKWAKER_PASSWORD')

# Synology Credentials
SYNOLOGY_EMAIL = os.getenv('SYNOLOGY_EMAIL')
SYNOLOGY_PASSWORD = os.getenv('SYNOLOGY_PASSWORD')
TOTP_SECRET = os.getenv('TOTP_SECRET')

TABLE_2025 = "2025"
TABLE_2026 = "2026"
TABLE_SOCIAL_ACCOUNT = "Social Account"
SOURCE = "Source"


BRAND_PREFIX_MAP = json.loads(os.getenv('BRAND_PREFIX_MAP', '{}'))

DOWNLOAD_TRAACKR = os.getenv('DOWNLOAD_TRAACKR', 'True').lower() == 'true'
DOWNLOAD_LEFTY = os.getenv('DOWNLOAD_LEFTY', 'True').lower() == 'true'
DOWNLOAD_TALKWALKER = os.getenv('DOWNLOAD_TALKWALKER', 'True').lower() == 'true'
FIELDS_TO_UPDATE_LEFTY_PERFS = [
    "MetaId",
    "Source",
    "Username",
    "Network",
    "Link",
    "Followers",
    "Posts",
    "Impressions",
    #"EMV",
    "Avg likes",
    "Engagement rate",
    "Avg comments",
    "Post frequency / day",
    #"RFM score",
    #"Recency score",
    "Last post date",
    #"Frequency score",
    "Monthly frequency",
    #"Monetary score",
    #"Average EMV"
]

FIELDS_TO_UPDATE_LEFTY_INFOS = [
    "MetaId",
    "Source",
    "First Name",
    "Last Name",
    "Market",
    #"Country",
    #"Website",
    #"Instagram",
    #"Youtube",
    #"X (Twitter)",
    #"TikTok",
    #"Last Hired for",
    #"Previous Products",
    "Tracked"
]

FIELDS_TO_UPDATE = [
    "Reach",
]



FIELDS_TO_UPDATE_2025 = FIELDS_TO_UPDATE + [
    "Views",
    "Engagement Rate",
    "Impresiones",
    "ID",
    "Engagement"
]

FIELDS_TO_UPDATE_LEFTY = FIELDS_TO_UPDATE + [
    "Likes",
    "Favorites",
    "Comments",
    "Views",
    "Shares",
    "Impresiones",
    "Unique ID",
    "Engagement Rate",
    "EMV",
    "Engagement"
]

FIELDS_TO_UPDATE_TALKWALKER = FIELDS_TO_UPDATE + [
    "Impresiones",
    "Views",
    "Engagement",
    "ID"
]

FIELDS_TO_UPDATE_TRAACKR = FIELDS_TO_UPDATE + [
    "Impresiones",
    "Video Views",
    "Likes",
    "Comments",
    "Engagement Rate",
    "Engagement",
    "Shares",
    "Unique ID"
]


COLUMNS_TO_CHECK_STATUS = [
    "Week",
    "Month",
    "Date",
    "Headline",
    "URL",
    "Post Type",
    "Source"
]

COLUMNS_TO_CHECK_STATUS_LEFTY = COLUMNS_TO_CHECK_STATUS + [
    "Country",
    "_Media Type_",
    "Brand",
    "Origin",
]

COLUMNS_TO_CHECK_STATUS_TRAACKR = COLUMNS_TO_CHECK_STATUS + [
    "_Country_",
    "Platform",
    "Brand",
    "_Origin_",
]

COLUMNS_TO_CHECK_STATUS_TALKWALKER = COLUMNS_TO_CHECK_STATUS + [
    "_Country_",
    "_Media Type_",
    "Brand",
    "_Origin_",
]


STATIC_LINKS  = [
    {
        "link_id_name": "Source",
        "table_name": "Sources",
        "other_table_name": TABLE_2025,
        "column_name": "Source",
        "other_column_name": "_Source_"
    },
    {
        "link_id_name": "Market",
        "table_name": "Markets",
        "other_table_name": TABLE_2025,
        "column_name": "Name",
        "other_column_name": "_Country_"
    },
    {
        "link_id_name": "Brand",
        "table_name": "Brands",
        "other_table_name": TABLE_2025,
        "column_name": "Name",
        "other_column_name": "Brand"
    },
]



STATIC_LINKS_2026  = [
    {
        "link_id_name": "Source",
        "table_name": "Sources",
        "other_table_name": TABLE_2026,
        "column_name": "Source",
        "other_column_name": "_Source_"
    },
    {
        "link_id_name": "Market",
        "table_name": "Markets",
        "other_table_name": TABLE_2026,
        "column_name": "Name",
        "other_column_name": "_Country_"
    },
    {
        "link_id_name": "Brand",
        "table_name": "Brands",
        "other_table_name": TABLE_2026,
        "column_name": "Name",
        "other_column_name": "Brand"
    },
]


PERF_LINKS  = [
    {
        "link_id_name": "Lefty Perfs",
        "table_name": "Lefty Perfs",
        "other_table_name": TABLE_2025,
        "column_name": "Unique ID",
        "other_column_name": "Lefty Perfs Unique ID"
    },
    {
        "link_id_name": "Talkwalker Perfs",
        "table_name": "Talkwalker Perfs",
        "other_table_name": TABLE_2025,
        "column_name": "ID",
        "other_column_name": "Talkwalker Perfs Unique ID"
    },
    {
        "link_id_name": "Traackr Perfs",
        "table_name": "Traackr Perfs",
        "other_table_name": TABLE_2025,
        "column_name": "Unique ID",
        "other_column_name": "Traackr Perfs Unique ID"
    },

]


LINK_ID_SOCIAL_ACCOUNT = [
    {
        "link_id_name": "Source",
        "table_name": "Influencer Info",
        "other_table_name": TABLE_SOCIAL_ACCOUNT,
        "column_name": "MetaId",
        "other_column_name": "Source"
    },
]

LINK_ID_INFLUENCER_INFO = [
    {
        "link_id_name": "Market",
        "table_name": "Markets",
        "other_table_name": "Influencer Info",
        "column_name": "Name",
        "other_column_name": "Market"
    },
]



LINK_ID_CHANNEL = [
    {
        "link_id_name": "Source",
        "table_name": "Source",
        "other_table_name": "Channel",
        "column_name": "Source",
        "other_column_name": "Username"
    },
    {
        "link_id_name": "Source",
        "table_name": "Source",
        "other_table_name": "Channel",
        "column_name": "Traackr ID",
        "other_column_name": "TraackrID"
    },
    {
        "link_id_name": "Source",
        "table_name": "Source",
        "other_table_name": "Channel",
        "column_name": "Talkwalker Lookup",
        "other_column_name": "TalkwalkerID"
    },
    {
        "link_id_name": "Source",
        "table_name": "Source",
        "other_table_name": "Channel",
        "column_name": "MetaID",
        "other_column_name": "Lefty MetaID"
    }
]

COLUMNS_TO_UPDATE_LEFTY_CHANNEL = [
    # "Lefty MetaID",
    "Followers",
    "Posts",
    "Impressions",
    #"Avg likes",
    #"Avg comments",
    "Engagement rate",
    "Original Link"
]

COLUMNS_TO_UPDATE_TALKWALKER_CHANNEL = [
    "Reach",
    "Original Link",
    "TalkwalkerID",
    "Monthly Visitors",
    "Monthly Pageviews"
]

COLUMNS_TO_UPDATE_TRAACKR_CHANNEL = [
    "Followers",
    "Original Link",
    "Reach",
    "_alternative_traackr_ids",
]


CHANNEL_LEFTY_MAPPING = {
    "Username": "Username",
    "MetaId": "Lefty MetaID",
    "Followers": "Followers",
    "Posts": "Posts",
    "Impressions": "Impressions",
    "Avg likes": "Avg likes",
    "Avg comments": "Avg comments",
    "Engagement rate": "Engagement rate",
    "Last post date": "Last post date",
    "Network": "Network",
    "Link": "Link"
}

CHANNEL_TALKWALKER_MAPPING = {
    "Username": "Username",
    "MetaId": "Lefty MetaID",
    "Followers": "Followers",
    "Posts": "Posts",
    "Impressions": "Impressions",
    "Avg likes": "Avg likes",
    "Avg comments": "Avg comments",
    "Engagement rate": "Engagement rate",
    "Last post date": "Last post date",
    "Network": "Network",
    "Link": "Link"
}

CHANNEL_TRAACKR_MAPPING = {
    "Username": "Username",
    "TraackrID": "TraackrID",
    "Followers": "Followers",
    "Posts": "Posts",
    "Engagement rate": "Engagement rate",
    "Network": "Network",
    "Link": "Link"
}