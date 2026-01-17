class ASRError(Exception):
    pass


class ASRQuotaExceeded(ASRError):
    pass


class ASRTemporaryError(ASRError):
    pass


class ASRFatalError(ASRError):
    pass
