import json
import pickle
import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
#from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import requests
from pyhelpers.ops import is_downloadable



credential_file = "gp-credentials.json"
scope = 'https://www.googleapis.com/auth/photoslibrary'


class GooglePhotosApi:
    def __init__(self,
                 api_name='photoslibrary',
                 client_secret_file=credential_file,
                 api_version='v1',
                 scopes=None):
        '''
        Args:
            client_secret_file: string, location where the requested credentials are saved
            api_version: string, the version of the service
            api_name: string, name of the api e.g."docs","photoslibrary",...
            api_version: version of the api

        Return:
            service:
        '''

        self.api_name = api_name
        self.client_secret_file = client_secret_file
        self.api_version = api_version
        self.scopes = scopes if scopes is not None else [scope]
        self.cred_pickle_file = f'token_{self.api_name}_{self.api_version}.pickle'

        self.cred = None

    def run_local_server(self):
        # is checking if there is already a pickle file with relevant credentials
        if os.path.exists(self.cred_pickle_file):
            with open(self.cred_pickle_file, 'rb') as token:
                self.cred = pickle.load(token)

        # if there is no pickle file with stored credentials, create one using google_auth_oauthlib.flow
        if not self.cred or not self.cred.valid:
            if self.cred and self.cred.expired and self.cred.refresh_token:
                self.cred.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_file, self.scopes)
                self.cred = flow.run_local_server()

            with open(self.cred_pickle_file, 'wb') as token:
                pickle.dump(self.cred, token)

        return self.cred

google_photos_api = GooglePhotosApi()
creds = google_photos_api.run_local_server()

def search_album(album_name=None):
    album_name = album_name if album_name is not None else ''
    album_list = []
    url = 'https://photoslibrary.googleapis.com/v1/albums?pageSize=50'
    headers = {
        'content-type': 'application/json',
        'Authorization': 'Bearer {}'.format(creds.token)
    }
    next_page = None
    while True:
        try:
            url = url if next_page is None else url + f'&pageToken={next_page}'
            res = requests.request("GET", url, headers=headers)
            res_dict = res.json()
            _album = res_dict.get('albums', [])
            next_page = res_dict.get('nextPageToken', None)
            album_list += _album
            if next_page is None:
                break
        except:
            print('Request error')

    print(f"album list length: {len(album_list)}")
    # for album in [a.get('title') for a in album_list]:
    search_result = [a for a in album_list if a.get('title').lower().find(album_name.lower()) > -1]
    print(f"search result length: {len(search_result)}")
    for i, album in enumerate(search_result):
        print(f"{i:02d} - {album.get('title')}")

    return search_result


def get_photo_list_from_album(album_id):
    url = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
    payload = {
      "pageSize": "100",
      "albumId": album_id
    }
    headers = {
        'content-type': 'application/json',
        'Authorization': 'Bearer {}'.format(creds.token)
    }

    try:
        res = requests.request("POST", url, data=json.dumps(payload), headers=headers)
        return res.json().get('mediaItems', [])
    except:
        print('Request error')

    # return (res)

# def get_photo_content()
error_list = []
def download_photo(img_list, folder_name):
    print(f"image list length: {len(img_list)}")
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    for i, img in enumerate(img_list):
        video = img['mediaMetadata'].get('video')
        suffix = '=dv' if video else f'=w{img["mediaMetadata"]["width"]}-h{img["mediaMetadata"]["height"]}'
        baseurl = img['baseUrl'] + suffix
        _down = is_downloadable(baseurl)
        if _down:
            file_format = img['filename'].split('.')[-1]
            file_name = f"{i:03d}.{file_format}"
            print(f"downloading {img['filename']} :> {file_name}")
            file_path = os.path.join(folder_name, file_name)
            try:
                r = requests.get(baseurl)
                with open(file_path, 'wb') as f:
                    f.write(r.content)
                    continue
            except Exception as e:
                print(f"Error downloading {e}")
        error_list.append(img)


if __name__ == '__main__':
    # search_result = search_album('test')
    # album_id = search_result[0].get('id')
    # response = get_photo_list_from_album(album_id)
    # download_photo(response, 'test')
    print("Google Photo downloader")
    album_name = input("Enter album name: ")
    search_result = search_album(album_name)
    search_index = int(input("Enter album index: "))
    album = search_result[search_index]

    img_list = get_photo_list_from_album(album['id'])
    folder_name = album['title']
    print(f"Downloading {len(img_list)} images to {folder_name}")
    download_photo(img_list, folder_name)
