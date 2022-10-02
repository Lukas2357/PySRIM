""" Upload folder to Google Drive

"""
from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from datetime import datetime, timedelta
import time
import calendar
import pathlib
import shutil

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFile, ApiRequestError


def parse_args():
    """ We might want to call from command line and parse arguments as follows

    """
    parser = ArgumentParser(
        description="Upload local folder to Google Drive")
    parser.add_argument('-s', '--source', type=str,
                        help='Folder to upload')
    parser.add_argument('-d', '--destination', type=str,
                        help='Destination Folder in Google Drive')
    parser.add_argument('-p', '--parent', type=str,
                        help='Parent Folder in Google Drive')
    parser.add_argument('-dl', '--just_down', type=bool,
                        help='Whether to just download files')
    parser.add_argument('-ul', '--just_upload', type=bool,
                        help='Whether to just upload files')
    parser.add_argument('-hi', '--hidden', type=bool,
                        help='Whether to sync hidden files')
    parser.add_argument('-c', '--clean_up', type=bool,
                        help='Whether to clean up the remote')
    parser.add_argument('-cp', '--copy', type=bool,
                        help='Whether to create a remote copy')
    parser.add_argument('-sf', '--sync_files', nargs='+',
                        help='Files to sync')

    return parser.parse_args()


def authenticate():
    """ Authenticate to Google API """
    gauth = GoogleAuth()
    return GoogleDrive(gauth)


def get_remote_file_dict(drive, parent_folder_id):

    # Iterate through all files in the parent folder and return title match:
    query = f"'{parent_folder_id}' in parents and trashed=false"
    remote_file_dict = {file['title']: file
                        for file in drive.ListFile({'q': query}).GetList()}
    return remote_file_dict


def get_remote_file(drive, parent_folder_id,
                    file_name, remote_file_dict=None) -> GoogleDriveFile | None:
    """ Check if remote folder exists and return its object (or None if not)

    """

    if remote_file_dict is None:
        remote_file_dict = get_remote_file_dict(drive, parent_folder_id)

    remote_file = remote_file_dict.get(file_name)

    return remote_file


def create_folder(drive, folder_name, parent_folder_id):
    """ Create folder on Google Drive

    """
    folder_metadata = {
        'title': folder_name,
        # Define the file type as folder
        'mimeType': 'application/vnd.google-apps.folder',
        # ID of the parent folder
        'parents': [{"kind": "drive#fileLink", "id": parent_folder_id}]
    }

    folder = drive.CreateFile(folder_metadata)
    folder.Upload()

    return folder


def upload_file(drive, folder_id, file_path, remote_file=None):

    if remote_file is None:
        file = drive.CreateFile({"parents": [{"id": folder_id}],
                                 "title": os.path.split(file_path)[-1]})
    else:
        file = drive.CreateFile({"parents": [{"id": folder_id}],
                                 "title": os.path.split(file_path)[-1],
                                 "id": remote_file['id']})

    file.SetContentFile(file_path)
    file.Upload()

    add_to_last_modified(file_path)


