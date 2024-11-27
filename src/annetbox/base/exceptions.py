from dataclass_rest.exceptions import ClientError, ServerError


class ErrorWithBody:
    body = None

    def __str__(self):
        if self.body:
            ret = ["HttpResponse error:"]

            if hasattr(self, "status_code"):
                ret.append(f"status_code={self.status_code};")

            ret.append(f"body={self.body};")

            return " ".join(ret)

        return super().__str__()


class ClientWithBodyError(ErrorWithBody, ClientError):
    def __init__(self, *args, body=None, **kwargs):
        self.body = body
        super().__init__(*args, **kwargs)


class ServerWithBodyError(ErrorWithBody, ServerError):
    def __init__(self, *args, body=None, **kwargs):
        self.body = body
        super().__init__(*args, **kwargs)
