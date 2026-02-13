from datetime import datetime

import dateutil.parser
from adaptix import Retort, loader
from descanso import RestBuilder
from descanso.response_transformers import ErrorRaiser

retort = Retort(recipe=[
    loader(datetime, dateutil.parser.parse),
])
rest = RestBuilder(
    request_body_dumper=retort,
    response_body_loader=retort,
    query_param_dumper=retort,
    error_raiser=ErrorRaiser(need_body=True),
)
