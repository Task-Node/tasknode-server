"""
Tests for model Foo
"""

from datetime import datetime
from database import get_connection_string, engine
from models.foo_models import Foo
from utils.test_utils import BaseTestCase
import pytest

from exceptions import TaskNodeException


class TestFoo(BaseTestCase):
    def test_foo(self):
        assert "foo" == "foo"
