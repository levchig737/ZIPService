from pydantic import BaseModel


class Bugs(BaseModel):
    total: int
    critical: int
    major: int
    minor: int


class CodeSmells(BaseModel):
    total: int
    critical: int
    major: int
    minor: int


class Vulnerabilities(BaseModel):
    total: int
    critical: int
    major: int
    minor: int


class CheckResult(BaseModel):
    overall_coverage: float
    bugs: Bugs
    code_smells: CodeSmells
    vulnerabilities: Vulnerabilities


class SonarQubeResults(BaseModel):
    sonarqube: CheckResult