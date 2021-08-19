# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from lisa.executable import Tool


class Cat(Tool):
    @property
    def command(self) -> str:
        return "cat"

    def _check_exists(self) -> bool:
        return True

    def read_from_file(self, file_path: str) -> str:
        # Run `cat <file_path>`
        return self.run(file_path).stdout
