"""
Shows basic usage of the Photos v1 API.

Creates a Photos v1 API service and prints the names and ids of the last 10 albums
the user has access to.
"""
from __future__ import print_function
import os
import pickle
import json
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import google_auth_httplib2  # This gotta be installed for build() to work

# Setup the Photo v1 API
SCOPES = [    "https://www.googleapis.com/auth/photoslibrary",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/photoslibrary.appendonly",
    "https://www.googleapis.com/auth/photoslibrary.sharing",
    "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata",
    ]
creds = None
if(os.path.exists("token.pickle")):
    with open("token.pickle", "rb") as tokenFile:
        creds = pickle.load(tokenFile)
        print("Access token:", creds.token)
        print("Is expired?", creds.expired)
        print("Is valid?", creds.valid)
if not creds or not creds.valid:
    if (creds and creds.expired and creds.refresh_token):
        creds.refresh(Request())
        print("Access token:", creds.token)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
        creds = flow.run_local_server()
    with open("token.pickle", "wb") as tokenFile:
        pickle.dump(creds, tokenFile)
service = build('photoslibrary', 'v1', credentials = creds, static_discovery = False)

results = service.albums().list(
    pageSize=50, fields="albums(id,title)").execute()
albums = results.get('albums', [])

items = results.get('albums', [])
if not items:
    print('No albums found.')
    new_album = {
        "album": {"title": "My New Album"}
    }
    created_album = service.albums().create(body=new_album).execute()
    print("Created album: {0} ({1})".format(
        created_album['title'], created_album['id']))
else:
    for item in items:
        print('{0} ({1})'.format(item['title'], item['id']))
print(f"https://photos.google.com/lr/album/{items[0]['id']}")

photos = []
nextPageToken = None
for item in items:
    print(f"Album: {item['title']}, ID: {item['id']}")
    if item['title'] == "My New Album":
        album_id = item['id']

for album in items:
    print(f"Title: {album['title']}, ID: {album['id']}")


while True:
    body = {'albumId': album_id}
    nexptPageToken = None
    if nextPageToken:
        print(f"Fetching next page with token: {nextPageToken}")
        response = service.mediaItems().list(pageSize=100, pageToken=nextPageToken).execute()
    else:
        response = service.mediaItems().list(pageSize=100).execute()
    print(f"Response: {json.dumps(response, indent=2)}")
    items = response.get('mediaItems', [])
    photos.extend(items)

    print(f"Fetched {len(items)} photos on this page.")
    nextPageToken = response.get('nextPageToken')
    if not nextPageToken:
        break

print(f"Total photos found in album: {len(photos)}")
for i, photo in enumerate(photos):
    print(f"{i+1}: {photo['filename']} - {photo['baseUrl']}")
