from __future__ import absolute_import
from unittest import TestCase
from ddsc.ddsclient import BaseCommand, UploadCommand, ListCommand, DownloadCommand
from ddsc.ddsclient import ShareCommand, DeliverCommand, read_argument_file_contents
from mock import patch, MagicMock, Mock, call


class TestBaseCommand(TestCase):
    def setUp(self):
        self.args_with_project_id = Mock(project_name=None, project_id='123')
        self.args_with_project_name = Mock(project_name='mouse', project_id=None)

    def test_project_name_or_id_from_args(self):
        project_name_or_id = BaseCommand.create_project_name_or_id_from_args(self.args_with_project_id)
        self.assertEqual('123', project_name_or_id.value)
        self.assertEqual(False, project_name_or_id.is_name)

        project_name_or_id = BaseCommand.create_project_name_or_id_from_args(self.args_with_project_name)
        self.assertEqual('mouse', project_name_or_id.value)
        self.assertEqual(True, project_name_or_id.is_name)

    @patch('ddsc.ddsclient.RemoteStore')
    def test_fetch_project(self, mock_remote_store):
        mock_config = MagicMock()
        base_cmd = BaseCommand(mock_config)
        base_cmd.fetch_project(self.args_with_project_id, must_exist=True, include_children=False)
        mock_remote_store.return_value.fetch_remote_project.assert_called()
        args, kwargs = mock_remote_store.return_value.fetch_remote_project.call_args
        project_name_or_id = args[0]
        self.assertEqual('123', project_name_or_id.value)
        self.assertEqual(False, project_name_or_id.is_name)
        self.assertEqual(True, kwargs['must_exist'])
        self.assertEqual(False, kwargs['include_children'])

    @patch('ddsc.ddsclient.RemoteStore')
    def test_make_user_list(self, mock_remote_store):
        mock_config = MagicMock()
        base_cmd = BaseCommand(mock_config)
        mock_remote_store.return_value.fetch_all_users.return_value = [
            Mock(username='joe', email='joe@joe.joe'),
            Mock(username='bob', email='bob@bob.bob'),
            Mock(username='tim', email='tim@tim.tim'),
        ]

        # Find users by username
        results = base_cmd.make_user_list(emails=None, usernames=[
            'joe',
            'bob'
        ])
        self.assertEqual([user.email for user in results], ['joe@joe.joe', 'bob@bob.bob'])

        # Find users by email
        results = base_cmd.make_user_list(emails=['joe@joe.joe'], usernames=None)
        self.assertEqual([user.username for user in results], ['joe'])

        # Should get an error for invalid emails or usernames
        with self.assertRaises(ValueError) as raisedError:
            base_cmd.make_user_list(emails=['no@no.no'], usernames=['george'])
        self.assertEqual('Unable to find users for the following email/usernames: no@no.no,george',
                         str(raisedError.exception))


class TestUploadCommand(TestCase):
    @patch("ddsc.ddsclient.ProjectUpload")
    def test_without_dry_run(self, mock_project_upload):
        cmd = UploadCommand(MagicMock())
        args = Mock()
        args.project_name = "test"
        args.project_id = None
        args.folders = ["data", "scripts"]
        args.follow_symlinks = False
        args.dry_run = False
        cmd.run(args)
        args, kwargs = mock_project_upload.call_args
        self.assertEqual('test', args[1].get_name_or_raise())
        self.assertFalse(mock_project_upload.return_value.dry_run_report.called)
        self.assertTrue(mock_project_upload.return_value.get_upload_report.called)

    @patch("ddsc.ddsclient.ProjectUpload")
    def test_without_dry_run_project_id(self, mock_project_upload):
        cmd = UploadCommand(MagicMock())
        args = Mock()
        args.project_name = None
        args.project_id = '123'
        args.folders = ["data", "scripts"]
        args.follow_symlinks = False
        args.dry_run = False
        cmd.run(args)
        args, kwargs = mock_project_upload.call_args
        self.assertEqual('123', args[1].get_id_or_raise())
        self.assertFalse(mock_project_upload.return_value.dry_run_report.called)
        self.assertTrue(mock_project_upload.return_value.get_upload_report.called)

    @patch("ddsc.ddsclient.ProjectUpload")
    def test_with_dry_run(self, FakeProjectUpload):
        cmd = UploadCommand(MagicMock())
        args = Mock()
        args.project_name = "test"
        args.project_id = None
        args.folders = ["data", "scripts"]
        args.follow_symlinks = False
        args.dry_run = True
        cmd.run(args)
        self.assertTrue(FakeProjectUpload().dry_run_report.called)
        self.assertFalse(FakeProjectUpload().get_upload_report.called)


