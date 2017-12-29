import os
from collections import OrderedDict
from ddsc.core.ddsapi import DataServiceAuth, DataServiceApi
from ddsc.config import create_config
from ddsc.core.remotestore import DOWNLOAD_FILE_CHUNK_SIZE
from ddsc.core.fileuploader import FileUploadOperations, ParallelChunkProcessor, ParentData
from ddsc.core.localstore import PathData
from ddsc.core.util import KindType
from future.utils import python_2_unicode_compatible


class DukeDS(object):
    @staticmethod
    def list_projects():
        return Session().list_projects()

    @staticmethod
    def list_files(project_name):
        return Session().list_files(project_name)

    @staticmethod
    def download_file(project_name, remote_path, local_path=None):
        return Session().download_file(project_name, remote_path, local_path)

    @staticmethod
    def upload_file(local_path, project_name, remote_path):
        return Session().upload_file(local_path, project_name, remote_path)


class Session(object):
    def __init__(self, config=create_config()):
        self.client = Client(config)
        self.projects = None

    def list_projects(self):
        self._cache_project_list_once()
        return [project.name for project in self.projects]

    def create_project(self, name, description):
        self.client.create_project(name, description)
        self.clear_project_cache()
        return name

    def list_files(self, project_name):
        project = self._get_project_for_name(project_name)
        file_path_dict = self._get_file_path_dict_for_project(project)
        return file_path_dict.keys()

    def download_file(self, project_name, remote_path, local_path=None):
        project = self._get_project_for_name(project_name)
        file = project.get_child_for_path(remote_path)
        file.download_to_path(local_path)

    def upload_file(self, local_path, project_name, remote_path):
        project = self._get_or_create_project(project_name)
        file_upload = FileUpload(self.client, project, remote_path, local_path)
        file_upload.run()

    def _get_or_create_project(self, project_name):
        try:
            return self._get_project_for_name(project_name)
        except ItemNotFound:
            project_description = project_name
            project = self.client.create_project(project_name, project_description)
            self.clear_project_cache()
            return project

    def _cache_project_list_once(self):
        if not self.projects:
            self.projects = self.client.get_projects()

    def clear_project_cache(self):
        self.projects = None

    def _get_project_for_name(self, project_name):
        self._cache_project_list_once()
        projects = [project for project in self.projects if project.name == project_name]
        if not projects:
            raise ItemNotFound("No project found with name {}".format(project_name))
        if len(projects) == 1:
            return projects[0]
        raise DuplicateNameError("Multiple projects found with name {}".format(project_name))

    @staticmethod
    def _get_file_path_dict_for_project(project):
        path_to_nodes = PathToFiles()
        path_to_nodes.add_paths_for_children_of_node(project)
        return path_to_nodes.paths


class Client(object):
    """
    Client that connects to the DDSConnection base on ~/.ddsclient configuration.
    This configuration can be customized by passing in a ddsc.config.Config object
    """
    def __init__(self, config=create_config()):
        """
        :param config: ddsc.config.Config: settings used to connect to DDSConnection
        """
        self.dds_connection = DDSConnection(config)

    def get_projects(self):
        """
        Get list of all projects user has access to.
        :return: [Project]: list of projects
        """
        return self.dds_connection.get_projects()

    def get_project_by_id(self, project_id):
        """
        Retrieve a single project.
        :param project_id:
        :return: Project
        """
        return self.dds_connection.get_project_by_id(project_id)

    def create_project(self, name, description):
        """
        Create a new project with the specified name and description
        :param name: str: name of the project
        :param description: str: description of the project
        :return: Project
        """
        return self.dds_connection.create_project(name, description)

    def get_folder_by_id(self, folder_id):
        """
        Return details about a folder with the specified uuid
        :param folder_id: str: uuid of the folder to fetch
        :return: Folder
        """
        return self.dds_connection.get_folder_by_id(folder_id)

    def get_file_by_id(self, file_id):
        """
        Return details about a file with the specified uuid
        :param file_id: str: uuid of the file to fetch
        :return: File
        """
        return self.dds_connection.get_file_by_id(file_id)


