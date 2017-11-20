from __future__ import absolute_import
from unittest import TestCase
import argparse
from ddsc.cmdparser import CommandParser, format_destination_path, DESTINATION_PATH_EXISTS_FMT
from mock import Mock, patch


def no_op():
    pass


class TestCommandParser(TestCase):
    def setUp(self):
        self.parsed_args = None

    def set_parsed_args(self, args):
        self.parsed_args = args

    def test_register_add_user_command_project_name(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_add_user_command(self.set_parsed_args)
        self.assertEqual(['add-user'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['add-user', '-p', 'myproj', '--user', 'joe123'])
        self.assertEqual('myproj', self.parsed_args.project_name)
        self.assertEqual(None, self.parsed_args.project_id)

    def test_register_add_user_command_project_id(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_add_user_command(self.set_parsed_args)
        self.assertEqual(['add-user'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['add-user', '-i', '123', '--user', 'joe123'])
        self.assertEqual(None, self.parsed_args.project_name)
        self.assertEqual('123', self.parsed_args.project_id)

    def test_register_remove_user_command_project_name(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_remove_user_command(self.set_parsed_args)
        self.assertEqual(['remove-user'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['remove-user', '-p', 'myproj', '--user', 'joe123'])
        self.assertEqual('myproj', self.parsed_args.project_name)
        self.assertEqual(None, self.parsed_args.project_id)

    def test_register_remove_user_command_project_id(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_remove_user_command(self.set_parsed_args)
        self.assertEqual(['remove-user'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['remove-user', '-i', '456', '--user', 'joe123'])
        self.assertEqual(None, self.parsed_args.project_name)
        self.assertEqual('456', self.parsed_args.project_id)

    def test_deliver_no_msg(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_deliver_command(self.set_parsed_args)
        self.assertEqual(['deliver'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['deliver', '-p', 'someproject', '--user', 'joe123'])
        self.assertEqual(None, self.parsed_args.msg_file)
        self.assertEqual('someproject', self.parsed_args.project_name)
        self.assertEqual(None, self.parsed_args.project_id)
        self.assertEqual(None, self.parsed_args.share_usernames)
        self.assertEqual(None, self.parsed_args.share_emails)

    def test_deliver_with_msg(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_deliver_command(self.set_parsed_args)
        self.assertEqual(['deliver'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['deliver', '-i', '123', '--user', 'joe123', '--msg-file', 'setup.py'])
        self.assertIn('setup(', self.parsed_args.msg_file.read())
        self.assertEqual(None, self.parsed_args.project_name)
        self.assertEqual('123', self.parsed_args.project_id)

    def test_deliver_with_share_users(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_deliver_command(self.set_parsed_args)
        self.assertEqual(['deliver'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['deliver', '-i', '123',
                                    '--user', 'joe123',
                                    '--share-users', 'bob555', 'tom666',
                                    '--share-emails', 'bob@bob.bob'])
        self.assertEqual(None, self.parsed_args.project_name)
        self.assertEqual('123', self.parsed_args.project_id)
        self.assertEqual(['bob555', 'tom666'], self.parsed_args.share_usernames)
        self.assertEqual(['bob@bob.bob'], self.parsed_args.share_emails)

    def test_share_no_msg(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_share_command(self.set_parsed_args)
        self.assertEqual(['share'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['share', '-p', 'someproject2', '--user', 'joe123'])
        self.assertEqual(None, self.parsed_args.msg_file)
        self.assertEqual('someproject2', self.parsed_args.project_name)
        self.assertEqual(None, self.parsed_args.project_id)

    def test_share_with_msg(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_share_command(self.set_parsed_args)
        self.assertEqual(['share'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['share', '-i', '456', '--user', 'joe123', '--msg-file', 'setup.py'])
        self.assertIn('setup(', self.parsed_args.msg_file.read())
        self.assertEqual(None, self.parsed_args.project_name)
        self.assertEqual('456', self.parsed_args.project_id)

    def test_list_command(self):
        func = Mock()
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_list_command(func)
        self.assertEqual(['list'], list(command_parser.subparsers.choices.keys()))

        # Test simple listing
        command_parser.run_command(['list'])
        func.assert_called()
        args, kwargs = func.call_args
        self.assertEqual(args[0].auth_role, None)
        self.assertEqual(args[0].project_name, None)
        self.assertEqual(args[0].long_format, False)
        func.reset_mock()

        # Test simple listing single project
        command_parser.run_command(['list', '-p', 'mouse'])
        func.assert_called()
        args, kwargs = func.call_args
        self.assertEqual(args[0].auth_role, None)
        self.assertEqual(args[0].project_name, 'mouse')

        # Test simple listing auth_role
        command_parser.run_command(['list', '--auth-role', 'project_admin'])
        func.assert_called()
        args, kwargs = func.call_args
        self.assertEqual(args[0].auth_role, 'project_admin')
        self.assertEqual(args[0].project_name, None)

    def test_list_command_long(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_list_command(self.set_parsed_args)
        command_parser.run_command(['list'])
        self.assertEqual(False, self.parsed_args.long_format)
        self.assertEqual(None, self.parsed_args.project_name)
        self.assertEqual(None, self.parsed_args.project_id)

        command_parser.run_command(['list', '-l'])
        self.assertEqual(True, self.parsed_args.long_format)
        self.assertEqual(None, self.parsed_args.project_name)
        self.assertEqual(None, self.parsed_args.project_id)

        command_parser.run_command(['list', '-i', '123', '-l'])
        self.assertEqual(True, self.parsed_args.long_format)
        self.assertEqual(None, self.parsed_args.project_name)
        self.assertEqual('123', self.parsed_args.project_id)

        command_parser.run_command(['list', '--project-id', '123', '-l'])
        self.assertEqual(True, self.parsed_args.long_format)
        self.assertEqual(None, self.parsed_args.project_name)
        self.assertEqual('123', self.parsed_args.project_id)

        command_parser.run_command(['list', '-p', 'mouse', '-l'])
        self.assertEqual(True, self.parsed_args.long_format)
        self.assertEqual('mouse', self.parsed_args.project_name)
        self.assertEqual(None, self.parsed_args.project_id)

        command_parser.run_command(['list', '--project-name', 'mouse', '-l'])
        self.assertEqual(True, self.parsed_args.long_format)
        self.assertEqual('mouse', self.parsed_args.project_name)
        self.assertEqual(None, self.parsed_args.project_id)

    def test_description(self):
        expected_description = 'DukeDSClient (1.0) Manage projects/folders/files in the duke-data-service'
        command_parser = CommandParser(version_str='1.0')
        self.assertEqual(expected_description, command_parser.parser.description)

    def test_register_download_command(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_download_command(self.set_parsed_args)
        self.assertEqual(['download'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['download', '-p', 'mouse'])
        self.assertEqual('mouse', self.parsed_args.project_name)
        self.assertEqual(False, self.parsed_args.resume)

    def test_register_download_command_resume(self):
        command_parser = CommandParser(version_str='1.0')
        command_parser.register_download_command(self.set_parsed_args)
        self.assertEqual(['download'], list(command_parser.subparsers.choices.keys()))
        command_parser.run_command(['download', '-p', 'mouse', '--resume'])
        self.assertEqual('mouse', self.parsed_args.project_name)
        self.assertEqual(True, self.parsed_args.resume)

    @patch("ddsc.cmdparser.os")
    def test_format_destination_path_raises_when_must_be_empty(self, mock_os):
        mock_os.path.exists.return_value = True
        mock_os.listdir.return_value = ['stuff']
        with self.assertRaises(argparse.ArgumentTypeError) as raisedException:
            format_destination_path(path='/tmp/somepath', must_be_empty=True)
        self.assertEqual(DESTINATION_PATH_EXISTS_FMT.format('/tmp/somepath'), str(raisedException.exception))

    @patch("ddsc.cmdparser.os")
    def test_format_destination_path_ok_when_can_be_empty(self, mock_os):
        mock_os.path.exists.return_value = True
        mock_os.listdir.return_value = ['stuff']
        format_destination_path(path='/tmp/somepath', must_be_empty=False)
