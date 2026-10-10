"""Versioned failure taxonomy shared by CLI and validation reports."""
from enum import StrEnum

FAILURE_TAXONOMY_VERSION = 1

class FailureCode(StrEnum):
    INPUT_INVALID = "input.invalid"
    ENVIRONMENT_UNAVAILABLE = "environment.unavailable"
    BUILD_FAILED = "build.failed"
    VALIDATION_FAILED = "validation.failed"
    RENDER_FAILED = "render.failed"
    EXPORT_FAILED = "export.failed"
    REIMPORT_FAILED = "reimport.failed"
    PUBLICATION_FAILED = "publication.failed"

MESSAGES = {
    FailureCode.INPUT_INVALID: "A Spec é inválida.", FailureCode.ENVIRONMENT_UNAVAILABLE: "O ambiente oficial não está disponível.",
    FailureCode.BUILD_FAILED: "A construção da IR falhou.", FailureCode.VALIDATION_FAILED: "A validação falhou.",
    FailureCode.RENDER_FAILED: "A renderização falhou.", FailureCode.EXPORT_FAILED: "A exportação falhou.",
    FailureCode.REIMPORT_FAILED: "A reimportação falhou.", FailureCode.PUBLICATION_FAILED: "A publicação falhou.",
}

def structured_error(code: FailureCode, detail: str) -> dict[str, str | int]:
    return {"taxonomy_version": FAILURE_TAXONOMY_VERSION, "code": code.value, "message": MESSAGES[code], "detail": detail}
