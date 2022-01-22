from nbgitpuller.plugin_hook_specs import hookimpl
from nbgitpuller_downloader_plugins_util.plugin_helper import HandleFilesHelper


@hookimpl
def prepare_non_git_source_local_origin(git_puller_ref):
    """
    The function handles a set of source files from any publicly available URL. The handle_files_helper function prepares a local origin git repo
    with the downloaded archive pointed to by git_puller_ref.git_url; the git_url points to a compressed archive stored at any publicly available URL.
    The archive is downloaded, decompressed and pushed(in a git sense) to the local origin repo. Once the local origin repo is prepared,
    the nbgitpuller.GitPuller class pulls, merges, etc. the files into the users jupyter folder.

    :param git_puller_ref the reference to nbgitpuller's GitPuller class containing state information from the request
    :return two parameter json source_dir_name and local_origin_repo_path
    :rtype json object
    """
    hfh = HandleFilesHelper(git_puller_ref)
    output_info = yield from hfh.handle_files_helper()
    return output_info
