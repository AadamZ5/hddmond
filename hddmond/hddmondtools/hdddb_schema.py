import sgqlc.types
import sgqlc.types.datetime


hdddb_schema = sgqlc.types.Schema()



########################################################################
# Scalars and Enumerations
########################################################################
Boolean = sgqlc.types.Boolean

DateTime = sgqlc.types.datetime.DateTime

Float = sgqlc.types.Float

Int = sgqlc.types.Int

String = sgqlc.types.String


########################################################################
# Input Objects
########################################################################
class AttributeInput(sgqlc.types.Input):
    __schema__ = hdddb_schema
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
    __schema__ = hdddb_schema
    __field_names__ = ('serial', 'model', 'wwn', 'capacity', 'first_seen', 'last_seen', 'decommissioned', 'decommissioned_date', 'tasks_completed', 'notes')
    serial = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='serial')
    model = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='model')
    wwn = sgqlc.types.Field(String, graphql_name='wwn')
    capacity = sgqlc.types.Field(Float, graphql_name='capacity')
    first_seen = sgqlc.types.Field(String, graphql_name='firstSeen')
    last_seen = sgqlc.types.Field(String, graphql_name='lastSeen')
    decommissioned = sgqlc.types.Field(Boolean, graphql_name='decommissioned')
    decommissioned_date = sgqlc.types.Field(String, graphql_name='decommissionedDate')
    tasks_completed = sgqlc.types.Field(sgqlc.types.list_of('TaskInput'), graphql_name='tasks_completed')
    notes = sgqlc.types.Field(sgqlc.types.list_of('NoteInput'), graphql_name='notes')


class NoteInput(sgqlc.types.Input):
    __schema__ = hdddb_schema
    __field_names__ = ('timestamp', 'note', 'note_taker', 'tags')
    timestamp = sgqlc.types.Field(String, graphql_name='timestamp')
    note = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='note')
    note_taker = sgqlc.types.Field(String, graphql_name='note_taker')
    tags = sgqlc.types.Field(sgqlc.types.list_of(String), graphql_name='tags')


class SmartCaptureInput(sgqlc.types.Input):
    __schema__ = hdddb_schema
    __field_names__ = ('date', 'firmware', 'attributes')
    date = sgqlc.types.Field(String, graphql_name='date')
    firmware = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='firmware')
    attributes = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of(AttributeInput)), graphql_name='attributes')


class TaskInput(sgqlc.types.Input):
    __schema__ = hdddb_schema
    __field_names__ = ('name', 'notes', 'return_code')
    name = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='name')
    notes = sgqlc.types.Field(sgqlc.types.list_of(NoteInput), graphql_name='notes')
    return_code = sgqlc.types.Field(Int, graphql_name='return_code')


class TestInput(sgqlc.types.Input):
    __schema__ = hdddb_schema
    __field_names__ = ('date', 'passed', 'status', 'power_on_hours')
    date = sgqlc.types.Field(DateTime, graphql_name='date')
    passed = sgqlc.types.Field(sgqlc.types.non_null(Boolean), graphql_name='passed')
    status = sgqlc.types.Field(String, graphql_name='status')
    power_on_hours = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='powerOnHours')



########################################################################
# Output Objects and Interfaces
########################################################################
class Attribute(sgqlc.types.Type):
    __schema__ = hdddb_schema
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


class Hdd(sgqlc.types.Type):
    __schema__ = hdddb_schema
    __field_names__ = ('serial', 'model', 'wwn', 'capacity', 'tests', 'seen', 'tasks_completed', 'smart_captures', 'first_seen', 'last_seen', 'decommissioned', 'decommissioned_date', 'notes')
    serial = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='serial')
    model = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='model')
    wwn = sgqlc.types.Field(String, graphql_name='wwn')
    capacity = sgqlc.types.Field(sgqlc.types.non_null(Float), graphql_name='capacity')
    tests = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of('Test')), graphql_name='tests')
    seen = sgqlc.types.Field(sgqlc.types.non_null(Int), graphql_name='seen')
    tasks_completed = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of('Task')), graphql_name='tasks_completed')
    smart_captures = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of('SmartCapture')), graphql_name='smart_captures')
    first_seen = sgqlc.types.Field(sgqlc.types.non_null(DateTime), graphql_name='firstSeen')
    last_seen = sgqlc.types.Field(sgqlc.types.non_null(DateTime), graphql_name='lastSeen')
    decommissioned = sgqlc.types.Field(sgqlc.types.non_null(Boolean), graphql_name='decommissioned')
    decommissioned_date = sgqlc.types.Field(DateTime, graphql_name='decommissionedDate')
    notes = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of('Note')), graphql_name='notes')


