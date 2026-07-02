class ClavisError(Exception):
    status_code = 400


class BoardNotFoundError(ClavisError):
    status_code = 404


class BoardAlreadyConnectedError(ClavisError):
    status_code = 409


class BoardNotConnectedError(ClavisError):
    status_code = 409


class BoardNotPoweredError(ClavisError):
    status_code = 409


class BoardAlreadyAcquiringError(ClavisError):
    status_code = 409


class BoardNotAcquiringError(ClavisError):
    status_code = 409


class InvalidParameterError(ClavisError):
    status_code = 422


class InvalidBoardConfigurationError(ClavisError):
    status_code = 422
