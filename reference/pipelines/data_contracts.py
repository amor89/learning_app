"""Automated data contract validation at ingestion.

Rules:
- Every delivery passes or fails a contract before it proceeds to silver.
- CRITICAL failures halt the pipeline. WARN proceeds with logging.
- Results are structured records, never narrative text.
"""
from dataclasses import dataclass, field
from typing import List

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, sum


@dataclass
class CheckResult:
    check_name: str
    status: str       # "PASS" | "FAIL" | "WARN"
    expected: str
    actual: str
    severity: str     # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    notes: str = ""


@dataclass
class ContractValidationResult:
    contract_id: str
    tracker_id: str
    wave_id: str
    overall_status: str     # "PASS" | "FAIL"
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def critical_failures(self):
        return [c for c in self.checks if c.status == "FAIL" and c.severity == "CRITICAL"]

    @property
    def pass_rate(self):
        passed = sum(1 for c in self.checks if c.status == "PASS")
        return passed / len(self.checks) if self.checks else 0


class DataContractValidator:

    def __init__(self, contract: dict, df: DataFrame, wave_id: str):
        self.contract = contract
        self.df = df
        self.wave_id = wave_id
        self.results = ContractValidationResult(
            contract_id=contract["contract_id"],
            tracker_id=contract["tracker_id"],
            wave_id=wave_id,
            overall_status="PASS",
        )

    def validate(self) -> ContractValidationResult:
        self._check_row_count()
        self._check_mandatory_columns()
        self._check_weight_nulls()
        self._check_weight_sum()
        self._check_key_uniqueness()
        self._check_categorical_values()
        self._check_distributions()

        if self.results.critical_failures:
            self.results.overall_status = "FAIL"

        return self.results

    def _check_row_count(self):
        actual = self.df.count()
        expected_min = self.contract["row_count_min"]
        expected_max = self.contract["row_count_max"]
        status = "PASS" if expected_min <= actual <= expected_max else "FAIL"
        self.results.checks.append(CheckResult(
            check_name="row_count", status=status,
            expected=f"{expected_min}-{expected_max}", actual=str(actual),
            severity="CRITICAL",
        ))

    def _check_mandatory_columns(self):
        for col_name in self.contract.get("mandatory_columns", []):
            null_count = self.df.filter(col(col_name).isNull()).count()
            status = "PASS" if null_count == 0 else "FAIL"
            self.results.checks.append(CheckResult(
                check_name=f"null_check_{col_name}", status=status,
                expected="0 nulls", actual=f"{null_count} nulls",
                severity="CRITICAL",
            ))

    def _check_weight_nulls(self):
        null_weights = self.df.filter(col("final_weight").isNull()).count()
        max_allowed = self.contract.get("weight_null_max", 0)
        status = "PASS" if null_weights <= max_allowed else "FAIL"
        self.results.checks.append(CheckResult(
            check_name="weight_null_check", status=status,
            expected=f"<= {max_allowed}", actual=str(null_weights),
            severity="CRITICAL",
        ))

    def _check_weight_sum(self):
        actual_sum = self.df.agg(sum("final_weight")).collect()[0][0] or 0
        w_min = self.contract["weight_sum_min"]
        w_max = self.contract["weight_sum_max"]
        status = "PASS" if w_min <= actual_sum <= w_max else "FAIL"
        self.results.checks.append(CheckResult(
            check_name="weight_sum", status=status,
            expected=f"{w_min:,.0f}-{w_max:,.0f}", actual=f"{actual_sum:,.0f}",
            severity="CRITICAL",
        ))

    def _check_key_uniqueness(self):
        for key_col in self.contract.get("key_columns", []):
            total = self.df.count()
            distinct = self.df.select(key_col).distinct().count()
            status = "PASS" if total == distinct else "FAIL"
            self.results.checks.append(CheckResult(
                check_name=f"uniqueness_{key_col}", status=status,
                expected="all unique", actual=f"{total - distinct} duplicates",
                severity="CRITICAL",
            ))

    def _check_categorical_values(self):
        for check in self.contract.get("categorical_checks", []):
            col_name = check["column"]
            allowed = check["allowed_values"]
            unexpected = (
                self.df
                .filter(~col(col_name).isin(allowed) & col(col_name).isNotNull())
                .count()
            )
            status = "PASS" if unexpected == 0 else "WARN"
            self.results.checks.append(CheckResult(
                check_name=f"categorical_{col_name}", status=status,
                expected=f"values in {allowed}", actual=f"{unexpected} unexpected values",
                severity="MEDIUM",
            ))

    def _check_distributions(self):
        total = self.df.count()
        for check in self.contract.get("distribution_checks", []):
            col_name = check["column"]
            value = check["value"]
            pct = self.df.filter(col(col_name) == value).count() / total
            min_pct = check["expected_min_pct"]
            max_pct = check["expected_max_pct"]
            status = "PASS" if min_pct <= pct <= max_pct else "WARN"
            self.results.checks.append(CheckResult(
                check_name=f"distribution_{col_name}_{value}", status=status,
                expected=f"{min_pct:.0%}-{max_pct:.0%}", actual=f"{pct:.1%}",
                severity="MEDIUM",
            ))