class Mutation(sgqlc.types.Type):
    __schema__ = hdddb_schema
    __field_names__ = ('see_hdd', 'set_hdd', 'add_smart_capture', 'add_test', 'add_task', 'decommission')
    see_hdd = sgqlc.types.Field(sgqlc.types.non_null(Hdd), graphql_name='seeHdd', args=sgqlc.types.ArgDict((
        ('serial', sgqlc.types.Arg(sgqlc.types.non_null(String), graphql_name='serial', default=None)),
))
    )
    set_hdd = sgqlc.types.Field(sgqlc.types.non_null(Hdd), graphql_name='setHdd', args=sgqlc.types.ArgDict((
        ('hdd', sgqlc.types.Arg(sgqlc.types.non_null(HddInput), graphql_name='hdd', default=None)),
))
    )
    add_smart_capture = sgqlc.types.Field('SmartCapture', graphql_name='addSmartCapture', args=sgqlc.types.ArgDict((
        ('serial', sgqlc.types.Arg(sgqlc.types.non_null(String), graphql_name='serial', default=None)),
        ('smart_capture', sgqlc.types.Arg(SmartCaptureInput, graphql_name='smartCapture', default=None)),
))
    )
    add_test = sgqlc.types.Field('Test', graphql_name='addTest', args=sgqlc.types.ArgDict((
        ('serial', sgqlc.types.Arg(sgqlc.types.non_null(String), graphql_name='serial', default=None)),
        ('test', sgqlc.types.Arg(sgqlc.types.non_null(TestInput), graphql_name='test', default=None)),
))
    )
    add_task = sgqlc.types.Field('Task', graphql_name='addTask', args=sgqlc.types.ArgDict((
        ('serial', sgqlc.types.Arg(sgqlc.types.non_null(String), graphql_name='serial', default=None)),
        ('task', sgqlc.types.Arg(sgqlc.types.non_null(TaskInput), graphql_name='task', default=None)),
))
    )
    decommission = sgqlc.types.Field(Hdd, graphql_name='decommission', args=sgqlc.types.ArgDict((
        ('serial', sgqlc.types.Arg(sgqlc.types.non_null(String), graphql_name='serial', default=None)),
        ('decommission', sgqlc.types.Arg(Boolean, graphql_name='decommission', default=None)),
))
    )


class Note(sgqlc.types.Type):
    __schema__ = hdddb_schema
    __field_names__ = ('timestamp', 'note', 'note_taker', 'tags')
    timestamp = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='timestamp')
    note = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='note')
    note_taker = sgqlc.types.Field(String, graphql_name='note_taker')
    tags = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of(String)), graphql_name='tags')


class Query(sgqlc.types.Type):
    __schema__ = hdddb_schema
    __field_names__ = ('hdd', 'hdds', 'tasks')
    hdd = sgqlc.types.Field(Hdd, graphql_name='hdd', args=sgqlc.types.ArgDict((
        ('serial', sgqlc.types.Arg(sgqlc.types.non_null(String), graphql_name='serial', default=None)),
))
    )
    hdds = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of(Hdd)), graphql_name='hdds', args=sgqlc.types.ArgDict((
        ('skip', sgqlc.types.Arg(Int, graphql_name='skip', default=None)),
        ('first', sgqlc.types.Arg(Int, graphql_name='first', default=None)),
))
    )
    tasks = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of('Task')), graphql_name='tasks', args=sgqlc.types.ArgDict((
        ('skip', sgqlc.types.Arg(Int, graphql_name='skip', default=None)),
        ('first', sgqlc.types.Arg(Int, graphql_name='first', default=None)),
))
    )


class SmartCapture(sgqlc.types.Type):
    __schema__ = hdddb_schema
    __field_names__ = ('hdd', 'date', 'firmware', 'attributes')
    hdd = sgqlc.types.Field(sgqlc.types.non_null(Hdd), graphql_name='hdd')
    date = sgqlc.types.Field(sgqlc.types.non_null(DateTime), graphql_name='date')
    firmware = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='firmware')
    attributes = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of(Attribute)), graphql_name='attributes')


class Task(sgqlc.types.Type):
    __schema__ = hdddb_schema
    __field_names__ = ('hdd', 'name', 'notes', 'return_code')
    hdd = sgqlc.types.Field(sgqlc.types.non_null(Hdd), graphql_name='hdd')
    name = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='name')
    notes = sgqlc.types.Field(sgqlc.types.non_null(sgqlc.types.list_of(Note)), graphql_name='notes')
    return_code = sgqlc.types.Field(Int, graphql_name='return_code')


class Test(sgqlc.types.Type):
    __schema__ = hdddb_schema
    __field_names__ = ('hdd', 'date', 'passed', 'status', 'power_on_hours')
    hdd = sgqlc.types.Field(sgqlc.types.non_null(Hdd), graphql_name='hdd')
    date = sgqlc.types.Field(sgqlc.types.non_null(DateTime), graphql_name='date')
    passed = sgqlc.types.Field(sgqlc.types.non_null(Boolean), graphql_name='passed')
    status = sgqlc.types.Field(String, graphql_name='status')
    power_on_hours = sgqlc.types.Field(sgqlc.types.non_null(String), graphql_name='powerOnHours')



########################################################################
# Unions
########################################################################

########################################################################
# Schema Entry Points
########################################################################
hdddb_schema.query_type = Query
hdddb_schema.mutation_type = Mutation
hdddb_schema.subscription_type = None

