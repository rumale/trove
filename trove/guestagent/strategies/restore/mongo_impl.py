# Copyright (c) 2014 eBay Software Foundation
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
from trove.common import utils
from trove.guestagent.common import operating_system
from trove.guestagent.datastore.mongodb import service as mongo_service
from trove.guestagent.strategies.restore import base
from trove.openstack.common import log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
IP = operating_system.get_ip_address()
LARGE_TIMEOUT = 600
MONGODB_DBPATH = CONF.mongodb.mount_point
MONGO_DUMP_DIR = MONGODB_DBPATH + "/dump"


class MongoDump(base.RestoreRunner):
    __strategy_name__ = 'mongodump'
    base_restore_cmd = 'sudo tar xPf -'

    cleanup_commands = [
        'sudo rm -fr ' + MONGO_DUMP_DIR,
        'sudo chown -R mongodb:nogroup ' + MONGODB_DBPATH
    ]

    def __init__(self, *args, **kwargs):
        super(MongoDump, self).__init__(*args, **kwargs)
        self.status = mongo_service.MongoDbAppStatus()
        self.app = mongo_service.MongoDBApp(self.status)

    def pre_restore(self):
        self.app.stop_db()

    def post_restore(self):
        """
        Actual restore command streams the archive data from the object store
        This command creates DB FS object xtype from the storage archive
        """
        utils.execute_with_timeout("mongorestore", '--host', IP,
                                   "--journal", "--drop", "--dbpath",
                                   MONGODB_DBPATH, MONGO_DUMP_DIR,
                                   run_as_root=True, root_helper="sudo",
                                   timeout=LARGE_TIMEOUT)

        # now that db fs system has been created cleanup archive dir
        for cmd in self.cleanup_commands:
            utils.execute_with_timeout(cmd, shell=True)

        self.app.start_db()
