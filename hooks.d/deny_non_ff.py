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
deny_non_ff: A hook to deny non-fast-forward pushes to some branches
'''
import re
import logging

import hookutil


class Hook(object):

    def __init__(self, repo_dir, settings, params):
        self.repo_dir = repo_dir
        self.settings = settings
        self.params = params

    def is_ff_push(self, old_sha, new_sha):
        '''
        Check if new_sha is a fast-forward reference.
        '''
        if old_sha == '0' * 40:
            old_sha = hookutil.git_empty_tree()

        cmd = ['git', 'rev-list', "%s..%s" % (new_sha, old_sha)]
        _, refs, _ = hookutil.run(cmd, self.repo_dir)

        # It is a non-fast-forward push
        if refs:
            return False

        return True

    def check(self, branch, old_sha, new_sha):
        logging.debug("branch='%s', old_sha='%s', new_sha='%s', params='%s'",
                      branch, old_sha, new_sha, self.params)

        # Do not run the hook if the branch is being deleted
        if new_sha == '0' * 40:
            logging.debug("Deleting the branch, skip the hook")
            return True, []

        # Check if branch matches any of the list
        for branch_re in self.settings:
            try:
                branch_rec = re.compile(branch_re)
            except re.error:
                logging.warning("Branch regexp '%s' does not compile, skip", branch_re)
                continue

            if branch_rec.match(branch):
                logging.debug("Matched '%s'", branch_re)
                permit = self.is_ff_push(old_sha, new_sha)
                if not permit:
                    hint = '\n'.join(['',
                        "Updates were rejected because the tip of your current branch is behind",
                        "its remote counterpart. Integrate the remote changes (e.g.",
                        "'git pull ...') before pushing again.",
                        "See the 'Note about fast-forwards' in 'git push --help' for details."
                    ])
                    return permit, [{'at': new_sha, 'text': "Cannot push a non-fast-forward reference." + hint}]
                return permit, []

        logging.debug("Branch '%s' does not match any of '%s', skip", branch, ' | '.join(self.settings))

        return True, []
