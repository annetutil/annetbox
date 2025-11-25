from adaptix import Retort, name_mapping, NameStyle
from descanso import RestBuilder
from descanso.response_transformers import ErrorRaiser

from annetbox.base.models import Status


status_retort = Retort(recipe=[name_mapping(name_style=NameStyle.LOWER_KEBAB)])
status_rest = RestBuilder(
    request_body_dumper=status_retort,
    response_body_loader=status_retort,
    query_param_dumper=status_retort,
    error_raiser=ErrorRaiser(need_body=True),
)


class BaseNetboxStatusClient:
    @status_rest.get("status")
    def status(self) -> Status: ...
