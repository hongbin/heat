#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from heat.common.i18n import _
from heat.common import exception
from heat.engine import attributes
from heat.engine import clients
from heat.engine import constraints
from heat.engine import properties
from heat.engine import resource
from heat.engine import support


class Container(resource.Resource):

    support_status = support.SupportStatus(
        version='9.0.0',
        status=support.UNSUPPORTED)

    PROPERTIES = (
        NAME, IMAGE, COMMAND, CPU, MEMORY,
        ENVIRONMENT, WORKDIR, LABEL, IMAGE_PULL_POLICY,
        RESTART_POLICY, TTY, STDIN_OPEN, IMAGE_DRIVER
    ) = (
        'name', 'image', 'command', 'cpu', 'memory',
        'environment', 'workdir', 'labels', 'image_pull_policy',
        'restart_policy', 'tty', 'stdin_open', 'image_driver'
    )

    properties_schema = {
        NAME: properties.Schema(
            properties.Schema.STRING,
            _('name of the container'),
            update_allowed=True
        ),
        IMAGE: properties.Schema(
            properties.Schema.STRING,
            _('name or ID of the image'),
            required=True
        ),
        COMMAND: properties.Schema(
            properties.Schema.STRING,
            _('Send command to the container'),
        ),
        CPU: properties.Schema(
            properties.Schema.STRING,
            _('The number of virtual cpus.'),
            update_allowed=True
        ),
        MEMORY: properties.Schema(
            properties.Schema.STRING,
            _('The container memory size in MiB.'),
            update_allowed=True
        ),
        ENVIRONMENT: properties.Schema(
            properties.Schema.MAP,
            _('The environment variables.'),
        ),
        WORKDIR: properties.Schema(
            properties.Schema.STRING,
            _('The working directory for commands to run in.'),
        ),
        LABEL: properties.Schema(
            properties.Schema.MAP,
            _('Adds a map of labels to a container. '
              'May be used multiple times.'),
        ),
        IMAGE_PULL_POLICY: properties.Schema(
            properties.Schema.STRING,
            _('The policy which determines if the image should'
              'be pulled prior to starting the container. '),
            constraints=[
                constraints.AllowedValues(['ifnotpresent', 'always',
                                           'never']),
            ]
        ),
        RESTART_POLICY: properties.Schema(
            properties.Schema.MAP,
            _('Restart policy to apply when a container exits'),
        ),
        TTY: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Allocate a pseudo-TTY.'),
        ),
        STDIN_OPEN: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Keep STDIN open even if not attached.'),
        ),
        IMAGE_DRIVER: properties.Schema(
            properties.Schema.STRING,
            _('The image driver to use to pull container image. '),
            constraints=[
                constraints.AllowedValues(['docker',
                                           'glance']),
            ]

        ),

    }

    ATTRIBUTES = (
        ADDRESSES
    ) = (
        'addresses'
    )

    attributes_schema = {
        ADDRESSES: attributes.Schema(
            _('A dict of all network addresses with corresponding port_id. '
              'Each network will have two keys in dict, they are network '
              'name and network id. '
              'The port ID may be obtained through the following expression: '
              '"{get_attr: [<container>, addresses, <network name_or_id>, 0, '
              'port]}".'),
            type=attributes.Schema.MAP
        )
    }

    default_client_name = 'zun'

    entity = 'containers'

    def _resolve_attribute(self, name):
        print("22222222222222")
        if self.resource_id is None:
            return
        try:
            container = self.client().containers.get(self.resource_id)
        except Exception as e:
            self.client_plugin().ignore_not_found(e)
            return ''
        if name == self.ADDRESSES:
            print("container: " + repr(container))
            return getattr(container, 'addresses', {})

    def handle_create(self):
        args = dict((k, v) for k, v in self.properties.items()
                    if v is not None)
        container = self.client().containers.run(**args)
        self.resource_id_set(container.uuid)
        return container.uuid

    def check_create_complete(self, id):
        print("111111111111")
        container = self.client().containers.get(id)
        if container.status == 'Creating':
            return False
        elif container.status is None:
            return False
        elif container.status in ('Running', 'Created'):
            print("container: " + repr(container))
            return True
        elif container.status == 'Error':
            msg = (_("Failed to create Container '%(name)s' - %(reason)s")
                   % {'name': self.name, 'reason': container.status_reason})
            raise exception.ResourceInError(status_reason=msg,
                                            resource_status=container.status)
        else:
            msg = (_("Unknown status creating Container '%(name)s' - %(reason)s")
                   % {'name': self.name, 'reason': container.status_reason})
            raise exception.ResourceUnknownStatus(status_reason=msg,
                                                  resource_status=container.status)

    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        if prop_diff:
            self.client().containers.update(self.resource_id,
                                            **prop_diff)

    def handle_delete(self):
        if not self.resource_id:
            return
        try:
            self.client().containers.delete(self.resource_id, force=True)
        except Exception as exc:
            self.client_plugin().ignore_not_found(exc)


def resource_mapping():
    return {
        'OS::Zun::Container': Container
    }


def available_resource_mapping():
    if not clients.has_client('zun'):
        return {}

    return resource_mapping()
