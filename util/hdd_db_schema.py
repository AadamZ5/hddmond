import sgqlc.types


hdd_db_schema = sgqlc.types.Schema()



########################################################################
# Scalars and Enumerations
########################################################################
Boolean = sgqlc.types.Boolean

Float = sgqlc.types.Float

Int = sgqlc.types.Int

String = sgqlc.types.String


########################################################################
# Input Objects
########################################################################
class AttributeEntryInput(sgqlc.types.Input):
    __schema__ = hdd_db_schema
    __field_names__ = ('date', 'attributes')
    date = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='date')
    attributes = sgqlc.types.Field(sgqlc.types.list_of('AttributeInput'), graphql_name='attributes')


class AttributeInput(sgqlc.types.Input):
    __schema__ = hdd_db_schema
    __field_names__ = ('number', 'name', 'value', 'flags', 'worst', 'threshold', 'type', 'updated', 'when_failed', 'raw')
    number = sgqlc.types.Field(sgqlc.types.non_null(Int), graphql_name='number')
    name = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='name')
    value = sgqlc.types.Field(sgqlc.types.non_null(Int), graphql_name='value')
    flags = sgqlc.types.Field(Int, graphql_name='flags')
    worst = sgqlc.types.Field(Int, graphql_name='worst')
    threshold = sgqlc.types.Field(Int, graphql_name='threshold')
    type = sgqlc.types.Field(String, graphql_name='type')
    updated = sgqlc.types.Field(String, graphql_name='updated')
    when_failed = sgqlc.types.Field(String, graphql_name='when_failed')
    raw = sgqlc.types.Field(sgqlc.types.non_null(Int), graphql_name='raw')


class HddInput(sgqlc.types.Input):
    __schema__ = hdd_db_schema
    __field_names__ = ('serial', 'model', 'wwn', 'capacity', 'first_seen', 'last_seen', 'decomissioned', 'decomissioned_date')
    serial = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='serial')
    model = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='model')
    wwn = sgqlc.types.Field(String, graphql_name='wwn')
    capacity = sgqlc.types.Field(Float, graphql_name='capacity')
    first_seen = sgqlc.types.Field(String, graphql_name='firstSeen')
    last_seen = sgqlc.types.Field(String, graphql_name='lastSeen')
    decomissioned = sgqlc.types.Field(Boolean, graphql_name='decomissioned')
    decomissioned_date = sgqlc.types.Field(String, graphql_name='decomissionedDate')


class TestInput(sgqlc.types.Input):
    __schema__ = hdd_db_schema
    __field_names__ = ('date', 'passed', 'status', 'power_on_hours')
    date = sgqlc.types.Field(String, graphql_name='date')
    passed = sgqlc.types.Field(sgqlc.types.non_null(Boolean), graphql_name='passed')
    status = sgqlc.types.Field(String, graphql_name='status')
    power_on_hours = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='powerOnHours')



########################################################################
# Output Objects and Interfaces
########################################################################
class Attribute(sgqlc.types.Type):
    __schema__ = hdd_db_schema
    __field_names__ = ('number', 'name', 'value', 'flags', 'worst', 'threshold', 'type', 'updated', 'when_failed', 'raw')
    number = sgqlc.types.Field(sgqlc.types.non_null(Int), graphql_name='number')
    name = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='name')
    value = sgqlc.types.Field(sgqlc.types.non_null(Int), graphql_name='value')
    flags = sgqlc.types.Field(Int, graphql_name='flags')
    worst = sgqlc.types.Field(Int, graphql_name='worst')
    threshold = sgqlc.types.Field(Int, graphql_name='threshold')
    type = sgqlc.types.Field(String, graphql_name='type')
    updated = sgqlc.types.Field(String, graphql_name='updated')
    when_failed = sgqlc.types.Field(String, graphql_name='when_failed')
    raw = sgqlc.types.Field(sgqlc.types.non_null(Int), graphql_name='raw')


