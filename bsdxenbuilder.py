import click
from click_configfile import ConfigFileReader, Param, SectionSchema
from click_configfile import matches_section
import XenAPI
import sys
import logging
import provision
import traceback

class ConfigSectionSchema(object):
    
    """
    Describes all config sections of this configuration file. Will read in the Configuration Settings found in xenbuilder.config.
    """

    @matches_section("POOL_CONFIG")   
    class Pool(SectionSchema):
        pooluser      = Param(type=str)
        pool          = Param(type=str)
        poolpassword  = Param(type=str)


class ConfigFileProcessor(ConfigFileReader):
    config_files = ["xenbuilder.config"]
    config_section_schemas = [
        ConfigSectionSchema.Pool     
    ]


CONTEXT_SETTINGS = dict(default_map=ConfigFileProcessor.read_config())
logger = logging.getLogger('bsdxenvmbuilder')

class ZenConnection(object):
    def __init__(self, pool, pooluser, poolpassword):
        self.pool = pool
        self.pooluser = pooluser
        self.poolpassword = poolpassword        

# Pool Connection param args
@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
        '--pool',
	default='',
	help='Pool Server to connect to'
)
@click.option(
        '--pooluser',
	default='',
	help='Connecting as Pool User'
)
@click.option(
        '--poolpassword', prompt=True,
        hide_input=True,
        help='Password to authenticate in the Xen Pool'
)
@click.pass_context
def cli(ctx,pool,pooluser,poolpassword):
     
     """ 
     BSD XEN VM BUILDER 
     Please NOTE: Options: pool, pooluser, and poolpassword need to  be set in a Configuration File named xenbuilder.config. Please refer to https://github.com/bsd/Xen-Builder for Instructions 
     """

     ctx.obj = ZenConnection(pool, pooluser, poolpassword)

@click.pass_obj
def xen_session(ctx):
    
    """ 
    Adds a Persistant Connection to the Pool Server.
    """

    logging.info('INFO: Establishing Connection...')
    try:
        session = XenAPI.Session(str(ctx.pool))
	session.xenapi.login_with_password(str(ctx.pooluser),str(ctx.poolpassword))
        logging.info('INFO: Connection Successful!!')
    except:
        logging.error("ERROR: Unexpected Error - ", sys.exc_info()[0])
        raise
    return session

# VM Building To Build VM based on Template with HD space, CPUs, and RAM
@click.option(
        '--cpus',
        default=1,
        help='Number of Virtual CPUs (Defaults to 1)'
)
@click.option(
        '--ram',
        default=1,
        help='Amount of Virtual RAM (Defaults to 1)'
)
@click.option(
        '--template',
        help='Xen VM Template. Please note, if you need spaces, make sure to use double quotes'
)
@click.option(
	'--name',
	help="Name of VM"
)
@click.option(
	'--sr',
	default='NFS VM disks',
	help='Storage Repository that Disk Image is located'
)
@click.option(
	'--networkdevice',
	help='What Interface are you trying to bond to?'
)

@cli.command()
@click.pass_obj
def build_vm(ctx,cpus,ram,template,name,sr,networkdevice):

    """
    Build VM Out passing VM's projected specifications. This will take in vCPU(s), RAM, HardDrive space, Template name, Network Device Name, and the SR to pull the Template from. 
    An example of doing this is: bsdxenvmbuilder build_vm --template "CentOS 7" --ram 2 --cpus 2 --name "Test" --sr "NFS VM disks" --networkdevice bond0
    This will essentially connect to the Xen Server configured and build out a CentOS VM named Test.
    """

    logging.info("Collecting Info on the VM Specs.....")
    
    try:
        session = xen_session()
        click.echo("Checking for template: " + template)
        vms = session.xenapi.VM.get_all_records()
        print ("Server has %d VM objects (this includes templates):" % (len(vms)))
        templates = []
        for vm in vms:
            record = vms[vm]
            ty = "VM"
            if record["is_a_template"]:
                ty = "Template"
            if record["name_label"].startswith(template):
               templates.append(vm)
               print("Found: " + vm + " " + record["name_label"])
        if not templates:
            print("Could not find any templates. Exiting.")
            sys.exit(1)
        template = templates[0]
        logger.info("Selected template: ", session.xenapi.VM.get_name_label(template))
        logger.info("Installing new VM from the template")
        vm = session.xenapi.VM.clone(template, name)

        logger.info("Adding non-interactive to the kernel commandline")
        session.xenapi.VM.set_PV_args(vm, "non-interactive")
        logger.info("Choosing an SR to instantiate the VM's disks")
        sr_pool = session.xenapi.pool.get_all()[0]
        default_sr = session.xenapi.pool.get_default_SR(sr_pool)
        default_sr = session.xenapi.SR.get_record(default_sr)
        print("Choosing SR: %s (uuid %s)" % (default_sr['name_label'], default_sr['uuid']))
	print("Rewriting the disk provisioning XML")
        spec = provision.getProvisionSpec(session, vm)
        spec.setSR(default_sr['uuid'])
        provision.setProvisionSpec(session, vm, spec)

        create = session.xenapi.VM.provision(vm)
       
        sr_dvd=session.xenapi.SR.get_by_name_label("ISO_IMAGES_LOCAL")
        record_dvd=session.xenapi.SR.get_record(sr_dvd[0])
        VDI_dvd=record_dvd["VDIs"]
        vm_uid=session.xenapi.VM.get_uuid(vm)
        vm_get=session.xenapi.VM.get_by_uuid(vm_uid)

	# Configuring Boot disk

        vbdconnectcd={'VDI':VDI_dvd[0],
                  'VM':vm_get,
                  'userdevice':"1",
                  'mode':"RO",
                  'type':"cd",
                  'bootable':True,
                  'unpluggable':True,
                  'empty':False,
                  'other_config':{},
                  'qos_algorithm_type':'',
                  'qos_algorithm_params':{}}
        
        vbdref=session.xenapi.VBD.create(vbdconnectcd)
        session.xenapi.VBD.set_bootable(vbdref, True)
      
	# Configuring Network
	pifs = session.xenapi.PIF.get_all_records()
        for pifRef in pifs.keys():
            if (pifs[pifRef]['device'] == networkdevice):
                networkdevice = pifRef
        logger.info("Choosing PIF with device: ", networkdevice)

        network = session.xenapi.PIF.get_network(str(networkdevice))
        logger.info("Chosen PIF is connected to network: ", session.xenapi.network.get_name_label(network))
        
        vif = { 'device': '0',
            'network': network,
            'VM': vm,
            'MAC': "",
            'MTU': "1500",
            "qos_algorithm_type": "",
            "qos_algorithm_params": {},
            "other_config": {} }

        vif_object = session.xenapi.VIF.create(vif)	
        
	# Need Byte Conversion
	bytes = str(long(ram) * 1024L * 1024L * 1024L)
        
        session.xenapi.VM.set_memory_limits(vm,bytes,bytes,bytes,bytes)
        session.xenapi.VM.set_VCPUs_max(vm,cpus)
        session.xenapi.VM.set_VCPUs_at_startup(vm,cpus)
        
        session.xenapi.VM.start(vm,False, True)
    except:
    	logging.error("ERROR: Unexpected Error - ", sys.exc_info()[0])
    	raise