class TestDownloadCommand(TestCase):
    @patch('ddsc.ddsclient.RemoteStore')
    @patch("ddsc.ddsclient.ProjectDownload")
    def test_run_project_name(self, mock_project_download, mock_remote_store):
        @patch('ddsc.ddsclient.RemoteStore')
        @patch('ddsc.ddsclient.ProjectDownload')
        def test_run_project_id(self, mock_project_download, mock_remote_store):
            cmd = DownloadCommand(MagicMock())
            args = Mock()
            args.project_name = 'mouse'
            args.project_id = None
            args.include_paths = None
            args.exclude_paths = None
            cmd.run(args)
            mock_remote_store.return_value.fetch_remote_project.assert_called()
            args, kwargs = mock_remote_store.return_value.fetch_remote_project.call_args
            self.assertEqual('mouse', args[0].get_name_or_raise())
            mock_project_download.return_value.run.assert_called()

    @patch('ddsc.ddsclient.RemoteStore')
    @patch('ddsc.ddsclient.ProjectDownload')
    def test_run_project_id(self, mock_project_download, mock_remote_store):
        cmd = DownloadCommand(MagicMock())
        args = Mock()
        args.project_name = None
        args.project_id = '123'
        args.include_paths = None
        args.exclude_paths = None
        args.folder = '/tmp/stuff'
        cmd.run(args)
        mock_remote_store.return_value.fetch_remote_project.assert_called()
        args, kwargs = mock_remote_store.return_value.fetch_remote_project.call_args
        self.assertEqual('123', args[0].get_id_or_raise())
        mock_project_download.return_value.run.assert_called()


class TestShareCommand(TestCase):
    @patch('ddsc.ddsclient.RemoteStore')
    @patch('ddsc.ddsclient.D4S2Project')
    def test_run_no_message(self, mock_d4s2_project, mock_remote_store):
        cmd = ShareCommand(MagicMock())
        myargs = Mock(project_name='mouse', email=None, username='joe123', force_send=False,
                      auth_role='project_viewer', msg_file=None)
        cmd.run(myargs)
        args, kwargs = mock_d4s2_project().share.call_args
        project, to_user, force_send, auth_role, message = args
        self.assertEqual(project, mock_remote_store.return_value.fetch_remote_project.return_value)
        self.assertEqual('project_viewer', auth_role)
        self.assertEqual('', message)
        args, kwargs = mock_remote_store.return_value.fetch_remote_project.call_args
        self.assertEqual('mouse', args[0].get_name_or_raise())

    @patch('ddsc.ddsclient.RemoteStore')
    @patch('ddsc.ddsclient.D4S2Project')
    def test_run_message(self, mock_d4s2_project, mock_remote_store):
        with open('setup.py') as message_infile:
            cmd = ShareCommand(MagicMock())
            myargs = Mock(project_name=None, project_id='123', email=None, username='joe123', force_send=False,
                          auth_role='project_viewer', msg_file=message_infile)
            cmd.run(myargs)
            args, kwargs = mock_d4s2_project().share.call_args
            project, to_user, force_send, auth_role, message = args
            self.assertEqual(project, mock_remote_store.return_value.fetch_remote_project.return_value)
            self.assertEqual('project_viewer', auth_role)
            self.assertIn('setup(', message)
            args, kwargs = mock_remote_store.return_value.fetch_remote_project.call_args
            self.assertEqual('123', args[0].get_id_or_raise())


