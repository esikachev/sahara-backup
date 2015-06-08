def check(self):
    namenode_ip = self._get_node_with_process('NAMENODE')
    self._run_command_on_node(namenode_ip,
                              'set server --host localhost --port 12000')
    self._run_command_on_node(namenode_ip,
                              'show server --all')
    self._run_command_on_node(namenode_ip,
                              'show job --all')