@click.option(
	'--name',
	help='Name of Disk'
)
@click.option(
	'--vm',
	help='Name of VM to attach to'
)
@click.option(
	'--size',
	default=10,
	help='Size of Disk in GB'
)
@click.option(
	'--sr',
	help='Storage Repository'
)
@click.option(
	'--readonly',
	default=False,
	help='Disk Set to Read-only (Defaults to False)'
)
@click.option(
	'--devicename',
	help='Name of the Device'
)
@click.option(
	'--userdeviceno',
	help='Device Number - This should be unique'
)
	

@cli.command()
@click.pass_obj
def create_disk(ctx,name,size,sr,readonly,vm,devicename,userdeviceno):
    
    """ 
    Create a VDI and Attach to VM. This essentially allows you to add additional disks to a running/stopped VM.
    An Example of using this is: bsdxenvmbuilder create_disk --devicename "/dev/xbdb" --readonly False --sr "NFS VM disks" --size 10 --vm mrtg-test --name "test" --userdeviceno "1"
    """    
    try:
        session = xen_session()
     
        sr_pool = session.xenapi.pool.get_all()[0]
        default_sr = session.xenapi.pool.get_default_SR(sr_pool)
        default_sr = session.xenapi.SR.get_record(default_sr)
        sr_get=default_sr['uuid']
        sr_uuid = session.xenapi.SR.get_by_uuid(default_sr['uuid'])

        opaque = session.xenapi.VM.get_by_name_label(vm) 

        # Need Byte Conversion
        bytes = str(long(size) * 1024L * 1024L * 1024L) 
    
        vdi={'name_label': name,
	    'name_description': name,
	    'SR': sr_uuid,
	    'virtual_size': str(bytes),
	    'type': "user",
            'sharable': False,
            'read_only': False,
            'other_config': dict()}

        vdi_object=session.xenapi.VDI.create(vdi)
    
        # Now that the VDI is created, I have to create it's VBD and attach to the VM
        vbdconnected={'VDI':vdi_object,
            'VM':str(opaque[0]),
            'userdevice': userdeviceno,
     	    'mode':"RW",
    	    'type':"Disk",
    	    'bootable':True,
            'empty':False,
    	    'unpluggable':True,
	    'other_config':{},
            'qos_algorithm_type':'',
	    'qos_algorithm_params':{},
    	    'device':devicename}
   
        session.xenapi.VBD.create(vbdconnected)
        logger.info("Device: " + name + " successfully created!")
    except:
        logging.error("ERROR: Unexpected Error - ", sys.exc_info()[0])
        raise

@click.option(
	'--vm',
	help='Name of VM to attach to'
)
@click.option(
	'--deviceno',
	default=0,
	help='Network Device Number - This should be unique (The first VIF for the VM is 0, so the device no should be incremented)'
)
@click.option(
	'--networkdevice',
	help='Name of the NIC to attach to'
)

@cli.command()
@click.pass_obj
def create_network(ctx,vm,deviceno,networkdevice):
    #""" Create VIF and Attach to Running VM -- Coming Soon """
    """ Coming Soon """

    session = xen_session()
    #opaque = session.xenapi.VM.get_by_name_label(vm) 

    # Configuring Network
    pifs = session.xenapi.PIF.get_all_records()
    for pifRef in pifs.keys():
        if (pifs[pifRef]['device'] == networkdevice):
            networkdevice = pifRef
    logger.info("Choosing PIF with device: ", networkdevice)

    network = session.xenapi.PIF.get_network(str(networkdevice))
    logger.info("Chosen PIF is connected to network: ", session.xenapi.network.get_name_label(network))

    vif = { 'device': str(deviceno),
        'network': network,
        'VM': vm,
        'MAC': "",
        'MTU': "1500",
        "qos_algorithm_type": "",
        "qos_algorithm_params": {},
         "other_config": {} }	

    vif_object = session.xenapi.VIF.create(vif)
    logger.info("VIF Object is now created for: " + vm)

cli()
