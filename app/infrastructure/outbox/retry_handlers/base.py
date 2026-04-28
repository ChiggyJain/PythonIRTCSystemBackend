
class BaseRetryHandler:

    def __init__(self, outbox_repo=None, security_repo=None):
        self.outbox_repo = outbox_repo
        self.security_repo = security_repo

    async def handle(self, event, **kwargs):
        raise NotImplementedError