# DukeDSClient
Command line tool to upload/manage project on the [duke-data-service](https://github.com/Duke-Translational-Bioinformatics/duke-data-service).
[![Build Status](https://travis-ci.org/Duke-GCB/DukeDSClient.svg?branch=master)](https://travis-ci.org/Duke-GCB/DukeDSClient)

Runs on Python 2.7 or 3.5.

# Install or Upgrade:
```
pip install --upgrade DukeDSClient
```

### Config file setup.
DukeDSClient requires a config file containing an __agent_key__ and a __user_key__.
DukeDSClient supports a global configuration file at /etc/ddsclient.conf and a user configuration file at ~/.ddsclient.
Settings in the user configuration file override those in the global configuration.

#####  Follow these instructions to setup your __user_key__ and  __agent_key__:
[Instructions for adding agent and user keys to the user config file.](docs/GettingAgentAndUserKeys.md)


###Use:
See general help screen:
```
ddsclient -h
```
See help screen for a particular command:
```
ddsclient <command> -h
```

All commands take the form:
```
ddsclient <command> <arguments...>
```

###Upload:
```
ddsclient upload -p <ProjectName> <Folders/Files...>
```

This will create a project with the name ProjectName in the duke data service for your user if one doesn't exist.
It will then upload the Folders and it's contents to that project.
Any items that already exist with the same hash will not be uploaded.


Example: Upload a folder named 'results' to new or existing project named 'Analyzed Mouse RNA':
```
ddsclient upload -p 'Analyzed Mouse RNA' results
```

### Download:
```
ddsclient download -p <ProjectName> [Folder]
```
This will download the contents of ProjectName into the specified folder.
Currently it requires the directory be empty or not exist.
It will create Folder if it doesn't exist.
If Folder is not specified it will use the name of the project with spaces translated to '_'.

Example: Download the contents of project named 'Mouse RNA' into '/tmp/mouserna' :
```
ddsclient download -p 'Mouse RNA' /tmp/mouserna
```


###Add User To Project:
#### Using duke netid:
```
ddsclient add_user -p <ProjectName> --user <Username> --auth_role 'project_admin'
```
Example: Grant permission to user with username 'jpb123' for a project named 'Analyzed Mouse RNA' with default permissions:
```
ddsclient add_user -p 'Analyzed Mouse RNA' --user 'jpb123'
```

#### Using email:
```
ddsclient add_user -p <ProjectName> --email <Username> --auth_role 'project_admin'
```
Example: Grant permission to user with email 'ada.lovelace@duke.edu' for a project named 'Analyzed Mouse RNA' with default permissions:
```
ddsclient add_user -p 'Analyzed Mouse RNA' --email 'ada.lovelace@duke.edu'
```


###Testing:
From the root directory run the following:
```
python setup.py test
```

### Data Service Web Portal:
[Duke Data Service Portal](https://dataservice.duke.edu).
This also requires a [Duke NetID](https://oit.duke.edu/email-accounts/netid/).

### Advanced:
You can specify an alternate url for use with ddsclient via the `DUKE_DATA_SERVICE_URL` environment variable.
Here is how you can set the environment variable so ddsclient will connect to the 'dev' url:
```
export DUKE_DATA_SERVICE_URL='https://apidev.dataservice.duke.edu/api/v1'
```
This will require using the associated apiexplorer to get a valid token.

