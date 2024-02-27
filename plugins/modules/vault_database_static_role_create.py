#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2024, Martin Chmielewski (@M4rt1nCh)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
module: vault_database_static_role_create
version_added: 2.6.0
author:
  - Martin Chmielewski (@M4rt1nCh)
short_description: Create or update a static role definition
requirements:
  - C(hvac) (L(Python library,https://hvac.readthedocs.io/en/stable/overview.html))
  - For detailed requirements, see R(the collection requirements page,ansible_collections.community.hashi_vault.docsite.user_guide.requirements).
description:
  - Creates a new or updates an existing static role identified by its role_name
notes:
  - C(vault_database_static_role_create) triggers the creation of a static role
  - https://hvac.readthedocs.io/en/stable/usage/secrets_engines/database.html#create-static-role
  - The I(data) option is not treated as secret and may be logged. Use the C(no_log) keyword if I(data) contains sensitive values.
  - This module always reports C(changed) status because it cannot guarantee idempotence.
  - Use C(changed_when) to control that in cases where the operation is known to not change state.
attributes:
  check_mode:
    support: partial
    details:
      - In check mode, an empty response will be returned and the write will not be performed.
extends_documentation_fragment:
  - community.hashi_vault.attributes
  - community.hashi_vault.attributes.action_group
  - community.hashi_vault.connection
  - community.hashi_vault.auth
options:
  path:
    description: Vault path of a database secrets engine.
    type: str
    required: True
  connection_name:
    description: The connection name under which the role should be created.
    type: str
    required: True
  role_name:
    description: The name of the role that should be created.
    type: str
    required: True
  db_username:
    description: The database username - Note that the user must exist in the target database!
    type: str
    required: True
  rotation_statements:
    description: SQL statements to rotate the password for the given C(db_username)
    type: list
    required: True
    elements: str
  rotation_period:
    description: Password rotation period in seconds (defaults to 24hs)
    type: int
    required: False
    default: 86400
'''

EXAMPLES = r"""
- name: Generate rotation statement
  ansible.builtin.set_fact:
    rotation_statements = ["ALTER USER \"{{name}}\" WITH PASSWORD '{{password}}';"]

- name: Create / update Static Role
  community.hashi_vault.vault_database_static_role_create:
    path: database
    connection_name: SomeConnection
    role_name: SomeRole
    db_username: '{{ db_username}}'
    rotation_statements: '{{ rotation_statements }}'
  register: response

- name: Display the result of the operation
  ansible.builtin.debug:
    msg: "{{ result }}"
"""

RETURN = r"""
data:
  description: The result of the operation.
  returned: success
  type: dict
  sample:
    status: "success"
raw:
  description: The raw result of the operation.
  returned: success
  type: dict
  sample:
    auth: null
    data: null
    lease_duration: 0
    lease_id: ""
    renewable: false
    request_id: "123456"
    warnings: null
    wrap_info: null
"""

import traceback

from ansible.module_utils._text import to_native
from ansible.module_utils.basic import missing_required_lib

from ..module_utils._hashi_vault_module import HashiVaultModule
from ..module_utils._hashi_vault_common import HashiVaultValueError

try:
    import hvac
except ImportError:
    HAS_HVAC = False
    HVAC_IMPORT_ERROR = traceback.format_exc()
else:
    HVAC_IMPORT_ERROR = None
    HAS_HVAC = True


def run_module():
    argspec = HashiVaultModule.generate_argspec(
        path=dict(type='str', required=True),
        connection_name=dict(type='str', required=True),
        role_name=dict(type='str', required=True),
        db_username=dict(type='str', required=True),
        rotation_statements=dict(type='list', required=True, elements='str'),
        rotation_period=dict(type='int', required=False, default=86400),
    )

    module = HashiVaultModule(
        argument_spec=argspec,
        supports_check_mode=True
    )

    if not HAS_HVAC:
        module.fail_json(
            msg=missing_required_lib('hvac'),
            exception=HVAC_IMPORT_ERROR
        )

    path = module.params.get('path')
    connection_name = module.params.get('connection_name')
    role_name = module.params.get('role_name')
    db_username = module.params.get('db_username')
    rotation_statements = module.params.get('rotation_statements')
    rotation_period = module.params.get('rotation_period')

    module.connection_options.process_connection_options()
    client_args = module.connection_options.get_hvac_connection_options()
    client = module.helper.get_vault_client(**client_args)

    try:
        module.authenticator.validate()
        module.authenticator.authenticate(client)
    except (NotImplementedError, HashiVaultValueError) as e:
        module.fail_json(msg=to_native(e), exception=traceback.format_exc())

    try:
        raw = client.secrets.database.create_static_role(
            name=role_name,
            db_name=connection_name,
            mount_point=path,
            rotation_period=rotation_period,
            rotation_statements=rotation_statements,
            username=db_username,
        )
    except hvac.exceptions.Forbidden as e:
        module.fail_json(msg="Forbidden: Permission Denied to path ['%s']." % path, exception=traceback.format_exc())
    except hvac.exceptions.InvalidPath as e:
        module.fail_json(
            msg="Invalid or missing path ['%s']. Check the path." % (path),
            exception=traceback.format_exc()
        )

    # this is required due to a different API response in vault 1.14.9 vs. later versions
    if raw:
        from requests.models import Response
        if isinstance(raw, Response):
            raw_res = raw.text
        else:
            raw_res = raw

    module.exit_json(
        data={
            'status': 'success',
        },
        raw=raw_res,
        changed=True
    )


def main():
    run_module()


if __name__ == '__main__':
    main()