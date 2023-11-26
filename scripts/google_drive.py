from __future__ import print_function
import time

import os.path

import os
import mimetypes
import sys
import io

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']



def get_gdrive_service():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None

    # Загрузите информацию учетной записи службы из JSON-ключа
    creds = service_account.Credentials.from_service_account_file(
        'service_account_key.json')

    # if os.path.exists('token.json'):
    #     creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # # If there are no (valid) credentials available, let the user log in.
    # if not creds or not creds.valid:
    #     from google.auth.transport.requests import Request
    #     from google_auth_oauthlib.flow import InstalledAppFlow

    #     if creds and creds.expired and creds.refresh_token:
    #         creds.refresh(Request())
    #     else:
    #         flow = InstalledAppFlow.from_client_secrets_file(
    #             'credentials.json',
    #             SCOPES,
    #         )
    #         flow.authorization_url(access_type='offline')
    #         creds = flow.run_local_server(port=50140)
    #     # Save the credentials for the next run
    #     with open('token.json', 'w') as token:
    #         token.write(creds.to_json())

    try:
        service = build('drive', 'v3', credentials=creds)

        return service
    except HttpError as error:
        print(f'An error occurred: {error}')


def download_file(file_id, folder, file_name, service):
    """Download a file by id

    Args:
        file_id: id of the file ot be downloaded
        folder: Local folder to download the file to
        file_name: name of the file to be created
        service: Google Drive service object
    """
    file_path = os.path.join(folder, file_name)
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_path, 'w')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))


def upload_file(folder, file_name, service, parent_folder_id=None):
    """Uploads a file

    Args:
        folder: Local folder where the file is located
        file_name: name of the file to be updated
        service: Google Drive service object
        parent_folder_id: Optional parent folder id in Google Drive
    """
    file_path = os.path.join(folder, file_name)
    mime_type = mimetypes.guess_type(file_path)

    file_metadata = {'name': file_name}
    if parent_folder_id:
        file_metadata['parents'] = [parent_folder_id]
    media = MediaFileUpload(file_path, mimetype=mime_type[0])
    try:
        file = service.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()
    except Exception as ex:
        error_message = f'Error occurred: {str(ex)}'
        with open('/app/error.log', 'w') as error_log:
            error_log.write(error_message)
        time.sleep(10)

    print(f"DB dump {file_name} uploaded to Google Drive.")


if __name__ == '__main__':
    command = sys.argv[1]
    folder = sys.argv[2]
    filename = sys.argv[3]
    if command == 'upload':
        service = get_gdrive_service()
        upload_file(folder=folder, file_name=filename, service=service,
                    parent_folder_id='1tti0k4AZGwCrpqEXTi8CUpbsxQXpdotC')
    elif command == 'download':
        service = get_gdrive_service()
        download_file(file_id=filename, folder=folder,
                    file_name='dump.sql.gz', service=service)
    else:
        raise ValueError(
            "You sould pass command 'upload' or 'download' like python goolge_drive.py upload /app/tmp $filename")