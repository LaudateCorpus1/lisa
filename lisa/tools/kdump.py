# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from lisa.tools.service import Systemctl
from lisa.tools.echo import Echo

from pathlib import PurePosixPath
from lisa.executable import Tool
from lisa.tools import Sed, Cat
from lisa.operating_system import Posix, Redhat, Suse, Debian
from typing import cast
from assertpy import assert_that


class Kdump(Tool):
    # Redhat: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/kernel_administration_guide/kernel_crash_dump_guide
    # Ubuntu: https://ubuntu.com/server/docs/kernel-crash-dump
    # Suse: https://www.suse.com/zh-cn/support/kb/doc/?id=000016171
    kexec_crash = "/sys/kernel/kexec_crash_loaded"

    @property
    def command(self) -> str:
        return "makedumpfile"

    @property
    def can_install(self) -> bool:
        return True

    def _check_exists(self) -> bool:
        if isinstance(self.node.os, Redhat):
            if self.node.os.package_exists("kexec-tools"):
                return True
        elif isinstance(self.node.os, Debian):
            if self.node.os.package_exists("linux-crashdump"):
                return True
        elif isinstance(self.node.os, Suse):
            if (
                self.node.os.package_exists("kexec-tools")
                and self.node.os.package_exists("kdump")
                and self.node.os.package_exists("makedumpfile")
            ):
                return True
        return False

    def _install(self) -> bool:
        if isinstance(self.node.os, Redhat):
            self.node.os.install_packages("kexec-tools")
        elif isinstance(self.node.os, Debian):
            self.node.os.install_packages("linux-crashdump")
        elif isinstance(self.node.os, Suse):
            package_names = ["kexec-tools", "kdump", "makedumpfile"]
            self.node.os.install_packages(package_names)
        return self._check_exists()

    def config_kdump(
        self,
        dump_path: str,
    ) -> None:
        sed = self.node.tools[Sed]
        echo = self.node.tools[Echo]
        if isinstance(self.node.os, Redhat):
            # Edit the /etc/kdump.conf file and specify the dump path
            sed.replace("^path", "path", "#path", "/etc/kdump.conf", sudo=True)
            echo.run(f"path {dump_path} > /etc/kdump.conf", shell=True, sudo=True)
            # When kdump fails to create a core dump at the target location,
            # kdump reboots the system without saving the vmcore
            sed.replace("^default", "default", "#default", "/etc/kdump.conf", sudo=True)
            echo.run("default reboot > /etc/kdump.conf", shell=True, sudo=True)
        elif isinstance(self.node.os, Debian):
            # Don't load a kexec kernel
            sed.replace(
                searched="",
                original="LOAD_KEXEC=true",
                replaced="LOAD_KEXEC=false",
                file="/etc/default/kexec",
                sudo=True,
            )
            # Enable kdump
            sed.replace(
                searched="",
                original="USE_KDUMP=0",
                replaced="USE_KDUMP=1",
                file="/etc/default/kdump-tools",
                sudo=True,
            )

        # Cleaning up any previous crash dump files
        self.node.execute(
            "mkdir -p /var/crash && rm -rf /var/crash/*", shell=True, sudo=True
        )

    def config_crashkernel_memory(
        self,
        crashkernel_memory: str,
    ) -> None:
        # For Ubuntu, /etc/default/grub.d/kdump-tools.cfg which is in kdump-tools package,
        # will override the crashkernel config defined as GRUB_CMDLINE_LINUX_DEFAULT in /etc/default/grub
        # We can keep the default crashkernel config for Ubuntu distro, no need to set crashkernel
        posix_os: Posix = cast(Posix, self.node.os)
        if isinstance(self.node.os, Redhat):
            posix_os.config_kenel_cmdline(
                "crashkernel=auto", f"crashkernel={crashkernel_memory}"
            )
        elif isinstance(self.node.os, Suse):
            posix_os.config_kenel_cmdline(
                '\\"$', f' crashkernel={crashkernel_memory}\\"'
            )

    def enable_kdump_service(self) -> None:
        # For Ubuntu, it has kdump-tools.service, when install kdump-tools package, it will enable by default
        # For Redhat, it has kdump.service which is in kexec-tools package, it will enable by default when install the package?
        systemctl = self.node.tools[Systemctl]
        if isinstance(self.node.os, Redhat) or isinstance(self.node.os, Suse):
            systemctl.enable_service("kdump")
        elif isinstance(self.node.os, Debian):
            systemctl.enable_service("kdump-tools")

    def config_nmi_panic(self) -> None:
        nmi_panic_file = "/proc/sys/kernel/unknown_nmi_panic"
        if self.node.shell.exists(PurePosixPath(nmi_panic_file)):
            result = self.node.execute(
                "sysctl -w kernel.unknown_nmi_panic=1", shell=True, sudo=True
            )
            result.assert_exit_code(
                message="Failed to enable kernel to call panic when it receives a NMI."
            )

    def check_kdump_loaded(self) -> None:
        result = self.node.execute(
            "grep -i crashkernel= /proc/cmdline",
            shell=True,
            sudo=True,
        )
        result.assert_exit_code(message="crashkernel boot parameter is not present")
        assert_that(
            self.node.shell.exists(PurePosixPath(self.kexec_crash))
        ).described_as(
            "Kexec crash is not loaded after reboot. "
            "Please check the configuration settings for kdump and grub."
        ).is_true()

        if isinstance(self.node.os, Debian):
            cat = self.node.tools[Cat]
            result = cat.run(self.kexec_crash)
            assert_that(result.stdout).described_as(
                "kexec_crash_loaded is not 1. "
                "Kexec crash is not loaded after reboot. "
            ).is_equal_to("1")

    def check_kdump_service(self) -> None:
        systemctl = self.node.tools[Systemctl]
        if isinstance(self.node.os, Redhat) or isinstance(self.node.os, Suse):
            systemctl._check_service_running("kdump")
        elif isinstance(self.node.os, Debian):
            systemctl._check_service_running("kdump-tools")