def upload_files(drive, folder_id, local_folder, uploaded_files, ignored_files,
                 sync_files, sync_hidden=False):
    """ Upload files in the local folder to Google Drive

    """
    local_folder_file_list = [os.path.join(local_folder, title)
                              for title in os.listdir(local_folder)]

    remote_file_dict = get_remote_file_dict(drive, folder_id)

    # Auto-iterate through all files in the local folder:

    for local_file_path in local_folder_file_list:

        add_to_last_modified(local_file_path)

        local_file_name = os.path.split(local_file_path)[-1]

        # Continue if file is not in sync_files:
        if sync_files is not None and local_file_path in sync_files:
            continue

        # Continue if file is empty:
        if os.stat(local_file_path) == 0:
            continue

        # Continue if file/folder is ignored:
        if any(x in local_file_path.split("/") for x in ignored_files):
            continue

        # Continue if file/folder is hidden and upload_hidden is false.
        if not sync_hidden and local_file_name[0] == '.':
            continue

        # Get the remote file matching the local file (if not exist -> None):
        remote_file = get_remote_file(drive, folder_id, local_file_name,
                                      remote_file_dict)

        # If file is folder, upload content recursively:
        if os.path.isdir(local_file_path):
            # If the subfolder does not exist, we need to create it:
            if remote_file is None:
                folder = create_folder(drive, local_file_name, folder_id)
                sub_folder_id = folder['id']
            else:
                # Else the remote file is the subfolder, and we get its id:
                sub_folder_id = remote_file['id']
            upload_files(drive, sub_folder_id, local_file_path, uploaded_files,
                         ignored_files, sync_files)
        else:
            # If we found a plain file, the actual file upload happens now:
            last_modified_local = os.path.getmtime(local_file_path)
            if remote_file is None:
                if '.sync' not in local_file_path.split('/'):
                    print('Uploading ' + local_file_path)
                else:
                    prepared_perc += 10
                    print(f'Setting up sync environment {prepared_perc}/100%')
                upload_file(drive, folder_id, local_file_path)
                uploaded_files.append(local_file_path)
            else:
                # If remote file exists, check last modification times:
                last_modified_remote = get_last_modified().get(local_file_path)
                mod_time = remote_file['modifiedDate'].split('.')[0]
                strp_time = datetime.strptime(mod_time, '%Y-%m-%dT%H:%M:%S') + timedelta(hours=2)
                strf_time = strp_time.strftime("%a %b %d %H:%M:%S %Y")
                timestamp = int(strp_time.timestamp())
                if not isinstance(last_modified_remote, float) and last_modified_remote is not None:
                    utc_time = time.strptime(last_modified_remote, 
                                             "%a %b %d %H:%M:%S %Y")
                    last_modified_remote = calendar.timegm(utc_time) - 60*60*2
                    last_modified_remote = max(last_modified_remote, timestamp)
                # If modification time is unknown, or local is newer, overwrite:
                if (last_modified_remote is None
                        or int(last_modified_remote) < int(last_modified_local)):
                    print('Overwriting remote ' + local_file_path)
                    upload_file(drive, folder_id, local_file_path, remote_file)

    return uploaded_files


def download_files(drive, folder_id, local_folder, uploaded_files,
                   ignored_files, sync_files, sync_hidden=False):
    """ Download files in the local folder from Google Drive

    """
    local_folder_file_list = [os.path.join(local_folder, title)
                              for title in os.listdir(local_folder)]

    google_mime = {
        'application/vnd.google-apps.document': 'application/pdf',
        'application/vnd.google-apps.presentation': 'application/pdf',
        'application/vnd.google-apps.spreadsheet': 'text/csv'
    }

    remote_file_dict = get_remote_file_dict(drive, folder_id)

    # Auto-iterate through all files in the remote folder:

    for title, file in remote_file_dict.items():

        path = os.path.join(local_folder, title)

        # Continue if file is not in sync_files:
        if sync_files is not None and path in sync_files:
            continue

        # Continue if file/folder is ignored:
        if title in ignored_files:
            continue

        # Continue if file/folder is hidden and upload_hidden is false:
        if not sync_hidden and title[0] == '.':
            continue

        # Continue if files were just uploaded:
        if path in uploaded_files:
            continue

        # If file is folder, upload content recursively:
        if file['mimeType'] == 'application/vnd.google-apps.folder':
            # If the subfolder does not exist, we need to create it:
            if path not in local_folder_file_list:
                os.mkdir(path)
            download_files(drive, file['id'], path, uploaded_files,
                           ignored_files, sync_files)
        else:
            # If we found a plain file, the actual file upload happens now:
            last_modified_remote = get_last_modified().get(path)
            if not isinstance(last_modified_remote, float) and last_modified_remote is not None:
                utc_time = time.strptime(last_modified_remote, 
                                         "%a %b %d %H:%M:%S %Y")
                last_modified_remote = calendar.timegm(utc_time) - 60*60*2
                mod_time = file['modifiedDate'].split('.')[0]
                strp_time = datetime.strptime(mod_time, '%Y-%m-%dT%H:%M:%S') + timedelta(hours=2)
                strf_time = strp_time.strftime("%a %b %d %H:%M:%S %Y")
                timestamp = int(strp_time.timestamp())
                last_modified_remote = max(last_modified_remote, timestamp)
            
            if path not in local_folder_file_list:
                print('Downloading ' + path)

                # If file is Google file format, convert it:
                if file['mimeType'] in google_mime:
                    download_mimetype = google_mime[file['mimeType']]
                    file.GetContentFile(path, mimetype=download_mimetype)

                else:
                    file.GetContentFile(path)

                add_to_last_modified(path)

            else:
                # If modification time is unknown, or remote newer, overwrite:
                file_modified_time = os.path.getmtime(path)

                if (last_modified_remote is None or int(last_modified_remote) > int(file_modified_time)):
                    print('Overwriting local ' + path)

                    # If file is Google file format, convert it:
                    if file['mimeType'] in google_mime:
                        download_mimetype = google_mime[file['mimeType']]
                        file.GetContentFile(path, mimetype=download_mimetype)

                    else:
                        file.GetContentFile(path)

                    add_to_last_modified(path)


