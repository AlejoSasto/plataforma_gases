class AppError(Exception):
    """Error de dominio base."""

    code: str = "app_error"
    status_code: int = 400

    def __init__(self, message: str = "Error de aplicación") -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404

    def __init__(self, message: str = "Recurso no encontrado") -> None:
        super().__init__(message)


class PermissionDeniedError(AppError):
    code = "permission_denied"
    status_code = 403

    def __init__(self, message: str = "Permiso denegado") -> None:
        super().__init__(message)


class UnauthorizedError(AppError):
    code = "unauthorized"
    status_code = 401

    def __init__(self, message: str = "No autenticado") -> None:
        super().__init__(message)


class ValidationError(AppError):
    code = "validation_error"
    status_code = 422

    def __init__(self, message: str = "Datos inválidos") -> None:
        super().__init__(message)
