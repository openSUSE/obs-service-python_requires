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
import os
import shutil
import tempfile
import time


# NOTE(toabctl): Hack to import non-module file for testing
pr = imp.load_source("python_requires", "python_requires")


class SanitizeRequirementsTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual({}, pr.sanitize_requirements(""))

    def test_single_wihtout_version(self):
        self.assertEqual({"python-xyz": None},
                         pr.sanitize_requirements(["xyz"]))

    def test_multiple_without_version(self):
        self.assertEqual({"python-xyz": None,
                          "python-foo": None,
                          "python-bar": None},
                         pr.sanitize_requirements(["xyz", "foo", "bar"]))

    def test_single_with_version(self):
        self.assertEqual({"python-xyz": "1"},
                         pr.sanitize_requirements(["xyz>=1"]))
        self.assertEqual({"python-xyz": "1.2.3"},
                         pr.sanitize_requirements(["xyz >= 1.2.3"]))

    def test_multiple_with_version(self):
        self.assertEqual({"python-xyz": "1",
                          "python-foo": "3.1"},
                         pr.sanitize_requirements(["xyz>=1", "foo==3.1"]))
        self.assertEqual({"python-xyz": "1.2.3",
                          "python-foo": "3.1"},
                         pr.sanitize_requirements(
                             ["xyz >= 1.2.3", "foo == 3.1"]))

    def test_starting_with_python(self):
        """something like python-foo is python-python-foo as
        spec requirement"""
        self.assertEqual({"python-python-xyz": None},
                         pr.sanitize_requirements(["python-xyz"]))

    def test_with_ending_client(self):
        """special case for the OpenStack clients.
        Avoid double python-python"""
        self.assertEqual({"python-xyzclient": None},
                         pr.sanitize_requirements(["python-xyzclient"]))
        self.assertEqual({"python-xyz-client": None},
                         pr.sanitize_requirements(["python-xyz-client"]))
        self.assertEqual({"python-xyzclient": None},
                         pr.sanitize_requirements(["xyzclient"]))

    def test_lowest_version(self):
        """select lowest version if multiple versions given"""
        self.assertEqual({"python-xyz": "1",
                          "python-foo": "3.1"},
                         pr.sanitize_requirements(
                             ["xyz>=1,>=2", "foo>=4,>=3.1"]))

    def test_ignore_list(self):
        self.assertEqual({},
                         pr.sanitize_requirements(
                             ["coverage>=1", "setuptools"]))
        self.assertEqual({},
                         pr.sanitize_requirements(
                             ["hacking>=0.10.0,<0.11", "qpid-python"]))

    def test_ignore_parameters(self):
        self.assertEqual(
            {},
            pr.sanitize_requirements(
                ["-e git://github.com/openstack/horizon.git"]))

    def test_with_markers(self):
        """ allow markers in requirement lines"""
        self.assertEqual(
            {"python-futures": "3.0"},
            pr.sanitize_requirements(
                ["futures>=3.0;python_version=='2.7' or python_version=='2.6'"]
            )
        )

    def test_with_markers_and_lowest_version(self):
        """ allow markers in requirement lines;multiple versions specified"""
        self.assertEqual(
            {"python-futures": "3.0"},
            pr.sanitize_requirements(
                ["futures>=3.0,<=4.1,!=4.0;python_version=='2.7'"
                 "or python_version=='2.6'"]))

    def test_skip_windows_requires(self):
        """ Ignore requirements with win32 marker"""
        self.assertEqual(
            {"python-true": "1"},
            pr.sanitize_requirements(
                ["true>=1",
                 "wmi;sys_platform=='win32'"]))

    def test_skip_python3_requires(self):
        """ Ignore requirements with python3 marker"""
        self.assertEqual(
            {"python-ovs": "2.5.0"},
            pr.sanitize_requirements(
                ["ovs>=2.5.0;python_version=='2.7' # Apache-2.0",
                 "ovs>=2.6.0.dev1;python_version>='3.4' # Apache-2.0"])
        )


class TarballFinderTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(
            prefix='obs-service-python_requires-test-')
        os.chdir(self._tmpdir)

    def tearDown(self):
        shutil.rmtree(self._tmpdir)

    def test_get_tarball_candidate_1(self):
        print(self._tmpdir)
        open('oslo.db-2.0.0.tar.gz', 'a').close()
        time.sleep(0.01)
        open('oslo.db-1.12.0.tar.gz', 'a').close()
        self.assertEqual(pr.get_tarball_candidate(),
                         'oslo.db-1.12.0.tar.gz')

    def test_get_tarball_candidate_2(self):
        print(self._tmpdir)
        open('oslo.db-1.12.0.tar.gz', 'a').close()
        time.sleep(0.01)
        open('oslo.db-2.0.0.tar.gz', 'a').close()
        self.assertEqual(pr.get_tarball_candidate(),
                         'oslo.db-2.0.0.tar.gz')


class UpdateSpecFileTest(unittest.TestCase):
    def test_parse_update_spec_file_no_changes(self):
        content_init = "\n".join([
            "Name: testpackage",
            "Requires: pkg1",
            "BuildRequires: pkg1 >= 1.0",
        ])
        content_expected = content_init
        self.assertEqual(
            content_expected,
            pr.parse_update_spec_file(
                "testpackage.spec", content_init,
                {'install': {}, 'extras': {}, 'tests': {}})
        )

    def test_parse_update_spec_file(self):
        """update Requires, keep BuildRequires"""
        content_init = "\n".join([
            "Requires: python-pkg1 >=1.0",
            "BuildRequires: python-pkg1 >= 1.0",
        ])
        content_expected = "\n".join([
            "Requires: python-pkg1 >= 2.0",
            "BuildRequires: python-pkg1 >= 1.0",
        ])
        self.assertEqual(
            content_expected,
            pr.parse_update_spec_file(
                "testpackage.spec",
                content_init, {
                    "install_requires": [
                        "pkg1>=2.0",
                    ],
                }
            )
        )


class BaseTests(unittest.TestCase):
    def _get_metaextract_fixture_1(self):
        return {
            "install_requires": [
                "Paste",
                "ovs>=2.5.0",
                "ryu!=4.1,!=4.2,!=4.2.1,!=4.4,>=3.30",
            ],
            "tests_require": [
                "WebOb",
            ],
            "extras_require": {
                ":(python_version!='2.7')": [
                    "Routes!=2.0,!=2.3.0,>=1.12.3"
                ],
                ":(python_version>='3.4')": [
                    "ovs>=2.6.0.dev3"
                ],
                ":(python_version=='2.7')": [
                    "testpkg>=123"
                ],
                "postgresql": [
                    "SQLAlchemy<1.1.0,>=0.9.7",
                    "psycopg2"
                ],

            }
        }

    def _get_metaextract_fixture_2(self):
        return {
            "install_requires": None,
            "tests_require": None,
            "extras_require": None,
        }

    def test_get_complete_requires(self):
        # requirement (from metaextract's 'data' key)
        reqs = self._get_metaextract_fixture_1()
        self.assertDictEqual(
            pr._get_complete_requires(reqs),
            {
                "python-Paste": (None, "install"),
                "python-ovs": ("2.5.0", "install"),
                "python-ryu": ("3.30", "install"),
                "python-WebOb": (None, "tests"),
                "python-testpkg": ("123", "extras"),
                "python-SQLAlchemy": ("0.9.7", "extras"),
                "python-psycopg2": (None, "extras"),
            }
        )

    def test_get_complete_requires_empty(self):
        # requirement (from metaextract's 'data' key)
        reqs = self._get_metaextract_fixture_2()
        self.assertDictEqual(pr._get_complete_requires(reqs), {})


if __name__ == '__main__':
    unittest.main()
