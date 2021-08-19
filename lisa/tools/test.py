# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from lisa.executable import Tool


class Test(Tool):
    @property
    def command(self) -> str:
        return "test"

    def _check_exists(self) -> bool:
        return True

    def file_exists(self, file_path: str) -> bool:
        # Run `test -e <file_path>`. This commands doesn't
        # return any output and sets the last exit code
        # with the result.
        result = self.run(f"-e {file_path}")
        if result.exit_code == 0:
            return True
        return False
