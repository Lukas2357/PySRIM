# GDriveBackup

Python module to automate folder synchronization in Google Drive.

To initialize a folder for automatic sync, we need to copy syncinit.sh to your local folder and execute it:

```bash
wget https://github.com/Lukas2357/GDriveBackup/blob/master/syncinit.sh?raw=true -q -O syncinit.sh && bash syncinit.sh <FOLDER_NAME>
```

If FOLDER_NAME is present in the cloud or inside your local folder, these contents are considered, else the folders are freshly generated.

You will be guided through the rest of the process.

After that you can now move in FOLDER_NAME and call... \
-> 'bash .sync/sync.sh sync' to sync all files bidirectional (local->cloud, cloud->local) \
-> 'bash .sync/sync.sh sync_down' to just download from the cloud \
-> 'bash .sync/sync.sh sync_up' to just upload to the cloud \
-> 'bash .sync/sync.sh sync_clean' to delete remote and replace with local (only if remote messed up!)

For convenience include content of .sync/sync.sh in .bash_functions file and call 'sync' etc. directly in bash.
