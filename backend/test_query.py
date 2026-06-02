from sqlalchemy import select, func, or_, case
from sqlalchemy.orm import aliased
from sqlalchemy.dialects import mssql
from models.sql_models import DSCRParameter

investor_id = "test-investor"
rn = func.row_number().over(
    partition_by=(DSCRParameter.category, DSCRParameter.parameter),
    order_by=case(
        (DSCRParameter.investor_id == investor_id, 1),
        else_=0
    ).desc()
).label('rn')

ranked_subq = select(DSCRParameter, rn).where(
    or_(DSCRParameter.investor_id == None, DSCRParameter.investor_id == investor_id)
).subquery()

ParamAlias = aliased(DSCRParameter, ranked_subq)

query = select(ParamAlias).where(
    ranked_subq.c.rn == 1,
    ParamAlias.is_active == True
)

print(query.compile(dialect=mssql.dialect(), compile_kwargs={"literal_binds": True}))
