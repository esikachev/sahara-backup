# Copyright (c) 2015 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from sahara import exceptions as ex
from sahara.plugins import base as plugin_base
from sahara.service.edp import api
from sahara.service import ops
from sahara.tests.unit import base


class EdpApiTestCase(base.SaharaTestCase):
    def setUp(self):
        super(EdpApiTestCase, self).setUp()
        l_ops = ops.LocalOps()
        api.setup_edp_api(l_ops)
        plugin_base.setup_plugins()

        # plugins descriptions
        vanilla_desc = (u'The Apache Vanilla plugin provides the ability to '
                        'launch upstream Vanilla Apache Hadoop cluster without'
                        ' any management consoles. It can also deploy the '
                        'Oozie component.')
        hdp_desc = (u'The Hortonworks Sahara plugin automates the deployment '
                    'of the Hortonworks Data Platform (HDP) on OpenStack.')
        cdh_desc = (u'The Cloudera Sahara plugin provides the ability to '
                    'launch the Cloudera distribution of Apache Hadoop (CDH) '
                    'with Cloudera Manager management console.')

        self.all_plugins = [
            {'name': 'Hive',
             'plugins': [{'description': vanilla_desc,
                          'name': 'vanilla',
                          'title': 'Vanilla Apache Hadoop',
                          'versions': {'1.2.1': {}, '2.6.0': {}}},
                         {'description': hdp_desc,
                          'name': 'hdp',
                          'title': 'Hortonworks Data Platform',
                          'versions': {'1.3.2': {}, '2.0.6': {}}},
                         {'description': cdh_desc,
                          'name': 'cdh',
                          'title': 'Cloudera Plugin',
                          'versions': {'5': {}, '5.3.0': {}}}]},
            {'name': 'Java',
             'plugins': [{'description': vanilla_desc,
                          'name': 'vanilla',
                          'title': 'Vanilla Apache Hadoop',
                          'versions': {'1.2.1': {}, '2.6.0': {}}},
                         {'description': hdp_desc,
                          'name': 'hdp',
                          'title': 'Hortonworks Data Platform',
                          'versions': {'1.3.2': {}, '2.0.6': {}}},
                         {'description': cdh_desc,
                          'name': 'cdh',
                          'title': 'Cloudera Plugin',
                          'versions': {'5': {}, '5.3.0': {}}}]},
            {'name': 'MapReduce',
             'plugins': [{'description': vanilla_desc,
                          'name': 'vanilla',
                          'title': 'Vanilla Apache Hadoop',
                          'versions': {'1.2.1': {}, '2.6.0': {}}},
                         {'description': hdp_desc,
                          'name': 'hdp',
                          'title': 'Hortonworks Data Platform',
                          'versions': {'1.3.2': {}, '2.0.6': {}}},
                         {'description': cdh_desc,
                          'name': 'cdh',
                          'title': 'Cloudera Plugin',
                          'versions': {'5': {}, '5.3.0': {}}}]},
            {'name': 'MapReduce.Streaming',
             'plugins': [{'description': vanilla_desc,
                          'name': 'vanilla',
                          'title': 'Vanilla Apache Hadoop',
                          'versions': {'1.2.1': {}, '2.6.0': {}}},
                         {'description': hdp_desc,
                          'name': 'hdp',
                          'title': 'Hortonworks Data Platform',
                          'versions': {'1.3.2': {}, '2.0.6': {}}},
                         {'description': cdh_desc,
                          'name': 'cdh',
                          'title': 'Cloudera Plugin',
                          'versions': {'5': {}, '5.3.0': {}}}]},
            {'name': 'Pig',
             'plugins': [{'description': vanilla_desc,
                          'name': 'vanilla',
                          'title': 'Vanilla Apache Hadoop',
                          'versions': {'1.2.1': {}, '2.6.0': {}}},
                         {'description': hdp_desc,
                          'name': 'hdp',
                          'title': 'Hortonworks Data Platform',
                          'versions': {'1.3.2': {}, '2.0.6': {}}},
                         {'description': cdh_desc,
                          'name': 'cdh',
                          'title': 'Cloudera Plugin',
                          'versions': {'5': {}, '5.3.0': {}}}]},
            {'name': 'Shell',
             'plugins': [{'description': vanilla_desc,
                          'name': 'vanilla',
                          'title': 'Vanilla Apache Hadoop',
                          'versions': {'1.2.1': {}, '2.6.0': {}}},
                         {'description': hdp_desc,
                          'name': 'hdp',
                          'title': 'Hortonworks Data Platform',
                          'versions': {'1.3.2': {}, '2.0.6': {}}},
                         {'description': cdh_desc,
                          'name': 'cdh',
                          'title': 'Cloudera Plugin',
                          'versions': {'5': {}, '5.3.0': {}}}]},
            {'name': 'Spark',
             'plugins': [{'description': (u'This plugin provides an ability to'
                                          ' launch Spark on Hadoop CDH cluster'
                                          ' without any management consoles.'),
                          'name': 'spark',
                          'title': 'Apache Spark',
                          'versions': {'1.0.0': {}}}]},
            ]

    @mock.patch('sahara.plugins.base.PluginManager')
    def test_get_job_types(self, mock_manger):
        res = api.get_job_types()
        self.assertEqual(self.all_plugins, res)

    @mock.patch('sahara.service.edp.job_manager.get_job_config_hints')
    def test_get_job_config_hints(self, mock_get):
        api.get_job_config_hints('to be')
        mock_get.assert_called_once_with('to be')

    @mock.patch('sahara.conductor.api.LocalApi.job_execution_create')
    def test_execute_job(self, mock_create):
        data = {'cluster_id': '1'}
        res = api.execute_job('1', data)
        self.assertEqual(mock_create(), res)

    @mock.patch('sahara.utils.proxy.create_proxy_user_for_job_execution')
    @mock.patch('sahara.utils.proxy.job_execution_requires_proxy_user')
    @mock.patch('sahara.conductor.api.LocalApi.job_execution_create')
    def test_execute_job_with_proxy(self, mock_create, mock_proxy_req,
                                    mock_proxy_user):
        data = {'cluster_id': '1'}
        res = api.execute_job('1', data)
        mock_proxy_user.assert_called_once_with(mock_create())
        self.assertEqual(mock_create(), res)

    @mock.patch('sahara.utils.proxy.create_proxy_user_for_job_execution')
    @mock.patch('sahara.utils.proxy.job_execution_requires_proxy_user')
    @mock.patch('sahara.conductor.api.LocalApi.job_execution_destroy')
    @mock.patch('sahara.conductor.api.LocalApi.job_execution_create')
    def test_execute_job_with_proxy_fail(self, mock_create, mock_destroy,
                                         mock_proxy_req, mock_proxy_user):
        data = {'cluster_id': '1'}
        mock_proxy_user.side_effect = ex.SaharaException
        self.assertRaises(ex.SaharaException, api.execute_job, '1', data)

    @mock.patch('sahara.service.edp.job_manager.get_job_status')
    def test_get_job_execution_status(self, mock_get):
        api.get_job_execution_status('1')
        mock_get.assert_called_once_with('1')

    @mock.patch('sahara.conductor.api.LocalApi.job_execution_get_all')
    @mock.patch('sahara.context.ctx')
    def test_job_execution_list(self, mock_ctx, mock_get):
        api.job_execution_list()
        mock_get.assert_called_once_with(mock_ctx())

    @mock.patch('sahara.conductor.api.LocalApi.job_execution_get')
    @mock.patch('sahara.context.ctx')
    def test_get_job_executiont(self, mock_ctx, mock_get):
        api.get_job_execution('1')
        mock_get.assert_called_once_with(mock_ctx(), '1')

    @mock.patch('sahara.service.ops.LocalOps.cancel_job_execution')
    @mock.patch('sahara.conductor.api.LocalApi.job_execution_get')
    @mock.patch('sahara.context.ctx')
    @mock.patch('sahara.context.set_current_job_execution_id')
    def test_cancel_job_execution(self, mock_current, mock_ctx, mock_get,
                                  mock_cancel):
        api.cancel_job_execution('1')
        mock_ctx.assert_called_once_with()
        mock_get.assert_called_once_with(mock_ctx('1'), '1')
        mock_current.assert_called_once_with('1')
        mock_cancel.assert_called_once_with('1')

    @mock.patch('sahara.service.ops.LocalOps.delete_job_execution')
    @mock.patch('sahara.context.set_current_job_execution_id')
    def test_delete_job_execution(self, mock_current, mock_cancel):
        api.delete_job_execution('1')
        mock_cancel.assert_called_once_with('1')
