# Copyright 2026 NXP
#
# NXP Proprietary. This software is owned or controlled by NXP and may
# only be used strictly in accordance with the applicable license terms.
# By expressly accepting such terms or by downloading, installing,
# activating and/or otherwise using the software, you are agreeing that
# you have read, and that you agree to comply with and are bound by,
# such license terms.  If you do not agree to be bound by the applicable
# license terms, then you may not retain, install, activate or otherwise
# use the software.

from nxp.mcp.shared import ActionContract, ActionParameter
from nxp.mcp.shared import ActionExecutable
from nxp.mcp.s32debugger.handlers.action_handlers import generate_gdb_config_file


GENERATE_GDB_CONFIG_FILE_ACTION = ActionExecutable(
    contract=ActionContract(
        name='generate.gdb_config_file',
        description='Generate an S32Debugger GDB configuration file from a Python example template, with an embedded interactive JSON-RPC bridge on the given port.',
        params=(
            ActionParameter(
                name='soc_family',
                required=True,
                schema={'description': 'S32Debugger SoC family identifier.', 'minLength': 1, 'type': 'string'},
            ),
            ActionParameter(
                name='script_type',
                required=True,
                schema={'description': 'Template script type.', 'minLength': 1, 'type': 'string'},
            ),
            ActionParameter(
                name='template_name',
                required=True,
                schema={'description': 'Python example template name.', 'minLength': 1, 'type': 'string'},
            ),
            ActionParameter(
                name='port',
                required=True,
                schema={'description': 'JSON-RPC bridge port baked into the generated config (start_bridge(port=...)).',
                        'maximum': 65535,
                        'minimum': 1,
                        'type': 'integer'},
            ),
            ActionParameter(
                name='output_name',
                required=False,
                schema={'description': 'Optional output file name override.', 'type': 'string'},
            ),
            ActionParameter(
                name='probe_ip',
                required=False,
                schema={'description': 'Optional probe IP address or hostname.', 'type': 'string'},
            ),
            ActionParameter(
                name='soc_name',
                required=False,
                schema={'description': 'Optional SoC name override.', 'type': 'string'},
            ),
            ActionParameter(
                name='core_name',
                required=False,
                schema={'description': 'Optional core name override.', 'type': 'string'},
            ),
            ActionParameter(
                name='core_id',
                required=False,
                schema={'description': 'Optional core identifier.', 'type': 'integer'},
            ),
            ActionParameter(
                name='cluster_id',
                required=False,
                schema={'description': 'Optional cluster ID override.', 'type': 'string'},
            ),
            ActionParameter(
                name='lockstep',
                required=False,
                schema={'description': 'Optional lockstep override.', 'type': 'boolean'},
            ),
            ActionParameter(
                name='jtag_speed',
                required=False,
                schema={'description': 'Optional JTAG speed override.', 'type': 'integer'},
            ),
            ActionParameter(
                name='gdb_server_port',
                required=False,
                schema={'description': 'Optional GDB server port override.',
                        'maximum': 65535,
                        'minimum': 1,
                        'type': 'integer'},
            ),
            ActionParameter(
                name='ccs_ip',
                required=False,
                schema={'description': 'Optional CCS IP address override.', 'type': 'string'},
            ),
            ActionParameter(
                name='ccs_port',
                required=False,
                schema={'description': 'Optional CCS port override.',
                        'maximum': 65535,
                        'minimum': 1,
                        'type': 'integer'},
            ),
            ActionParameter(
                name='is_logging_enabled',
                required=False,
                schema={'description': 'Enable or disable debugger-side logging.', 'type': 'boolean'},
            ),
            ActionParameter(
                name='file_debug',
                required=False,
                schema={'description': 'Optional debug log file path.', 'type': 'string'},
            ),
            ActionParameter(
                name='init_script',
                required=False,
                schema={'description': 'Optional initialization script path.', 'type': 'string'},
            ),
            ActionParameter(
                name='secure_type',
                required=False,
                schema={'description': 'Optional security mode override.', 'type': 'string'},
            ),
            ActionParameter(
                name='secure_key',
                required=False,
                schema={'description': 'Optional secure key material path or value.', 'type': 'string'},
            ),
            ActionParameter(
                name='lifecycle',
                required=False,
                schema={'description': 'Optional lifecycle override.', 'type': 'string'},
            ),
            ActionParameter(
                name='reset_type',
                required=False,
                schema={'description': 'Optional reset type override.', 'type': 'string'},
            ),
            ActionParameter(
                name='reset_delay',
                required=False,
                schema={'description': 'Optional reset delay override in milliseconds or tool-specific units.',
                        'type': 'integer'},
            ),
            ActionParameter(
                name='remote_timeout',
                required=False,
                schema={'description': 'Optional remote timeout override.', 'type': 'integer'},
            ),
            ActionParameter(
                name='gdb_timeout',
                required=False,
                schema={'description': 'Optional GDB timeout override.', 'type': 'integer'},
            ),
            ActionParameter(
                name='resultexception',
                required=False,
                schema={'description': 'Optional RESULTEXCEPTION override.', 'type': 'boolean'},
            ),
            ActionParameter(
                name='non_stop_mode',
                required=False,
                schema={'description': 'Optional NON_STOP_MODE override. When omitted, defaults to True in the generated config.', 'type': 'boolean'},
            ),
            ActionParameter(
                name='overwrite',
                required=False,
                schema={'description': 'When True, overwrite an existing config file with the same name. When False (default), an explicit output_name collision returns an error, while an auto-generated name falls back to a timestamped file.', 'type': 'boolean'},
            ),
        ),
        preconditions=(
            'An effective installation path must be configured.',
        ),
        workflow_hints=(
            'Typical flow: generate.gdb_config_file -> control.start_gdb with the generated config file.',
        ),
        related_actions=(
            'control.start_gdb',
        ),
        category='generate',
    ),
    handler=generate_gdb_config_file,
)
