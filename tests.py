#!/usr/bin/env python
#
# Copyright 2015 SUSE Linux GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# py26 compat
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import imp


# NOTE(toabctl): Hack to import non-module file for testing
pr = imp.load_source("python_requires", "python_requires")


class SanitizeRequirementsTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual({}, pr.sanitize_requirements(""))

    def test_single_wihtout_version(self):
        self.assertEqual({"python-xyz": None},
                         pr.sanitize_requirements("xyz"))

    def test_multiple_without_version(self):
        self.assertEqual({"python-xyz": None,
                          "python-foo": None,
                          "python-bar": None},
                         pr.sanitize_requirements("xyz\nfoo\nbar"))

    def test_single_with_version(self):
        self.assertEqual({"python-xyz": "1"},
                         pr.sanitize_requirements("xyz>=1"))
        self.assertEqual({"python-xyz": "1.2.3"},
                         pr.sanitize_requirements("xyz >= 1.2.3"))

    def test_multiple_with_version(self):
        self.assertEqual({"python-xyz": "1",
                          "python-foo": "3.1"},
                         pr.sanitize_requirements("xyz>=1\nfoo==3.1"))
        self.assertEqual({"python-xyz": "1.2.3",
                          "python-foo": "3.1"},
                         pr.sanitize_requirements("xyz >= 1.2.3\nfoo == 3.1"))

    def test_starting_with_python(self):
        """something like python-foo is python-python-foo as
        spec requirement"""
        self.assertEqual({"python-python-xyz": None},
                         pr.sanitize_requirements("python-xyz"))

    def test_with_ending_client(self):
        """special case for the OpenStack clients.
        Avoid double python-python"""
        self.assertEqual({"python-xyzclient": None},
                         pr.sanitize_requirements("python-xyzclient"))
        self.assertEqual({"python-xyz-client": None},
                         pr.sanitize_requirements("python-xyz-client"))
        self.assertEqual({"python-xyzclient": None},
                         pr.sanitize_requirements("xyzclient"))

    def test_lowest_version(self):
        """select lowest version if multiple versions given"""
        self.assertEqual({"python-xyz": "1",
                          "python-foo": "3.1"},
                         pr.sanitize_requirements("xyz>=1,>=2\nfoo>=4,>=3.1"))

    def test_ignore_list(self):
        self.assertEqual({},
                         pr.sanitize_requirements("coverage>=1\nsetuptools"))
        self.assertEqual({},
                         pr.sanitize_requirements(
                             "hacking>=0.10.0,<0.11\nqpid-python"))


class UpdateRequiresCompleteTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual({"python-foo": ("2.0", "mysrc")},
                         pr.update_requires_complete({},
                                                     {"python-foo": "2.0"},
                                                     "mysrc"))

    def test_update(self):
        self.assertEqual({"python-foo": ("2.0", "mysrc")},
                         pr.update_requires_complete(
                             {"python-foo": ("5.0", "initsrc")},
                             {"python-foo": "2.0"}, "mysrc"))


if __name__ == '__main__':
    unittest.main()
