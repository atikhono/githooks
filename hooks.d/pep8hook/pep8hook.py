#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:expandtab
#
# ==================================================================
#
# Copyright (c) 2016, Parallels IP Holdings GmbH
# Released under the terms of MIT license (see LICENSE for details)
#
# ==================================================================
#
'''
pep8hook: A hook to check python scripts style with PEP8
'''

import os
import tempfile
import shutil
import logging
import hookutil


class Hook(object):
    def __init__(self, repo_dir, settings, params):
        self.repo_dir = repo_dir
        self.settings = settings
        self.params = params


    def check(self, branch, old_sha, new_sha):
        logging.debug("Run: branch=%s, old_sha=%s, new_sha=%s",
                      branch, old_sha, new_sha)
        logging.debug("params=%s", self.params)

        permit = True


        log = hookutil.parse_git_log(self.repo_dir, branch, old_sha, new_sha, this_branch_only=False)

        for commit in log:
            print "Checking commit %s ..." % commit['commit']

            # Filter python scripts from the files modified in new_sha
            modfiles = hookutil.parse_git_show(self.repo_dir, commit['commit'], ['.py'])

            # Exit early if there are no modified python scripts in the changeset
            if not modfiles:
                return permit

            # Set up a working directory for pep8 and fill it with the blobs to be checked.
            pep8_workdir = tempfile.mkdtemp(suffix='pep8hook')

            for modfile in modfiles:
                # Skip deleted files
                if modfile['status'] == 'D':
                    logging.debug("Deleted '%s', skip", modfile['path'])
                    continue

                cmd = ['git', 'show', modfile['new_blob']]
                _, file_contents, _ = hookutil.run(cmd, self.repo_dir)

                file_path = os.path.join(pep8_workdir, modfile['path'])
                assert(not os.path.exists(file_path))

                file_dir = os.path.join(pep8_workdir, os.path.dirname(modfile['path']))
                if not os.path.exists(file_dir):
                    os.makedirs(os.path.join(pep8_workdir, os.path.dirname(modfile['path'])))

                with open(file_path, 'w') as fd:
                    fd.write(file_contents)

            # Copy setup.cfg to the working directory
            shutil.copy(os.path.join(os.path.dirname(__file__), 'setup.cfg'), pep8_workdir)

            # Get the commit's diff; pep8 needs it to report only against modified lines
            cmd = ['git', 'show', commit['commit']]
            _, diff, _ = hookutil.run(cmd, self.repo_dir)

            local_dir = os.curdir
            os.chdir(pep8_workdir)
            # Run pep8 in the working directory we have just prepared.
            selected_lines = pep8.parse_udiff(diff, patterns=['*.py'], parent='')

            pep8style = pep8.StyleGuide(
                {
                    'diff'          : True,
                    'paths'         : sorted(selected_lines),
                    'selected_lines': selected_lines,
                    'reporter'      : pep8.DiffReport
                }
            )

            report = pep8style.check_files()
            os.chdir(local_dir)

            if report.total_errors:
                permit = False

            # Clean up
            shutil.rmtree(pep8_workdir)

        logging.debug("Permit: %s" % permit)
        return permit, []
