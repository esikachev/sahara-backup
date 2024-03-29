# Copyright (c) 2013 Mirantis Inc.
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

from heatclient import exc as heat_exc
from oslo_config import cfg
from oslo_log import log as logging

from sahara import conductor as c
from sahara import context
from sahara.i18n import _
from sahara.i18n import _LW
from sahara.service import engine as e
from sahara.service.heat import templates as ht
from sahara.service import volumes
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils import general as g
from sahara.utils.openstack import base as b
from sahara.utils.openstack import heat

conductor = c.API
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class HeatEngine(e.Engine):
    def get_type_and_version(self):
        return "heat.3.0"

    def create_cluster(self, cluster):
        self._update_rollback_strategy(cluster, shutdown=True)

        launcher = _CreateLauncher()

        target_count = self._get_ng_counts(cluster)
        self._nullify_ng_counts(cluster)

        launcher.launch_instances(cluster, target_count)

        self._update_rollback_strategy(cluster)

    def _get_ng_counts(self, cluster):
        count = {}
        for node_group in cluster.node_groups:
            count[node_group.id] = node_group.count
        return count

    def _nullify_ng_counts(self, cluster):
        ctx = context.ctx()

        for node_group in cluster.node_groups:
            conductor.node_group_update(ctx, node_group, {"count": 0})

    def scale_cluster(self, cluster, target_count):
        ctx = context.ctx()

        rollback_count = self._get_ng_counts(cluster)

        self._update_rollback_strategy(cluster, rollback_count=rollback_count,
                                       target_count=target_count)

        launcher = _ScaleLauncher()

        launcher.launch_instances(cluster, target_count)

        cluster = conductor.cluster_get(ctx, cluster)
        g.clean_cluster_from_empty_ng(cluster)

        self._update_rollback_strategy(cluster)

        return launcher.inst_ids

    def rollback_cluster(self, cluster, reason):
        rollback_info = cluster.rollback_info or {}
        self._update_rollback_strategy(cluster)

        if rollback_info.get('shutdown', False):
            self._rollback_cluster_creation(cluster, reason)
            LOG.warning(_LW("Cluster creation rollback "
                            "(reason: {reason})").format(reason=reason))

            return False

        rollback_count = rollback_info.get('rollback_count', {}).copy()
        target_count = rollback_info.get('target_count', {}).copy()
        if rollback_count or target_count:
            self._rollback_cluster_scaling(
                cluster, rollback_count, target_count, reason)
            LOG.warning(_LW("Cluster scaling rollback "
                            "(reason: {reason})").format(reason=reason))

            return True

        return False

    def _update_rollback_strategy(self, cluster, shutdown=False,
                                  rollback_count=None, target_count=None):
        rollback_info = {}

        if shutdown:
            rollback_info['shutdown'] = shutdown

        if rollback_count:
            rollback_info['rollback_count'] = rollback_count

        if target_count:
            rollback_info['target_count'] = target_count

        cluster = conductor.cluster_update(
            context.ctx(), cluster, {'rollback_info': rollback_info})
        return cluster

    def _populate_cluster(self, cluster, stack):
        ctx = context.ctx()
        old_ids = [i.instance_id for i in g.get_instances(cluster)]
        new_ids = []

        for node_group in cluster.node_groups:
            instances = stack.get_node_group_instances(node_group)
            for instance in instances:
                nova_id = instance['physical_id']
                name = instance['name']
                if nova_id not in old_ids:
                    instance_id = conductor.instance_add(
                        ctx, node_group, {"instance_id": nova_id,
                                          "instance_name": name})
                    new_ids.append(instance_id)

        return new_ids

    def _rollback_cluster_creation(self, cluster, ex):
        """Shutdown all instances and update cluster status."""

        self.shutdown_cluster(cluster)

    def _rollback_cluster_scaling(self, cluster, rollback_count,
                                  target_count, ex):
        """Attempt to rollback cluster scaling.

        Our rollback policy for scaling is as follows:
        We shut down nodes created during scaling, but we don't try to
        to get back decommissioned nodes. I.e. during the rollback
        we only shut down nodes and not launch them. That approach should
        maximize the chance of rollback success.
        """

        for ng in rollback_count:
            if rollback_count[ng] > target_count[ng]:
                rollback_count[ng] = target_count[ng]

        launcher = _RollbackLauncher()
        launcher.launch_instances(cluster, rollback_count)

    def shutdown_cluster(self, cluster):
        """Shutdown specified cluster and all related resources."""
        try:
            b.execute_with_retries(heat.client().stacks.delete, cluster.name)
            stack = heat.get_stack(cluster.name)
            heat.wait_stack_completion(stack)
        except heat_exc.HTTPNotFound:
            LOG.warning(_LW('Did not find stack for cluster. Trying to delete '
                            'cluster manually.'))

            # Stack not found. Trying to delete cluster like direct engine
            #  do it
            self._shutdown_instances(cluster)
            self._delete_aa_server_group(cluster)

        self._clean_job_executions(cluster)
        self._remove_db_objects(cluster)


class _CreateLauncher(HeatEngine):
    STAGES = ["Spawning", "Waiting", "Preparing"]
    UPDATE_STACK = False
    DISABLE_ROLLBACK = True
    inst_ids = []

    @cpo.event_wrapper(
        True, step=_('Create Heat stack'), param=('cluster', 1))
    def create_instances(self, cluster, target_count):
        tmpl = ht.ClusterTemplate(cluster)

        self._configure_template(tmpl, cluster, target_count)
        stack = tmpl.instantiate(update_existing=self.UPDATE_STACK,
                                 disable_rollback=self.DISABLE_ROLLBACK)
        heat.wait_stack_completion(stack.heat_stack)
        self.inst_ids = self._populate_cluster(cluster, stack)

    def launch_instances(self, cluster, target_count):
        # create all instances
        cluster = g.change_cluster_status(cluster, self.STAGES[0])

        self.create_instances(cluster, target_count)

        # wait for all instances are up and networks ready
        cluster = g.change_cluster_status(cluster, self.STAGES[1])

        instances = g.get_instances(cluster, self.inst_ids)

        self._await_networks(cluster, instances)

        # prepare all instances
        cluster = g.change_cluster_status(cluster, self.STAGES[2])

        instances = g.get_instances(cluster, self.inst_ids)
        volumes.mount_to_instances(instances)

        self._configure_instances(cluster)

    def _configure_template(self, tmpl, cluster, target_count):
        ctx = context.ctx()
        for node_group in cluster.node_groups:
            count = target_count[node_group.id]
            tmpl.add_node_group_extra(node_group.id, count,
                                      self._generate_user_data_script)

            # if number of instances decreases, we need to drop
            # the excessive ones
            for i in range(count, node_group.count):
                conductor.instance_remove(ctx, node_group.instances[i])


class _ScaleLauncher(_CreateLauncher):
    STAGES = ["Scaling: Spawning", "Scaling: Waiting", "Scaling: Preparing"]
    UPDATE_STACK = True
    DISABLE_ROLLBACK = False


class _RollbackLauncher(_CreateLauncher):
    STAGES = ["Rollback: Spawning", "Rollback: Waiting", "Rollback: Preparing"]
    UPDATE_STACK = True
