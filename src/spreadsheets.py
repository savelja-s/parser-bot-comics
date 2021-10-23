import datetime
import json
import os

import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials

CREDENTIALS_FILE = os.path.join(os.getcwd(), 'config', 'google_credentials.json')
CONFIG = json.load(open('config/config.json'))


def get_http_auth():
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE,
        ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive']
    )
    return credentials.authorize(httplib2.Http())


def get_sheets_service():
    return apiclient.discovery.build('sheets', 'v4', http=get_http_auth())


def add_permissions(email: str, spreadsheet_id: str):
    return apiclient.discovery.build('drive', 'v3', http=get_http_auth()).permissions().create(
        fileId=spreadsheet_id,
        body={'type': 'user', 'role': 'writer', 'emailAddress': email},
        fields='id'
    ).execute()


def create_file():
    spreadsheet = get_sheets_service().spreadsheets().create(body={
        'properties': {'title': 'first doc'},
        'sheets': [{'properties': {'sheetType': 'GRID',
                                   'sheetId': 0,
                                   'title': 'title#1',
                                   'gridProperties': {'rowCount': 6000, 'columnCount': 15}}}]
    }).execute()
    print('https://docs.google.com/spreadsheets/d/' + spreadsheet['spreadsheetId'])
    return spreadsheet['spreadsheetId']


def create_sheet(title: str):
    return get_sheets_service().spreadsheets().batchUpdate(
        spreadsheetId=CONFIG['spreadsheet_id'],
        body=
        {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": title,
                            "gridProperties": {
                                "rowCount": 6000,
                                "columnCount": 15
                            }
                        }
                    }
                }
            ]
        }).execute()


def insert_in_sheet(title: str, values: list):
    return get_sheets_service().spreadsheets().values().append(
        spreadsheetId=CONFIG['spreadsheet_id'],
        range=f"{title}!A:Z",
        valueInputOption="USER_ENTERED",
        body={"majorDimension": "ROWS", "values": values},
    ).execute()