class AttributeEntry(sgqlc.types.Type):
    __schema__ = hdd_db_schema
    __field_names__ = ('hdd', 'date', 'attributes')
    hdd = sgqlc.types.Field(sgqlc.types.non_null('Hdd'), graphql_name='hdd')
    date = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='date')
    attributes = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of(Attribute)), graphql_name='attributes')


class Hdd(sgqlc.types.Type):
    __schema__ = hdd_db_schema
    __field_names__ = ('serial', 'model', 'wwn', 'capacity', 'tests', 'attribute_entries', 'first_seen', 'last_seen', 'decomissioned', 'decomissioned_date')
    serial = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='serial')
    model = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='model')
    wwn = sgqlc.types.Field(String, graphql_name='wwn')
    capacity = sgqlc.types.Field(sgqlc.types.non_null(Float), graphql_name='capacity')
    tests = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of('Test')), graphql_name='tests')
    attribute_entries = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of(AttributeEntry)), graphql_name='attributeEntries')
    first_seen = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='firstSeen')
    last_seen = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='lastSeen')
    decomissioned = sgqlc.types.Field(sgqlc.types.non_null(Boolean), graphql_name='decomissioned')
    decomissioned_date = sgqlc.types.Field(String, graphql_name='decomissionedDate')


class Mutation(sgqlc.types.Type):
    __schema__ = hdd_db_schema
    __field_names__ = ('set_hdd', 'add_hdd_attributes', 'add_test')
    set_hdd = sgqlc.types.Field(sgqlc.types.non_null(Hdd), graphql_name='setHdd', args=sgqlc.types.ArgDict((
        ('hdd', sgqlc.types.Arg(HddInput, graphql_name='hdd', default=None)),
))
    )
    add_hdd_attributes = sgqlc.types.Field(AttributeEntry, graphql_name='addHddAttributes', args=sgqlc.types.ArgDict((
        ('serial', sgqlc.types.Arg(sgqlc.types.non_null(String), graphql_name='serial', default=None)),
        ('attribute_entry', sgqlc.types.Arg(AttributeEntryInput, graphql_name='attributeEntry', default=None)),
))
    )
    add_test = sgqlc.types.Field('Test', graphql_name='addTest', args=sgqlc.types.ArgDict((
        ('serial', sgqlc.types.Arg(sgqlc.types.non_null(String), graphql_name='serial', default=None)),
        ('test', sgqlc.types.Arg(sgqlc.types.non_null(TestInput), graphql_name='test', default=None)),
))
    )


class Query(sgqlc.types.Type):
    __schema__ = hdd_db_schema
    __field_names__ = ('hdd', 'hdds')
    hdd = sgqlc.types.Field(Hdd, graphql_name='hdd', args=sgqlc.types.ArgDict((
        ('serial', sgqlc.types.Arg(sgqlc.types.non_null(String), graphql_name='serial', default=None)),
))
    )
    hdds = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of(Hdd)), graphql_name='hdds', args=sgqlc.types.ArgDict((
        ('skip', sgqlc.types.Arg(Int, graphql_name='skip', default=None)),
        ('first', sgqlc.types.Arg(Int, graphql_name='first', default=None)),
))
    )


class Test(sgqlc.types.Type):
    __schema__ = hdd_db_schema
    __field_names__ = ('hdd', 'date', 'passed', 'status', 'power_on_hours')
    hdd = sgqlc.types.Field(sgqlc.types.non_null(Hdd), graphql_name='hdd')
    date = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='date')
    passed = sgqlc.types.Field(sgqlc.types.non_null(Boolean), graphql_name='passed')
    status = sgqlc.types.Field(String, graphql_name='status')
    power_on_hours = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='powerOnHours')



########################################################################
# Unions
########################################################################

########################################################################
# Schema Entry Points
########################################################################
hdd_db_schema.query_type = Query
hdd_db_schema.mutation_type = Mutation
hdd_db_schema.subscription_type = None