class DDSConnection(object):
    """
    Contains methods for accessing various DDSConnection API functionality
    """
    def __init__(self, config):
        """
        :param config: ddsc.config.Config: settings used to connect to DDSConnection
        """
        self.config = config
        self.data_service = DataServiceApi(DataServiceAuth(config), config.url)

    def _create_array_response(self, resp, array_item_constructor):
        items = resp.json()['results']
        return [array_item_constructor(self, data_dict) for data_dict in items]

    def _create_item_response(self, resp, item_constructor):
        data_dict = resp.json()
        return item_constructor(self, data_dict)

    def get_projects(self):
        """
        Get details for all projects you have access to in DDSConnection
        :return: [Project]: list of projects
        """
        return self._create_array_response(
            self.data_service.get_projects(),
            Project)

    def get_project_by_id(self, project_id):
        """
        Get details about project with the specified uuid
        :param project_id: str: uuid of the project to fetch
        :return: Project
        """
        return self._create_item_response(
            self.data_service.get_project_by_id(project_id),
            Project)

    def create_project(self, name, description):
        """
        Create a new project with the specified name and description
        :param name: str: name of the project to create
        :param description: str: description of the project to create
        :return: Project
        """
        return self._create_item_response(
            self.data_service.create_project(name, description),
            Project)

    def delete_project(self, project_id):
        """
        Delete the project with the specified uuid
        :param project_id: str: uuid of the project to delete
        """
        self.data_service.delete_project(project_id)

    def create_folder(self, folder_name, parent_kind_str, parent_uuid):
        """
        Create a folder under a particular parent
        :param folder_name: str: name of the folder to create
        :param parent_kind_str: str: kind of the parent of this folder
        :param parent_uuid: str: uuid of the parent of this folder (project or another folder)
        :return: Folder: folder metadata
        """
        return self._create_item_response(
            self.data_service.create_folder(folder_name, parent_kind_str, parent_uuid),
            Folder
        )

    def delete_folder(self, folder_id):
        """
        Delete the folder with the specified uuid
        :param folder_id: str: uuid of the folder to delete
        """
        self.data_service.delete_folder(folder_id)

    def get_project_children(self, project_id, name_contains=None):
        """
        Get direct files and folders of a project.
        :param project_id: str: uuid of the project to list contents
        :param name_contains: str: filter children based on a pattern
        :return: [File|Folder]: list of Files/Folders contained by the project
        """
        return self._create_array_response(
            self.data_service.get_project_children(
                project_id, name_contains
            ),
            DDSConnection._folder_or_file_constructor
        )

    def get_folder_children(self, folder_id, name_contains=None):
        """
        Get direct files and folders of a folder.
        :param folder_id: str: uuid of the folder
        :param name_contains: str: filter children based on a pattern
        :return: File|Folder
        """
        return self._create_array_response(
            self.data_service.get_folder_children(
                folder_id, name_contains
            ),
            DDSConnection._folder_or_file_constructor
        )

    def get_file_download(self, file_id):
        """
        Get a file download object that contains temporary url settings needed to download the contents of a file.
        :param file_id: str: uuid of the file
        :return: FileDownload
        """
        return self._create_item_response(
            self.data_service.get_file_url(file_id),
            FileDownload
        )

    def upload_file(self, local_path, project_id, parent_data, existing_file_id=None):
        """
        Upload a file under a specific location in DDSConnection possibly replacing an existing file.
        :param local_path: str: path to a local file to upload
        :param project_id: str: uuid of the project to add this file to
        :param parent_data: ParentData: info about the parent of this file
        :param existing_file_id: str: uuid of file to create a new version of (or None to create a new file)
        :return: File
        """
        path_data = PathData(local_path)
        hash_data = path_data.get_hash()
        file_upload_operations = FileUploadOperations(self.data_service, None)
        upload_id = file_upload_operations.create_upload(project_id, path_data, hash_data)
        context = UploadContext(self.config, self.data_service, upload_id, path_data)
        ParallelChunkProcessor(context).run()
        remote_file_data = file_upload_operations.finish_upload(upload_id, hash_data, parent_data, existing_file_id)
        return File(self, remote_file_data)

    @staticmethod
    def _folder_or_file_constructor(dds_connection, data_dict):
        """
        Create a File or Folder based on the kind value in data_dict
        :param dds_connection: DDSConnection
        :param data_dict: dict: payload received from DDSConnection API
        :return: File|Folder
        """
        kind = data_dict['kind']
        if kind == KindType.folder_str:
            return Folder(dds_connection, data_dict)
        elif data_dict['kind'] == KindType.file_str:
            return File(dds_connection, data_dict)

    def get_folder_by_id(self, folder_id):
        """
        Get folder details for a folder id.
        :param folder_id: str: uuid of the folder
        :return: Folder
        """
        return self._create_item_response(
            self.data_service.get_folder(folder_id),
            Folder
        )

    def get_file_by_id(self, file_id):
        """
        Get folder details for a file id.
        :param file_id: str: uuid of the file
        :return: File
        """
        return self._create_item_response(
            self.data_service.get_file(file_id),
            File
        )

    def delete_file(self, file_id):
        self.data_service.delete_file(file_id)


