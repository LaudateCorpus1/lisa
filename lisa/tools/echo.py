# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from typing import Optional, Type

from lisa.executable import Tool


class Echo(Tool):
    @property
    def command(self) -> str:
        return "echo"

    @classmethod
    def _windows_tool(cls) -> Optional[Type[Tool]]:
        return WindowsEcho

    def _check_exists(self) -> bool:
        return True

    def write_to_file(
        self,
        val: str,
        file_path: str,
        sudo: bool = False,
        super_user: bool = False,
    ) -> None:
        # Run `echo <val> > <file_path>`
        output = self.run(
            f"{val} > {file_path}", sudo=sudo, super_user=super_user
        ).stdout
        assert "Permission denied" not in output


class WindowsEcho(Echo):
    @property
    def command(self) -> str:
        return "cmd /c echo"
