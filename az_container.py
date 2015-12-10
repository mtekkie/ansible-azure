#!/usr/bin/python

# (c) Robert Forsström, robert@middleware.se




#---- From Library File: AzureStorage.py ----



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


#---- EOF: AzureStorage.py ---



#---- From Library File: AzureStorageContainer.py ----


class AzureStorageContainer(AzureStorage):
    def __init__(self, resource_group, storage_account_name, container_name):
        self.containerName = container_name
        self.modified = False
        super(self.__class__, self).__init__(resource_group, storage_account_name)

    def provision(self):
        azp = AzureClient.run(["azure", "storage", "container", "create", "--connection-string", self.getConnectionString() , "--container", self.containerName , "--json"])
        if azp["rc"] != 0:
            raise AzureProvisionException(azp["err"])
        self.modified = True

    def delete (self):
        azp = AzureClient.run(["azure", "storage", "container", "delete", "--connection-string", self.getConnectionString() , "--container", self.containerName , "--json", "--quiet"])
        if azp["rc"] != 0:
            raise AzureProvisionException(azp["err"])
        self.modified = True

    def isProvisioned(self):
        azp = AzureClient.run(["azure", "storage", "container", "show", "--connection-string", self.getConnectionString(), "--container", self.containerName , "--json"])
        if azp["rc"] != 0:
            return False
        return True


#---- EOF: AzureStorageContainer.py ---



#---- From Library File: AzureClient.py ----



from subprocess import  CalledProcessError, check_output, Popen, PIPE

class AzureClient ():
    @staticmethod
    def run (args):
        azp = Popen (args, stdout=PIPE, stderr=PIPE)
        output = azp.communicate();
        stdout = output[0]
        stderr = output[1]
        return dict (out=stdout, err=stderr, rc=azp.returncode)


#---- EOF: AzureClient.py ---



#---- From Library File: AzureExceptions.py ----


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


#---- EOF: AzureExceptions.py ---



def main():

    module = AnsibleModule(
        argument_spec = dict(
            state           = dict(default='present', choices=['present', 'absent']),
            name            = dict(required=True),
            resource_group  = dict(required=True),
            storage_account = dict(required=True),
            username        = dict(required=False),
            password        = dict(required=False)
        )
    )

    try:
        azs = AzureStorageContainer(module.params["resource_group"], module.params["storage_account"], module.params["name"] )


        if module.params["state"] == "present":
            if azs.isProvisioned() == False:
                azs.provision()
            module.exit_json(changed=azs.modified)

        if module.params["state"] == "absent":
            if azs.isProvisioned() == True:
                azs.delete();
            module.exit_json(changed=azs.modified)

    except AzureClientException as e:
        module.fail_json(msg=e.msg)

    except AzureProvisionException as e:
        module.fail_json(msg=e.msg)

from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
