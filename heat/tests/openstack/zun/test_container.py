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


import mock
import six

from heat.common import exception
from heat.common import template_format
from heat.engine import resource
from heat.engine.resources.openstack.zun import container
from heat.engine import scheduler
from heat.engine import template
from heat.tests import common
from heat.tests import utils

zun_template = '''
heat_template_version: 2017-03-25

resources:
  test_container:
    type: OS::Zun::Container
    properties:
      name: test_container
      image: cirros-latest
      command: sleep 10000
      memory: 100
      environement:{}
      image_driver: docker
'''

zun_template_update = '''
heat_template_version: 2013-05-23

resources:
  test_container:
    type: OS::Zun::Container
    properties:
      name: fake_container
      cpu: 10
      memory: 10
'''

zun_template_update_replace = '''
heat_template_version: 2017-03-25

resources:
  test_container:
    type: OS::Zun::Container
    properties:
      name: test_container
      image: cirros-latest
      command: sleep 10000
      memory: 100
      environement:{}
      image_driver: docker
'''


class ZunContainerTest(common.HeatTestCase):

    def setUp(self):
        super(ZunContainerTest, self).setUp()

        t = template_format.parse(zun_template)
        self.stack = utils.parse_stack(t)
        resource_defns = self.stack.t.resource_definitions(self.stack)
        self.rsrc_defn = resource_defns['test_container']

        self.client = mock.Mock()
        self.patchobject(container.Container, 'client',
                         return_value=self.client)

    def _create_resource(self, name, snippet, stack):
        c = container.Container(name, snippet, stack)
        value = mock.MagicMock(id='12345')
        self.client.containers.create.return_value = value
        self.client.containers.get.return_value = value
        scheduler.TaskRunner(c.create)()
        args = self.client.containers.create.call_args[1]
        self.assertEqual(self.rsrc_defn._properties, args)
        self.assertEqual('12345', c.resource_id)
        return c

    def test_create(self):
        ct = self._create_resource('container', self.rsrc_defn,
                                   self.stack)
        expected_state = (ct.CREATE, ct.COMPLETE)
        self.assertEqual(expected_state, ct.state)
        self.assertEqual('containers', ct.entity)

    def test_create_failed(self):
        c = container.Container('container', self.rsrc_defn,
                                self.stack)
        self.client.containers.run.side_effect = Exception('error')

        exc = self.assertRaises(exception.ResourceFailure,
                                scheduler.TaskRunner(c.run))
        expected_state = (c.CREATE, c.FAILED)
        self.assertEqual(expected_state, c.state)
        self.assertIn('Exception: resources.container: error',
                      six.text_type(exc))

    def test_update(self):
        c = self._create_resource('container', self.rsrc_defn,
                                  self.stack)
        t = template_format.parse(zun_template_update)
        rsrc_defns = template.Template(t).resource_definitions(self.stack)
        new_c = rsrc_defns['container']
        scheduler.TaskRunner(c.update, new_c)()
        args = {
            'name': 'fake-container',
            'cpu': 10,
            'memory': 10,
        }
        self.client.container.update.assert_called_once_with(
            '12345', **args)
        self.assertEqual((c.UPDATE, c.COMPLETE), c.state)

    def test_update_replace(self):
        c = self._create_resource('container', self.rsrc_defn,
                                  self.stack)
        t = template_format.parse(zun_template_update_replace)
        rsrc_defns = template.Template(t).resource_definitions(self.stack)
        new_c = rsrc_defns['container']
        self.assertEqual(0, self.client.container.update.call_count)
        err = self.assertRaises(resource.UpdateReplace,
                                scheduler.TaskRunner(c.update, new_c))
        msg = 'The Resource container requires replacement.'
        self.assertEqual(msg, six.text_type(err))