class BaseResponseItem(object):
    """
    Base class for responses from DDSConnection API converts dict into properties for subclasses.
    """
    def __init__(self, dds_connection, data_dict):
        """
        :param dds_connection: DDSConnection
        :param data_dict: dict: dictionary response from DDSConnection API
        """
        self.dds_connection = dds_connection
        self._data_dict = dict(data_dict)

    def __getattr__(self, key):
        """
        Return property from the dictionary passed to the constructor.
        """
        try:
            return self._data_dict[key]
        except KeyError:
            msg = "'{}' object has no attribute '{}'".format(self.__class__.__name__, key)
            raise AttributeError(msg)


@python_2_unicode_compatible
class Project(BaseResponseItem):
    """
    Contains project details based on DDSConnection API response
    """
    def __init__(self, dds_connection, data):
        """
        :param dds_connection: DDSConnection
        :param data: dict: dictionary response from DDSConnection API in project format
        """
        super(Project, self).__init__(dds_connection, data)

    def get_children(self):
        """
        Fetch the direct children of this project.
        :return: [File|Folder]
        """
        return self.dds_connection.get_project_children(self.id)

    def get_child_for_path(self, path):
        """
        Based on a remote path get a single remote child.
        :param path: str: path within a project specifying a file or folder to download
        :return: File|Folder
        """
        child_finder = ChildFinder(path, self)
        return child_finder.get_child()

    def create_folder(self, folder_name):
        """
        Create a new folder as a top level child of this project.
        :param folder_name: str: name of the folder to create
        :return: Folder
        """
        return self.dds_connection.create_folder(folder_name, KindType.project_str, self.id)

    def upload_file(self, local_path):
        """
        Upload a new file based on a file on the file system as a top level child of this project.
        :param local_path: str: path to a file to upload
        :return: File
        """
        parent_data = ParentData(self.kind, self.id)
        return self.dds_connection.upload_file(local_path, project_id=self.id, parent_data=parent_data)

    def delete(self):
        """
        Delete this project and it's children.
        """
        self.dds_connection.delete_project(self.id)

    def __str__(self):
        return u'{} id:{} name:{}'.format(self.__class__.__name__, self.id, self.name)


@python_2_unicode_compatible
class Folder(BaseResponseItem):
    """
    Contains folder details based on DDSConnection API response
    """
    def __init__(self, dds_connection, data):
        """
        :param dds_connection: DDSConnection
        :param data: dict: dictionary response from DDSConnection API in folder format
        """
        super(Folder, self).__init__(dds_connection, data)
        self.project_id = self.project['id']

    def get_children(self):
        """
        Fetch the direct children of this folder.
        :return: [File|Folder]
        """
        return self.dds_connection.get_folder_children(self.id)

    def create_folder(self, folder_name):
        """
        Create a new folder as a top level child of this folder.
        :param folder_name: str: name of the folder to create
        :return: Folder
        """
        return self.dds_connection.create_folder(folder_name, KindType.folder_str, self.id)

    def upload_file(self, local_path):
        """
        Upload a new file based on a file on the file system as a top level child of this folder.
        :param local_path: str: path to a file to upload
        :return: File
        """
        parent_data = ParentData(self.kind, self.id)
        return self.dds_connection.upload_file(local_path, project_id=self.project_id, parent_data=parent_data)

    def delete(self):
        """
        Delete this folder and it's children.
        """
        self.dds_connection.delete_folder(self.id)

    def __str__(self):
        return u'{} id:{} name:{}'.format(self.__class__.__name__, self.id, self.name)


@python_2_unicode_compatible
class File(BaseResponseItem):
    """
    Contains folder details based on DDSConnection API response
    """
    def __init__(self, dds_connection, data):
        """
        :param dds_connection: DDSConnection
        :param data: dict: dictionary response from DDSConnection API in folder format
        """
        super(File, self).__init__(dds_connection, data)
        self.project_id = self.project['id']

    def download_to_path(self, file_path):
        """
        Download the contents of this file to a local file path
        :param file_path: str: local filesystem path to write this file contents into, if none it will default to self.name
        """
        file_download = self.dds_connection.get_file_download(self.id)
        path = file_path
        if not path:
            path = self.name
        file_download.save_to_path(path)

    def delete(self):
        """
        Delete this file and it's children.
        """
        self.dds_connection.delete_file(self.id)

    def upload_new_version(self, file_path):
        """
        Upload a new version of this file.
        :param file_path: str: local filesystem path to write this file contents into
        :return: File
        """
        parent_data = ParentData(self.parent['kind'], self.parent['id'])
        return self.dds_connection.upload_file(file_path, project_id=self.project_id, parent_data=parent_data,
                                        existing_file_id=self.id)

    def __str__(self):
        return u'{} id:{} name:{}'.format(self.__class__.__name__, self.id, self.name)


