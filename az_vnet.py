#!/usr/bin/python

# (c) Robert Forsström, robert@middleware.se




#---- From Library File: AzureVirtualNetwork.py ----

# (c) Robert Forsstrom, robert@middleware.se

class AzureVirtualNetwork(object):
    def __init__(self, resource_group, name):
        self.name = name
        self.resourceGroup = resource_group
        self.modified= False
        self.msg = []
        self.provisioned = False
        self.accountType = False
        self.creationTime = False
        self.addressSpace =  False
        self.modified = False
        self.dhcpOptions = False
        self.dnsServers = False
        self.load()

    def load(self):
        azr =  AzureClient.run(["azure", "network", "vnet", "show", "--resource-group", self.resourceGroup,"--name", self.name,  "--json"])
        if azr["rc"] == 0 and len (azr["out"]) >10:
            self.provisioned = True
            vnet = json.loads (azr["out"])
            self.location = vnet["location"]
            self.addressSpace = vnet["addressSpace"]
            self.subnets = vnet["subnets"]
            self.dhcpOptions = vnet["dhcpOptions"]

    # def addAddressPrefixes(self, prefixes):
    #     modified = False
    #     prefixes = prefixes.split(",")
    #     existingPrefixes = self.addressSpace["adressPrefixes"]
    #
    #     ##Check if we need to modify:
    #     for prefix in prefixes:
    #         if prefix not in existingPrefixes:
    #             modified=True
    #
    #     if modified:
    #         commaseperated = ",".join(list(set(prefixes+existingPrefixes)))
    #         self.setAddressPrefixes(commaseperated)
    #         self.modified = True

    def setDNSServers (self, dnsServers):
        if not self.provisioned:
            self.dnsServers = dnsServers
        else:

            if dnsServers != ",".join(self.dhcpOptions["dnsServers"]):
                azp = AzureClient.run(["azure", "network", "vnet", "set", "--resource-group", self.resourceGroup , "--name", self.name , "--dns-servers", dnsServers, "--json"])
                if azp["rc"] != 0:
                    raise AzureProvisionException(azp["err"])
                self.modified = True
                self.msg.append("Added DNS Servers " + dnsServers )

    def setAddressPrefixes(self, prefixes):
        if not self.provisioned:
            self.addressSpace=prefixes
            return

        if prefixes != ",".join(self.addressSpace["addressPrefixes"]):
            azp = AzureClient.run(["azure", "network", "vnet", "set", "--resource-group", self.resourceGroup , "--name", self.name , "--address-prefixes", prefixes, "--json"])
            if azp["rc"] != 0:
                raise AzureProvisionException(azp["err"])
            self.modified = True
            self.msg.append("Added addressPrefixes " + prefixes )

    def provision(self):
        azp = AzureClient.run(["azure", "network", "vnet", "create", "--resource-group", self.resourceGroup ,"--location", self.location, "--name", self.name , "--address-prefixes", self.addressSpace, "--json"])
        if azp["rc"] != 0:
            raise AzureProvisionException(azp["err"])
        self.load()
        self.modified = True
        self.msg.append("Provisioned network")


    def delete (self):
        azp = AzureClient.run(["azure", "network", "vnet", "delete", "--resource-group", self.resourceGroup , "--name", self.name , "--json", "--quiet"])
        if azp["rc"] != 0:
            raise AzureProvisionException(azp["err"])
        self.modified = True

    def isProvisioned(self):
        return self.provisioned

    def setLocation(self, location):
        if self.isProvisioned() and location != self.location:
            raise AzureNotModifiable ("Not possible to move an existing network to a another location. From: " + self.location + " to " +location)
        self.location = location

    def addSubnet (self, name, addressPrefix):
        ## Is the subnet aleady present?
        for subnet in self.subnets:
            if subnet["name"] == name:
                ## Subnet is already present. Does it have the correct configuration?
                if subnet["addressPrefix"] != addressPrefix:
                    #Exists, but it does not have the correct configuration.
                    azp = AzureClient.run(["azure", "network", "vnet", "subnet","set" , "--resource-group", self.resourceGroup , "--name", name , "--address-prefix", addressPrefix, "--vnet-name", self.name,  "--json"])
                    if azp["rc"] != 0:
                        raise AzureProvisionException(azp["err"])
                    self.modified = True
                    self.msg.append("Changed subnets addressPrefix: " + name +"("+addressPrefix+")"  )
                    return
                else:
                    #Nothing to do. Return.
                    return

        # Subnet does not exist. Create.
        azp = AzureClient.run(["azure", "network", "vnet", "subnet", "create" , "--resource-group", self.resourceGroup , "--name", name , "--address-prefix", addressPrefix, "--vnet-name", self.name,  "--json"])
        if azp["rc"] != 0:
            raise AzureProvisionException(azp["err"])
        self.modified = True
        self.msg.append("Created Subnet: " + name +"("+addressPrefix+")"  )

    def deleteSubnet(self, name):
        ## Is the subnet present?
        for subnet in self.subnets:
            if subnet["name"] == name:
                ## Subnet is present, delete!
                azp = AzureClient.run(["azure", "network", "vnet", "subnet", "delete" , "--resource-group", self.resourceGroup , "--name", name , "--vnet-name", self.name,  "--json", "--quiet"])
                if azp["rc"] != 0:
                    raise AzureProvisionException(azp["err"])
                self.modified = True


#---- EOF: AzureVirtualNetwork.py ---



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
            state                   = dict(default='present', choices=['present', 'absent']),
            name                    = dict(required=True),
            resource_group          = dict(required=True),
            location                = dict(required=True),
            address_spaces          = dict(required=True), #Comma seperated
            subnet_name             = dict(required=False),
            subnet_prefix           = dict(required=False),
            dns_servers             = dict(required=False), #Comma seperated
            username                = dict(required=False),
            password                = dict(required=False)
        )
    )

    try:
        azvnet = AzureVirtualNetwork(module.params["resource_group"],  module.params["name"])


        if module.params["state"] == "present":
          azvnet.setLocation(module.params["location"])
          azvnet.setAddressPrefixes(module.params["address_spaces"])


          if not azvnet.isProvisioned():
              azvnet.provision()

          if module.params["dns_servers"] is not None:
              azvnet.setDNSServers(module.params["dns_servers"])

          if module.params["subnet_name"] is not None:
              azvnet.addSubnet(module.params["subnet_name"], module.params["subnet_prefix"])

          module.exit_json(changed=azvnet.modified, msg=azvnet.msg)



        if module.params["state"] == "absent":
            if azvnet.isProvisioned():
                azvnet.delete()
                module.exit_json(changed=True)
            module.exit_json(changed=False)

        if module.params["subnet_name"] is None:
            azvnet.deleteSubnet(module.params["subnet_name"])


    except AzureNotModifiable as e:
        module.fail_json(msg=e.msg)
    except AzureClientException as e:
        module.fail_json(msg=e.msg)
    except AzureProvisionException as e:
        module.fail_json(msg=e.msg)
    except AzureNotFound as e:
        module.fail_json(msg=e.msg)

from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
