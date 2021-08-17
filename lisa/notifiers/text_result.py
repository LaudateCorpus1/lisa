# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from typing import Any, List, Type

from lisa import notifier, schema
from lisa.testsuite import TestResultMessage
from lisa.util import constants


class TextResult(notifier.Notifier):
    """
    Creating log notifier to dump text formatted results for easier
    view in editing mode. The original log is complete but too long to
    check only the summary.
    """

    @classmethod
    def type_name(cls) -> str:
        return constants.NOTIFIER_TEXT_RESULT

    @classmethod
    def type_schema(cls) -> Type[schema.TypedSchema]:
        return schema.Notifier

    def _received_message(self, message: TestResultMessage) -> None:
        if message.is_completed:
            self.result_file.write(f"{message.status.name:<8} {message.message}")

    def _subscribed_message_type(self) -> List[Type[notifier.MessageBase]]:
        return [TestResultMessage]

    def _initialize(self, *args: Any, **kwargs: Any) -> None:
        self.result_file = open(
            "{constants.RUN_LOCAL_PATH}/lisa-{constants.RUN_ID}-result.txt",
            "w"
        )

    def finalize(self) -> None:
        self.result_file.close()