class FileDownload(BaseResponseItem):
    """
    Contains file download url details based on DDSConnection API response
    """
    def __init__(self, dds_connection, data):
        """
        :param dds_connection: DDSConnection
        :param data: dict: dictionary response from DDSConnection API in file download url format
        """
        super(FileDownload, self).__init__(dds_connection, data)

    def _get_download_response(self):
        return self.dds_connection.data_service.receive_external(self.http_verb, self.host, self.url, self.http_headers)

    def save_to_path(self, file_path, chunk_size=DOWNLOAD_FILE_CHUNK_SIZE):
        """
        Save the contents of the remote file to a local path.
        :param file_path: str: file path
        :param chunk_size: chunk size used to write local file
        """
        response = self._get_download_response()
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)


class FileUpload(object):
    def __init__(self, client, project, remote_path, local_path):
        self.client = client
        self.project = project
        self.remote_path = remote_path
        self.local_path = local_path

    def run(self):
        parts = self.remote_path.split(os.sep)
        if len(parts) == 1:
            self._upload_to_parent(self.project)
        else:
            folder_names = parts[:-1]
            parent = self.project
            for folder_name in folder_names:
                folder = self._try_get_child(parent, folder_name)
                if not folder:
                    folder = parent.create_folder(folder_name)
                parent = folder
            self._upload_to_parent(parent)

    def _upload_to_parent(self, parent):
        child = self._try_get_child(parent, os.path.basename(self.remote_path))
        if child:
            print("New version" + parent.id)
            child.upload_new_version(self.local_path)
        else:
            print("upload file" + parent.id)
            parent.upload_file(self.local_path)

    @staticmethod
    def _try_get_child(parent, child_name):
        for child in parent.get_children():
            if child.name == child_name:
                return child
        return None


class ChildFinder(object):
    """
    Recursively looks for a child based on a path
    """
    def __init__(self, remote_path, node):
        """
        :param remote_path: path under a project in DDSConnection
        :param node: Project|Folder to find children under
        """
        self.remote_path = remote_path
        self.node = node

    def get_child(self):
        """
        Find file or folder at the remote_path
        :return: File|Folder
        """
        path_parts = self.remote_path.split(os.sep)
        return self._get_child_recurse(path_parts, self.node)

    def _get_child_recurse(self, path_parts, node):
        if not path_parts:
            return node
        head, tail = path_parts[0], path_parts[1:]
        for child in node.get_children():
            if child.name == head:
                return self._get_child_recurse(tail, child)
        raise ItemNotFound("No item at path {}".format(self.remote_path))


class PathToFiles(object):
    def __init__(self):
        self.paths = OrderedDict()

    def add_paths_for_children_of_node(self, node):
        self._child_recurse(node, '')

    def _child_recurse(self, node, parent_path):
        for child in node.get_children():
            path = self._make_path(parent_path, child)
            if child.kind == KindType.file_str:
                self.paths[path] = child
            else:
                self._child_recurse(child, path)

    @staticmethod
    def _make_path(parent_path, child):
        if parent_path:
            return os.path.join(parent_path, child.name)
        else:
            return child.name


class UploadContext(object):
    """
    Contains settings and monitoring methods used while uploading a file.
    """
    def __init__(self, config, data_service, upload_id, path_data):
        self.config = config
        self.data_service = data_service
        self.upload_id = upload_id
        self.watcher = self
        self.local_file = UploadFileInfo(path_data)

    def transferring_item(self, item, increment_amt):
        pass

    def start_waiting(self):
        pass

    def done_waiting(self):
        pass


class UploadFileInfo(object):
    """
    Settings about a file being uploaded
    """
    def __init__(self, path_data):
        """
        :param path_data: PathData
        """
        self.size = path_data.size()
        self.path = path_data.path
        self.kind = KindType.file_str


class ItemNotFound(Exception):
    pass


class DuplicateNameError(Exception):
    pass
