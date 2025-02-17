import os

import pandas as pd
from pydantic import Field, model_validator

from synda.config.input.input_properties import InputProperties


class CSVInputProperties(InputProperties):
    path: str
    target_column: str
    separator: str = Field(default=";")

    @model_validator(mode="after")
    def validate_properties(self) -> "CSVInputProperties":
        self._validate_path()
        self._validate_file()
        return self

    def _validate_path(self) -> None:
        if not os.path.isfile(self.path):
            raise ValueError(f"Source file does not exist: {self.path}")

    def _validate_file(self) -> None:
        try:
            df = pd.read_csv(self.path, sep=self.separator)

            if self.target_column not in df.columns:
                raise ValueError(
                    f"Target column '{self.target_column}' not found in CSV file. Available columns: {', '.join(df.columns)}"
                )

        except pd.errors.EmptyDataError:
            raise ValueError(f"CSV file is empty: {self.path}")

        except pd.errors.ParserError:
            raise ValueError(f"Unable to parse CSV file: {self.path}")