def add_to_last_modified(local_file_path):

    file_modified_time = os.path.getmtime(local_file_path)
    clear_time = time.ctime(file_modified_time)

    new_entry = {local_file_path: clear_time}

    last_modified = get_last_modified()
    last_modified.update(new_entry)

    with open('.last_modified.json', 'w') as file:
        file.write(json.dumps(last_modified))


def get_last_modified():

    last_modified_file_path = ".last_modified.json"

    if os.stat(last_modified_file_path).st_size == 0:
        return {}
    else:
        with open(last_modified_file_path, 'r') as j:
            last_modified = json.loads(j.read())
        return last_modified


def init_remote_folder(drive, remote_path):

    n = len(remote_path)
    parent_id = 'root'

    for idx, folder in enumerate(remote_path):
    
        current_folder = get_remote_file(drive, parent_id, folder)

        if current_folder is None:
            print('Creating remote folder ' + folder)
            current_folder = create_folder(drive, folder, parent_id)
        elif idx < n-1:
            parent_id = current_folder['id']

    with open(".parent_id.json", 'w') as file:
        file.write(json.dumps({'parent_id': parent_id}))

    return parent_id



def sync_folder(local_folder='.', remote_folder=None, remote_parent='root',
                just_upload=False, just_download=False, sync_hidden=False,
                clean_up_remote=False, create_copy=False, sync_files=None):
    """ Upload an entire folder with all contents to google Drive """

    args = parse_args()

    # Use command line arguments of given, else function call attributes:
    if args.source is not None:
        local_folder = args.source
        if local_folder in ['.', '..']:
            local_path = os.getcwd().split('/')
        else:
            local_path = local_folder.split('/')
        if args.destination is None:
            remote_folder = local_folder
        else:
            remote_folder = args.destination
        if args.parent is not None:
            remote_parent = args.parent
        just_upload = False if args.just_upload is None else args.just_upload
        just_download = False if args.just_down is None else args.just_down
        sync_hidden = False if args.hidden is None else args.hidden
        clean_up_remote = False if args.clean_up is None else args.clean_up
        create_copy = False if args.copy is None else args.copy
        sync_files = None if args.sync_files is None else args.sync_files
    else:
        local_path = os.getcwd().split('/')

    if local_path[-1] == '':
        local_path = local_path[:-1]

    if remote_folder is None:
        remote_folder = local_folder

    if local_folder == '.':
        remote_folder = local_path[-1]

    if local_folder == '..':
        remote_folder = local_path[-2]

    # Authenticate to Google API
    drive = authenticate()

    remote_path = remote_folder.split('/')
    if remote_path[-1] == '':
        remote_path = remote_path[:-1]
    folder_name = remote_path[-1]

    if not os.path.isfile('.parent_id.json'):
        parent_folder_id = init_remote_folder(drive, remote_path)
    else:
        with open('.parent_id.json', 'r') as file:
            parent_folder_id = json.loads(file.read())['parent_id']

    if create_copy:

        folder = get_remote_file(drive, parent_folder_id, folder_name)
        if folder is None:
            new_folder = create_folder(drive, folder_name, parent_folder_id)
            parent_folder_id = new_folder['id']
        else:
            parent_folder_id = folder['id']

        today = datetime.today().strftime('%Y-%m-%d')
        file_dict = get_remote_file_dict(drive, parent_folder_id)
        project_files = file_dict.keys()

        if len(project_files) == 0:
            new_version = '1.1.0'
        else:
            file_versions = [x.split('_')[-2].split('.') for x in project_files]
            recent = sorted(file_versions, key=lambda x: (x[0], x[1], x[2]))[-1]
            recent[-1] = str(int(recent[-1]) + 1)
            new_version = '.'.join(recent)

        remote_folder += ('_' + new_version + '_' + today)
        backup_path = local_backup(remote_folder)
        os.chdir(os.path.join(backup_path, os.getcwd().split('/')[-1]))

        folder = create_folder(drive, remote_folder, parent_folder_id)

    else:
        folder = get_remote_file(drive, parent_folder_id, folder_name)

    if folder is None:
        print('Remote folder not found... did you call syncin and connection works?')
        return

    if clean_up_remote:
        folder.Delete()

    mod_json = ".last_modified.json"
    # Check if the .sync folder exists in the main local folder (should be
    # since we call this function from within it, but who knows...)
    # Get the .last_modified.json file from it if possible, else we create it:
    sync_config_folder = get_remote_file(drive, folder['id'], '.sync')
    if sync_config_folder is not None:
        last_modified_file = get_remote_file(drive, sync_config_folder['id'],
                                             mod_json)
    else:
        last_modified_file = None

    if last_modified_file is not None:
        last_modified_file.GetContentFile(mod_json)

    # We might add files to ignore in .gdriveignore:
    ignored_files = [x.strip() for x in open('.gdriveignore', 'r').readlines()]

    local_folder = '..' # QUICK FIX, WAS ACTUALLY NOT THE IDEA HERE ...

    # Finally upload the local files which are not ignored but modified:
    if not just_download:
        try:
            uploaded_files = upload_files(drive, folder['id'], local_folder, [],
                                          ignored_files, sync_files,
                                          sync_hidden=sync_hidden)
        except ApiRequestError:
            return -1
    else:
        uploaded_files = []

    # And download the remote ones which are not ignored but modified:
    if not just_upload:
        download_files(drive, folder['id'], local_folder, uploaded_files,
                       ignored_files, sync_files, sync_hidden=sync_hidden)

    # Make sure to finally update the .last_modified.json file:
    if sync_config_folder is not None:
        upload_file(drive, sync_config_folder['id'], mod_json,
                    remote_file=last_modified_file)

    return 0


