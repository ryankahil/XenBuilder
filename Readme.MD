bsdxenvmbuilder: CLI tool that will build VMs using XenAPI.

For any issues, please reach out to me. My email is ryan.kahil@outlook.com.

```
Usage: bsdxenvmbuilder [OPTIONS] COMMAND [ARGS]...

  BSD Xen VM Builder

Options:
  --pool TEXT          Pool Server to connect to
  --pooluser TEXT      Connecting as Pool User
  --poolpassword TEXT  Password to authenticate in the Xen Pool
  --help               Show this message and exit.

Commands:
  build_vm     Build VM Out passing VM's projected...
  create_disk  Create a VDI and Attach to VM
```

build_vm:

```
Usage: bsdxenvmbuilder build_vm [OPTIONS]

  Build VM Out passing VM's projected specifications

Options:
  --sr TEXT        Storage Repository that Disk Image is located
  --name TEXT      Name of VM
  --template TEXT  Xen VM Template. Please note, if you need spaces, make sure
                   to use double quotes
  --ram INTEGER    Amount of Virtual RAM (Defaults to 1)
  --cpus INTEGER   Number of Virtual CPUs (Defaults to 1)
  --help           Show this message and exit.
```

Example USAGE for build_vm: 

```bsdxenvmbuilder build_vm --template "CentOS 7" --ram 2 --cpus 2 --name "Test" --sr "NFS VM disks" --networkdevice bond1```


Creating a Disk for a VM:

```
Usage: bsdxenvmbuilder create_disk [OPTIONS]

  Create a VDI and Attach to VM

Options:
  --userdeviceno TEXT  Device Number - This should be unique
  --devicename TEXT    Name of the Device
  --readonly TEXT      Disk Set to Read-only (Defaults to False)
  --sr TEXT            Storage Repository
  --size INTEGER       Size of Disk in GB
  --vm TEXT            Name of VM to attach to
  --name TEXT          Name of Disk
  --help               Show this message and exit.
```

Example USAGE for create_disk:


```bsdxenvmbuilder create_disk --devicename "/dev/xbdb" --readonly False --sr "NFS VM disks" --size 10 --vm mrtg-test --name "test" --userdeviceno "1"```

SETUP:

In order to install, please follow these steps:

1.) Clone the repository -- ```git clone <repo>```

2.) CD into the directory and run pip install: ```sudo pip install --ignore-installed six --editable .```



CONFIGURATION:

This CLI comes with the ability to be configured so that it automatically connects to a Xen Pool. This is how you would configure it:

1.) Create a File called: xenbuilder.config

2.) You will want to fill in each field respectively:

```
[POOL_CONFIG]
pooluser = foo
poolpassword = bar
pool = http://foobar
```

The pooluser is the user that you would connect to the XenServer Pool, Along w/ it's password. The pool connects via HTTP, so you will need to provide either hostname or IP Address.
