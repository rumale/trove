# Copyright (c) 2014 eBay Software Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

from trove.common import cfg
from trove.common import exception
from trove.common import utils
from trove.guestagent.datastore.mongodb import service as mongo_service
from trove.guestagent.strategies.backup import base
from trove.openstack.common import log as logging

CONF = cfg.CONF

LOG = logging.getLogger(__name__)
MONGODB_DBPATH = CONF.mongodb.mount_point
MONGO_DUMP_DIR = MONGODB_DBPATH + "/dump"
LARGE_TIMEOUT = 600


class MongoDump(base.BackupRunner):
    """Implementation of Backup Strategy for MongoDump."""
    __strategy_name__ = 'mongodump'

    backup_commands = [
        'sudo mkdir -p ' + MONGO_DUMP_DIR,
        'sudo chown -R mongodb:mongodb ' + MONGO_DUMP_DIR,
        'sudo mongodump --journal --dbpath ' + MONGODB_DBPATH +
        ' --out ' + MONGO_DUMP_DIR,
    ]

    def __init__(self, *args, **kwargs):
        self.status = mongo_service.MongoDbAppStatus()
        self.app = mongo_service.MongoDBApp(self.status)
        super(MongoDump, self).__init__(*args, **kwargs)

    def _run_pre_backup(self):
        """Create archival contents in dump dir"""
        self.app.stop_db()
        try:
            for cmd in self.backup_commands:
                # setting really high timeout here since
                # mongodump can takeup a lot of time
                utils.execute_with_timeout(cmd, shell=True,
                                           timeout=LARGE_TIMEOUT)
        except exception.ProcessExecutionError as e:
            LOG.debug("Caught exception when creating the dump")
            self.cleanup_and_restart()
            raise e

    @property
    def cmd(self):
        """Tars and streams the dump dir contents to
        the stdout
        """
        cmd = 'sudo tar cPf - ' + MONGO_DUMP_DIR
        return cmd + self.zip_cmd + self.encrypt_cmd

    def cleanup_and_restart(self):
        utils.execute_with_timeout('sudo rm -fr ' + MONGO_DUMP_DIR, shell=True)
        self.app.start_db()

    def _run_post_backup(self):
        self.cleanup_and_restart()
