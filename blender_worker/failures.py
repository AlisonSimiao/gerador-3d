"""Versioned failure taxonomy shared by CLI and validation reports."""
from enum import StrEnum

FAILURE_TAXONOMY_VERSION = 1
CANCELLATION_TAXONOMY_VERSION = 2

class FailureCode(StrEnum):
    INPUT_INVALID = "input.invalid"
    ENVIRONMENT_UNAVAILABLE = "environment.unavailable"
    PROCESS_TIMEOUT = "environment.timeout"
    EXECUTION_CANCELLED = "execution.cancelled"
    BUILD_FAILED = "build.failed"
    VALIDATION_FAILED = "validation.failed"
    RENDER_FAILED = "render.failed"
    EXPORT_FAILED = "export.failed"
    REIMPORT_FAILED = "reimport.failed"
    PUBLICATION_FAILED = "publication.failed"

MESSAGES = {
    FailureCode.INPUT_INVALID: "A Spec é inválida.", FailureCode.ENVIRONMENT_UNAVAILABLE: "O ambiente oficial não está disponível.",
    FailureCode.PROCESS_TIMEOUT: "O processo Blender excedeu o timeout.",
    FailureCode.EXECUTION_CANCELLED: "A Tentativa de Geração foi cancelada.",
    FailureCode.BUILD_FAILED: "A construção da IR falhou.", FailureCode.VALIDATION_FAILED: "A validação falhou.",
    FailureCode.RENDER_FAILED: "A renderização falhou.", FailureCode.EXPORT_FAILED: "A exportação falhou.",
    FailureCode.REIMPORT_FAILED: "A reimportação falhou.", FailureCode.PUBLICATION_FAILED: "A publicação falhou.",
}

def structured_error(code: FailureCode, detail: str) -> dict[str, str | int]:
    taxonomy_version = (
        CANCELLATION_TAXONOMY_VERSION
        if code is FailureCode.EXECUTION_CANCELLED
        else FAILURE_TAXONOMY_VERSION
    )
    return {"taxonomy_version": taxonomy_version, "code": code.value, "message": MESSAGES[code], "detail": detail}


#: Stable `stage` vocabulary of the versioned validation report (ADR 0007):
#: the furthest pipeline step an attempt reached. Only a successful attempt
#: that published its Result of Generation reports "published".
REPORT_STAGES: tuple[str, ...] = (
    "input",
    "environment",
    "validation",
    "build",
    "export",
    "reimport",
    "render",
    "publication",
    "published",
)

_CODE_TO_STAGE: dict[FailureCode, str] = {
    FailureCode.INPUT_INVALID: "input",
    FailureCode.ENVIRONMENT_UNAVAILABLE: "environment",
    FailureCode.PROCESS_TIMEOUT: "environment",
    FailureCode.EXECUTION_CANCELLED: "input",
    FailureCode.BUILD_FAILED: "build",
    FailureCode.VALIDATION_FAILED: "validation",
    FailureCode.RENDER_FAILED: "render",
    FailureCode.EXPORT_FAILED: "export",
    FailureCode.REIMPORT_FAILED: "reimport",
    FailureCode.PUBLICATION_FAILED: "publication",
}


def stage_for_code(code: FailureCode) -> str:
    """Map a failure code to the documented report stage it stopped at."""
    return _CODE_TO_STAGE[code]
