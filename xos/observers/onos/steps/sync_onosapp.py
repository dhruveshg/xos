import hashlib
import os
import socket
import sys
import base64
import time
from django.db.models import F, Q
from xos.config import Config
from observer.syncstep import SyncStep
from observer.ansible import run_template_ssh
from observers.base.SyncInstanceUsingAnsible import SyncInstanceUsingAnsible
from core.models import Service, Slice
from services.onos.models import ONOSService, ONOSApp
from util.logger import Logger, logging

# hpclibrary will be in steps/..
parentdir = os.path.join(os.path.dirname(__file__),"..")
sys.path.insert(0,parentdir)

logger = Logger(level=logging.INFO)

class SyncONOSApp(SyncInstanceUsingAnsible):
    provides=[ONOSApp]
    observes=ONOSApp
    requested_interval=0
    template_name = "sync_onosapp.yaml"
    service_key_name = "/opt/xos/observers/onos/onos_key"

    def __init__(self, *args, **kwargs):
        super(SyncONOSApp, self).__init__(*args, **kwargs)

    def fetch_pending(self, deleted):
        if (not deleted):
            objs = ONOSApp.get_tenant_objects().filter(Q(enacted__lt=F('updated')) | Q(enacted=None),Q(lazy_blocked=False))
        else:
            objs = ONOSApp.get_deleted_tenant_objects()

        return objs

    def get_instance(self, o):
        # We assume the ONOS service owns a slice, so pick one of the instances
        # inside that slice to sync to.

        serv = self.get_onos_service(o)

        if serv.use_external_host:
            return serv.use_external_host

        if serv.slices.exists():
            slice = serv.slices.all()[0]
            if slice.instances.exists():
                return slice.instances.all()[0]

        return None

    def get_onos_service(self, o):
        if not o.provider_service:
            return None

        onoses = ONOSService.get_service_objects().filter(id=o.provider_service.id)
        if not onoses:
            return None

        return onoses[0]

    def get_files_dir(self, o):
        if not hasattr(Config(), "observer_steps_dir"):
            # make steps_dir mandatory; there's no valid reason for it to not
            # be defined.
            raise Exception("observer_steps_dir is not defined in config file")

        step_dir = Config().observer_steps_dir

        return os.path.join(step_dir, "..", "files", str(self.get_onos_service(o).id), o.name)

    def write_configs(self, o):
        o.config_fns = []
        o.rest_configs = []
        o.files_dir = self.get_files_dir(o)

        if not os.path.exists(o.files_dir):
            os.makedirs(o.files_dir)

        # Combine the service attributes with the tenant attributes. Tenant
        # attribute can override service attributes.
        attrs = o.provider_service.serviceattribute_dict
        attrs.update(o.tenantattribute_dict)

        for (name, value) in attrs.items():
            if name.startswith("config_"):
                fn = name[7:] # .replace("_json",".json")
                o.config_fns.append(fn)
                file(os.path.join(o.files_dir, fn),"w").write(value)
            if name.startswith("rest_"):
                fn = name[5:].replace("/","_")
                endpoint = name[5:]
                # Ansible goes out of it's way to make our life difficult. If
                # 'lookup' sees a file that it thinks contains json, then it'll
                # insist on parsing and return a json object. We just want
                # a string, so prepend a space and then strip the space off
                # later.
                file(os.path.join(o.files_dir, fn),"w").write(" " +value)
                o.rest_configs.append( {"endpoint": endpoint, "fn": fn} )

    def prepare_record(self, o):
        self.write_configs(o)

    def get_extra_attributes(self, o):
        fields={}
        fields["files_dir"] = o.files_dir
        fields["appname"] = o.name
        fields["nat_ip"] = self.get_instance(o).get_ssh_ip()
        fields["config_fns"] = o.config_fns
        fields["rest_configs"] = o.rest_configs
        fields["dependencies"] = [x.strip() for x in o.dependencies.split(",")]
        fields["ONOS_container"] = "ONOS"
        return fields

    def sync_fields(self, o, fields):
        # the super causes the playbook to be run
        super(SyncONOSApp, self).sync_fields(o, fields)

    def run_playbook(self, o, fields):
        super(SyncONOSApp, self).run_playbook(o, fields)

    def delete_record(self, m):
        pass
