#!/usr/bin/python

# (c) Robert Forsström, robert@middleware.se


# From AzureStorage.py

import json


class AzureStorage(object):
     def __init__(self, resource_group, name):
         self.resourceGroup = resource_group
         self.storageAccountName = name
         self.connectionString = False

     def getConnectionString(self):
         if self.connectionString==False:
            azcs = AzureClient.run(["azure", "storage", "account", "connectionstring", "show", "--json",  "--resource-group", self.resourceGroup, self.storageAccountName])
            if azcs["rc"] != 0:
                raise AzureProvisionException(azcs["err"])
            cs = json.loads (azcs["out"])
            self.connectionString = cs["string"]

         return self.connectionString

# End AzureStorage.py
## From AzureBlob.py


class AzureBlob(AzureStorage):
    def __init__(self, resource_group, account, container, name):
        super(self.__class__, self).__init__(resource_group, account)
        self.container = container
        self.name = name

class AzureBlobOps():

    @staticmethod
    def upload(localPath, dest , type):
         #type = block, page, append
        pass

    @staticmethod
    def exists(blob):
        azcs = AzureClient.run(["azure", "storage", "blob", "show", "--connection-string", blob.getConnectionString(),  "--container", blob.container, "--blob", blob.name, "--json"])
        if azcs["rc"] != 0:
            return False
        return True

    @staticmethod
    def copy(blob):
        pass

    def isSameAs(blob, srcBlob):
        pass

    @staticmethod
    def delete(blob):
        pass

## End AzureBlob.py
# From AzureClient.py
from subprocess import  CalledProcessError, check_output, Popen, PIPE

class AzureClient ():
    @staticmethod
    def run (args):
        azp = Popen (args, stdout=PIPE, stderr=PIPE)
        output = azp.communicate();
        stdout = output[0]
        stderr = output[1]
        return dict (out=stdout, err=stderr, rc=azp.returncode)


# End AzureClient.py
#From AzureExcptions.py

class AzureNotModifiable (Exception):
    def __init__(self, msg):
        self.msg=msg

class AzureClientException (Exception):
    def __init__(self, msg):
        self.msg=msg

class AzureProvisionException(Exception):
    def __init__(self, msg):
        self.msg=msg

#End AzureExcptions.py


def main():

    module = AnsibleModule(
        argument_spec = dict(
            state               = dict(default='present', choices=['present', 'absent', 'same_as']),
            name                = dict(required=True),
            container           = dict(required=True),
            resource_group      = dict(required=True),
            storage_account     = dict(required=True),
            blob_type           = dict(required=False),
            src_name            = dict(required=False),
            src_account         = dict(required=False),
            src_container       = dict(required=False),
            src_local_path      = dict(required=False),
            overwrite           = dict(default=False, choices=BOOLEANS),
            username            = dict(required=False),
            password            = dict(required=False)
        )
    )

    try:
        azs = AzureBlob(module.params["resource_group"], module.params["storage_account"], module.params["container"],  module.params["name"])

        if module.params["state"] == "present":
            if AzureBlobOps.exists(azs):
                module.exit_json(changed=False)


            if not AzureBlobOps.exists(azs) and module.params["src_name"] is not None :
                module.exit_json(changed=False)

        module.fail_json(msg="Hello mr")

        if module.params["state"] == "absent":
            pass

    except AzureClientException as e:
        module.fail_json(msg=e.msg)

    except AzureProvisionException as e:
        module.fail_json(msg=e.msg)

from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
