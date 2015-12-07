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

import os
import hashlib
import base64

class AzureBlob(AzureStorage):
    def __init__(self, resource_group, account, container, name):
        super(self.__class__, self).__init__(resource_group, account)
        self.container = container
        self.name = name

class AzureBlobOps():

    @staticmethod
    def upload(localPath, blob , type):
        if not os.path.isfile(localPath):
            raise AzureNotFound("Local file not found: "+ localPath)
        azcs = AzureClient.run(["azure", "storage", "blob", "upload", "--connection-string", blob.getConnectionString(),  "--container", blob.container, "--blob", blob.name,"--blobtype", type, "--json", "--quiet", "--file", localPath])
        if azcs["rc"] != 0:
            raise AzureNotFound("Upload failed: "+ azcs["err"])

    @staticmethod
    def exists(blob):
        azcs = AzureClient.run(["azure", "storage", "blob", "show", "--connection-string", blob.getConnectionString(),  "--container", blob.container, "--blob", blob.name, "--json"])
        if azcs["rc"] != 0:
            return False
        return True

    @staticmethod
    def copy(blob, dest):
        azcs = AzureClient.run(["azure", "storage", "blob", "copy", "start", "--connection-string", blob.getConnectionString(),  "--source-container", blob.container, "--source-blob", blob.name,"--dest-connection-string", dest.getConnectionString(), "--dest-container", dest.container,  "--dest-blob", dest.name,  "--quiet", "--json"])
        ## TODO: Wait until filecopy has succeeded.

        if azcs["rc"] != 0:
            raise AzureNotFound("Copy failed"+ azcs["err"])

    @staticmethod
    def blobIsSameAs(blob1, blob2):
        azcs1 = AzureClient.run(["azure", "storage", "blob", "show", "--connection-string", blob1.getConnectionString(),  "--container", blob1.container, "--blob", blob1.name, "--json"])
        azcs2 = AzureClient.run(["azure", "storage", "blob", "show", "--connection-string", blob2.getConnectionString(),  "--container", blob2.container, "--blob", blob2.name, "--json"])

        if azcs1["rc"] != 0 or azcs2["rc"] != 0 :
            raise AzureNotFound("Comparison failed "+ azcs1["err"] + azcs2["err"])
        b1res = json.loads (azcs1["out"])
        b2res = json.loads (azcs2["out"])

        if b1res["contentMD5"] == b2res["contentMD5"]:
            return True
        return False

    @staticmethod
    def localFileIsSameAs(localPath, blob):

        if not os.path.isfile(localPath):
            raise AzureNotFound("Local file not found: "+ localPath)

        azcs1 = AzureClient.run(["azure", "storage", "blob", "show", "--connection-string", blob.getConnectionString(),  "--container", blob.container, "--blob", blob.name, "--json"])
        if azcs1["rc"] != 0:
            raise AzureNotFound("Comparison failed "+ azcs1["err"])

        b1res = json.loads (azcs1["out"])

        fileMD5 = AzureBlobOps._md5(localPath)

        if b1res["contentMD5"] == base64.b64encode(fileMD5):
            return True
        return False


    @staticmethod
    def _md5(fname):
        hash = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash.update(chunk)
        return hash.digest()

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

class AzureParamentersNotValid(Exception):
    def __init__(self, msg):
        self.msg=msg

class AzureNotFound(Exception):
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
            upload_blob_type    = dict(default='block', choices=['block', 'page', 'append']),
            src_blob_name       = dict(required=False),
            src_storage_account = dict(required=False),
            src_container       = dict(required=False),
            src_local_path      = dict(required=False),
            overwrite           = dict(default=False, choices=BOOLEANS),
            username            = dict(required=False),
            password            = dict(required=False)
        )
    )

    try:
        azb = AzureBlob(module.params["resource_group"], module.params["storage_account"], module.params["container"],  module.params["name"])
        azb_src = None

        blobExist= AzureBlobOps.exists(azb)

        if module.params["state"] == "present":

            if blobExist:
                module.exit_json(changed=False)

            if not blobExist and module.params["src_blob_name"] is not None:
                src_storage_account = module.params["storage_account"] if module.params["src_storage_account"] is None else module.params["src_storage_account"]
                src_container = module.params["container"] if module.params["src_container"] is None else module.params["src_container"]

                azb_src = AzureBlob(module.params["resource_group"],src_storage_account, src_container,  module.params["src_blob_name"])

                if AzureBlobOps.exists(azb_src):
                    AzureBlobOps.copy (azb_src, azb)
                    module.exit_json(changed=True)
                else:
                    module.fail_json(msg="Can not find source blob: "+module.params["src_blob_name"]+ " in container "+src_container + " on account " +src_storage_account)

            if not blobExist and module.params["src_local_path"] is not None:
                AzureBlobOps.upload(module.params["src_local_path"], azb, module.params["upload_blob_type"] )
                module.exit_json(changed=True)

            module.fail_json(msg="Blob does not exist.")



        if module.params["state"] == "absent":
            if blobExist:
                AzureBlobOps.delete(azb);
                module.exit_json(changed=True)

            module.exit_json(changed=False)

        if module.params["state"] == "same_as":
            if module.params["src_blob_name"] is not None:
                src_storage_account = module.params["storage_account"] if module.params["src_storage_account"] is None else module.params["src_storage_account"]
                src_container = module.params["container"] if module.params["src_container"] is None else module.params["src_container"]
                azb_src = AzureBlob(module.params["resource_group"],src_storage_account, src_container,  module.params["src_blob_name"])

                if AzureBlobOps.exists(azb_src):
                    if AzureBlobOps.blobIsSameAs (azb_src, azb):
                        module.exit_json(changed=False)
                    else:
                        if module.boolean(module.params["overwrite"]):
                            AzureBlobOps.copy(azb_src, azb)
                            module.exit_json(changed=True)
                        else:
                            module.fail_json(msg="The two blobs are not the same: "+azb.name +" != "+azb_src.name)
                else:
                    module.fail_json(msg="Can not find source blob: "+module.params["src_blob_name"]+ " in container "+src_container + " on account " +src_storage_account)

            if module.params["src_local_path"] is not None:
                if AzureBlobOps.localFileIsSameAs (module.params["src_local_path"], azb):
                    module.exit_json(changed=False)
                else:
                    if module.boolean(module.params["overwrite"]):
                        AzureBlobOps.upload(module.params["src_local_path"], azb, module.params["upload_blob_type"])
                        module.exit_json(changed=True)
                    else:
                        module.fail_json(msg="The blob and file are not the same: "+azb.name +" != "+module.params["src_local_path"])

    except AzureClientException as e:
        module.fail_json(msg=e.msg)

    except AzureProvisionException as e:
        module.fail_json(msg=e.msg)

    except AzureNotFound as e:
        module.fail_json(msg=e.msg)

from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