def local_backup(remote_folder):

    project_path = pathlib.Path(os.getcwd()).parent.absolute()
    backups_path = pathlib.Path(os.path.join(project_path, 'backups'))
    backup_path = pathlib.Path(os.path.join(backups_path, remote_folder))
    backup_path.mkdir(parents=True, exist_ok=True)

    file_list = os.listdir(project_path)
    for file in file_list:
        file_name = str(file)
        file_path = os.path.join(project_path, file_name)
        if not file_name in ['backups', '.git']:
            if os.path.isdir(file_path):
                shutil.copytree(file_path, os.path.join(backup_path, file_name))
            else:
                shutil.copy(file_path, os.path.join(backup_path, file_name))

    return backup_path


def extend_gitignore():
    
    try:
        with open(".gitignore", "r") as f:
            content = f.readlines()
    except FileNotFoundError:
        content = []

    additions = [
        ".sync*/*\n",
        "!.sync*/.last_modified.json\n",
        "!.sync*/.gdriveignore\n",
        "!.sync*/.parent_id.json\n"
    ]
    with open(".gitignore", "a") as f:
        for line in additions:
            if line not in content:
                f.writelines(line)


if __name__ == "__main__":
    response = sync_folder()
    # Sometimes we need to run twice, since first run yields error. As a
    # workaround we capture that error, return -1 and restart the process:
    if response == -1:
        print('--- restart required -> issue should be fixed in future ---')
        response = sync_folder()
