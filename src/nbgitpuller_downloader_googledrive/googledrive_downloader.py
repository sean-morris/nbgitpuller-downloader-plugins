import re
import requests
from nbgitpuller.plugin_hook_specs import hookimpl
from nbgitpuller_downloader_plugins_util.plugin_helper import HandleFilesHelper

DOWNLOAD_URL = "https://docs.google.com/uc?export=download"


@hookimpl
def prepare_non_git_source_local_origin(git_puller_ref):
    """
    The function handles a set of compressed source files from Google Drive. The handle_files_helper function prepares a local origin git repo
    with the downloaded archive pointed to by git_puller_ref.git_url; the git_url points to a compressed archive publicly shared in GoogleDrive.
    The archive is downloaded, decompressed and pushed(in a git sense) to the local origin repo. Once the local origin repo is prepared,
    the nbgitpuller.GitPuller class pulls, merges, etc. the files into the users jupyter folder.

    :param git_puller_ref the reference to nbgitpuller's GitPuller class containing state information from the request
    :return two parameter json source_dir_name and local_origin_repo_path
    :rtype json object
    """
    repo = git_puller_ref.git_url
    yield "Determining type of archive...\n"
    response = get_response_from_drive(DOWNLOAD_URL, get_id(repo))
    ext = determine_file_extension_from_response(response)
    yield f"Archive is: {ext}\n"
    git_puller_ref.other_kw_args["extension"] = ext
    git_puller_ref.other_kw_args["download_func"] = download_archive_for_google

    hfh = HandleFilesHelper(git_puller_ref)
    output_info = yield from hfh.handle_files_helper()
    return output_info


def get_id(repo):
    """
    This gets the id of the file from the URL.

    :param str repo: the url to the compressed file contained the Google Drive id
    :return the Google Drive id of the file to be downloaded
    :rtype str
    """
    start_id_index = repo.index("d/") + 2
    end_id_index = repo.index("/view")
    return repo[start_id_index:end_id_index]


def get_confirm_token(session):
    """
    Google may include a confirm dialog if the file is too big. This retrieves the
    confirmation token and uses it to complete the download.

    :param session: used to the get the cookies from the response
    :type session requests.Session
    :return the cookie if found or None if not found
    :rtype str
    """
    cookies = session.cookies
    for key, cookie in cookies.items():
        if key.startswith('download_warning'):
            return cookie
    return None


def download_archive_for_google(source_url=None, temp_download_file=None):
    """
    This requests the file from the repo(url) given and saves it to the disk. This is executed
    in plugin_helper.py and note that the parameters to this function are the same as the standard
    parameters used by the standard download_archive function in plugin_helper. You may also note that I let
    plugin_helper handle passing the temp_download_file to the function

    :param str source_url: the url to compressed archive in GoogleDrove
    :param str temp_download_file: the path to save the requested file to
    """
    yield "Downloading archive ...\n"
    try:
        file_id = get_id(source_url)
        with requests.Session() as session:
            with session.get(DOWNLOAD_URL, params={'id': file_id}) as response:
                token = get_confirm_token(session)
                if token:
                    params = {'id': file_id, 'confirm': token}
                    response = session.get(DOWNLOAD_URL, params=params)
                with open(temp_download_file, 'ab') as f:
                    count_chunks = 1
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            count_chunks += 1
                            if count_chunks % 1000 == 0:
                                display = count_chunks / 1000
                                yield f"Downloading Progress ... {display}MB\n"
                            f.write(chunk)
        yield "Archive Downloaded....\n"
    except Exception as ex:
        raise ex


def get_response_from_drive(url, file_id):
    """
    You need to check to see that Google Drive has not asked the
    request to confirm that they disabled the virus scan on files that
    are bigger than 100MB(The size is mentioned online but, I did not see
    confirmation - something larger essentially). For large files, you have
    to request again but this time putting the 'confirm=XXX' as a query
    parameter.

    :param str url: the Google Drive download URL
    :param str file_id: the Google Drive id of the file to download
    :return response object
    :rtype json object
    """
    with requests.Session() as session:
        with session.get(url, params={'id': file_id}) as response:
            token = get_confirm_token(session)
            if token:
                params = {'id': file_id, 'confirm': token}
                response = session.get(url, params=params)
                return response
            return response


def determine_file_extension_from_response(response):
    """
    This retrieves the file extension from the response.
    :param response the response object from the download
    :type response: requests.Response
    :return the extension indicating the file compression(e.g. zip, tgz)
    :rtype str
    """
    content_disposition = response.headers.get('content-disposition')
    ext = None
    if content_disposition:
        file_name = re.findall("filename\\*?=([^;]+)", content_disposition)
        file_name = file_name[0].strip().strip('"')
        ext = file_name.split(".")[1]

    if ext is None:
        message = f"Could not determine compression type of: {content_disposition}"
        raise Exception(message)
    return ext
