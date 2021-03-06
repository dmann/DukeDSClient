from unittest import TestCase
import pickle
import multiprocessing
from ddsc.core.projectuploader import UploadSettings, UploadContext, ProjectUploadDryRun, CreateProjectCommand, \
    upload_project_run
from ddsc.core.util import KindType
from ddsc.core.remotestore import ProjectNameOrId
from mock import MagicMock, Mock


class FakeDataServiceApi(object):
    def __init__(self):
        self.auth = FakeDataServiceAuth()


class FakeDataServiceAuth(object):
    def get_auth_data(self):
        return ()


class TestUploadContext(TestCase):
    def test_can_pickle(self):
        """Make sure we can pickle context since it must be passed to another process."""
        settings = UploadSettings(None, FakeDataServiceApi(), None, ProjectNameOrId.create_from_name('mouse'), None)
        params = ('one', 'two', 'three')
        context = UploadContext(settings, params, multiprocessing.Manager().Queue(), 12)
        pickle.dumps(context)

    def test_start_waiting(self):
        mock_message_queue = MagicMock()
        context = UploadContext(settings=MagicMock(),
                                params=[],
                                message_queue=mock_message_queue,
                                task_id=12)
        context.start_waiting()
        mock_message_queue.put.assert_called_with((12, True))

    def test_done_waiting(self):
        mock_message_queue = MagicMock()
        context = UploadContext(settings=MagicMock(),
                                params=[],
                                message_queue=mock_message_queue,
                                task_id=13)
        context.done_waiting()
        mock_message_queue.put.assert_called_with((13, False))


class TestProjectUploadDryRun(TestCase):
    def test_single_empty_non_existant_directory(self):
        local_file = MagicMock(kind=KindType.folder_str, children=[], path='joe', remote_id=None)
        local_project = MagicMock(kind=KindType.project_str, children=[local_file])
        upload_dry_run = ProjectUploadDryRun()
        upload_dry_run.run(local_project)
        self.assertEqual(['joe'], upload_dry_run.upload_items)

    def test_single_empty_existing_directory(self):
        local_file = MagicMock(kind=KindType.folder_str, children=[], path='joe', remote_id='abc')
        local_project = MagicMock(kind=KindType.project_str, children=[local_file])
        upload_dry_run = ProjectUploadDryRun()
        upload_dry_run.run(local_project)
        self.assertEqual([], upload_dry_run.upload_items)

    def test_some_files(self):
        local_file1 = MagicMock(kind=KindType.file_str, path='joe.txt', need_to_send=True)
        local_file2 = MagicMock(kind=KindType.file_str, path='data.txt', need_to_send=False)
        local_file3 = MagicMock(kind=KindType.file_str, path='results.txt', need_to_send=True)
        local_project = MagicMock(kind=KindType.project_str, children=[local_file1, local_file2, local_file3])
        upload_dry_run = ProjectUploadDryRun()
        upload_dry_run.run(local_project)
        self.assertEqual(['joe.txt', 'results.txt'], upload_dry_run.upload_items)

    def test_nested_directories(self):
        local_file1 = MagicMock(kind=KindType.file_str, path='/data/2017/08/flyresults/joe.txt', need_to_send=True)
        local_file2 = MagicMock(kind=KindType.file_str, path='/data/2017/08/flyresults/data.txt', need_to_send=False)
        local_file3 = MagicMock(kind=KindType.file_str, path='/data/2017/08/flyresults/results.txt', need_to_send=True)
        grandchild_folder = MagicMock(kind=KindType.folder_str,
                                      path="/data/2017/08/flyresults",
                                      children=[local_file1, local_file2, local_file3],
                                      remote_id=None)
        child_folder = MagicMock(kind=KindType.folder_str,
                                 path="/data/2017/08",
                                 children=[grandchild_folder],
                                 remote_id=None)
        parent_folder = MagicMock(kind=KindType.folder_str,
                                  path="/data/2017",
                                  children=[child_folder],
                                  remote_id=None)
        local_project = MagicMock(kind=KindType.project_str, children=[parent_folder])
        upload_dry_run = ProjectUploadDryRun()
        upload_dry_run.run(local_project)
        expected_results = [
            '/data/2017',
            '/data/2017/08',
            '/data/2017/08/flyresults',
            '/data/2017/08/flyresults/joe.txt',
            '/data/2017/08/flyresults/results.txt',
        ]
        self.assertEqual(expected_results, upload_dry_run.upload_items)

    def test_nested_directories_skip_parents(self):
        local_file1 = MagicMock(kind=KindType.file_str, path='/data/2017/08/flyresults/joe.txt', need_to_send=True)
        local_file2 = MagicMock(kind=KindType.file_str, path='/data/2017/08/flyresults/data.txt', need_to_send=False)
        local_file3 = MagicMock(kind=KindType.file_str, path='/data/2017/08/flyresults/results.txt', need_to_send=True)
        grandchild_folder = MagicMock(kind=KindType.folder_str,
                                      path="/data/2017/08/flyresults",
                                      children=[local_file1, local_file2, local_file3],
                                      remote_id=None)
        child_folder = MagicMock(kind=KindType.folder_str,
                                 path="/data/2017/08",
                                 children=[grandchild_folder],
                                 remote_id='355')
        parent_folder = MagicMock(kind=KindType.folder_str,
                                  path="/data/2017",
                                  children=[child_folder],
                                  remote_id='123')
        local_project = MagicMock(kind=KindType.project_str, children=[parent_folder])
        upload_dry_run = ProjectUploadDryRun()
        upload_dry_run.run(local_project)
        expected_results = [
            '/data/2017/08/flyresults',
            '/data/2017/08/flyresults/joe.txt',
            '/data/2017/08/flyresults/results.txt',
        ]
        self.assertEqual(expected_results, upload_dry_run.upload_items)


class TestCreateProjectCommand(TestCase):
    def test_constructor_fails_for_id(self):
        mock_settings = Mock(project_name_or_id=ProjectNameOrId.create_from_project_id('123'))
        mock_local_project = Mock()
        with self.assertRaises(ValueError):
            CreateProjectCommand(mock_settings, mock_local_project)

    def test_constructor_ok_for_name(self):
        mock_settings = Mock(project_name_or_id=ProjectNameOrId.create_from_name('mouse'))
        mock_local_project = Mock()
        CreateProjectCommand(mock_settings, mock_local_project)

    def test_upload_project_run(self):
        mock_data_service = Mock()
        mock_data_service.create_project.return_value = MagicMock()
        mock_upload_context = Mock()
        mock_upload_context.make_data_service.return_value = mock_data_service
        mock_upload_context.project_name_or_id = ProjectNameOrId.create_from_name('mouse')
        upload_project_run(mock_upload_context)
        mock_data_service.create_project.assert_called_with('mouse', 'mouse')
