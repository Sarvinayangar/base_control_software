from ftplib import FTP_TLS
import os
from datetime import datetime
import zipfile
import gzip
import shutil
import io

def RemoteFileSize(ftps, Filename):
    if ftps.size(Filename) is None:
            return ftps.size(Filename)  # Get file size
    return None # Get file size

def Compress(Input, Output):
    with open(Input, 'rb') as ffin:
        with gzip.open(Output, 'wb') as ffout:
            shutil.copyfileobj(ffin, ffout)

def CompressFolder(local_folder, output_zip):
    """Compress a folder into a ZIP file."""
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(local_folder):
            for file in files:
                local_file_path = os.path.join(root, file)
                arcname = os.path.relpath(local_file_path, local_folder)
                zipf.write(local_file_path, arcname)

def Connect(LocalFile, Hostname, Username, Password, Savefolder):
    """ Establishes a secure FTP connection and navigates to the Uploads directory. """
    # Check if the local directory exists
    if not os.path.exists(LocalFile):
        raise FileNotFoundError(f"Local directory '{LocalFile}' does not exist.")

    # Establish a connection to the FTP server with TLS
    ftps = FTP_TLS(Hostname)
    ftps.auth()       # Secure the control connection
    ftps.prot_p()     # Switch to secure data connection
    ftps.login(user=Username, passwd=Password)
    print(f"Successfully connected to {Hostname} as {Username}.")

    # List directories on the server
    print("Listing directories on the server:")
    Folders = []

    def list_folders(line, FolderList):
        parts = line.split()
        if len(parts) > 8:  # Ensure the line contains expected format
            name = parts[-1]
            if line.startswith('d'):  # Indicates a directory in UNIX-style listing
                FolderList.append(name)

    ftps.retrlines('LIST', lambda line: list_folders(line, Folders))

    if Folders:
        print("Directories:")
        for File in Folders:
            print(File)
        
        # Enter the first directory
        EnterFolder = "UCLH"
        print(f"\nEntering the first directory: {EnterFolder}")
        ftps.cwd(EnterFolder)

        # List subdirectories within the first directory
        print(f"\nListing directories within {EnterFolder}:")
        SubFolders = []
        ftps.retrlines('LIST', lambda line: list_folders(line, SubFolders))

        if SubFolders:
            for folders in SubFolders:
                print(folders)
        else:
            print("No Folders found.")
    else:
        print("No folder found on the server.")


    # Check if the folder exists and create it if not
    if SaveFolder not in SubFolders:
        print(f"There is no folder",SaveFolder,".Creating and directing into this folder")
        ftps.mkd(SaveFolder)
    else:
        print(f"Folder",SaveFolder,"already exists.")
        ftps.cwd(SaveFolder)
        print(f"Changed to",SaveFolder,"Folder")
    return ftps

def ManageZipFolder(ftps, LocalFile, ZipFolde.r):
    """Uploads files to the ZipFolder, replaces files if needed, then re-compresses."""
    remote_zip = f"{ZipFolder}.zip"

    # Upload or replace files
    UploadFiles(ftps, LocalFile)

    # Navigate back to compress the updated folder
    ftps.cwd(remote_zip)
    print(f"Compressing '{ZipFolder}' into '{remote_zip}' remotely...")

    # Compress the folder locally first before uploading it
    temp_zip = os.path.join(LocalFile, remote_zip)
    CompressFolder(LocalFile, temp_zip)

    # Upload the updated ZIP file
    with open(temp_zip, "rb") as file:
        ftps.storbinary(f"STOR {remote_zip}", file)
    print(f"Uploaded updated {remote_zip}.")

    # Cleanup local temp zip
    os.remove(temp_zip)

    print("Upload and compression process complete.")

def UploadFiles(ftps, LocalFile):
    """ Uploads files from LocalFile directory to the current FTP directory. """
    Log = os.path.join(LocalFile, "upload_log.txt")
    

    # Set connection to binary mode again to be safe
    ftps.sendcmd("TYPE I")

    # Ensure log file exists and has a header
    if not os.path.exists(Log) or os.stat(Log).st_size == 0:
        with open(Log, "w") as LogFile:
            LogFile.write("Upload Log:\n")
            LogFile.write(f"{'Timestamp':<25}{'File':<30}{'Status':<10}\n")
            LogFile.write("-" * 65 + "\n")

    # Upload or replace files in the local directory
    for Filename in os.listdir(LocalFile):
        LocalPath = os.path.join(LocalFile, Filename)
        
        # Ensure file exists
        if not os.path.isfile(LocalPath):
            print(f"Skipping {Filename} (not a file)")
            continue
        
        print(f"Processing {Filename}...")  # Debugging print

        RemoteSize = RemoteFileSize(ftps, Filename)
        LocalSize = os.path.getsize(LocalPath)

        # If file doesn't exist on server, upload it
        if RemoteSize is None:
                with open(LocalPath, "rb") as file:
                    ftps.storbinary(f"STOR {Filename}", file)
                print(LocalPath,"was uploaded successfully as",Filename)
                with open(Log, "a") as LogFile:
                    LogFile.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<25}{Filename:<30}Uploaded\n")

            # If local file is larger, replace the remote file
        elif LocalSize > RemoteSize:
                with open(LocalPath, "rb") as file:
                    ftps.storbinary(f"STOR {Filename}", file)
                print(Filename,"was replaced.")
                with open(Log, "a") as LogFile:
                    LogFile.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<25}{Filename:<30}Replaced\n")

            # If remote file is larger, skip the upload
        else:
                print(f"File",Filename,"was Skipped.")
                with open(Log, "a") as LogFile:
                    LogFile.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<25}{Filename:<30}Skipped\n")

    # Close FTP connection
    ftps.quit()

if __name__ == "__main__":
    LocalFile = r"C:\Users\sebas\Documents\Uni\Testing"
    SaveFolder = "Testing2"
    ZipFolder = "Testing"
    
    # Ensure Connect function is defined
    ftps = Connect(LocalFile, "nikoleta.medphys.ucl.ac.uk", "uclh", "\"Hh2jaKe29", SaveFolder)
    ManageZipFolder(ftps, LocalFile, ZipFolder)
    #UploadFiles(ftps, LocalFile,ZipFolder)
