# ansible-azure
Ansible Module for idempotent handling of Azure Cloud resources.

## Table of modules

## az_storage

### Synopsis
Idempotent handling of Azure storage accounts.

### Options
Parameter: state
Required: no
Default: present
Options: present, absent

Parameter: name
Required: yes

Parameter: resource_group
Required: yes

Parameter: location
Required: yes
Default: northeurope
Comment: See azures homepage for valid locations

Parameter: type
Required: yes
Default: LRS
Options: LRS, ZRS, GRS, RAGS, PLRS
Comment: LRS = Local Redunadant storage. PLRS = Premium (SSD) Local Redunadant Storage

## az_container

### Synopsis
Idempotent handling of Azure storage containers.

### Options
Parameter: state
Default: present
Options: present, absent

Parameter: name
Required: yes

Parameter: resource_group
Required: yes

Parameter: storage_account
Required: yes