class TestDeliverCommand(TestCase):
    @patch('ddsc.ddsclient.RemoteStore')
    @patch('ddsc.ddsclient.D4S2Project')
    def test_run_no_message(self, mock_d4s2_project, mock_remote_store):
        cmd = DeliverCommand(MagicMock())
        myargs = Mock(project_name='mouse',
                      project_id=None,
                      email=None,
                      resend=False,
                      username='joe123',
                      share_usernames=[],
                      share_emails=[],
                      skip_copy_project=True,
                      include_paths=None,
                      exclude_paths=None,
                      msg_file=None)
        cmd.run(myargs)
        args, kwargs = mock_d4s2_project().deliver.call_args
        project, new_project_name, to_user, share_users, force_send, path_filter, message = args
        self.assertEqual(project, mock_remote_store.return_value.fetch_remote_project.return_value)
        self.assertEqual(False, force_send)
        self.assertEqual('', message)
        args, kwargs = mock_remote_store.return_value.fetch_remote_project.call_args
        self.assertEqual('mouse', args[0].get_name_or_raise())

    @patch('ddsc.ddsclient.RemoteStore')
    @patch('ddsc.ddsclient.D4S2Project')
    def test_run_message(self, mock_d4s2_project, mock_remote_store):
        with open('setup.py') as message_infile:
            cmd = DeliverCommand(MagicMock())
            myargs = Mock(project_name=None,
                          project_id='456',
                          resend=False,
                          email=None,
                          username='joe123',
                          share_emails=[],
                          share_usernames=[],
                          skip_copy_project=True,
                          include_paths=None,
                          exclude_paths=None,
                          msg_file=message_infile)
            cmd.run(myargs)
            args, kwargs = mock_d4s2_project().deliver.call_args
            project, new_project_name, to_user, share_users, force_send, path_filter, message = args
            self.assertEqual(project, mock_remote_store.return_value.fetch_remote_project.return_value)
            self.assertEqual(False, force_send)
            self.assertIn('setup(', message)
            args, kwargs = mock_remote_store.return_value.fetch_remote_project.call_args
            self.assertEqual('456', args[0].get_id_or_raise())


class TestDDSClient(TestCase):
    def test_read_argument_file_contents(self):
        self.assertEqual('', read_argument_file_contents(None))
        with open("setup.py") as infile:
            self.assertIn("setup(", read_argument_file_contents(infile))


class TestListCommand(TestCase):
    @patch('sys.stdout.write')
    @patch('ddsc.ddsclient.RemoteStore')
    def test_print_project_list_details(self, mock_remote_store, mock_print):
        mock_remote_store.return_value.get_projects_details.return_value = [
            {'name': 'one', 'id': '123'},
            {'name': 'two', 'id': '456'},
            {'name': 'three', 'id': '456'},
        ]
        cmd = ListCommand(MagicMock())
        cmd.print_project_list_details(filter_auth_role=None, long_format=False)
        expected_calls = [
            call("one"),
            call("\n"),
            call("two"),
            call("\n"),
            call("three"),
            call("\n")
        ]
        self.assertEqual(expected_calls, mock_print.call_args_list)

    @patch('sys.stdout.write')
    @patch('ddsc.ddsclient.RemoteStore')
    def test_print_project_list_details_long_format(self, mock_remote_store, mock_print):
        mock_remote_store.return_value.get_projects_details.return_value = [
            {'name': 'one', 'id': '123'},
            {'name': 'two', 'id': '456'},
            {'name': 'three', 'id': '789'},
        ]
        cmd = ListCommand(MagicMock())
        cmd.print_project_list_details(filter_auth_role=None, long_format=True)
        expected_calls = [
            call("123\tone"),
            call("\n"),
            call("456\ttwo"),
            call("\n"),
            call("789\tthree"),
            call("\n")
        ]
        self.assertEqual(expected_calls, mock_print.call_args_list)

    @patch('sys.stdout.write')
    @patch('ddsc.ddsclient.RemoteStore')
    def test_pprint_project_list_details_with_auth_role(self, mock_remote_store, mock_print):
        mock_remote_store.return_value.get_projects_with_auth_role.return_value = [
            {'name': 'mouse', 'id': '123'},
            {'name': 'ant', 'id': '456'},
        ]
        cmd = ListCommand(MagicMock())
        cmd.print_project_list_details(filter_auth_role='project_admin', long_format=False)
        expected_calls = [
            call("mouse"),
            call("\n"),
            call("ant"),
            call("\n")
        ]
        self.assertEqual(expected_calls, mock_print.call_args_list)

    @patch('sys.stdout.write')
    @patch('ddsc.ddsclient.RemoteStore')
    def test_print_project_list_details_with_auth_role_long_format(self, mock_remote_store, mock_print):
        mock_remote_store.return_value.get_projects_with_auth_role.return_value = [
            {'name': 'mouse', 'id': '123'},
            {'name': 'ant', 'id': '456'},
        ]
        cmd = ListCommand(MagicMock())
        cmd.print_project_list_details(filter_auth_role='project_admin', long_format=True)
        expected_calls = [
            call("123\tmouse"),
            call("\n"),
            call("456\tant"),
            call("\n")
        ]
        self.assertEqual(expected_calls, mock_print.call_args_list)

    def test_get_project_info_line(self):
        project_dict = {
            'id': '123',
            'name': 'mouse'
        }
        self.assertEqual('mouse', ListCommand.get_project_info_line(project_dict, False))
        self.assertEqual('123\tmouse', ListCommand.get_project_info_line(project_dict, True))
