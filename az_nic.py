#!/usr/bin/python

# (c) Robert Forsström, robert@middleware.se





#---- From Library File: AzureNic.py ----

# (c) Robert Forsstrom, robert@middleware.se

class AzureNic(object):
    def __init__(self, resource_group, name):
        self.name = name
        self.resourceGroup = resource_group
        self.modified= False
        self.msg = []
        self.provisioned = False
        self.location = False
        self.loadBalancerBackendAddressPools = False
        self.loadBalancerInboundNatRules = False
        self.privateIpAddress = False
        self.privateIpAllocationMethod = False
        self.enableIPForwarding = False

        self.load()


    def load(self):
        azr =  AzureClient.run(["azure", "network", "nic", "show", "--resource-group", self.resourceGroup,"--name", self.name,  "--json"])
        if azr["rc"] == 0 and len (azr["out"]) >10:
            self.provisioned = True
            nic = json.loads (azr["out"])
            self.location = nic["location"]
            #self.loadBalancerBackendAddressPools = nic["loadBalancerBackendAddressPools"]
            #self.loadBalancerInboundNatRules = nic["loadBalancerInboundNatRules"]
            self.privateIpAddress = nic["ipConfigurations"][0]["privateIpAddress"]
            self.privateIpAllocationMethod = nic["ipConfigurations"][0]["privateIpAllocationMethod"]
            #self.enableIPForwarding = nic["ipConfigurations"]["enableIPForwarding"]
            self.subnetId = nic["ipConfigurations"][0]["subnet"]["id"]


    def setLocation(self, location):
        if self.isProvisioned() and location != self.location:
            raise AzureNotModifiable ("Not possible to move an existing NIC to a another location. From: " + self.location + " to " +location)
        self.location = location

    def setPrivateIpAddress (self, ipAddress):
        if self.isProvisioned() and ipAddress != self.privateIpAddress or self.privateIpAllocationMethod != "Static":
            azp = AzureClient.run(["azure", "network", "nic", "set", "--resource-group", self.resourceGroup ,"--private-ip-address", ipAddress, "--name", self.name, "--json"])
            if azp["rc"] != 0:
                raise AzureProvisionException(azp["err"])
            self.modified = True
            self.msg.append("Addedd or changed the static private ip-address: "+ipAddress)
        self.privateIpAddress = ipAddress

    def setNetwork (self, network):
        ## TODO: This is kind of ugly- The subnet id should be able to change. For now we don't support that and the way we find out is a bit crazy and unreliable.
        if self.isProvisioned() and network not in self.subnetId:
            raise AzureNotModifiable ("Not possible to move an existing NIC to a another subnet in this implementation of this library. Migth be supported in the future.")
        self.network = network

    def setSubnet (self, subnet):
        ## TODO: This is kind of ugly- The subnet id should be able to change. For now we don't support that.
        if self.isProvisioned() and subnet not in self.subnetId:
            raise AzureNotModifiable ("Not possible to move an existing NIC to a another subnet in this implementation of this library. Migth be supported in the future.")
        self.subnet = subnet

    def provision(self):
        azp = AzureClient.run(["azure", "network", "nic", "create", "--resource-group", self.resourceGroup ,"--location", self.location, "--name", self.name , "--subnet-vnet-name", self.network, "--subnet-name",self.subnet, "--json"])
        if azp["rc"] != 0:
            raise AzureProvisionException(azp["err"])
        self.load()
        self.modified = True
        self.msg.append("Provisioned a new Nic")


    def delete (self):
        azp = AzureClient.run(["azure", "network", "nic", "delete", "--resource-group", self.resourceGroup , "--name", self.name , "--json", "--quiet"])
        if azp["rc"] != 0:
            raise AzureProvisionException(azp["err"])
        self.modified = True

    def isProvisioned(self):
        return self.provisioned


#---- EOF: AzureNic.py ---



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
            network                 = dict(required=True),
            subnet                  = dict(required=True),
            ipaddress               = dict(required=False),
            username                = dict(required=False),
            password                = dict(required=False)
        )
    )

    try:
        aznic = AzureNic(module.params["resource_group"],  module.params["name"])


        if module.params["state"] == "present":
          aznic.setLocation(module.params["location"])
          aznic.setNetwork(module.params["network"])
          aznic.setSubnet(module.params["subnet"])

          if not aznic.isProvisioned():
              aznic.provision()

          if module.params["ipaddress"] is not None:
              aznic.setPrivateIpAddress(module.params["ipaddress"])

          module.exit_json(changed=aznic.modified, msg=aznic.msg)



        if module.params["state"] == "absent":
            if aznic.isProvisioned():
                aznic.delete()
                module.exit_json(changed=True)
            module.exit_json(changed=False)

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
