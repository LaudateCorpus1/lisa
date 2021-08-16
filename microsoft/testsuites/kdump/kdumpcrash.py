# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from lisa import (
    Node,
    SkippedException,
    TestCaseMetadata,
    TestSuite,
    TestSuiteMetadata,
    simple_requirement,
    schema,
)

from pathlib import PurePosixPath
from lisa.tools import Dmesg, Uname, Kdump
from assertpy import assert_that
from lisa.operating_system import Redhat, Suse, Debian


@TestSuiteMetadata(
    area="kdump",
    category="functional",
    description="""
    This test suite is used to check if vmcore is generated after triggering
    kdump through injecting NMI or echoing c into sysrq-trigger.
    """,
)
class KdumpCrash(TestSuite):
    crash_kernel = "512M"
    vmbus_string = "Vmbus version:"
    dump_path = "/var/crash"
    trigger_kdump_cmd = "sync; echo c > /proc/sysrq-trigger"
    config_path = ""

    def _get_boot_config_path(self, node: Node) -> str:
        uname_tool = node.tools[Uname]
        kernel_ver = uname_tool.get_linux_information().kernel_version
        config_path = f"/boot/config-{kernel_ver}"
        assert_that(node.shell.exists(PurePosixPath(config_path))).described_as(
            f"/boot/config-{kernel_ver} not exist."
            " Please check if the kernel version is right."
        ).is_true()
        return config_path

    def _kdump_test(self, node: Node) -> None:
        dmesg = node.tools[Dmesg]
        if self.vmbus_string not in dmesg.get_output():
            raise SkippedException(
                "Negotiated VMBus version is not 3.0. "
                "Kernel might be old or patches not included. "
                "Full support for kdump is not present."
            )

        self.config_path = self._get_boot_config_path(node)
        cmd_result = node.execute(
            f"grep CONFIG_KEXEC_AUTO_RESERVE=y {self.config_path}",
            shell=True,
            sudo=True,
        )

        if isinstance(node.os, Redhat) and node.os.information.version < "8.0.0":
            if self.crash_kernel == "auto" and cmd_result.exit_code != 0:
                raise SkippedException("crashkernel=auto doesn't work for this distro.")
        if (
            not isinstance(node.os, Redhat)
            and not isinstance(node.os, Debian)
            and not isinstance(node.os, Suse)
        ):
            raise SkippedException("Distro not supported. Skip the test.")

        kdump = node.tools[Kdump]
        kdump.config_kdump(self.dump_path)
        kdump.config_crashkernel_memory(self.crash_kernel)
        kdump.enable_kdump_service()

        # Reboot system to make kdump take effect
        node.reboot()

        # If /proc/sys/kernel/unknown_nmi_panic exist, config unknown_nmi_panic as 1
        kdump.config_nmi_panic()

        # Confirm that the kernel dump mechanism is enabled
        kdump.check_kdump_loaded()
        kdump.check_kdump_service()

        # Activate the magic SysRq option
        cmd_result = node.execute(
            "echo 1 > /proc/sys/kernel/sysrq",
            shell=True,
            sudo=True,
        )

        # Trigger kdump
        cmd_result = node.execute(
            self.trigger_kdump_cmd,
            shell=True,
            sudo=True,
        )

    @TestCaseMetadata(
        description="""
        This test case will trigger kdump in the VM which has one core
        """,
        priority=0,
        requirement=simple_requirement(node=schema.NodeSpace(core_count=2)),
    )
    def kdumpcrash_validate_single_core(self, node: Node) -> None:
        self.crash_kernel = "512M"
        self._kdump_test(node)