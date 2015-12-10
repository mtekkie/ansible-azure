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



#---- From Library File: AzureStorageAccount.py ----


import json


class AzureStorageAccount(AzureStorage):
    def __init__(self, resource_group, name):
        super(self.__class__, self).__init__(resource_group, name)
        self.modified= False
        self.provisioned = False
        self.accountType = ""
        self.creationTime = ""
        self.primaryEndpoints = ""

        self.load()

    def load(self):
        azr =  AzureClient.run(["azure", "storage", "account", "show", self.storageAccountName, "--resource-group", self.resourceGroup, "--json"])

        if azr["rc"] == 0:
            self.provisioned = True
            account = json.loads (azr["out"])
            self.location = account["location"]

             ## Account type in the oject returned has thestorage format before the type: eg.
             ## Standard_LRS = LRS, Standard_ZRS..., Premium_LRS = PLRS
            if account["accountType"] == "Premium_LRS":
                self.accountType= "PLRS"
            elif len(account["accountType"]) > 9:
                self.accountType = account["accountType"][9:]
            else:
                self.accountType = account["accountType"]

            self.creationTime = account["creationTime"]
            self.primaryEndpoints = account["primaryEndpoints"]

    def getFacts(self):
        return dict (name=self.storageAccountName,
                 location=self.location,
                 accountType=self.accountType,
                 creationTime=self.creationTime,
                 primaryEndpoints=self.primaryEndpoints,
                 resourceGroup=self.resourceGroup)

    def isProvisioned(self):
        return self.provisioned

    def getName(self, name):
        return self.storageAccountName

    def getResourceGroup(self, resource_group):
        return self.resourceGroup

    def getLocation(self, location):
        return self.location

    def setLocation(self, location):
        if self.isProvisioned() and location != self.location:
            raise AzureNotModifiable ("Not possible to move an existing account to a another location. From: " + self.location + " to " +location)
        self.location = location

    def setAccountType(self, accountType):
        if self.isProvisioned() and self.accountType != accountType:
            azp = AzureClient.run(["azure", "storage", "account","set", "--resource-group", self.resourceGroup, "--type", self.accountType, self.storageAccountName, "--json"])
            if azp["rc"] != 0:
                raise AzureProvisionException(azp["err"])
            self.modified = True;
        self.accountType = accountType

    def getAccountType (self):
        return self.accountType

    def getCreationTime(self):
        return self.creationTime

    def getPrimaryEndpoints(self):
        return self.primaryEndpoints

    def provision(self):
        azp = AzureClient.run(["azure", "storage", "account", "create", "--location", self.location, "--type", self.accountType, "--resource-group", self.resourceGroup, self.storageAccountName, "--json"])
        if azp["rc"] != 0:
            raise AzureProvisionException(azp["err"])
        self.load()
        self.modified = True

    def deleteAccount (self):
        azp = AzureClient.run(["azure", "storage", "account", "delete","--resource-group", self.resourceGroup, "--quiet",  "--json",  self.storageAccountName])
        if azp["rc"] != 0:
            raise AzureProvisionException(azp["err"])
        self.modified = True


#---- EOF: AzureStorageAccount.py ---



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
            location        = dict(default='northeurope'),
            type            = dict(default='LRS', choices=['LRS', 'ZRS', 'GRS', 'RAGRS', 'PLRS']),
            username        = dict(required=False),
            password        = dict(required=False)
        )
    )



    try:
        azs = AzureStorageAccount(module.params["resource_group"], module.params["name"])


        if module.params["state"] == "present":

            ## Try setting the wanted state - If there is a failure the excepts will display the error message.
            azs.setLocation(module.params["location"])
            azs.setAccountType(module.params["type"])

            if azs.isProvisioned() == False:
                azs.provision()

            module.exit_json(changed=azs.modified, ansible_facts=azs.getFacts())

        if module.params["state"] == "absent":
            azs.deleteAccount();
            module.exit_json(changed=azs.modified)

    except AzureNotModifiable as e:
        module.fail_json(msg=e.msg)

    except AzureClientException as e:
        module.fail_json(msg=e.msg)

    except AzureProvisionException as e:
        module.fail_json(msg=e.msg)


from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
