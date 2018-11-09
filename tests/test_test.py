import argparse
import tempfile
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from rpdk.cli import main
from rpdk.test import local_lambda, temporary_ini_file

RANDOM_INI = "pytest_SOYPKR.ini"
EXPECTED_PYTEST_ARGS = ["--pyargs", "rpdk.contract.suite", "-c", RANDOM_INI]


@contextmanager
def mock_temporary_ini_file():
    yield RANDOM_INI


def test_test_command_help(capsys):
    # also mock other transports here
    with patch("rpdk.test.local_lambda", autospec=True) as mock_local_lambda:
        main(args_in=["test"])
    out, _ = capsys.readouterr()
    assert "--help" in out
    mock_local_lambda.assert_not_called()


def test_test_command_local_lambda_help(capsys):
    with patch("rpdk.test.local_lambda", autospec=True) as mock_local_lambda:
        with pytest.raises(SystemExit):
            main(args_in=["test", "local-lambda"])
    _, err = capsys.readouterr()
    assert "usage" in err
    mock_local_lambda.assert_not_called()


def test_test_command_args():
    with patch("rpdk.test.local_lambda", autospec=True) as mock_lambda_command:
        test_resource_file = tempfile.NamedTemporaryFile()
        test_updated_resource_file = tempfile.NamedTemporaryFile()
        test_resource_def_file = tempfile.NamedTemporaryFile()
        main(
            args_in=[
                "test",
                "local-lambda",
                test_resource_file.name,
                test_updated_resource_file.name,
                test_resource_def_file.name,
            ]
        )

    mock_lambda_command.assert_called_once()
    args, _ = mock_lambda_command.call_args
    argparse_namespace = args[0]
    assert argparse_namespace.endpoint == "http://127.0.0.1:3001"
    assert argparse_namespace.function_name == "Handler"
    assert argparse_namespace.resource_file.name == test_resource_file.name
    assert (
        argparse_namespace.updated_resource_file.name == test_updated_resource_file.name
    )
    assert argparse_namespace.resource_def_file.name == test_resource_def_file.name
    assert argparse_namespace.subparser_name == "test"


def test_local_lambda_command():
    with tempfile.TemporaryFile() as test_file:
        arg_namespace = argparse.Namespace(
            endpoint="http://127.0.0.1:3001",
            function_name="Handler",
            resource_file=test_file,
            updated_resource_file=test_file,
            resource_def_file=test_file,
            subparser_name="test",
            test_types=None,
        )
        mock_json = patch("json.load", return_value={}, autospec=True)
        mock_init = patch(
            "rpdk.test.temporary_ini_file", side_effect=mock_temporary_ini_file
        )
        with mock_json, mock_init, patch("pytest.main") as mock_pytest:
            local_lambda(arg_namespace)
    mock_pytest.assert_called_once()
    args, kwargs = mock_pytest.call_args
    assert len(args) == 1
    assert args[0] == EXPECTED_PYTEST_ARGS
    assert kwargs.keys() == {"plugins"}


def test_local_lambda_with_test_type():
    with tempfile.TemporaryFile() as test_file:
        arg_namespace = argparse.Namespace(
            endpoint="http://127.0.0.1:3001",
            function_name="Handler",
            resource_file=test_file,
            updated_resource_file=test_file,
            resource_def_file=test_file,
            subparser_name="test",
            test_types="TEST_TYPE",
        )
        mock_json = patch("json.load", return_value={}, autospec=True)
        mock_init = patch(
            "rpdk.test.temporary_ini_file", side_effect=mock_temporary_ini_file
        )
        with mock_json, mock_init, patch("pytest.main") as mock_pytest:
            local_lambda(arg_namespace)
    mock_pytest.assert_called_once()
    args, kwargs = mock_pytest.call_args
    assert len(args) == 1
    assert args[0] == EXPECTED_PYTEST_ARGS + ["-k", "TEST_TYPE"]
    assert kwargs.keys() == {"plugins"}


def test_temporary_ini_file():
    with temporary_ini_file() as path:
        with open(path, "r", encoding="utf-8") as f:
            assert "[pytest]" in f.read()